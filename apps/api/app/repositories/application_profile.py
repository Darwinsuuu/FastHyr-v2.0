"""Reads for the candidate profile (ASMT-004), in one workspace.

`ApplicationProfileRepository.application()` is the scope check: the application's pipeline must
be in the caller's departments (unless `department_ids` is None) and, built with
`shortlist=True` (Hiring managers, SECURITY.md §2), the application must be shortlisted: ready
for review, flagged, or advanced. Everything else is read for an application that passed it.
"""

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import (
    Application,
    Assessment,
    Candidate,
    IntegrityFlag,
    Interview,
    InterviewPlan,
    Pipeline,
    ResumeAssessment,
    Workspace,
)
from app.repositories.pipeline_candidates import FLAGGABLE_STAGES


@dataclass(frozen=True)
class ProfileRow:
    application: Application
    candidate: Candidate
    pipeline: Pipeline
    workspace_name: str


@dataclass(frozen=True)
class PipelineScore:
    """One completed, assessed interview in the pipeline: what the comparisons need."""

    application_id: uuid.UUID
    overall_score: int
    passed: bool
    criteria: dict[str, Any]
    topics: list[Any]
    answer_stats: dict[str, Any]


@dataclass(frozen=True)
class HistoryRow:
    application: Application
    pipeline_title: str


def shortlisted() -> ColumnElement[bool]:
    """Ready for review, advanced, or flagged (open flags on a ready or did-not-pass one)."""
    return or_(
        Application.stage.in_(("ready_for_review", "advanced")),
        and_(Application.has_open_flags, Application.stage.in_(FLAGGABLE_STAGES)),
    )


class ApplicationProfileRepository:
    def __init__(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        *,
        department_ids: Collection[uuid.UUID] | None,
        shortlist: bool,
    ) -> None:
        if not isinstance(workspace_id, uuid.UUID):
            raise TypeError("an application profile repository needs a workspace_id")
        self.session = session
        self.workspace_id = workspace_id
        self.department_ids = None if department_ids is None else list(department_ids)
        self.shortlist = shortlist

    def _in_scope(self) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = [
            Application.workspace_id == self.workspace_id,
            Candidate.deleted_at.is_(None),
        ]
        if self.department_ids is not None:
            # No department is Admins only (null is never in the list).
            clauses.append(Pipeline.department_id.in_(self.department_ids))
        if self.shortlist:
            clauses.append(shortlisted())
        return clauses

    @staticmethod
    def _joined(statement: Any) -> Any:
        return statement.join(
            Candidate,
            and_(
                Candidate.workspace_id == Application.workspace_id,
                Candidate.id == Application.candidate_id,
            ),
        ).join(
            Pipeline,
            and_(
                Pipeline.workspace_id == Application.workspace_id,
                Pipeline.id == Application.pipeline_id,
            ),
        )

    async def application(self, application_id: uuid.UUID) -> ProfileRow:
        """The application with its candidate, pipeline and workspace name; 404 outside the
        caller's reach."""
        row = (
            await self.session.execute(
                self._joined(select(Application, Candidate, Pipeline, Workspace.name))
                .join(Workspace, Workspace.id == Application.workspace_id)
                .where(*self._in_scope(), Application.id == application_id)
            )
        ).first()
        if row is None:
            raise NotFoundError()
        return ProfileRow(*row)

    async def resume_assessment(self, application_id: uuid.UUID) -> ResumeAssessment | None:
        result: ResumeAssessment | None = await self.session.scalar(
            select(ResumeAssessment).where(
                ResumeAssessment.workspace_id == self.workspace_id,
                ResumeAssessment.application_id == application_id,
            )
        )
        return result

    async def interview(self, application_id: uuid.UUID) -> Interview | None:
        """The application's live interview link (a re-invite supersedes the old one)."""
        result: Interview | None = await self.session.scalar(
            select(Interview).where(
                Interview.workspace_id == self.workspace_id,
                Interview.application_id == application_id,
                Interview.superseded_by.is_(None),
            )
        )
        return result

    async def assessment(self, application_id: uuid.UUID) -> Assessment | None:
        """The application's latest assessment."""
        result: Assessment | None = await self.session.scalar(
            select(Assessment)
            .where(
                Assessment.workspace_id == self.workspace_id,
                Assessment.application_id == application_id,
            )
            .order_by(Assessment.created_at.desc())
            .limit(1)
        )
        return result

    async def flags(self, interview_id: uuid.UUID) -> list[IntegrityFlag]:
        return list(
            await self.session.scalars(
                select(IntegrityFlag)
                .where(
                    IntegrityFlag.workspace_id == self.workspace_id,
                    IntegrityFlag.interview_id == interview_id,
                )
                .order_by(IntegrityFlag.start_ms, IntegrityFlag.type)
            )
        )

    async def pipeline_scores(self, pipeline_id: uuid.UUID) -> list[PipelineScore]:
        """Every assessed interview in the pipeline, the latest per application, whoever the
        caller is: the comparisons are aggregates (FR-ASMT-07)."""
        rows = await self.session.execute(
            select(
                Assessment.application_id,
                Assessment.overall_score,
                Assessment.passed,
                Assessment.criteria,
                Assessment.topics,
                Assessment.answer_stats,
            )
            .join(
                Application,
                and_(
                    Application.workspace_id == Assessment.workspace_id,
                    Application.id == Assessment.application_id,
                ),
            )
            .where(
                Assessment.workspace_id == self.workspace_id,
                Application.pipeline_id == pipeline_id,
            )
            .ext(distinct_on(Assessment.application_id))
            .order_by(Assessment.application_id, Assessment.created_at.desc())
        )
        return [
            PipelineScore(
                application_id=row.application_id,
                overall_score=row.overall_score,
                passed=row.passed,
                criteria=row.criteria or {},
                topics=row.topics or [],
                answer_stats=row.answer_stats or {},
            )
            for row in rows
        ]

    async def plan_topics(
        self, application_ids: Collection[uuid.UUID]
    ) -> dict[uuid.UUID, list[Any]]:
        """Each application's plan topics as `{kind, skills}`, for the topic averages."""
        ids = list(application_ids)
        if not ids:
            return {}
        rows = await self.session.execute(
            select(InterviewPlan.application_id, InterviewPlan.topics).where(
                InterviewPlan.workspace_id == self.workspace_id,
                InterviewPlan.application_id.in_(ids),
            )
        )
        return {
            application_id: [
                {"kind": topic.get("kind"), "skills": topic.get("skills") or []}
                for topic in topics or []
                if isinstance(topic, dict)
            ]
            for application_id, topics in rows
        }

    async def history(self, candidate_id: uuid.UUID) -> list[HistoryRow]:
        """The person's applications in this workspace the caller can see, oldest first."""
        rows = await self.session.execute(
            self._joined(select(Application, Pipeline.title))
            .where(*self._in_scope(), Application.candidate_id == candidate_id)
            .order_by(Application.applied_at, Application.id)
        )
        return [HistoryRow(application, title) for application, title in rows]
