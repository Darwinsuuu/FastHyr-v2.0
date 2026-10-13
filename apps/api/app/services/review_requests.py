"""Human review requests (ASMT-008, ADR-015, FR-COMP-03, SCREEN_SPECS.md S-03 and A-03).

Every rejection email carries a "Request a human review" link (`review_links`, SCREEN-003 and
ASMT-007). The candidate opens it without signing in (the token is the key, and the page shows
only the company and job title) and may add a message. The request marks the application
Review requested, emails the pipeline's owner (or the Admins when it has none) and acknowledges
it to the candidate with the workspace's `review_received` email.

A member who may decide candidates resolves it with a note only the team sees:
- **Uphold**: the decision stands. No email: the rejection already went out.
- **Override** an automated decision: a résumé that didn't pass goes to Invited with a new
  interview link and the invitation; an interview below the pass mark goes to Ready for review.
A person's own rejection (stage `rejected`) is final, so a request about it can only be upheld.
Either way the overlay clears, and each request and resolution goes to `audit_log` (never the
message or note, which may describe the person).
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.context import RequestContext
from app.core.errors import (
    NotFoundError,
    OverrideNotAllowedError,
    ReviewLinkClosedError,
    ReviewLinkNotFoundError,
    ReviewRequestResolvedError,
)
from app.core.tokens import hash_token
from app.emails import system
from app.emails.defaults import TemplateKey
from app.jobs.queue import JobQueue
from app.models import Application, EmailMessage, HumanReviewRequest, Workspace
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.company_profiles import BrandingRow
from app.repositories.review_requests import (
    ReviewLinkRow,
    ReviewRequestRepository,
    ReviewRequestRow,
    review_link_of,
)
from app.repositories.screening import ScreeningRepository
from app.schemas.interviews import InterviewCompany
from app.schemas.review_requests import (
    ResolvedReviewRequest,
    ResolveReviewRequest,
    ReviewLink,
    ReviewLinkState,
    ReviewRequestCreate,
    ReviewRequestItem,
    ReviewRequestList,
)
from app.services import candidate_emails, emails, interview_lifecycle, interviews
from app.services.applications import move_stage
from app.services.company_profile import branding_url

logger = logging.getLogger("app.review_requests")

# Tokens are `secrets.token_urlsafe(32)`; anything far longer is not a link of ours.
MAX_TOKEN_LENGTH = 128
REJECTED = "rejected"
# The stages in which each kind of decision still stands. `rejected` is a person's decision
# (ASMT-007), made before the interview (résumé link) or after it (interview link).
STANDING = {
    "resume": frozenset({"resume_not_match", REJECTED}),
    "interview": frozenset({"did_not_pass", REJECTED}),
}
# Where an override takes an automated decision (WORKFLOW.md §3).
OVERRIDES = {"resume_not_match": "invited", "did_not_pass": "ready_for_review"}
LIST_LIMIT = 100


# --- The candidate's side: /review-request/{token} -----------------------------------------


def link_state(row: ReviewLinkRow, now: datetime) -> ReviewLinkState:
    link = row.link
    if row.candidate_deleted_at is not None:
        return "unavailable"
    if link.requested_at is not None:
        return "requested"
    if now >= link.expires_at:
        return "expired"
    if row.stage not in STANDING.get(link.decision_type, frozenset()):
        # Looked at again already, or the candidate moved on: nothing left to review.
        return "unavailable"
    return "open"


async def review_link(
    session: AsyncSession, token: str, *, api_url: str, now: datetime | None = None
) -> ReviewLink:
    """The page's state for whoever holds the link. `404 review_link_not_found` for unknown
    tokens."""
    row = await _link_row(session, token)
    return _page(row, link_state(row, now or datetime.now(UTC)), api_url)


async def request_review(
    session: AsyncSession,
    settings: Settings,
    queue: JobQueue,
    token: str,
    body: ReviewRequestCreate,
    *,
    now: datetime | None = None,
) -> ReviewLink:
    """Creates the request, once: a repeat (a double click, a reload) gets `requested` back.
    `409 review_link_closed` once the link expired or the decision no longer stands. Commits,
    then sends the candidate's acknowledgement and the owner's notification."""
    now = now or datetime.now(UTC)
    row = await _link_row(session, token, lock=True)
    state = link_state(row, now)
    # Built now: a rollback expires the rows it reads from.
    requested = _page(row, "requested", settings.api_url)
    if state == "requested":
        await session.rollback()
        return requested
    if state != "open":
        await session.rollback()
        raise ReviewLinkClosedError()

    link = row.link
    workspace_id = link.workspace_id
    application = await ApplicationRepository(session, workspace_id).get_scoped(
        link.application_id, department_ids=None, lock=True
    )
    if application is None:
        raise ReviewLinkClosedError()
    request = HumanReviewRequest(
        workspace_id=workspace_id,
        application_id=application.id,
        decision_type=link.decision_type,
        review_link_id=link.id,
        candidate_message=body.message or None,
    )
    ReviewRequestRepository(session, workspace_id).add(request)
    link.requested_at = now
    application.review_requested = True
    try:
        await session.flush()
    except IntegrityError:
        # Already an open request on this application (through its other link): one at a time.
        await session.rollback()
        return requested

    messages = [
        (
            await candidate_emails.schedule(
                session,
                settings,
                workspace_id=workspace_id,
                application_id=application.id,
                key=TemplateKey.REVIEW_RECEIVED,
                at=now,
                dedupe_key=f"{TemplateKey.REVIEW_RECEIVED.value}:{request.id}",
            )
        ).message
    ]
    messages += await _notify_team(session, settings, row, application, request)
    AuditRepository(session, workspace_id).record(
        actor_id=None,
        action="review_request.created",
        entity_type="human_review_request",
        entity_id=request.id,
        data={
            "application_id": str(application.id),
            "decision_type": request.decision_type,
            "stage": application.stage,
        },
    )
    await session.commit()
    for message in messages:
        await emails.enqueue(queue, message)
    logger.info("review requested: application %s (%s)", application.id, request.decision_type)
    return requested


async def _link_row(session: AsyncSession, token: str, *, lock: bool = False) -> ReviewLinkRow:
    if not token or len(token) > MAX_TOKEN_LENGTH:
        raise ReviewLinkNotFoundError()
    row = await review_link_of(session, hash_token(token), lock=lock)
    if row is None:
        raise ReviewLinkNotFoundError()
    return row


def _page(row: ReviewLinkRow, state: ReviewLinkState, api_url: str) -> ReviewLink:
    workspace_id = row.link.workspace_id
    branding = BrandingRow(row.company_name, row.logo_path, None, row.profile_updated_at)
    return ReviewLink(
        state=state,
        company=InterviewCompany(
            name=row.company_name,
            logo_url=(
                branding_url(api_url, workspace_id, branding, "logo") if row.logo_path else None
            ),
            website=row.website,
            careers_url=row.careers_url,
        ),
        job_title=row.job_title or "",
    )


async def _notify_team(
    session: AsyncSession,
    settings: Settings,
    row: ReviewLinkRow,
    application: Application,
    request: HumanReviewRequest,
) -> list[EmailMessage]:
    workspace_id = application.workspace_id
    repo = ReviewRequestRepository(session, workspace_id)
    candidate = await ScreeningRepository(session, workspace_id).candidate_name(
        application.candidate_id
    )
    workspace_name = await session.scalar(
        select(Workspace.name).where(Workspace.id == workspace_id)
    )
    profile_url = (
        f"{settings.app_url.rstrip('/')}/candidates/{application.candidate_id}"
        f"?application={application.id}"
    )
    email = system.review_request(
        site_url=settings.site_url,
        profile_url=profile_url,
        workspace_name=workspace_name or "",
        candidate_name=candidate or "A candidate",
        job_title=row.job_title or "",
        decision_type=request.decision_type,
        by_person=application.stage == REJECTED,
    )
    return [
        emails.queue_email(
            session,
            workspace_id=workspace_id,
            template_key="review_request",
            to_email=recipient.email,
            from_name=system.FROM_FASTHYR,
            email=email,
        )
        for recipient in await repo.recipients(application.pipeline_id)
    ]


# --- The team's side ----------------------------------------------------------------------


def can_override(stage: str) -> bool:
    return stage in OVERRIDES


async def list_requests(
    session: AsyncSession, ctx: RequestContext, *, status: str | None
) -> ReviewRequestList:
    rows, total = await ReviewRequestRepository(session, ctx.workspace_id).page(
        status=status, department_ids=_departments(ctx), limit=LIST_LIMIT
    )
    return ReviewRequestList(items=[_item(row) for row in rows], total=total)


@dataclass
class _Resolved:
    emails: list[EmailMessage] = field(default_factory=list)


async def resolve(
    session: AsyncSession,
    settings: Settings,
    queue: JobQueue,
    ctx: RequestContext,
    request_id: uuid.UUID,
    body: ResolveReviewRequest,
    *,
    now: datetime | None = None,
) -> ResolvedReviewRequest:
    """Upholds or overrides the request; commits, then sends the email an override brings.
    `404` outside the caller's workspace or departments; `409 review_request_resolved` once
    resolved; `409 override_not_allowed` for a person's rejection or a stage that moved on."""
    now = now or datetime.now(UTC)
    repo = ReviewRequestRepository(session, ctx.workspace_id)
    row = await repo.get_scoped(request_id, department_ids=_departments(ctx), lock=True)
    if row is None:
        raise NotFoundError()
    request = row.request
    if request.status != "open":
        raise ReviewRequestResolvedError()
    application = await ApplicationRepository(session, ctx.workspace_id).get_scoped(
        request.application_id, department_ids=None, lock=True
    )
    if application is None:
        raise NotFoundError()

    previous = application.stage
    resolved = _Resolved()
    if body.outcome == "override":
        resolved.emails = await _override(session, settings, application, request, now)
    request.status = "overridden" if body.outcome == "override" else "upheld"
    request.resolved_by = ctx.member_id
    request.resolved_at = now
    request.resolution_note = body.note
    application.review_requested = False
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action="review_request.resolved",
        entity_type="human_review_request",
        entity_id=request.id,
        data={
            "application_id": str(application.id),
            "decision_type": request.decision_type,
            "outcome": request.status,
            "from": previous,
            "to": application.stage,
        },
    )
    result = ResolvedReviewRequest(
        id=request.id,
        status="overridden" if request.status == "overridden" else "upheld",
        application_id=application.id,
        stage=application.stage,
        emailed=bool(resolved.emails),
    )
    await session.commit()
    for message in resolved.emails:
        await emails.enqueue(queue, message)
    logger.info("review request %s %s", request.id, request.status)
    return result


async def _override(
    session: AsyncSession,
    settings: Settings,
    application: Application,
    request: HumanReviewRequest,
    now: datetime,
) -> list[EmailMessage]:
    stage = OVERRIDES.get(application.stage)
    if stage is None or application.stage not in STANDING[request.decision_type]:
        raise OverrideNotAllowedError()
    await move_stage(session, application.workspace_id, application.id, stage, now=now)
    if stage != "invited":
        # Back to Ready for review: the team decides from there (ASMT-007); no email yet.
        return []
    # A résumé that didn't pass has no interview plan: the plain skills plan, then the link and
    # the invitation, as for a passed screen (SCREEN-003, INTV-007).
    await interviews.add_fallback_plan(session, application)
    pipeline = await ScreeningRepository(session, application.workspace_id).pipeline(
        application.pipeline_id
    )
    issued = await interview_lifecycle.issue_link(session, settings, application, pipeline, now)
    return issued.emails


def _departments(ctx: RequestContext) -> list[uuid.UUID] | None:
    return None if ctx.sees_all_departments else list(ctx.department_ids)


def _item(row: ReviewRequestRow) -> ReviewRequestItem:
    request = row.request
    return ReviewRequestItem(
        id=request.id,
        application_id=request.application_id,
        candidate_id=row.candidate_id,
        candidate_name=row.candidate_name,
        pipeline_id=row.pipeline_id,
        pipeline_title=row.pipeline_title or "",
        decision_type="interview" if request.decision_type == "interview" else "resume",
        by_person=row.stage == REJECTED,
        status=request.status,
        created_at=request.created_at,
    )
