"""What happens after the résumé screen (SCREEN-003, WORKFLOW.md §3, FR-SCREEN-05).

`act()` moves a screened application out of `processing_resume`:
- a failed screen goes to `resume_not_match`, and, when the pipeline's "Email candidates whose
  résumé isn't a match" is on, `reject_resume` is scheduled 2 business days after the screen
  with a "Request a human review" link (ADR-015);
- a passed screen waits for its interview plan (INTV-001), then goes to `invited` with a new
  interview link and the `interview_invitation` email, sent now.

It runs after every screen and every plan, from the jobs and the sweeper, and does nothing for
an application that isn't screened yet, is unreadable, or has already moved on. The application
row is locked first, so two runs take turns and the second finds nothing to do.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_days import end_of_day_after, zone_of
from app.core.config import Settings
from app.core.tokens import new_token
from app.emails.defaults import TemplateKey
from app.jobs.queue import JobQueue
from app.models import Application, EmailMessage, Interview, ResumeAssessment, ReviewLink
from app.repositories import screening as screening_repo
from app.repositories.company_profiles import workspace_timezone
from app.repositories.interviews import InterviewPlanRepository, InterviewRepository
from app.repositories.review_links import ReviewLinkRepository
from app.repositories.screening import DONE, ScreeningRepository
from app.services import candidate_emails, emails

logger = logging.getLogger("app.screening")

PROCESSING_RESUME = "processing_resume"
RESUME_NOT_MATCH = "resume_not_match"
INVITED = "invited"

# NOTIFICATIONS.md §1: the résumé rejection goes out 2 business days after the screen.
REJECTION_DELAY_BUSINESS_DAYS = 2
# ADR-015 / SCREEN_SPECS.md S-03: a review link works for 30 days after its email.
REVIEW_LINK_DAYS = 30


class Outcome(StrEnum):
    SKIPPED = "skipped"  # not screened, unreadable, or already moved on
    WAITING = "waiting"  # passed, waiting for its interview plan
    INVITED = "invited"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Acted:
    outcome: Outcome
    # The email to `emails.enqueue()` after the commit; None when there is none.
    email: EmailMessage | None = None


def interview_link(settings: Settings, token: str) -> str:
    return f"{settings.site_url}/interview/{token}"


def review_link(settings: Settings, token: str) -> str:
    return f"{settings.site_url}/review-request/{token}"


async def act(
    session: AsyncSession,
    settings: Settings,
    application_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Acted:
    """Invites or rejects the screened application, once. Runs in the caller's transaction:
    the caller commits on INVITED or REJECTED (and rolls back otherwise, to release the row
    lock), then calls `emails.enqueue()` with `email`."""
    now = now or datetime.now(UTC)
    application = await screening_repo.application_for_update(session, application_id)
    if (
        application is None
        or application.stage != PROCESSING_RESUME
        or application.resume_status != DONE
    ):
        return Acted(Outcome.SKIPPED)
    assessment = await ScreeningRepository(session, application.workspace_id).assessment_of(
        application.id
    )
    if assessment is None:
        return Acted(Outcome.SKIPPED)
    if not assessment.passed:
        return await _reject(session, settings, application, assessment, now)
    plan = await InterviewPlanRepository(session, application.workspace_id).plan_of(application.id)
    if plan is None:
        return Acted(Outcome.WAITING)
    return await _invite(session, settings, application, now)


async def act_and_commit(
    session: AsyncSession,
    settings: Settings,
    queue: JobQueue | None,
    application_id: uuid.UUID,
) -> Outcome:
    """`act()` in its own transaction, for the jobs: commits, then queues the email when it is
    due. Without a queue (a job's failure hook) the every-minute `dispatch_scheduled_emails`
    cron sends it."""
    acted = await act(session, settings, application_id)
    if acted.outcome in (Outcome.INVITED, Outcome.REJECTED):
        await session.commit()
        if acted.email is not None and queue is not None:
            await emails.enqueue(queue, acted.email)
    else:
        await session.rollback()
    return acted.outcome


async def _move(session: AsyncSession, application: Application, stage: str, now: datetime) -> None:
    # Imported here: services/applications imports the screening job, which imports this module.
    from app.services.applications import move_stage

    await move_stage(session, application.workspace_id, application.id, stage, now=now)


async def _invite(
    session: AsyncSession, settings: Settings, application: Application, now: datetime
) -> Acted:
    workspace_id = application.workspace_id
    pipeline = await ScreeningRepository(session, workspace_id).pipeline(application.pipeline_id)
    await _move(session, application, INVITED, now)

    token, token_hash = new_token()
    zone = zone_of(await workspace_timezone(session, workspace_id))
    expires_at = end_of_day_after(now, pipeline.link_expiry_days, zone)
    InterviewRepository(session, workspace_id).add(
        Interview(
            workspace_id=workspace_id,
            application_id=application.id,
            token_hash=token_hash,
            format=pipeline.interview_format,
            invited_at=now,
            expires_at=expires_at,
        )
    )
    # The invitation always goes out (NOTIFICATIONS.md §1).
    scheduled = await candidate_emails.schedule(
        session,
        settings,
        workspace_id=workspace_id,
        application_id=application.id,
        key=TemplateKey.INTERVIEW_INVITATION,
        at=now,
        values={
            "Interview.link": interview_link(settings, token),
            "Interview.expiry": await candidate_emails.local_time(
                session, workspace_id, expires_at
            ),
        },
    )
    logger.info("application %s invited to interview", application.id)
    return Acted(Outcome.INVITED, scheduled.message)


async def _reject(
    session: AsyncSession,
    settings: Settings,
    application: Application,
    assessment: ResumeAssessment,
    now: datetime,
) -> Acted:
    workspace_id = application.workspace_id
    pipeline = await ScreeningRepository(session, workspace_id).pipeline(application.pipeline_id)
    await _move(session, application, RESUME_NOT_MATCH, now)
    if not pipeline.email_resume_reject:
        logger.info("application %s not a match; no email (pipeline setting)", application.id)
        return Acted(Outcome.REJECTED)

    send_at = await candidate_emails.send_at(
        session, workspace_id, assessment.screened_at, REJECTION_DELAY_BUSINESS_DAYS
    )
    token, token_hash = new_token()
    ReviewLinkRepository(session, workspace_id).add(
        ReviewLink(
            workspace_id=workspace_id,
            application_id=application.id,
            decision_type="resume",
            token_hash=token_hash,
            expires_at=send_at + timedelta(days=REVIEW_LINK_DAYS),
        )
    )
    scheduled = await candidate_emails.schedule(
        session,
        settings,
        workspace_id=workspace_id,
        application_id=application.id,
        key=TemplateKey.REJECT_RESUME,
        at=send_at,
        values={"Review.link": review_link(settings, token)},
    )
    logger.info("application %s not a match; rejection email scheduled", application.id)
    return Acted(Outcome.REJECTED, scheduled.message)
