"""Résumé screening (AI_PIPELINE.md): queued once per submitted application (APPLY-003).

SCREEN-001 (extraction and redaction) and SCREEN-002 (fit score) fill in the body; until then
the application waits in `processing_resume` with `resume_status = pending`.
"""

import logging
import uuid

from app.jobs.framework import JobRun, RetryPolicy, job
from app.models import Application

logger = logging.getLogger("app.jobs")

SCREEN_JOB = "screen_resume"


@job(retry=RetryPolicy(max_tries=3))
async def screen_resume(run: JobRun, application_id: uuid.UUID) -> bool:
    """Screens one application's résumé. Returns False when there is nothing to do (already
    screened, or the application is gone), so a repeated enqueue is harmless."""
    application = await run.session.get(Application, application_id)
    if application is None or application.resume_status != "pending":
        return False
    logger.info("screen_resume: application %s waits for SCREEN-001", application_id)
    return False
