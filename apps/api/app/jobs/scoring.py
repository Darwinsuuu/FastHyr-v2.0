"""Interview scoring (AI_PIPELINE.md §4): `score_interview` is queued by `transcribe_interview`
once the transcript is ready, and again by the requeue_stuck_work sweeper for transcripts still
unscored after 10 minutes (`services/scoring.score()`). Model errors are retried; after the last
try the interview's `assessment_status` is `failed` and the application waits in `scoring` for a
person.
"""

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient, AIOutputError
from app.core.config import get_settings
from app.jobs.framework import JobRun, PermanentJobError, RetryPolicy, job
from app.services import emails, scoring

# Up to two model answers on a 30-minute transcript (the client also retries invalid JSON once).
SCORE_TIMEOUT = timedelta(minutes=10)


class AIOutputJobError(PermanentJobError):
    """The model's assessment failed the evidence checks twice; retrying won't fix it."""

    code = "ai_invalid_output"


async def _mark_failed(session: AsyncSession, error: BaseException, args: tuple[Any, ...]) -> None:
    await scoring.mark_failed(session, args[0], args[1])


@job(retry=RetryPolicy(max_tries=3), on_failure=_mark_failed)
async def score_interview(run: JobRun, workspace_id: uuid.UUID, interview_id: uuid.UUID) -> str:
    ai: AIClient = run.ctx["ai"]
    try:
        outcome = await scoring.score(run.session, get_settings(), ai, workspace_id, interview_id)
    except AIOutputError as error:
        raise AIOutputJobError() from error
    for message in outcome.emails:
        await emails.enqueue(run.queue, message)
    return outcome.scored.value
