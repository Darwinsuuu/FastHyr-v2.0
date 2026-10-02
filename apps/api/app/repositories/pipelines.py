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

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import CompanyProfile, Department, Pipeline, Workspace
from app.repositories.base import WorkspaceRepository

# Statuses the close-on-schedule cron looks at (WORKFLOW.md §2).
OPEN_STATUSES = ("live", "paused", "paused_no_credits")


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
        statement = super()._scoped(statement)
        if self.department_ids is not None:
            statement = statement.where(Pipeline.department_id.in_(self.department_ids))
        return statement

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
