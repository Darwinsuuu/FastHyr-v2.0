"""What happens around a live interview (INTV-007, WORKFLOW.md §3-4, NOTIFICATIONS.md §1):
interview links and their emails, the "Finish your interview" nudge, link expiry and drop-off
reasons, and re-invites.

The link token is stored only as its hash, so every email that carries the link is written while
the token is at hand:
- `issue_link()` creates the interview and schedules the invitation (now) and, when the
  pipeline's "Remind candidates" toggle is on, the reminder for 24 hours before the link closes.
  Starting the interview moves the stage, which cancels the reminder (MSG-003).
- `hold_finish_email()` runs when an attempt starts and writes the "Finish your interview" email
  held. `interview_left()` schedules it for 1 hour after the interview is left unfinished (or
  cancels it when the link closes first); a new attempt puts it back on hold. Its dedupe key is
  per interview, so it goes out at most once per link.

Drop-off reasons (`interviews.drop_reason`, FR-INTV-08) describe a live, unfinished interview:
`left_unfinished` while it is abandoned, `technical_issue` after repeated failed connections
(services/interview_sessions.py), `link_expired` when the link closed before it started.
`expire_links()` closes links past their expiry. Re-inviting gives the application a new link
(new token, fresh expiry and 30 minutes, same plan and credit) and supersedes the old one.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_days import end_of_day_after, zone_of
from app.core.config import Settings
from app.core.context import RequestContext
from app.core.errors import NotFoundError, ReinviteNotAllowedError
from app.core.ids import new_id
from app.core.tokens import new_token
from app.emails.defaults import TemplateKey
from app.jobs.queue import JobQueue
from app.models import Application, Candidate, EmailMessage, Interview, InterviewAttempt, Pipeline
from app.repositories import interviews as interview_repo
from app.repositories.audit import AuditRepository
from app.repositories.company_profiles import workspace_timezone
from app.repositories.emails import LINK_CLOSED
from app.repositories.interviews import InterviewRepository
from app.repositories.pipelines import PipelineRepository
from app.services import candidate_emails, emails

logger = logging.getLogger("app.interview")

# NOTIFICATIONS.md §1.
REMINDER_BEFORE_EXPIRY = timedelta(hours=24)
FINISH_AFTER_LEAVING = timedelta(hours=1)

# Applications still waiting on their interview (WORKFLOW.md §3).
REINVITABLE_STAGES = ("invited", "interview_in_progress")
CLOSED_PIPELINES = ("cancelled", "archived")


def interview_link(settings: Settings, token: str) -> str:
    return f"{settings.site_url}/interview/{token}"


def finish_key(interview_id: uuid.UUID) -> str:
    return f"{TemplateKey.FINISH_INTERVIEW.value}:{interview_id}"


def reminder_key(interview_id: uuid.UUID) -> str:
    return f"{TemplateKey.INTERVIEW_REMINDER.value}:{interview_id}"


def invitation_key(interview_id: uuid.UUID) -> str:
    return f"{TemplateKey.INTERVIEW_INVITATION.value}:{interview_id}"


@dataclass
class IssuedLink:
    interview: Interview
    # Emails to `emails.enqueue()` after the commit (a no-op for the ones due later).
    emails: list[EmailMessage] = field(default_factory=list)


# --- Links and their emails -------------------------------------------------------------------


async def issue_link(
    session: AsyncSession,
    settings: Settings,
    application: Application,
    pipeline: Pipeline,
    now: datetime,
    *,
    interview_id: uuid.UUID | None = None,
) -> IssuedLink:
    """A new interview link for the application, in the caller's transaction, with the
    invitation (always) and the reminder (pipeline toggle). The application must already be in
    `invited`, the stage the emails are written for. A re-invite passes the `interview_id` it
    already pointed the old interview at."""
    workspace_id = application.workspace_id
    token, token_hash = new_token()
    zone = zone_of(await workspace_timezone(session, workspace_id))
    expires_at = end_of_day_after(now, pipeline.link_expiry_days, zone)
    interview = Interview(
        id=interview_id or new_id(),
        workspace_id=workspace_id,
        application_id=application.id,
        token_hash=token_hash,
        format=pipeline.interview_format,
        invited_at=now,
        expires_at=expires_at,
    )
    InterviewRepository(session, workspace_id).add(interview)
    await session.flush()

    values = {
        "Interview.link": interview_link(settings, token),
        "Interview.expiry": await candidate_emails.local_time(session, workspace_id, expires_at),
    }
    issued = IssuedLink(interview)
    invitation = await candidate_emails.schedule(
        session,
        settings,
        workspace_id=workspace_id,
        application_id=application.id,
        key=TemplateKey.INTERVIEW_INVITATION,
        at=now,
        values=values,
        dedupe_key=invitation_key(interview.id),
    )
    issued.emails.append(invitation.message)
    remind_at = expires_at - REMINDER_BEFORE_EXPIRY
    if pipeline.reminder_enabled and remind_at > now:
        reminder = await candidate_emails.schedule(
            session,
            settings,
            workspace_id=workspace_id,
            application_id=application.id,
            key=TemplateKey.INTERVIEW_REMINDER,
            at=remind_at,
            values=values,
            dedupe_key=reminder_key(interview.id),
        )
        issued.emails.append(reminder.message)
    return issued


async def hold_finish_email(
    session: AsyncSession, settings: Settings, interview: Interview, token: str
) -> None:
    """When an attempt starts: makes sure the "Finish your interview" email is written and on
    hold. One already sent is never written again."""
    workspace_id = interview.workspace_id
    held = await candidate_emails.schedule(
        session,
        settings,
        workspace_id=workspace_id,
        application_id=interview.application_id,
        key=TemplateKey.FINISH_INTERVIEW,
        values={
            "Interview.link": interview_link(settings, token),
            "Interview.expiry": await candidate_emails.local_time(
                session, workspace_id, interview.expires_at
            ),
        },
        dedupe_key=finish_key(interview.id),
        held=True,
    )
    if not held.created:
        # Scheduled after an earlier attempt was left and not sent yet: wait again.
        await emails.hold(session, finish_key(interview.id))


async def interview_left(session: AsyncSession, interview: Interview, now: datetime) -> None:
    """An attempt ended and left the interview unfinished (`abandoned`): records why, and
    schedules the "Finish your interview" email for an hour later while the link is still
    open then."""
    if interview.drop_reason is None:
        interview.drop_reason = "left_unfinished"
    send_at = now + FINISH_AFTER_LEAVING
    if send_at < interview.expires_at:
        await emails.release_held(session, finish_key(interview.id), send_at)
    else:
        await emails.cancel_waiting(session, finish_key(interview.id), reason=LINK_CLOSED)


def interview_resumed(interview: Interview) -> None:
    """A new attempt is running: the interview is no longer left unfinished."""
    if interview.drop_reason == "left_unfinished":
        interview.drop_reason = None


async def interview_completed(session: AsyncSession, interview: Interview) -> None:
    """A finished interview is no drop-off, and gets no nudges."""
    interview.drop_reason = None
    for key in (finish_key(interview.id), reminder_key(interview.id)):
        await emails.cancel_waiting(session, key, reason=LINK_CLOSED)


# --- Expiry -----------------------------------------------------------------------------------


async def expire_links(session: AsyncSession, *, now: datetime | None = None) -> int:
    """For the expire_interview_links cron: closes live links past their expiry that are not
    running, sets their drop-off reason and cancels their waiting interview emails. The caller
    commits. Returns how many expired."""
    now = now or datetime.now(UTC)
    expired = await interview_repo.expire_links(session, now)
    for link in expired:
        for key in (finish_key(link.interview_id), reminder_key(link.interview_id)):
            await emails.cancel_waiting(session, key, reason=LINK_CLOSED)
    return len(expired)


# --- Re-invites -------------------------------------------------------------------------------


@dataclass
class Reinvited:
    # The emails are sent once committed.
    application_ids: list[uuid.UUID] = field(default_factory=list)
    emails: list[EmailMessage] = field(default_factory=list)


async def reinvite(
    session: AsyncSession,
    settings: Settings,
    queue: JobQueue,
    ctx: RequestContext,
    application_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Reinvited:
    """A new interview link for one application that hasn't finished its interview; commits and
    sends the invitation. `404` outside the caller's workspace or departments;
    `409 reinvite_not_allowed` when the application isn't waiting on an unfinished interview."""
    now = now or datetime.now(UTC)
    application = await _application(session, ctx, application_id)
    pipeline = await _pipeline(session, ctx, application.pipeline_id)
    done = Reinvited()
    await _reinvite_one(session, settings, ctx, application, pipeline, now, done, strict=True)
    return await _commit_and_send(session, queue, done)


async def reinvite_unfinished(
    session: AsyncSession,
    settings: Settings,
    queue: JobQueue,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Reinvited:
    """The pipeline dashboard's "Re-invite all" (FR-PIPE-11): a new link for every application
    whose interview expired, was left unfinished, or hit a technical issue; commits and sends the
    invitations. A cancelled or archived pipeline is `409 reinvite_not_allowed`."""
    now = now or datetime.now(UTC)
    pipeline = await _pipeline(session, ctx, pipeline_id)
    done = Reinvited()
    if pipeline.status in CLOSED_PIPELINES:
        raise ReinviteNotAllowedError()
    running = exists().where(
        InterviewAttempt.interview_id == Interview.id, InterviewAttempt.ended_at.is_(None)
    )
    unfinished = (
        Interview.status.in_(("expired", "abandoned"))
        | ((Interview.status == "not_started") & (Interview.expires_at <= now))
        | (Interview.drop_reason == "technical_issue")
    )
    applications = await session.scalars(
        select(Application)
        .join(
            Interview,
            (Interview.workspace_id == Application.workspace_id)
            & (Interview.application_id == Application.id)
            & Interview.superseded_by.is_(None),
        )
        .join(
            Candidate,
            (Candidate.workspace_id == Application.workspace_id)
            & (Candidate.id == Application.candidate_id),
        )
        .where(
            Application.workspace_id == ctx.workspace_id,
            Application.pipeline_id == pipeline.id,
            Application.stage.in_(REINVITABLE_STAGES),
            Candidate.deleted_at.is_(None),
            Interview.status != "completed",
            unfinished,
            ~running,
        )
        .order_by(Application.applied_at)
    )
    for application in list(applications):
        await _reinvite_one(session, settings, ctx, application, pipeline, now, done, strict=False)
    return await _commit_and_send(session, queue, done)


async def _commit_and_send(session: AsyncSession, queue: JobQueue, done: Reinvited) -> Reinvited:
    await session.commit()
    for message in done.emails:
        await emails.enqueue(queue, message)
    return done


async def _reinvite_one(
    session: AsyncSession,
    settings: Settings,
    ctx: RequestContext,
    application: Application,
    pipeline: Pipeline,
    now: datetime,
    done: Reinvited,
    *,
    strict: bool,
) -> None:
    workspace_id = application.workspace_id
    attempts = interview_repo.InterviewAttemptRepository(session, workspace_id)
    old = await InterviewRepository(session, workspace_id).live_of(application.id)
    allowed = pipeline.status not in CLOSED_PIPELINES and old is not None
    if allowed and old is not None:
        # The interview first, then the application: the order a starting attempt takes them in.
        old = await attempts.lock_interview(old.id)
        await _lock(session, application)
        history = await attempts.of_interview(old.id)
        allowed = (
            old.superseded_by is None
            and old.status != "completed"
            and application.stage in REINVITABLE_STAGES
            and all(a.ended_at is not None for a in history)
        )
    if not allowed or old is None:
        if strict:
            raise ReinviteNotAllowedError()
        return

    # Imported here: services/applications imports the jobs, which import this module.
    from app.services.applications import move_stage

    # The old link's waiting emails (reminder, finish) must not go out with a dead link.
    await emails.cancel_scheduled(session, application.id, reason=LINK_CLOSED)
    await move_stage(session, workspace_id, application.id, "invited", now=now)
    new_interview_id = new_id()
    old.superseded_by = new_interview_id
    await session.flush()
    issued = await issue_link(
        session, settings, application, pipeline, now, interview_id=new_interview_id
    )
    AuditRepository(session, workspace_id).record(
        actor_id=ctx.user_id,
        action="application.reinvited",
        entity_type="application",
        entity_id=application.id,
        data={"interview_id": str(issued.interview.id), "replaces": str(old.id)},
    )
    done.application_ids.append(application.id)
    done.emails.extend(issued.emails)
    logger.info("application %s re-invited to interview", application.id)


async def _application(
    session: AsyncSession, ctx: RequestContext, application_id: uuid.UUID
) -> Application:
    application: Application | None = await session.scalar(
        select(Application).where(
            Application.workspace_id == ctx.workspace_id, Application.id == application_id
        )
    )
    if application is None:
        raise NotFoundError()
    return application


async def _lock(session: AsyncSession, application: Application) -> None:
    """Locks the application and reads it as it is now."""
    await session.scalar(
        select(Application)
        .where(
            Application.workspace_id == application.workspace_id,
            Application.id == application.id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )


async def _pipeline(session: AsyncSession, ctx: RequestContext, pipeline_id: uuid.UUID) -> Pipeline:
    departments = None if ctx.sees_all_departments else ctx.department_ids
    pipeline: Pipeline = await PipelineRepository(
        session, ctx.workspace_id, department_ids=departments
    ).get(pipeline_id)
    return pipeline
