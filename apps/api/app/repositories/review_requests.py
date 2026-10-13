"""Human review requests (ASMT-008, ADR-015): the review link a candidate opens, the requests a
workspace's team resolves, and who hears about a new one."""

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Application,
    Candidate,
    CompanyProfile,
    HumanReviewRequest,
    Pipeline,
    Profile,
    ReviewLink,
    WorkspaceMember,
)
from app.repositories.base import WorkspaceRepository


@dataclass(frozen=True)
class ReviewLinkRow:
    link: ReviewLink
    stage: str
    candidate_deleted_at: datetime | None
    job_title: str | None
    company_name: str
    website: str | None
    careers_url: str | None
    logo_path: str | None
    profile_updated_at: datetime


async def review_link_of(
    session: AsyncSession, token_hash: str, *, lock: bool = False
) -> ReviewLinkRow | None:
    """The link whose token hashes to `token_hash`, with what the page shows. Not
    workspace-scoped on purpose, like interview links: the token is the key, and the lookup is
    one equality match on the unique hash. `lock` locks the link and its application."""
    statement = (
        select(
            ReviewLink,
            Application.stage,
            Candidate.deleted_at,
            Pipeline.title,
            CompanyProfile.company_name,
            CompanyProfile.website,
            CompanyProfile.careers_url,
            CompanyProfile.logo_path,
            CompanyProfile.updated_at,
        )
        .join(
            Application,
            (Application.workspace_id == ReviewLink.workspace_id)
            & (Application.id == ReviewLink.application_id),
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
        .join(CompanyProfile, CompanyProfile.workspace_id == ReviewLink.workspace_id)
        .where(ReviewLink.token_hash == token_hash)
    )
    if lock:
        statement = statement.with_for_update(of=(ReviewLink, Application)).execution_options(
            populate_existing=True
        )
    row = (await session.execute(statement)).one_or_none()
    return ReviewLinkRow(*cast(Any, tuple(row))) if row else None


@dataclass(frozen=True)
class ReviewRequestRow:
    request: HumanReviewRequest
    stage: str
    candidate_id: uuid.UUID
    candidate_name: str
    pipeline_id: uuid.UUID
    pipeline_title: str | None


@dataclass(frozen=True)
class Recipient:
    email: str
    name: str | None


class ReviewRequestRepository(WorkspaceRepository[HumanReviewRequest]):
    model = HumanReviewRequest

    def add(self, request: HumanReviewRequest) -> None:
        if request.workspace_id != self.workspace_id:
            raise ValueError("review request belongs to another workspace")
        self.session.add(request)

    def _listed(self, department_ids: Collection[uuid.UUID] | None) -> Select[Any]:
        columns = cast(
            Select[Any],
            select(
                HumanReviewRequest,
                Application.stage,
                Candidate.id,
                Candidate.full_name,
                Pipeline.id,
                Pipeline.title,
            ),
        )
        statement = (
            self._scoped(columns)
            .join(
                Application,
                (Application.workspace_id == HumanReviewRequest.workspace_id)
                & (Application.id == HumanReviewRequest.application_id),
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
            .where(Candidate.deleted_at.is_(None))
        )
        if department_ids is not None:
            # No department is Admins only (null is never in the list).
            statement = statement.where(Pipeline.department_id.in_(list(department_ids)))
        return statement

    async def get_scoped(
        self,
        request_id: uuid.UUID,
        *,
        department_ids: Collection[uuid.UUID] | None,
        lock: bool = False,
    ) -> ReviewRequestRow | None:
        """The request, when its pipeline is in `department_ids` (None: every department). `lock`
        locks the request and its application and re-reads them."""
        statement = self._listed(department_ids).where(HumanReviewRequest.id == request_id)
        if lock:
            statement = statement.with_for_update(
                of=(HumanReviewRequest, Application)
            ).execution_options(populate_existing=True)
        row = (await self.session.execute(statement)).one_or_none()
        return ReviewRequestRow(*tuple(row)) if row else None

    async def page(
        self,
        *,
        status: str | None,
        department_ids: Collection[uuid.UUID] | None,
        limit: int,
    ) -> tuple[list[ReviewRequestRow], int]:
        """Requests oldest first (the longest wait on top), and how many there are."""
        statement = self._listed(department_ids)
        if status is not None:
            statement = statement.where(HumanReviewRequest.status == status)
        total = await self.session.scalar(select(func.count()).select_from(statement.subquery()))
        rows = await self.session.execute(
            statement.order_by(HumanReviewRequest.created_at, HumanReviewRequest.id).limit(limit)
        )
        return [ReviewRequestRow(*tuple(row)) for row in rows], total or 0

    async def latest_of(self, application_id: uuid.UUID) -> list[HumanReviewRequest]:
        """The application's requests, oldest first (the profile's banner and journey)."""
        rows = await self.session.scalars(
            self._scoped()
            .where(HumanReviewRequest.application_id == application_id)
            .order_by(HumanReviewRequest.created_at)
        )
        return list(rows)

    async def recipients(self, pipeline_id: uuid.UUID) -> list[Recipient]:
        """Who hears about a new request (NOTIFICATIONS.md §4): the pipeline's owner while they
        are still a member, else the workspace's Admins."""
        owner = (
            await self.session.execute(
                select(Profile.email, Profile.full_name)
                .join(WorkspaceMember, WorkspaceMember.user_id == Profile.id)
                .join(
                    Pipeline,
                    (Pipeline.workspace_id == WorkspaceMember.workspace_id)
                    & (Pipeline.owner_id == WorkspaceMember.id),
                )
                .where(
                    Pipeline.workspace_id == self.workspace_id,
                    Pipeline.id == pipeline_id,
                    WorkspaceMember.status == "active",
                    Profile.email.is_not(None),
                )
            )
        ).one_or_none()
        if owner is not None:
            return [Recipient(owner.email, owner.full_name)]
        admins = await self.session.execute(
            select(Profile.email, Profile.full_name)
            .join(WorkspaceMember, WorkspaceMember.user_id == Profile.id)
            .where(
                WorkspaceMember.workspace_id == self.workspace_id,
                WorkspaceMember.role == "admin",
                WorkspaceMember.status == "active",
                Profile.email.is_not(None),
            )
            .order_by(Profile.email)
        )
        return [Recipient(row.email, row.full_name) for row in admins]
