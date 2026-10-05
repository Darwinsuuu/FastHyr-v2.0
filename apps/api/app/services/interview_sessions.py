"""Live interview sessions (INTV-004, MEDIA.md §2, WORKFLOW.md §4): starting and resuming
attempts on OpenAI Realtime, heartbeats, the candidate ending the interview, and the watchdog.

The 30-minute cap counts talk time across attempts on the server's clock, never the browser's.
Each attempt records what was left of the cap when it started (`seconds_allowed`) and ends at
`started_at + seconds_allowed` whatever the browser does: the sideband job hangs the call up on
time, a heartbeat past the deadline ends it, and the every-minute watchdog ends attempts that are
past it or stopped sending heartbeats. The API opens every call itself (ADR-021), so it can
always hang one up.

Ending an attempt (`end_attempt()`): `candidate_ended`, `wrap_up` and `time_cap` complete the
interview and move the application to `scoring`; `disconnect` and `error` leave it `abandoned`
(`drop_reason = left_unfinished`), to be resumed while the link is valid, and schedule the
"Finish your interview" email an attempt's start wrote on hold (INTV-007,
services/interview_lifecycle.py). Three attempts that never connected within 5 minutes set
`drop_reason = technical_issue`, which the link page shows as "We couldn't connect you".
"""

import logging
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import interviewer
from app.ai.realtime import (
    RealtimeOfferRejectedError,
    RealtimeProvider,
    RealtimeUnavailableError,
)
from app.core.config import Settings
from app.core.context import CandidateContext
from app.core.errors import (
    InterviewAttemptNotFoundError,
    InterviewConsentRequiredError,
    InterviewNotFoundError,
    InterviewNotOpenError,
    InterviewTechnicalIssueError,
    RealtimeOfferRejectedAppError,
    RealtimeUnavailableAppError,
)
from app.core.ids import new_id
from app.interview.plan import INTERVIEW_MINUTES
from app.jobs.queue import JobQueue
from app.models import Application, Interview, InterviewAttempt, InterviewPlan
from app.repositories.interviews import (
    InterviewAttemptRepository,
    InterviewLinkRow,
    InterviewPlanRepository,
)
from app.repositories.screening import ScreeningRepository
from app.schemas.interviews import (
    EndReason,
    InterviewCompleted,
    InterviewCompleteRequest,
    InterviewHeartbeat,
    InterviewHeartbeatRequest,
    InterviewSession,
    InterviewSessionRequest,
    InterviewTopic,
)
from app.services import interview_lifecycle, interview_links

logger = logging.getLogger("app.interview")

SIDEBAND_JOB = "run_realtime_session"
CAP_SECONDS = INTERVIEW_MINUTES * 60
WRAP_UP_SECONDS = interviewer.WRAP_UP_MINUTES * 60
HEARTBEAT_SECONDS = 15
# The watchdog ends an attempt that sent no heartbeat for this long (4 missed beats).
SILENCE_SECONDS = 60
# Fewer seconds than this left isn't worth a new attempt: the interview is complete.
MIN_ATTEMPT_SECONDS = 15
FAILED_CONNECTS = 3
FAILED_CONNECTS_WINDOW = timedelta(minutes=5)

COMPLETING = frozenset({"candidate_ended", "wrap_up", "time_cap"})


@dataclass
class _Ended:
    """Calls to hang up once the transaction that ended their attempts has committed."""

    call_ids: list[str]


# --- Starting ---------------------------------------------------------------------------------


async def start(
    session: AsyncSession,
    realtime: RealtimeProvider,
    queue: JobQueue,
    settings: Settings,
    token: str,
    candidate: CandidateContext,
    body: InterviewSessionRequest,
    *,
    now: datetime | None = None,
) -> InterviewSession:
    """Starts the interview, or a new attempt after a drop or a reload: opens the Realtime call
    with the browser's offer and the interviewer's instructions, and queues the sideband job
    that runs it. A running attempt is ended first (one connection at a time)."""
    now = now or datetime.now(UTC)
    row = await _own_link(session, token, candidate, now)
    state = interview_links.resolve(row, candidate, now)
    if state not in interview_links.OPEN_STATES:
        raise InterviewNotOpenError()
    if row.interview.consent_version is None:
        raise InterviewConsentRequiredError()

    workspace_id = row.interview.workspace_id
    attempts = InterviewAttemptRepository(session, workspace_id)
    interview = await attempts.lock_interview(row.interview.id)
    history = await attempts.of_interview(interview.id)
    ended = _Ended([])
    for attempt in history:
        if attempt.ended_at is None:
            reason = "disconnect" if attempt.connected_at else "error"
            await end_attempt(session, interview, attempt, reason, now, ended)

    if _failed_connects(history, now) >= FAILED_CONNECTS:
        interview.drop_reason = "technical_issue"
        await session.commit()
        await hang_up(realtime, ended)
        raise InterviewTechnicalIssueError()

    time_left = CAP_SECONDS - (interview.talk_seconds or 0)
    if time_left < MIN_ATTEMPT_SECONDS:
        await _complete(session, interview, now)
        await session.commit()
        await hang_up(realtime, ended)
        raise InterviewNotOpenError()

    application = await _application(session, interview)
    reached = [a.topic_index for a in history if a.topic_index is not None]
    prepared = await prepare(
        session, interview, application, seconds_left=time_left, reached=max(reached, default=None)
    )
    resume_from = prepared.resume_from
    instructions = prepared.instructions
    topics = prepared.topics

    attempt = InterviewAttempt(
        id=new_id(),
        workspace_id=workspace_id,
        interview_id=interview.id,
        started_at=now,
        seconds_allowed=time_left,
        talk_seconds=0,
        resume_from=resume_from,
    )
    attempts.add(attempt)
    try:
        call = await realtime.create_call(
            sdp=body.sdp,
            session=interviewer.session_config(
                instructions.text,
                model=realtime.model,
                voice=settings.openai_realtime_voice,
                caption_model=settings.openai_caption_model,
            ),
        )
    except (RealtimeUnavailableError, RealtimeOfferRejectedError) as error:
        # Counts as a connection that never came up.
        await end_attempt(session, interview, attempt, "error", now, ended)
        await session.commit()
        await hang_up(realtime, ended)
        if isinstance(error, RealtimeOfferRejectedError):
            raise RealtimeOfferRejectedAppError() from error
        raise RealtimeUnavailableAppError() from error

    attempt.realtime_session_id = call.call_id
    interview.status = "in_progress"
    interview.started_at = interview.started_at or now
    prepared.plan.instructions_version = instructions.version
    if application.stage == "invited":
        await _move(session, application, "interview_in_progress", now)
    interview_lifecycle.interview_resumed(interview)
    await interview_lifecycle.hold_finish_email(session, settings, interview, token)
    await session.commit()
    await hang_up(realtime, ended)
    await queue.enqueue(SIDEBAND_JOB, workspace_id, attempt.id, key=attempt.id)
    return InterviewSession(
        attempt_id=attempt.id,
        sdp=call.sdp,
        time_left_seconds=time_left,
        wrap_up_in_seconds=wrap_up_after(attempt),
        heartbeat_seconds=HEARTBEAT_SECONDS,
        topics=[
            InterviewTopic(number=number, title=str(topic.get("title", "")))
            for number, topic in enumerate(topics, 1)
        ],
        topic_number=resume_from + 1,
    )


def _failed_connects(history: list[InterviewAttempt], now: datetime) -> int:
    since = now - FAILED_CONNECTS_WINDOW
    return sum(
        1
        for attempt in history
        if attempt.ended_at is not None
        and attempt.connected_at is None
        and attempt.started_at >= since
    )


# --- Instructions -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Prepared:
    plan: InterviewPlan
    topics: list[dict[str, Any]]
    resume_from: int
    instructions: interviewer.Instructions


async def prepare(
    session: AsyncSession,
    interview: Interview,
    application: Application | None = None,
    *,
    seconds_left: int,
    reached: int | None = None,
    resume_from: int | None = None,
) -> Prepared:
    """The interviewer's instructions for an attempt: from the topic after the furthest one
    `reached` before (a new attempt), or from `resume_from` (the sideband re-applying an
    attempt's own instructions). Built the same way both times, so the sideband can tell when
    the browser changed them."""
    workspace_id = interview.workspace_id
    application = application or await _application(session, interview)
    plans = InterviewPlanRepository(session, workspace_id)
    plan = await plans.plan_of(interview.application_id)
    if plan is None:
        # Invitations go out only once a plan exists (SCREEN-003).
        logger.error("interview %s has no plan", interview.id)
        raise InterviewNotOpenError()
    pipeline = await ScreeningRepository(session, workspace_id).pipeline(application.pipeline_id)
    company_name, about = await plans.company()
    topics = list(plan.topics)
    start_at = (
        resume_from if resume_from is not None else interviewer.resume_point(reached, len(topics))
    )
    instructions = interviewer.build(
        interviewer.Context(
            company_name=company_name,
            job_title=pipeline.title or "",
            job_description=pipeline.jd_text or "",
            company_about=about,
            tone=pipeline.tone,
            seniority=pipeline.seniority,
            interview_format=interview.format,
            open_to=list(pipeline.open_to),
            topics=topics,
            claims=list(plan.claims_to_verify),
            resume_from=start_at,
            minutes_left=max(1, math.ceil(seconds_left / 60)),
        )
    )
    return Prepared(plan=plan, topics=topics, resume_from=start_at, instructions=instructions)


# --- Heartbeats and ending --------------------------------------------------------------------


async def heartbeat(
    session: AsyncSession,
    realtime: RealtimeProvider,
    token: str,
    candidate: CandidateContext,
    body: InterviewHeartbeatRequest,
    *,
    now: datetime | None = None,
) -> InterviewHeartbeat:
    """Every 15 s while connected: records that the browser is there and connected, counts talk
    time on the server's clock, and ends the attempt once its time is up."""
    now = now or datetime.now(UTC)
    row = await _own_link(session, token, candidate, now)
    attempts = InterviewAttemptRepository(session, row.interview.workspace_id)
    interview = await attempts.lock_interview(row.interview.id)
    attempt = await _attempt_of(attempts, interview, body.attempt_id)
    if attempt.ended_at is not None:
        reason = cast(EndReason, attempt.end_reason)
        await session.rollback()
        return InterviewHeartbeat(status="ended", time_left_seconds=0, end_reason=reason)

    if body.connected and attempt.connected_at is None:
        attempt.connected_at = now
        if interview.drop_reason == "technical_issue":
            interview.drop_reason = None
    attempt.last_seen_at = now
    if now >= deadline(attempt):
        ended = _Ended([])
        await end_attempt(session, interview, attempt, "time_cap", now, ended)
        await session.commit()
        await hang_up(realtime, ended)
        return InterviewHeartbeat(status="ended", time_left_seconds=0, end_reason="time_cap")

    await count_talk(session, interview, attempt, now)
    await session.commit()
    left = attempt.seconds_allowed - attempt.talk_seconds
    return InterviewHeartbeat(
        status="wrap_up" if (interview.talk_seconds or 0) >= WRAP_UP_SECONDS else "active",
        time_left_seconds=left,
    )


async def complete(
    session: AsyncSession,
    realtime: RealtimeProvider,
    token: str,
    candidate: CandidateContext,
    body: InterviewCompleteRequest,
    *,
    now: datetime | None = None,
) -> InterviewCompleted:
    """The candidate ends the interview ("End interview"). Ending it again is harmless."""
    now = now or datetime.now(UTC)
    row = await _own_link(session, token, candidate, now)
    attempts = InterviewAttemptRepository(session, row.interview.workspace_id)
    interview = await attempts.lock_interview(row.interview.id)
    if interview.status == "completed":
        talk = interview.talk_seconds or 0
        await session.rollback()
        return InterviewCompleted(status="completed", talk_seconds=talk)
    if body.attempt_id is not None:
        await _attempt_of(attempts, interview, body.attempt_id)
    history = await attempts.of_interview(interview.id)
    running = any(attempt.ended_at is None for attempt in history)
    # A running attempt can always be ended, even once the link has expired meanwhile.
    if not history or (
        not running
        and interview_links.resolve(row, candidate, now) not in interview_links.OPEN_STATES
    ):
        raise InterviewNotOpenError()
    ended = _Ended([])
    for attempt in history:
        if attempt.ended_at is None:
            await end_attempt(session, interview, attempt, "candidate_ended", now, ended)
    await _complete(session, interview, now)
    await session.commit()
    await hang_up(realtime, ended)
    return InterviewCompleted(status="completed", talk_seconds=interview.talk_seconds or 0)


def deadline(attempt: InterviewAttempt) -> datetime:
    """When the attempt's share of the cap runs out."""
    return attempt.started_at + timedelta(seconds=attempt.seconds_allowed)


def wrap_up_after(attempt: InterviewAttempt) -> int:
    """Seconds into the attempt when the interview reaches 25 minutes of talk (0 if it already
    has)."""
    before = CAP_SECONDS - attempt.seconds_allowed
    return max(0, WRAP_UP_SECONDS - before)


async def count_talk(
    session: AsyncSession, interview: Interview, attempt: InterviewAttempt, now: datetime
) -> None:
    """The attempt's talk time so far (from its start, capped at its share) and the interview's
    total across attempts."""
    elapsed = (now - attempt.started_at).total_seconds()
    attempt.talk_seconds = int(min(max(elapsed, 0), attempt.seconds_allowed))
    await session.flush()
    total = await session.scalar(
        select(func.coalesce(func.sum(InterviewAttempt.talk_seconds), 0)).where(
            InterviewAttempt.workspace_id == interview.workspace_id,
            InterviewAttempt.interview_id == interview.id,
        )
    )
    interview.talk_seconds = min(int(total or 0), CAP_SECONDS)


async def end_attempt(
    session: AsyncSession,
    interview: Interview,
    attempt: InterviewAttempt,
    reason: str,
    now: datetime,
    ended: _Ended | None = None,
) -> bool:
    """Ends an attempt (the caller holds the interview's lock and commits). Returns False if it
    had already ended. The call id goes to `ended` to be hung up after the commit."""
    if attempt.ended_at is not None:
        return False
    await count_talk(session, interview, attempt, now)
    attempt.ended_at = now
    attempt.end_reason = reason
    if ended is not None and attempt.realtime_session_id:
        ended.call_ids.append(attempt.realtime_session_id)
    if reason in COMPLETING:
        await _complete(session, interview, now)
    elif interview.status == "in_progress":
        interview.status = "abandoned"
        await interview_lifecycle.interview_left(session, interview, now)
    return True


async def hang_up(realtime: RealtimeProvider, ended: _Ended) -> None:
    """Best effort: a call that can't be hung up now is ended by OpenAI when the browser leaves,
    and the watchdog has already closed its attempt."""
    for call_id in ended.call_ids:
        try:
            await realtime.hangup(call_id)
        except RealtimeUnavailableError:
            logger.warning("could not hang up a realtime call")


async def end_if_overdue(
    session: AsyncSession,
    realtime: RealtimeProvider,
    workspace_id: uuid.UUID,
    attempt_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> str | None:
    """For the watchdog: ends the attempt if its time is up (`time_cap`) or its browser went
    quiet (`disconnect`, or `error` if it never connected). Returns the end reason, or None
    when the attempt is fine or already over."""
    now = now or datetime.now(UTC)
    attempts = InterviewAttemptRepository(session, workspace_id)
    attempt = await attempts.get(attempt_id)
    if attempt is None or attempt.ended_at is not None:
        await session.rollback()
        return None
    interview = await attempts.lock_interview(attempt.interview_id)
    attempt = await attempts.get(attempt_id, lock=True)
    if attempt is None or attempt.ended_at is not None:
        await session.rollback()
        return None
    reason: str | None = None
    if now >= deadline(attempt):
        reason = "time_cap"
    elif (attempt.last_seen_at or attempt.started_at) <= now - timedelta(seconds=SILENCE_SECONDS):
        reason = "disconnect" if attempt.connected_at else "error"
    if reason is None:
        await session.rollback()
        return None
    ended = _Ended([])
    await end_attempt(session, interview, attempt, reason, now, ended)
    await session.commit()
    await hang_up(realtime, ended)
    return reason


# --- Helpers ----------------------------------------------------------------------------------


async def _own_link(
    session: AsyncSession, token: str, candidate: CandidateContext, now: datetime
) -> InterviewLinkRow:
    """The link, for the account that applied only: anyone else learns nothing (`404`)."""
    row = await interview_links.link_row(session, token)
    if interview_links.resolve(row, candidate, now) == "wrong_account":
        raise InterviewNotFoundError()
    return row


async def _attempt_of(
    attempts: InterviewAttemptRepository, interview: Interview, attempt_id: uuid.UUID
) -> InterviewAttempt:
    attempt = await attempts.get(attempt_id, lock=True)
    if attempt is None or attempt.interview_id != interview.id:
        raise InterviewAttemptNotFoundError()
    return attempt


async def _application(session: AsyncSession, interview: Interview) -> Application:
    application: Application = (
        await session.scalars(
            select(Application).where(
                Application.workspace_id == interview.workspace_id,
                Application.id == interview.application_id,
            )
        )
    ).one()
    return application


async def _complete(session: AsyncSession, interview: Interview, now: datetime) -> None:
    if interview.status == "completed":
        return
    interview.status = "completed"
    interview.completed_at = now
    await interview_lifecycle.interview_completed(session, interview)
    application = await _application(session, interview)
    if application.stage in ("invited", "interview_in_progress"):
        await _move(session, application, "scoring", now)


async def _move(session: AsyncSession, application: Application, stage: str, now: datetime) -> None:
    # Imported here: services/applications imports the jobs, which import this module.
    from app.services.applications import move_stage

    await move_stage(session, application.workspace_id, application.id, stage, now=now)
