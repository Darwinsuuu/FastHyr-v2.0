"""Advancing and rejecting a candidate (ASMT-007, ADR-017, FR-PIPE-13, WORKFLOW.md §3).

A person makes every hiring decision. "Advance to next round" moves a candidate who is Ready for
review, with every integrity flag reviewed, to Advanced and sends the "Moving to the next stage"
email unless the member unticks it. "Reject candidate" needs a reason that only the team sees and
sends the rejection email unless unticked: `reject_interview` after a finished interview,
otherwise `reject_resume` (NOTIFICATIONS.md §1), with the review line every rejection carries
(ADR-015). Both are final. Moving the stage cancels the application's waiting emails (an
automatic rejection, a reminder), so the candidate only hears the team's decision. Each decision
goes to `audit_log`, without the note or reason, which may describe the person.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.realtime import RealtimeProvider
from app.core.config import Settings
from app.core.context import RequestContext
from app.core.errors import DecisionNotAllowedError, FlagsToReviewError, NotFoundError
from app.core.tokens import new_token
from app.emails.defaults import TemplateKey
from app.jobs.queue import JobQueue
from app.models import Application, EmailMessage, Interview, ReviewLink
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.interviews import InterviewAttemptRepository, InterviewRepository
from app.repositories.review_links import ReviewLinkRepository
from app.schemas.decisions import AdvanceRequest, ApplicationDecision, RejectRequest
from app.services import candidate_emails, emails, interview_sessions, post_screen
from app.services.applications import move_stage

logger = logging.getLogger("app.decisions")

ADVANCED = "advanced"
REJECTED = "rejected"
# WORKFLOW.md §3: a TA rejects before a decision is final; an unreadable résumé (still
# processing, never rejected automatically) can be rejected by a person too (SCREEN-004).
REJECTABLE = frozenset({"invited", "interview_in_progress", "ready_for_review"})
UNREADABLE = "unreadable"


@dataclass
class _Decided:
    emails: list[EmailMessage] = field(default_factory=list)
    hang_up: list[interview_sessions.Ended] = field(default_factory=list)


async def advance(
    session: AsyncSession,
    settings: Settings,
    queue: JobQueue,
    ctx: RequestContext,
    application_id: uuid.UUID,
    body: AdvanceRequest,
    *,
    now: datetime | None = None,
) -> ApplicationDecision:
    """Moves a Ready for review candidate to Advanced; commits, then sends the email. `404`
    outside the caller's workspace or departments; `409 flags_to_review` while integrity flags
    are open; `409 decision_not_allowed` from any other stage."""
    now = now or datetime.now(UTC)
    application = await _lock(session, ctx, application_id)
    if application.stage != "ready_for_review":
        raise DecisionNotAllowedError()
    if application.has_open_flags:
        raise FlagsToReviewError()

    previous = application.stage
    application.advanced_note = body.note or None
    application.advanced_by = ctx.member_id
    application.advanced_at = now
    await move_stage(session, ctx.workspace_id, application.id, ADVANCED, now=now)
    decided = _Decided()
    if body.send_email:
        # After the move: the email is written for the Advanced stage, so nothing cancels it.
        scheduled = await candidate_emails.schedule(
            session,
            settings,
            workspace_id=ctx.workspace_id,
            application_id=application.id,
            key=TemplateKey.NEXT_STAGE,
            at=now,
        )
        decided.emails.append(scheduled.message)
    _audit(session, ctx, application, "application.advanced", previous, bool(decided.emails))
    return await _commit(session, queue, None, application, ADVANCED, decided)


async def reject(
    session: AsyncSession,
    settings: Settings,
    queue: JobQueue,
    realtime: RealtimeProvider,
    ctx: RequestContext,
    application_id: uuid.UUID,
    body: RejectRequest,
    *,
    now: datetime | None = None,
) -> ApplicationDecision:
    """Moves the candidate to Rejected with the reason; a running interview is ended. Commits,
    then sends the email and hangs up the call. `404` outside the caller's workspace or
    departments; `409 decision_not_allowed` once decided or from a stage with an automatic
    outcome."""
    now = now or datetime.now(UTC)
    application = await _visible(session, ctx, application_id)
    interview = await InterviewRepository(session, ctx.workspace_id).live_of(application.id)
    decided = _Decided()
    if interview is not None:
        # The interview first, then the application: the order a starting attempt takes them in.
        interview = await InterviewAttemptRepository(session, ctx.workspace_id).lock_interview(
            interview.id
        )
    application = await _lock(session, ctx, application_id)
    if not _rejectable(application):
        raise DecisionNotAllowedError()

    if interview is not None:
        # A call still running ends now; the link then says the step is closed (INTV-002).
        decided.hang_up.append(
            await interview_sessions.end_running(session, interview, "disconnect", now)
        )
    previous = application.stage
    application.rejected_reason = body.reason
    application.rejected_by = ctx.member_id
    application.rejected_at = now
    await move_stage(session, ctx.workspace_id, application.id, REJECTED, now=now)
    if body.send_email:
        decided.emails.append(
            await _rejection_email(session, settings, application, interview, now)
        )
    _audit(session, ctx, application, "application.rejected", previous, bool(decided.emails))
    return await _commit(session, queue, realtime, application, REJECTED, decided)


def _rejectable(application: Application) -> bool:
    if application.stage in REJECTABLE:
        return True
    return application.stage == "processing_resume" and application.resume_status == UNREADABLE


async def _rejection_email(
    session: AsyncSession,
    settings: Settings,
    application: Application,
    interview: Interview | None,
    now: datetime,
) -> EmailMessage:
    """The rejection, sent now, with a "Request a human review" link like every rejection: after
    a finished interview it's about the interview, before that about the résumé."""
    workspace_id = application.workspace_id
    interviewed = interview is not None and interview.status == "completed"
    decision_type = "interview" if interviewed else "resume"
    token, token_hash = new_token()
    expires_at = now + timedelta(days=post_screen.REVIEW_LINK_DAYS)
    links = ReviewLinkRepository(session, workspace_id)
    existing = await links.link_of(application.id, decision_type)
    if existing is not None:
        # One link per decision type: an earlier one gets the new token, so this email's works.
        existing.token_hash = token_hash
        existing.expires_at = expires_at
        # A new decision: the candidate may ask for this one to be reviewed too (ASMT-008).
        existing.requested_at = None
    else:
        links.add(
            ReviewLink(
                workspace_id=workspace_id,
                application_id=application.id,
                decision_type=decision_type,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
    scheduled = await candidate_emails.schedule(
        session,
        settings,
        workspace_id=workspace_id,
        application_id=application.id,
        key=TemplateKey.REJECT_INTERVIEW if interviewed else TemplateKey.REJECT_RESUME,
        at=now,
        values={"Review.link": post_screen.review_link(settings, token)},
    )
    return scheduled.message


async def _visible(
    session: AsyncSession, ctx: RequestContext, application_id: uuid.UUID
) -> Application:
    application = await ApplicationRepository(session, ctx.workspace_id).get_scoped(
        application_id, department_ids=None if ctx.sees_all_departments else ctx.department_ids
    )
    if application is None:
        raise NotFoundError()
    return application


async def _lock(
    session: AsyncSession, ctx: RequestContext, application_id: uuid.UUID
) -> Application:
    application = await ApplicationRepository(session, ctx.workspace_id).get_scoped(
        application_id,
        department_ids=None if ctx.sees_all_departments else ctx.department_ids,
        lock=True,
    )
    if application is None:
        raise NotFoundError()
    return application


def _audit(
    session: AsyncSession,
    ctx: RequestContext,
    application: Application,
    action: str,
    previous: str,
    emailed: bool,
) -> None:
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action=action,
        entity_type="application",
        entity_id=application.id,
        data={"from": previous, "emailed": emailed},
    )


async def _commit(
    session: AsyncSession,
    queue: JobQueue,
    realtime: RealtimeProvider | None,
    application: Application,
    stage: str,
    decided: _Decided,
) -> ApplicationDecision:
    await session.commit()
    for message in decided.emails:
        await emails.enqueue(queue, message)
    if realtime is not None:
        for ended in decided.hang_up:
            await interview_sessions.hang_up(realtime, ended)
    logger.info("application %s %s", application.id, stage)
    return ApplicationDecision(
        id=application.id,
        stage=ADVANCED if stage == ADVANCED else REJECTED,
        emailed=bool(decided.emails),
    )
