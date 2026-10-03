"""Résumé screening (AI_PIPELINE.md §1): queued once per submitted application (APPLY-003), and
again by the requeue_stuck_work sweeper for applications still pending after 10 minutes.

Two steps, each done once and skipped on a repeat: extract and redact the text
(`services/screening.prepare_resume()`, SCREEN-001), then score it and decide pass or fail
(`assess_resume()`, SCREEN-002). A retry after a model error resumes from the step that failed.
A passed screen queues `plan_interview` (INTV-001); a failed one is moved to `resume_not_match`
with its rejection email scheduled (`services/post_screen.act()`, SCREEN-003). That last step
runs on every try, so a retry finishes it.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient, AIOutputError
from app.core.config import get_settings
from app.integrations.storage import Storage, StorageObjectMissingError
from app.jobs.framework import JobRun, PermanentJobError, RetryPolicy, job
from app.jobs.interviews import PLAN_JOB
from app.services import post_screen, screening

SCREEN_JOB = "screen_resume"


class ResumeMissingJobError(PermanentJobError):
    code = "resume_missing"


class AIOutputJobError(PermanentJobError):
    """The model's answer failed validation twice (the client already retried once)."""

    code = "ai_invalid_output"


async def _mark_error(session: AsyncSession, error: BaseException, args: tuple[Any, ...]) -> None:
    await screening.record_failure(session, args[0])


@job(retry=RetryPolicy(max_tries=3), on_failure=_mark_error)
async def screen_resume(run: JobRun, application_id: uuid.UUID) -> bool:
    """Screens one application's résumé. Returns False when there is nothing to do (already
    screened, or the application is gone), so a repeated enqueue is harmless."""
    storage: Storage = run.ctx["storage"]
    ai: AIClient = run.ctx["ai"]
    try:
        prepared = await screening.prepare_resume(run.session, storage, ai, application_id)
        assessed = await screening.assess_resume(run.session, ai, application_id)
    except StorageObjectMissingError as error:
        raise ResumeMissingJobError() from error
    except AIOutputError as error:
        raise AIOutputJobError() from error
    if assessed is screening.Assessed.PASSED:
        # The interview plan comes next (INTV-001); the invitation follows it (SCREEN-003).
        await run.queue.enqueue(PLAN_JOB, application_id, key=application_id)
    # Rejects a failed screen (or invites a passed one whose plan is already there).
    acted = await post_screen.act_and_commit(run.session, get_settings(), run.queue, application_id)
    return (
        prepared is not screening.Prepared.SKIPPED
        or assessed is not screening.Assessed.SKIPPED
        or acted is not post_screen.Outcome.SKIPPED
    )
