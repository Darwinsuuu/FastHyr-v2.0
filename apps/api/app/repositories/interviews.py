"""Interview plans (INTV-001) and interviews (SCREEN-003) in one workspace. Jobs start from an
application ID, read the application with `screening.application_by_id()`, then work through
these repositories for that application's workspace."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Application,
    Candidate,
    CompanyProfile,
    Interview,
    InterviewAttempt,
    InterviewPlan,
    Pipeline,
    RecordingChunk,
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

    async def company(self) -> tuple[str, str]:
        """The company's name and "About" text, for the live interviewer (INTV-004)."""
        row = (
            await self.session.execute(
                select(CompanyProfile.company_name, CompanyProfile.about).where(
                    CompanyProfile.workspace_id == self.workspace_id
                )
            )
        ).one()
        return row.company_name, row.about or ""

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


async def open_attempts(session: AsyncSession) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """For the end_overdue_attempts watchdog (INTV-004): every open attempt, as (workspace_id,
    attempt_id). There are only as many as interviews running right now; the watchdog checks
    each one's own cap, which depends on the talk time before it started."""
    rows = await session.execute(
        select(InterviewAttempt.workspace_id, InterviewAttempt.id)
        .where(InterviewAttempt.ended_at.is_(None))
        .order_by(InterviewAttempt.started_at)
        .limit(1000)
    )
    return [(row.workspace_id, row.id) for row in rows]


class InterviewAttemptRepository(WorkspaceRepository[InterviewAttempt]):
    model = InterviewAttempt

    async def get(self, attempt_id: uuid.UUID, *, lock: bool = False) -> InterviewAttempt | None:
        # Always the row as it is now: the API and the sideband job both change attempts.
        statement = (
            self._scoped()
            .where(InterviewAttempt.id == attempt_id)
            .execution_options(populate_existing=True)
        )
        if lock:
            statement = statement.with_for_update()
        row: InterviewAttempt | None = await self.session.scalar(statement)
        return row

    async def of_interview(self, interview_id: uuid.UUID) -> list[InterviewAttempt]:
        rows = await self.session.scalars(
            self._scoped()
            .where(InterviewAttempt.interview_id == interview_id)
            .order_by(InterviewAttempt.started_at)
        )
        return list(rows)

    async def get_interview(self, interview_id: uuid.UUID) -> Interview | None:
        row: Interview | None = await self.session.scalar(
            select(Interview)
            .where(Interview.workspace_id == self.workspace_id, Interview.id == interview_id)
            .execution_options(populate_existing=True)
        )
        return row

    async def lock_interview(self, interview_id: uuid.UUID) -> Interview:
        """The interview row, locked, so attempts on it start and end one at a time."""
        row: Interview = (
            await self.session.scalars(
                select(Interview)
                .where(Interview.workspace_id == self.workspace_id, Interview.id == interview_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).one()
        return row

    def add(self, attempt: InterviewAttempt) -> None:
        if attempt.workspace_id != self.workspace_id:
            raise ValueError("interview attempt belongs to another workspace")
        self.session.add(attempt)


# Statuses of a completed interview's recording that still need the finalize_recording job.
RECORDING_PENDING = ("none", "uploading", "finalizing")


async def recordings_due(
    session: AsyncSession,
    now: datetime,
    *,
    quiet: timedelta,
    latest: timedelta,
    interview_id: uuid.UUID | None = None,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """Completed interviews whose recording can be put together now, as (workspace_id,
    interview_id) (INTV-006): every attempt is settled, meaning the browser registered its last
    chunk, or it ended and no chunk arrived for `quiet`; or the interview finished more than
    `latest` ago, whatever is still missing. With `interview_id`, only that interview."""
    last_upload = (
        select(func.max(RecordingChunk.uploaded_at))
        .where(RecordingChunk.attempt_id == InterviewAttempt.id)
        .correlate(InterviewAttempt)
        .scalar_subquery()
    )
    unsettled = exists().where(
        InterviewAttempt.interview_id == Interview.id,
        InterviewAttempt.recording_stopped_at.is_(None),
        func.greatest(
            func.coalesce(InterviewAttempt.ended_at, now),
            func.coalesce(last_upload, InterviewAttempt.started_at),
        )
        > now - quiet,
    )
    statement = (
        select(Interview.workspace_id, Interview.id)
        .where(
            Interview.status == "completed",
            Interview.recording_status.in_(RECORDING_PENDING),
            (Interview.completed_at < now - latest) | ~unsettled,
        )
        .order_by(Interview.completed_at)
        .limit(200)
    )
    if interview_id is not None:
        statement = statement.where(Interview.id == interview_id)
    rows = await session.execute(statement)
    return [(row.workspace_id, row.id) for row in rows]


class RecordingChunkRepository(WorkspaceRepository[RecordingChunk]):
    model = RecordingChunk

    async def add_if_new(self, chunk: RecordingChunk) -> None:
        """Stores the chunk unless it is already registered (the browser retried)."""
        if chunk.workspace_id != self.workspace_id:
            raise ValueError("recording chunk belongs to another workspace")
        await self.session.execute(
            insert(RecordingChunk)
            .values(
                id=chunk.id,
                workspace_id=chunk.workspace_id,
                interview_id=chunk.interview_id,
                attempt_id=chunk.attempt_id,
                seq=chunk.seq,
                path=chunk.path,
                bytes=chunk.bytes,
                uploaded_at=chunk.uploaded_at,
            )
            .on_conflict_do_nothing(constraint="recording_chunks_attempt_id_seq_key")
        )

    async def count_of_interview(self, interview_id: uuid.UUID) -> int:
        count: int = (
            await self.session.scalar(
                self._scoped(select(func.count()).select_from(RecordingChunk)).where(
                    RecordingChunk.interview_id == interview_id
                )
            )
            or 0
        )
        return count

    async def delete_of_interview(self, interview_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(RecordingChunk).where(
                RecordingChunk.workspace_id == self.workspace_id,
                RecordingChunk.interview_id == interview_id,
            )
        )
