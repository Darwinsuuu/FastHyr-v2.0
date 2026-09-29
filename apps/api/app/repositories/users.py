"""Queries keyed by the signed-in user rather than a workspace: their profile, their
memberships (to resolve `X-Workspace-Id`) and their workspace list. MULTI_TENANCY.md §2 lists
these as the only reads that cross workspaces, and they only ever return the user's own rows."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MemberDepartment, Profile, Workspace, WorkspaceMember

ACTIVE = "active"
# How stale `last_active_at` may get before a request writes it again (WS-003).
LAST_ACTIVE_EVERY = timedelta(minutes=5)


@dataclass(frozen=True)
class MembershipRow:
    workspace_id: uuid.UUID
    workspace_name: str
    workspace_slug: str
    role: str
    is_owner: bool
    member_count: int


class UserRepository:
    def __init__(self, session: AsyncSession, user_id: uuid.UUID) -> None:
        self.session = session
        self.user_id = user_id

    async def get_profile(self) -> Profile | None:
        profile: Profile | None = await self.session.get(Profile, self.user_id)
        return profile

    async def get_active_membership(self, workspace_id: uuid.UUID) -> WorkspaceMember | None:
        member: WorkspaceMember | None = await self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == self.user_id,
                WorkspaceMember.status == ACTIVE,
            )
        )
        return member

    async def touch_last_active(self, member: WorkspaceMember) -> None:
        """Records activity at most every `LAST_ACTIVE_EVERY`, so most requests write nothing."""
        seen = member.last_active_at
        if seen is not None and datetime.now(UTC) - seen < LAST_ACTIVE_EVERY:
            return
        await self.session.execute(
            update(WorkspaceMember)
            .where(
                WorkspaceMember.id == member.id,
                or_(
                    WorkspaceMember.last_active_at.is_(None),
                    WorkspaceMember.last_active_at < func.now() - LAST_ACTIVE_EVERY,
                ),
            )
            .values(last_active_at=func.now())
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()

    async def department_ids(self, member: WorkspaceMember) -> frozenset[uuid.UUID]:
        rows = await self.session.scalars(
            select(MemberDepartment.department_id).where(
                MemberDepartment.workspace_id == member.workspace_id,
                MemberDepartment.member_id == member.id,
            )
        )
        return frozenset(rows)

    async def list_memberships(self, workspace_id: uuid.UUID | None = None) -> list[MembershipRow]:
        """The user's active memberships, or just the one in `workspace_id` if given."""
        counts = (
            select(WorkspaceMember.workspace_id, func.count().label("member_count"))
            .where(WorkspaceMember.status == ACTIVE)
            .group_by(WorkspaceMember.workspace_id)
            .subquery()
        )
        rows = await self.session.execute(
            select(
                Workspace.id,
                Workspace.name,
                Workspace.slug,
                WorkspaceMember.role,
                WorkspaceMember.is_owner,
                counts.c.member_count,
            )
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .join(counts, counts.c.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == self.user_id, WorkspaceMember.status == ACTIVE)
            .where(Workspace.id == workspace_id if workspace_id else true())
            .order_by(Workspace.name, Workspace.id)
        )
        return [MembershipRow(*row) for row in rows]
