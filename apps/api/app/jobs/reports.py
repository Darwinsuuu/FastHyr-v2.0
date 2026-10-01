"""Report jobs: long jobs a member waits on, with progress in report_jobs (FND-008). The PDF
report tasks add theirs here, following `sample_report_job`."""

import asyncio
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.framework import JobRun, RetryPolicy, job
from app.services import jobs as job_service


async def _mark_failed(session: AsyncSession, error: BaseException, args: tuple[Any, ...]) -> None:
    workspace_id, job_id = args[0], args[1]
    await job_service.record_failure(session, workspace_id, job_id, error)


class SampleJobError(Exception):
    """The failure `fail_tries` asks for."""


@job(retry=RetryPolicy(max_tries=3, base_delay=timedelta(seconds=1)), on_failure=_mark_failed)
async def sample_report_job(run: JobRun, workspace_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Local-only demo (`POST /v1/dev/sample-job`): walks `steps` steps, failing the first
    `fail_tries` tries, so retries, backoff and progress can be watched end to end."""
    progress = job_service.Progress(run.session, workspace_id, job_id)
    row = await progress.start()
    if row is None:
        return  # already finished or cancelled
    params = row.params
    if run.job_try <= int(params.get("fail_tries", 0)):
        raise SampleJobError()
    for step in range(1, row.steps_total + 1):
        await asyncio.sleep(float(params.get("step_seconds", 1.0)))
        if not await progress.step(step):
            return  # cancelled
    await progress.done()
