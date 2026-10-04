"""Interview plans (INTV-001) and interviews (SCREEN-003) in one workspace. Jobs start from an
application ID, read the application with `screening.application_by_id()`, then work through
these repositories for that application's workspace."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Application,
    Candidate,
    CompanyProfile,
    Interview,
    InterviewPlan,
    Pipeline,
    ResumeAssessment,
    Workspace,
)
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


async def screened_awaiting_action_before(
    session: AsyncSession, before: datetime
) -> list[tuple[uuid.UUID, bool]]:
    """For the requeue_stuck_work sweeper: applications screened before `before` that are still
    in `processing_resume` although their next step is ready (a failed screen, or a passed one
    with its plan), with whether the screen passed (SCREEN-003)."""
    rows = await session.execute(
        select(ResumeAssessment.application_id, ResumeAssessment.passed)
        .join(Application, Application.id == ResumeAssessment.application_id)
        .outerjoin(InterviewPlan, InterviewPlan.application_id == ResumeAssessment.application_id)
        .where(
            ResumeAssessment.screened_at < before,
            Application.stage == "processing_resume",
            Application.resume_status == "done",
            (ResumeAssessment.passed.is_(False)) | (InterviewPlan.application_id.is_not(None)),
        )
        .order_by(ResumeAssessment.screened_at)
        .limit(500)
    )
    return [(row.application_id, row.passed) for row in rows]


@dataclass(frozen=True)
class InterviewLinkRow:
    """What the interview link page needs about one interview (INTV-002)."""

    interview: Interview
    application_stage: str
    candidate_auth_user_id: uuid.UUID
    candidate_email: str
    candidate_full_name: str
    candidate_deleted_at: datetime | None
    pipeline_status: str
    integrity_enabled: bool
    job_title: str | None
    company_name: str
    website: str | None
    careers_url: str | None
    logo_path: str | None
    profile_updated_at: datetime
    timezone: str | None


async def interview_link_of(session: AsyncSession, token_hash: str) -> InterviewLinkRow | None:
    """The interview whose link token hashes to `token_hash`, with its application, candidate,
    pipeline and company. Not workspace-scoped on purpose: the link's token is the key, as for
    invite tokens, and the lookup is one equality match on the unique hash."""
    row = (
        await session.execute(
            select(
                Interview,
                Application.stage,
                Candidate.auth_user_id,
                Candidate.email,
                Candidate.full_name,
                Candidate.deleted_at,
                Pipeline.status,
                Pipeline.integrity_enabled,
                Pipeline.title,
                CompanyProfile.company_name,
                CompanyProfile.website,
                CompanyProfile.careers_url,
                CompanyProfile.logo_path,
                CompanyProfile.updated_at,
                func.coalesce(CompanyProfile.timezone, Workspace.timezone),
            )
            .join(
                Application,
                (Application.workspace_id == Interview.workspace_id)
                & (Application.id == Interview.application_id),
            )
            .join(
                Candidate,
                (Candidate.workspace_id == Application.workspace_id)
                & (Candidate.id == Application.candidate_id),
            )
            .join(
                Pipeline,
                (Pipeline.workspace_id == Application.workspace_id)
                & (Pipeline.id == Application.pipeline_id),
            )
            .join(Workspace, Workspace.id == Interview.workspace_id)
            .join(CompanyProfile, CompanyProfile.workspace_id == Interview.workspace_id)
            .where(Interview.token_hash == token_hash)
        )
    ).one_or_none()
    return InterviewLinkRow(*tuple(row)) if row else None


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


class InterviewRepository(WorkspaceRepository[Interview]):
    model = Interview

    async def live_of(self, application_id: uuid.UUID) -> Interview | None:
        """The application's current interview (not replaced by a re-invite)."""
        row: Interview | None = await self.session.scalar(
            self._scoped().where(
                Interview.application_id == application_id, Interview.superseded_by.is_(None)
            )
        )
        return row

    def add(self, interview: Interview) -> None:
        if interview.workspace_id != self.workspace_id:
            raise ValueError("interview belongs to another workspace")
        self.session.add(interview)
