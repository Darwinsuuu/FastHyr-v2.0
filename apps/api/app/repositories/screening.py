"""Résumé screening rows in one workspace (SCREEN-001, SCREEN-002). The screening job starts from an
application ID, reads the application with `application_by_id()`, then works through
`ScreeningRepository` for that application's workspace."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AIDecision,
    Application,
    Candidate,
    Pipeline,
    ResumeAssessment,
    ResumeText,
)
from app.repositories.base import WorkspaceRepository

PENDING = "pending"
DONE = "done"


async def application_by_id(session: AsyncSession, application_id: uuid.UUID) -> Application | None:
    """For jobs, which carry only the ID (BACKEND.md §2)."""
    return await session.get(Application, application_id)


async def application_for_update(
    session: AsyncSession, application_id: uuid.UUID
) -> Application | None:
    """The application read fresh and locked until the transaction ends, so two runs acting on
    the same screen take turns (SCREEN-003)."""
    row: Application | None = await session.scalar(
        select(Application)
        .where(Application.id == application_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return row


async def pending_before(session: AsyncSession, before: datetime) -> list[uuid.UUID]:
    """For the requeue_stuck_work sweeper: applications still waiting for their résumé screen
    that were submitted before `before`."""
    rows = await session.scalars(
        select(Application.id)
        .where(Application.resume_status == PENDING, Application.applied_at < before)
        .order_by(Application.applied_at)
        .limit(500)
    )
    return list(rows)


class ScreeningRepository(WorkspaceRepository[ResumeText]):
    model = ResumeText

    async def text_of(self, application_id: uuid.UUID) -> ResumeText | None:
        row: ResumeText | None = await self.session.scalar(
            self._scoped().where(ResumeText.application_id == application_id)
        )
        return row

    async def assessment_of(self, application_id: uuid.UUID) -> ResumeAssessment | None:
        row: ResumeAssessment | None = await self.session.scalar(
            select(ResumeAssessment).where(
                ResumeAssessment.workspace_id == self.workspace_id,
                ResumeAssessment.application_id == application_id,
            )
        )
        return row

    async def pipeline(self, pipeline_id: uuid.UUID) -> Pipeline:
        """The application's pipeline; its setup is locked once it went live."""
        result = await self.session.scalars(
            select(Pipeline).where(
                Pipeline.workspace_id == self.workspace_id, Pipeline.id == pipeline_id
            )
        )
        return result.one()

    async def candidate_name(self, candidate_id: uuid.UUID) -> str | None:
        name: str | None = await self.session.scalar(
            select(Candidate.full_name).where(
                Candidate.workspace_id == self.workspace_id, Candidate.id == candidate_id
            )
        )
        return name

    def add_text(self, row: ResumeText) -> None:
        if row.workspace_id != self.workspace_id:
            raise ValueError("résumé text belongs to another workspace")
        self.session.add(row)

    async def set_resume_status(self, application_id: uuid.UUID, status: str) -> bool:
        """Moves a pending application's résumé status; False when it was no longer pending."""
        result = await self.session.execute(
            update(Application)
            .where(
                Application.workspace_id == self.workspace_id,
                Application.id == application_id,
                Application.resume_status == PENDING,
            )
            .values(resume_status=status)
            .returning(Application.id)
        )
        return result.first() is not None

    def add_assessment(self, assessment: ResumeAssessment, decision: AIDecision) -> None:
        """The assessment and its `ai_decisions` entry, written together (ADR-015)."""
        for row in (assessment, decision):
            if row.workspace_id != self.workspace_id:
                raise ValueError("assessment belongs to another workspace")
        self.session.add_all([assessment, decision])
