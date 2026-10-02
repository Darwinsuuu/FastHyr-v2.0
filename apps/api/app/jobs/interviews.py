"""Interview plans (AI_PIPELINE.md §2): `plan_interview` is queued by `screen_resume` when an
application passes the résumé screen, and again by the requeue_stuck_work sweeper for passed
applications still without a plan after 10 minutes.

When the model can't give a usable plan after the job's tries, the failure hook stores the
plain skills plan instead (`services/interviews.record_fallback()`), so the invitation
(SCREEN-003) never waits on the model.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient, AIOutputError
from app.jobs.framework import JobRun, PermanentJobError, RetryPolicy, job
from app.services import interviews

PLAN_JOB = "plan_interview"


class AIOutputJobError(PermanentJobError):
    """The model's plan failed the checks twice; retrying the job won't fix it."""

    code = "ai_invalid_output"


async def _fall_back(session: AsyncSession, error: BaseException, args: tuple[Any, ...]) -> None:
    await interviews.record_fallback(session, args[0])


@job(retry=RetryPolicy(max_tries=3), on_failure=_fall_back)
async def plan_interview(run: JobRun, application_id: uuid.UUID) -> bool:
    """Builds one application's interview plan. Returns False when there is nothing to do
    (already planned, past the interview stage, or gone), so a repeated enqueue is harmless."""
    ai: AIClient = run.ctx["ai"]
    try:
        planned = await interviews.plan_interview(run.session, ai, application_id)
    except AIOutputError as error:
        raise AIOutputJobError() from error
    return planned is interviews.Planned.PLANNED
