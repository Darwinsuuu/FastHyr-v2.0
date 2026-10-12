"""Integrity flags in one workspace (ASMT-002)."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIDecision, Application, IntegrityFlag, Interview
from app.repositories.base import WorkspaceRepository


class IntegrityFlagRepository(WorkspaceRepository[IntegrityFlag]):
    model = IntegrityFlag

    async def of_interview(self, interview_id: uuid.UUID) -> list[IntegrityFlag]:
        rows = await self.session.scalars(
            self._scoped()
            .where(IntegrityFlag.interview_id == interview_id)
            .order_by(IntegrityFlag.start_ms, IntegrityFlag.type)
        )
        return list(rows)

    def add(self, flags: Sequence[IntegrityFlag], decisions: Sequence[AIDecision]) -> None:
        """The flags and their `ai_decisions` entries, written together (FRAUD_INTEGRITY.md
        §3)."""
        scopes = [flag.workspace_id for flag in flags] + [row.workspace_id for row in decisions]
        if any(scope != self.workspace_id for scope in scopes):
            raise ValueError("integrity flag belongs to another workspace")
        self.session.add_all([*flags, *decisions])

    async def mark_flagged(self, application_id: uuid.UUID) -> None:
        """Sets the application's Flagged overlay (WORKFLOW.md §3) until ASMT-003 resolves
        its flags; the Candidates tab and dashboards read it."""
        await self.session.execute(
            update(Application)
            .where(Application.workspace_id == self.workspace_id, Application.id == application_id)
            .values(has_open_flags=True)
        )


async def integrity_pending_before(
    session: AsyncSession, before: datetime
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """For requeue_stuck_work: (workspace_id, interview_id) of live interviews transcribed
    before `before` and not checked yet."""
    rows = await session.execute(
        select(Interview.workspace_id, Interview.id)
        .where(
            Interview.transcript_status == "ready",
            Interview.integrity_status == "none",
            Interview.superseded_by.is_(None),
            Interview.transcribed_at < before,
        )
        .order_by(Interview.transcribed_at)
        .limit(200)
    )
    return [(row.workspace_id, row.id) for row in rows]
