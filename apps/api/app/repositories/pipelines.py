"""Pipelines of one workspace, limited to the caller's departments (MULTI_TENANCY.md §2).

A repository built with `department_ids` only reaches pipelines in those departments, so a
Recruiter or Hiring manager never sees one in another department or in No department: it reads as
missing (404). Admins and background jobs pass `department_ids=None` and see every pipeline.
"""

import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import (
    Application,
    CompanyProfile,
    Department,
    Pipeline,
    Profile,
    Workspace,
    WorkspaceMember,
)
from app.repositories.base import WorkspaceRepository

# Statuses the close-on-schedule cron looks at (WORKFLOW.md §2).
OPEN_STATUSES = ("live", "paused", "paused_no_credits")


@dataclass(frozen=True)
class PipelineListRow:
    """One row of the Pipelines list (PIPE-004): the pipeline, its department and owner, and how
    many people applied and are waiting on a review."""

    pipeline: Pipeline
    department_name: str | None
    owner_user_id: uuid.UUID | None
    owner_name: str | None
    owner_email: str | None
    owner_avatar_url: str | None
    candidates: int
    to_review: int


class PipelineRepository(WorkspaceRepository[Pipeline]):
    model = Pipeline

    def __init__(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        *,
        department_ids: Collection[uuid.UUID] | None,
    ) -> None:
        super().__init__(session, workspace_id)
        self.department_ids = None if department_ids is None else list(department_ids)

    def _scoped(self, statement: Select[Any] | None = None) -> Select[Any]:
        statement = statement if statement is not None else select(Pipeline)
        return statement.where(*self._in_scope())

    def _in_scope(self) -> list[ColumnElement[bool]]:
        """The workspace and, unless `department_ids` is None, the caller's departments, for
        statements that select more than one column."""
        clauses = [Pipeline.workspace_id == self.workspace_id]
        if self.department_ids is not None:
            clauses.append(Pipeline.department_id.in_(self.department_ids))
        return clauses

    async def get(self, pipeline_id: uuid.UUID) -> Pipeline:
        return await self._get_or_404(pipeline_id)

    async def lock(self, pipeline_id: uuid.UUID) -> Pipeline:
        """Holds the workspace row, then the pipeline row, `FOR UPDATE` until the transaction
        ends: the same order as services/credits.py, so the two never deadlock."""
        locked = await self.session.scalar(
            select(Workspace.id).where(Workspace.id == self.workspace_id).with_for_update()
        )
        if locked is None:
            raise NotFoundError()
        pipeline: Pipeline | None = await self.session.scalar(
            self._scoped()
            .where(Pipeline.id == pipeline_id)
            .with_for_update()
            # An earlier read in this session may be stale; take the row as locked.
            .execution_options(populate_existing=True)
        )
        if pipeline is None:
            raise NotFoundError()
        return pipeline

    async def add(self, pipeline: Pipeline) -> Pipeline:
        self.session.add(pipeline)
        await self.session.flush()
        await self.session.refresh(pipeline)
        return pipeline

    # -- The Pipelines list (PIPE-004) ---------------------------------------------------------
    async def count_by_status(self) -> dict[str, int]:
        """How many pipelines the list holds per status (archived ones are left out)."""
        rows = await self.session.execute(
            select(Pipeline.status, func.count())
            .where(*self._in_scope(), Pipeline.archived_at.is_(None))
            .group_by(Pipeline.status)
        )
        return {status: count for status, count in rows}

    async def to_review(self) -> int:
        """Candidates ready for a review across the caller's open pipelines (the greeting)."""
        count: int = (
            await self.session.scalar(
                self._scoped(select(func.count()).select_from(Pipeline))
                .join(Application, Application.pipeline_id == Pipeline.id)
                .where(Pipeline.status.in_(OPEN_STATUSES), Pipeline.archived_at.is_(None))
                .where(Application.workspace_id == self.workspace_id, _waiting_on_review())
            )
            or 0
        )
        return count

    async def list_page(
        self, *, statuses: Collection[str], query: str, offset: int, limit: int
    ) -> tuple[list[PipelineListRow], int]:
        """One page of the list and how many pipelines match, needing attention first:
        out of credits, then open pipelines with candidates to review (most first), the rest
        of the open ones (closing soonest first), scheduled (opening soonest), drafts (edited
        last first) and finally closed or cancelled (ended last first)."""
        counts = (
            select(
                Application.pipeline_id,
                func.count().label("candidates"),
                func.count().filter(_waiting_on_review()).label("to_review"),
            )
            .where(Application.workspace_id == self.workspace_id)
            .group_by(Application.pipeline_id)
            .subquery()
        )
        candidates = func.coalesce(counts.c.candidates, 0)
        to_review = func.coalesce(counts.c.to_review, 0)
        statement = (
            select(
                Pipeline,
                Department.name,
                Profile.id,
                Profile.full_name,
                Profile.email,
                Profile.avatar_url,
                candidates,
                to_review,
            )
            .outerjoin(
                Department,
                and_(
                    Department.workspace_id == Pipeline.workspace_id,
                    Department.id == Pipeline.department_id,
                ),
            )
            .outerjoin(
                WorkspaceMember,
                and_(
                    WorkspaceMember.workspace_id == Pipeline.workspace_id,
                    WorkspaceMember.id == Pipeline.owner_id,
                ),
            )
            .outerjoin(Profile, Profile.id == WorkspaceMember.user_id)
            .outerjoin(counts, counts.c.pipeline_id == Pipeline.id)
            .where(
                *self._in_scope(),
                Pipeline.archived_at.is_(None),
                Pipeline.status.in_(list(statuses)),
            )
        )
        if query:
            statement = statement.where(
                or_(
                    Pipeline.title.icontains(query, autoescape=True),
                    Department.name.icontains(query, autoescape=True),
                )
            )
        total: int = (
            await self.session.scalar(
                select(func.count()).select_from(statement.order_by(None).subquery())
            )
            or 0
        )

        rank = case(
            (Pipeline.status == "paused_no_credits", 0),
            (and_(Pipeline.status.in_(OPEN_STATUSES), to_review > 0), 1),
            (Pipeline.status.in_(OPEN_STATUSES), 2),
            (Pipeline.status == "scheduled", 3),
            (Pipeline.status == "draft", 4),
            else_=5,
        )
        rows = await self.session.execute(
            statement.order_by(
                rank,
                to_review.desc(),
                case((rank <= 2, Pipeline.closes_at)).asc().nulls_last(),
                case((rank == 3, Pipeline.opens_at)).asc().nulls_last(),
                case((rank == 4, Pipeline.updated_at)).desc().nulls_last(),
                case((rank == 5, Pipeline.ended_at)).desc().nulls_last(),
                Pipeline.created_at.desc(),
                Pipeline.id,
            )
            .offset(offset)
            .limit(limit)
        )
        return [PipelineListRow(*row) for row in rows], total

    async def department_exists(self, department_id: uuid.UUID) -> bool:
        found = await self.session.scalar(
            select(Department.id).where(
                Department.workspace_id == self.workspace_id, Department.id == department_id
            )
        )
        return found is not None

    async def slugs_like(self, base: str) -> set[str]:
        """Slugs in the workspace equal to `base` or starting with `base-` (whatever the
        caller's departments: slugs are unique across the workspace)."""
        rows = await self.session.scalars(
            select(Pipeline.slug).where(
                Pipeline.workspace_id == self.workspace_id,
                or_(Pipeline.slug == base, Pipeline.slug.startswith(f"{base}-", autoescape=True)),
            )
        )
        return {slug for slug in rows if slug is not None}


def _waiting_on_review() -> ColumnElement[bool]:
    """Ready for review and not flagged: flagged candidates wait under the Flagged filter
    until a person resolves their flags (WORKFLOW.md §3)."""
    return and_(Application.stage == "ready_for_review", Application.has_open_flags.is_(False))


async def due_to_open(
    session: AsyncSession, now: datetime
) -> Sequence[tuple[uuid.UUID, uuid.UUID]]:
    """(workspace_id, pipeline_id) of scheduled pipelines whose `opens_at` has come."""
    rows = await session.execute(
        select(Pipeline.workspace_id, Pipeline.id)
        .where(Pipeline.status == "scheduled", Pipeline.opens_at <= now)
        .order_by(Pipeline.opens_at)
    )
    return [(workspace_id, pipeline_id) for workspace_id, pipeline_id in rows]


async def due_to_close(
    session: AsyncSession, now: datetime
) -> Sequence[tuple[uuid.UUID, uuid.UUID]]:
    """(workspace_id, pipeline_id) of open pipelines whose `closes_at` has passed."""
    rows = await session.execute(
        select(Pipeline.workspace_id, Pipeline.id)
        .where(Pipeline.status.in_(OPEN_STATUSES), Pipeline.closes_at <= now)
        .order_by(Pipeline.closes_at)
    )
    return [(workspace_id, pipeline_id) for workspace_id, pipeline_id in rows]


async def out_of_credit_pipeline_ids(
    session: AsyncSession, workspace_id: uuid.UUID
) -> Sequence[uuid.UUID]:
    """Pipelines paused for credits that still have reserve left."""
    rows = await session.scalars(
        select(Pipeline.id).where(
            Pipeline.workspace_id == workspace_id,
            Pipeline.status == "paused_no_credits",
            Pipeline.credits_used < Pipeline.credits_reserved,
        )
    )
    return rows.all()


# The public apply page (APPLY-001): no member context, so no repository object.


@dataclass(frozen=True)
class PublicPipelineRow:
    """Only what a candidate may see. Must-haves, nice-to-haves, skills to probe, tone,
    seniority, weights, pass marks and credits are never read here."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_slug: str
    slug: str
    status: str
    title: str | None
    department: str | None
    employment_type: str | None
    work_setup: str | None
    location: str | None
    jd_text: str | None
    open_to: list[str]
    interview_format: str | None
    opens_at: datetime | None
    closes_at: datetime | None
    company_name: str
    website: str | None
    industry: str | None
    company_size: str | None
    hq_country: str | None
    about: str | None
    careers_url: str | None
    logo_path: str | None
    profile_updated_at: datetime
    timezone: str


# Drafts were never published and cancelled pipelines never opened: their links read as missing.
HIDDEN_STATUSES = ("draft", "cancelled")


async def public_pipeline_of(
    session: AsyncSession, workspace_slug: str, pipeline_slug: str
) -> PublicPipelineRow | None:
    row = (
        await session.execute(
            select(
                Pipeline.id,
                Pipeline.workspace_id,
                Workspace.slug,
                Pipeline.slug,
                Pipeline.status,
                Pipeline.title,
                Department.name,
                Pipeline.employment_type,
                Pipeline.work_setup,
                Pipeline.location,
                Pipeline.jd_text,
                Pipeline.open_to,
                Pipeline.interview_format,
                Pipeline.opens_at,
                Pipeline.closes_at,
                CompanyProfile.company_name,
                CompanyProfile.website,
                CompanyProfile.industry,
                CompanyProfile.company_size,
                CompanyProfile.hq_country,
                CompanyProfile.about,
                CompanyProfile.careers_url,
                CompanyProfile.logo_path,
                CompanyProfile.updated_at,
                func.coalesce(CompanyProfile.timezone, Workspace.timezone),
            )
            .join(Workspace, Workspace.id == Pipeline.workspace_id)
            .join(CompanyProfile, CompanyProfile.workspace_id == Pipeline.workspace_id)
            .outerjoin(
                Department,
                (Department.workspace_id == Pipeline.workspace_id)
                & (Department.id == Pipeline.department_id),
            )
            .where(
                Workspace.slug == workspace_slug,
                Pipeline.slug == pipeline_slug,
                Pipeline.status.not_in(HIDDEN_STATUSES),
            )
        )
    ).one_or_none()
    return PublicPipelineRow(*tuple[Any, ...](row)) if row else None
