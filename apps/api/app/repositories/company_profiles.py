"""The company profile of one workspace (FR-WS-01), and the narrow public read the branding
image route needs."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import CompanyProfile, Workspace
from app.repositories.base import WorkspaceRepository


class CompanyProfileRepository(WorkspaceRepository[CompanyProfile]):
    model = CompanyProfile

    async def get(self) -> CompanyProfile:
        row: CompanyProfile | None = await self.session.scalar(self._scoped())
        if row is None:
            raise NotFoundError()
        return row

    async def set_workspace_timezone(self, timezone: str) -> None:
        """Business-day email delays use the workspace's time zone (DATABASE.md)."""
        await self.session.execute(
            update(Workspace).where(Workspace.id == self.workspace_id).values(timezone=timezone)
        )


@dataclass(frozen=True)
class BrandingRow:
    company_name: str
    logo_path: str | None
    banner_path: str | None
    updated_at: datetime


async def branding_of(session: AsyncSession, workspace_id: uuid.UUID) -> BrandingRow | None:
    """Only the fields candidates and email clients may see: the name and image paths. Used
    without a member's context (public branding route, emails)."""
    row = (
        await session.execute(
            select(
                CompanyProfile.company_name,
                CompanyProfile.logo_path,
                CompanyProfile.banner_path,
                CompanyProfile.updated_at,
            ).where(CompanyProfile.workspace_id == workspace_id)
        )
    ).one_or_none()
    return BrandingRow(*row) if row else None


async def workspace_timezone(session: AsyncSession, workspace_id: uuid.UUID) -> str | None:
    """The time zone candidate emails are timed and written in (MSG-003): the company profile's,
    else the workspace's."""
    timezone: str | None = await session.scalar(
        select(func.coalesce(CompanyProfile.timezone, Workspace.timezone))
        .select_from(Workspace)
        .outerjoin(CompanyProfile, CompanyProfile.workspace_id == Workspace.id)
        .where(Workspace.id == workspace_id)
    )
    return timezone
