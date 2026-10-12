"""One pipeline's applications for the Candidates tab (PIPE-008), in one workspace.

The caller checks the pipeline is in their departments first (`PipelineRepository.get`). Built
with `shortlist=True` (Hiring managers, SECURITY.md §2), the repository only reaches shortlisted
applications: ready for review, flagged, or advanced.
"""

import uuid
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, and_, case, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, Assessment, Candidate, IntegrityFlag, ResumeAssessment

# Stages a flag holds back from the Ready for review and Didn't pass filters (WORKFLOW.md §3).
FLAGGABLE_STAGES = ("ready_for_review", "did_not_pass")

# Needing attention first: waiting on a review, then on the candidate or the AI, then decided.
STAGE_ORDER = (
    "ready_for_review",
    "interview_in_progress",
    "scoring",
    "invited",
    "processing_resume",
    "advanced",
    "did_not_pass",
    "resume_not_match",
    "rejected",
)


def _flagged() -> ColumnElement[bool]:
    return and_(Application.has_open_flags, Application.stage.in_(FLAGGABLE_STAGES))


def _stage(*stages: str) -> ColumnElement[bool]:
    return Application.stage.in_(stages)


def filters() -> dict[str, ColumnElement[bool]]:
    """Each stage filter as a condition on the application (CandidateFilter)."""
    return {
        "all": true(),
        "processing": _stage("processing_resume"),
        "not_a_match": _stage("resume_not_match"),
        "invited": _stage("invited"),
        "in_progress": _stage("interview_in_progress", "scoring"),
        "ready": and_(_stage("ready_for_review"), ~_flagged()),
        "did_not_pass": and_(_stage("did_not_pass"), ~_flagged()),
        "flagged": _flagged(),
        "review_requested": Application.review_requested.is_(True),
        "advanced": _stage("advanced"),
        "rejected": _stage("rejected"),
    }


@dataclass(frozen=True)
class CandidateRow:
    application: Application
    candidate_id: uuid.UUID
    name: str
    email: str


@dataclass(frozen=True)
class RowDetails:
    """What the fit explanation needs, read for one page of rows."""

    must_haves: dict[uuid.UUID, tuple[int, int]]
    criteria: dict[uuid.UUID, dict[str, Any]]
    flag_types: dict[uuid.UUID, list[str]]


class PipelineCandidatesRepository:
    def __init__(self, session: AsyncSession, workspace_id: uuid.UUID, *, shortlist: bool) -> None:
        if not isinstance(workspace_id, uuid.UUID):
            raise TypeError("a pipeline candidates repository needs a workspace_id")
        self.session = session
        self.workspace_id = workspace_id
        self.shortlist = shortlist

    def _in_scope(self, pipeline_id: uuid.UUID) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = [
            Application.workspace_id == self.workspace_id,
            Application.pipeline_id == pipeline_id,
            Candidate.deleted_at.is_(None),
        ]
        if self.shortlist:
            clauses.append(or_(_stage("ready_for_review", "advanced"), _flagged()))
        return clauses

    def _with_candidate(self, statement: Any) -> Any:
        return statement.join(
            Candidate,
            and_(
                Candidate.workspace_id == Application.workspace_id,
                Candidate.id == Application.candidate_id,
            ),
        )

    async def counts(self, pipeline_id: uuid.UUID) -> dict[str, int]:
        """How many applications each filter holds."""
        columns = [
            func.count().filter(condition).label(name) for name, condition in filters().items()
        ]
        row = (
            await self.session.execute(
                self._with_candidate(select(*columns).select_from(Application)).where(
                    *self._in_scope(pipeline_id)
                )
            )
        ).one()
        return dict(row._mapping)

    async def page(
        self,
        pipeline_id: uuid.UUID,
        *,
        filter_name: str,
        query: str,
        offset: int,
        limit: int,
    ) -> tuple[list[CandidateRow], int]:
        """One page of the filter's applications matching `query` (name or email) and how many
        match: ready for review first, then flagged, in progress, scoring, invited, processing,
        advanced, didn't pass, not a match and rejected; higher scores, then newest, first."""
        where = [*self._in_scope(pipeline_id), filters()[filter_name]]
        if query:
            where.append(
                or_(
                    Candidate.full_name.icontains(query, autoescape=True),
                    Candidate.email.icontains(query, autoescape=True),
                )
            )
        total: int = (
            await self.session.scalar(
                self._with_candidate(select(func.count()).select_from(Application)).where(*where)
            )
            or 0
        )
        # Flagged candidates sort straight after the ready ones, whatever their stage.
        rank = case(
            (_flagged(), 1),
            (Application.stage == STAGE_ORDER[0], 0),
            *(
                (Application.stage == stage, index + 2)
                for index, stage in enumerate(STAGE_ORDER[1:])
            ),
            else_=len(STAGE_ORDER) + 1,
        )
        rows = await self.session.execute(
            self._with_candidate(
                select(Application, Candidate.id, Candidate.full_name, Candidate.email)
            )
            .where(*where)
            .order_by(
                rank,
                Application.overall_score.desc().nulls_last(),
                Application.applied_at.desc(),
                Application.id,
            )
            .offset(offset)
            .limit(limit)
        )
        return [CandidateRow(*row) for row in rows], total

    async def details(self, application_ids: Collection[uuid.UUID]) -> RowDetails:
        """Must-haves met (résumé screen), the latest assessment's criteria and the open flags'
        types for these applications."""
        ids = list(application_ids)
        if not ids:
            return RowDetails({}, {}, {})
        must_haves: dict[uuid.UUID, tuple[int, int]] = {}
        for application_id, results in await self.session.execute(
            select(ResumeAssessment.application_id, ResumeAssessment.must_have_results).where(
                ResumeAssessment.workspace_id == self.workspace_id,
                ResumeAssessment.application_id.in_(ids),
            )
        ):
            rows = list(results or [])
            must_haves[application_id] = (sum(1 for r in rows if r.get("met")), len(rows))
        criteria: dict[uuid.UUID, dict[str, Any]] = {}
        for application_id, values in await self.session.execute(
            select(Assessment.application_id, Assessment.criteria)
            .where(Assessment.workspace_id == self.workspace_id, Assessment.application_id.in_(ids))
            # Oldest first, so a re-invited candidate's latest assessment wins.
            .order_by(Assessment.created_at)
        ):
            criteria[application_id] = values or {}
        flag_types: dict[uuid.UUID, list[str]] = defaultdict(list)
        for application_id, flag_type in await self.session.execute(
            select(IntegrityFlag.application_id, IntegrityFlag.type)
            .where(
                IntegrityFlag.workspace_id == self.workspace_id,
                IntegrityFlag.application_id.in_(ids),
                IntegrityFlag.status == "open",
            )
            .order_by(IntegrityFlag.application_id, IntegrityFlag.start_ms, IntegrityFlag.type)
        ):
            if flag_type not in flag_types[application_id]:
                flag_types[application_id].append(flag_type)
        return RowDetails(must_haves, criteria, dict(flag_types))
