"""Interview plan rows in one workspace (INTV-001). The plan job starts from an application ID,
reads the application with `screening.application_by_id()`, then works through
`InterviewPlanRepository` for that application's workspace."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, CompanyProfile, InterviewPlan, ResumeAssessment
from app.repositories.base import WorkspaceRepository

# Stages in which a plan is still useful: waiting for the screen's outcome, or invited.
PLANNABLE_STAGES = ("processing_resume", "invited")


async def passed_without_plan_before(session: AsyncSession, before: datetime) -> list[uuid.UUID]:
    """For the requeue_stuck_work sweeper: applications that passed the résumé screen before
    `before` and still have no interview plan."""
    rows = await session.scalars(
        select(ResumeAssessment.application_id)
        .join(Application, Application.id == ResumeAssessment.application_id)
        .outerjoin(InterviewPlan, InterviewPlan.application_id == ResumeAssessment.application_id)
        .where(
            ResumeAssessment.passed.is_(True),
            ResumeAssessment.screened_at < before,
            InterviewPlan.application_id.is_(None),
            Application.stage.in_(PLANNABLE_STAGES),
        )
        .order_by(ResumeAssessment.screened_at)
        .limit(500)
    )
    return list(rows)


class InterviewPlanRepository(WorkspaceRepository[InterviewPlan]):
    model = InterviewPlan

    async def plan_of(self, application_id: uuid.UUID) -> InterviewPlan | None:
        row: InterviewPlan | None = await self.session.scalar(
            self._scoped().where(InterviewPlan.application_id == application_id)
        )
        return row

    async def company_about(self) -> str:
        about: str | None = await self.session.scalar(
            select(CompanyProfile.about).where(CompanyProfile.workspace_id == self.workspace_id)
        )
        return about or ""

    def add(self, plan: InterviewPlan) -> None:
        if plan.workspace_id != self.workspace_id:
            raise ValueError("interview plan belongs to another workspace")
        self.session.add(plan)
