"""Résumé screening (AI_PIPELINE.md §1): queued once per submitted application (APPLY-003), and
again by the requeue_stuck_work sweeper for applications still pending after 10 minutes.

Two steps, each done once and skipped on a repeat: extract and redact the text
(`services/screening.prepare_resume()`, SCREEN-001), then score it and decide pass or fail
(`assess_resume()`, SCREEN-002). A retry after a model error resumes from the step that failed.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient, AIOutputError
from app.integrations.storage import Storage, StorageObjectMissingError
from app.jobs.framework import JobRun, PermanentJobError, RetryPolicy, job
from app.services import screening

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
    return prepared is not screening.Prepared.SKIPPED or assessed is not screening.Assessed.SKIPPED
