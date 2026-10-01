"""Long jobs people wait on (report_jobs, FND-008): create, read, cancel, and the progress
helper the job bodies use. Redis only queues the work; the state shown lives in Postgres.

A report job moves queued → running → done | failed | cancelled. The job body claims it, records
each step (committing, so polling sees it), and stops early if the requester cancelled it.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.jobs.queue import JobQueue
from app.models import ReportJob
from app.repositories.jobs import CANCELLED, DONE, FAILED, ReportJobRepository
from app.schemas.jobs import Job, SampleJobRequest

# The worker function that runs each kind of report job (app/worker.py registers them). Report
# tasks (CAND, PIPE-010) add their kinds here.
JOB_FUNCTIONS: dict[str, str] = {"sample": "sample_report_job"}


def to_schema(row: ReportJob) -> Job:
    return Job.model_validate(row, from_attributes=True)


async def get_job(session: AsyncSession, ctx: RequestContext, job_id: uuid.UUID) -> Job:
    repo = ReportJobRepository(session, ctx.workspace_id)
    return to_schema(await repo.get_requested_by(job_id, ctx.user_id))


async def cancel_job(session: AsyncSession, ctx: RequestContext, job_id: uuid.UUID) -> None:
    """Stops a queued or running job; the worker notices before its next step. A finished job
    stays as it is."""
    repo = ReportJobRepository(session, ctx.workspace_id)
    row = await repo.get_requested_by(job_id, ctx.user_id)
    await repo.finish(row.id, status=CANCELLED, now=datetime.now(UTC))
    await session.commit()


async def start_report_job(
    session: AsyncSession,
    ctx: RequestContext,
    queue: JobQueue,
    *,
    kind: str,
    params: dict[str, Any],
    steps_total: int,
) -> Job:
    """Creates the job row, commits, then queues it. If Redis loses the enqueue, the
    `requeue_stuck_work` cron queues it again from the row."""
    repo = ReportJobRepository(session, ctx.workspace_id)
    row = await repo.add(
        requested_by=ctx.user_id, kind=kind, params=params, steps_total=steps_total
    )
    await session.commit()
    await queue.enqueue(JOB_FUNCTIONS[kind], ctx.workspace_id, row.id, key=row.id)
    return to_schema(row)


async def start_sample_job(
    session: AsyncSession, ctx: RequestContext, queue: JobQueue, body: SampleJobRequest
) -> Job:
    return await start_report_job(
        session,
        ctx,
        queue,
        kind="sample",
        params=body.model_dump(),
        steps_total=body.steps,
    )


class Progress:
    """A job body's handle on its report_jobs row. Each call commits, so `GET /v1/jobs/{id}`
    shows progress as it happens."""

    def __init__(self, session: AsyncSession, workspace_id: uuid.UUID, job_id: uuid.UUID) -> None:
        self.session = session
        self.repo = ReportJobRepository(session, workspace_id)
        self.job_id = job_id

    async def start(self) -> ReportJob | None:
        """The job, now running; None if it already finished or was cancelled (skip the work)."""
        row = await self.repo.claim(self.job_id)
        await self.session.commit()
        return row

    async def step(self, step: int) -> bool:
        """Records `step` as reached. False means the job was cancelled: stop."""
        still_running = await self.repo.set_step(self.job_id, step)
        await self.session.commit()
        return still_running

    async def done(self, *, file_path: str | None = None) -> None:
        await self.repo.finish(self.job_id, status=DONE, now=datetime.now(UTC), file_path=file_path)
        await self.session.commit()


async def record_failure(
    session: AsyncSession, workspace_id: uuid.UUID, job_id: uuid.UUID, error: BaseException
) -> None:
    """After the last try failed: the job shows as failed with the error's class as its code."""
    await ReportJobRepository(session, workspace_id).finish(
        job_id, status=FAILED, now=datetime.now(UTC), error=_error_code(error)
    )


def _error_code(error: BaseException) -> str:
    code = getattr(error, "code", None)
    return code if isinstance(code, str) else "job_failed"
