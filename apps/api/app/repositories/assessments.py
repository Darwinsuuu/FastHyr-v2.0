"""Interview assessments in one workspace (ASMT-001)."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIDecision, Assessment, Interview
from app.repositories.base import WorkspaceRepository


class AssessmentRepository(WorkspaceRepository[Assessment]):
    model = Assessment

    async def of_interview(self, interview_id: uuid.UUID) -> Assessment | None:
        row: Assessment | None = await self.session.scalar(
            self._scoped().where(Assessment.interview_id == interview_id)
        )
        return row

    def add(self, assessment: Assessment, decision: AIDecision) -> None:
        """The assessment and its `ai_decisions` entry, written together (ADR-015)."""
        for row in (assessment, decision):
            if row.workspace_id != self.workspace_id:
                raise ValueError("assessment belongs to another workspace")
        self.session.add_all([assessment, decision])


async def assessments_pending_before(
    session: AsyncSession, before: datetime
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """For requeue_stuck_work: (workspace_id, interview_id) of live interviews transcribed
    before `before` and still not scored."""
    rows = await session.execute(
        select(Interview.workspace_id, Interview.id)
        .where(
            Interview.transcript_status == "ready",
            Interview.assessment_status == "none",
            Interview.superseded_by.is_(None),
            Interview.transcribed_at < before,
        )
        .order_by(Interview.transcribed_at)
        .limit(200)
    )
    return [(row.workspace_id, row.id) for row in rows]
