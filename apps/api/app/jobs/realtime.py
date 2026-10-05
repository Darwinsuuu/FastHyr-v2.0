"""Live interview jobs (INTV-004, MEDIA.md §2).

`run_realtime_session` is queued by `POST /v1/candidate/interviews/{token}/session` for each
attempt and holds the server's sideband connection to the call until it ends
(`app/interview/sideband.py`). A retry re-attaches to the same call without greeting the
candidate again; an attempt that already ended is skipped.

`end_overdue_attempts` runs every minute: it ends attempts past their share of the 30-minute cap
or whose browser stopped sending heartbeats, and hangs up their calls, so the cap holds even if
the sideband job or the browser misbehaves.
"""

import uuid
from datetime import timedelta

from app.ai.realtime import RealtimeProvider, RealtimeUnavailableError
from app.core.config import get_settings
from app.interview.sideband import SessionController
from app.jobs.framework import NO_RETRY, JobRun, RetryPolicy, job
from app.repositories.interviews import open_attempts
from app.services import interview_sessions

# The longest a call can run (the cap) plus room for the goodbye and reconnects.
SIDEBAND_TIMEOUT = timedelta(seconds=interview_sessions.CAP_SECONDS + 5 * 60)


class SidebandUnavailableError(Exception):
    """OpenAI couldn't be reached to attach to the call; the job retries."""


@job(retry=RetryPolicy(max_tries=3, base_delay=timedelta(seconds=2)))
async def run_realtime_session(
    run: JobRun, workspace_id: uuid.UUID, attempt_id: uuid.UUID
) -> str | None:
    realtime: RealtimeProvider = run.ctx["realtime"]
    controller = SessionController(
        run.session, realtime, workspace_id, attempt_id, prices=get_settings().openai_prices
    )
    try:
        return await controller.run(opening=run.job_try == 1)
    except RealtimeUnavailableError as error:
        raise SidebandUnavailableError() from error


@job(retry=NO_RETRY)
async def end_overdue_attempts(run: JobRun) -> int:
    realtime: RealtimeProvider = run.ctx["realtime"]
    ended = 0
    for workspace_id, attempt_id in await open_attempts(run.session):
        await run.session.rollback()
        reason = await interview_sessions.end_if_overdue(
            run.session, realtime, workspace_id, attempt_id
        )
        ended += reason is not None
    return ended
