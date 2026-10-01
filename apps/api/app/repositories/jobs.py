"""Report jobs of one workspace: the progress rows behind `GET /v1/jobs/{id}` (FND-008)."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import ReportJob
from app.repositories.base import WorkspaceRepository

QUEUED, RUNNING, DONE, FAILED, CANCELLED = "queued", "running", "done", "failed", "cancelled"
UNFINISHED = (QUEUED, RUNNING)


class ReportJobRepository(WorkspaceRepository[ReportJob]):
    model = ReportJob

    async def add(
        self, *, requested_by: uuid.UUID, kind: str, params: dict[str, Any], steps_total: int
    ) -> ReportJob:
        row = ReportJob(
            workspace_id=self.workspace_id,
            requested_by=requested_by,
            kind=kind,
            params=params,
            steps_total=steps_total,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_requested_by(self, job_id: uuid.UUID, user_id: uuid.UUID) -> ReportJob:
        """A job is visible only to the member who asked for it; anyone else gets a 404."""
        row: ReportJob | None = await self.session.scalar(
            self._scoped().where(ReportJob.id == job_id, ReportJob.requested_by == user_id)
        )
        if row is None:
            raise NotFoundError()
        return row

    async def claim(self, job_id: uuid.UUID) -> ReportJob | None:
        """Marks the job running and returns it, or None when it is already finished or
        cancelled, so a repeated run does nothing. A retry finds it running and carries on."""
        row: ReportJob | None = await self.session.scalar(
            update(ReportJob)
            .where(
                ReportJob.workspace_id == self.workspace_id,
                ReportJob.id == job_id,
                ReportJob.status.in_(UNFINISHED),
            )
            .values(status=RUNNING)
            .returning(ReportJob)
        )
        return row

    async def set_step(self, job_id: uuid.UUID, step: int) -> bool:
        """Records progress unless the job was cancelled meanwhile. Returns False if it was."""
        result = await self.session.execute(
            update(ReportJob)
            .where(
                ReportJob.workspace_id == self.workspace_id,
                ReportJob.id == job_id,
                ReportJob.status == RUNNING,
            )
            .values(step=step)
            .returning(ReportJob.id)
        )
        return result.first() is not None

    async def finish(
        self,
        job_id: uuid.UUID,
        *,
        status: str,
        now: datetime,
        error: str | None = None,
        file_path: str | None = None,
    ) -> bool:
        """Moves an unfinished job to `status` (done, failed or cancelled). Returns False when
        it had already finished, which leaves it as it was."""
        values: dict[str, Any] = {"status": status, "finished_at": now, "error": error}
        if file_path is not None:
            values["file_path"] = file_path
        result = await self.session.execute(
            update(ReportJob)
            .where(
                ReportJob.workspace_id == self.workspace_id,
                ReportJob.id == job_id,
                ReportJob.status.in_(UNFINISHED),
            )
            .values(**values)
            .returning(ReportJob.id)
        )
        return result.first() is not None


@dataclass(frozen=True)
class StuckJob:
    workspace_id: uuid.UUID
    job_id: uuid.UUID
    kind: str


async def queued_report_jobs_before(session: AsyncSession, before: datetime) -> list[StuckJob]:
    """For the requeue_stuck_work sweeper, which runs across workspaces: jobs still queued that
    were created before `before`, oldest first (their enqueue may have been lost with Redis)."""
    rows = await session.execute(
        select(ReportJob.workspace_id, ReportJob.id, ReportJob.kind)
        .where(ReportJob.status == QUEUED, ReportJob.created_at < before)
        .order_by(ReportJob.created_at)
        .limit(500)
    )
    return [StuckJob(workspace_id, job_id, kind) for workspace_id, job_id, kind in rows]
