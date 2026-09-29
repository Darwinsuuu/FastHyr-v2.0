"""Member invites of one workspace (FR-WS-03)."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Department, Invite, Profile, WorkspaceMember
from app.repositories.base import WorkspaceRepository

PENDING = "pending"


@dataclass(frozen=True)
class InviteRow:
    invite: Invite
    invited_by_name: str | None


class InviteRepository(WorkspaceRepository[Invite]):
    model = Invite

    async def list_pending(self, now: datetime) -> list[InviteRow]:
        """Pending invites that can still be accepted, most recently sent first."""
        rows = await self.session.execute(
            self._with_inviter()
            .where(Invite.status == PENDING, Invite.expires_at > now)
            .order_by(Invite.expires_at.desc(), Invite.id)
        )
        return [InviteRow(invite, name) for invite, name in rows]

    async def get_row(self, invite_id: uuid.UUID) -> InviteRow:
        rows = await self.session.execute(self._with_inviter().where(Invite.id == invite_id))
        invite, name = rows.one()
        return InviteRow(invite, name)

    def _with_inviter(self) -> Select[Invite, str | None]:
        return (
            select(Invite, func.coalesce(Profile.full_name, Profile.email))
            .join(Profile, Profile.id == Invite.invited_by)
            .where(Invite.workspace_id == self.workspace_id)
        )

    async def get_pending(self, invite_id: uuid.UUID, now: datetime) -> Invite:
        """The invite if it can still be accepted, or 404: accepted, revoked, expired and other
        workspaces' invites read as missing."""
        invite: Invite | None = await self.session.scalar(
            self._scoped()
            .where(Invite.id == invite_id, Invite.status == PENDING, Invite.expires_at > now)
            .with_for_update()
        )
        if invite is None:
            raise NotFoundError()
        return invite

    async def find_pending_for_email(self, email: str) -> Invite | None:
        """The one pending invite for this email, even if past its expiry (the unique index
        counts it until the expiry job marks it expired)."""
        invite: Invite | None = await self.session.scalar(
            self._scoped().where(Invite.email == email, Invite.status == PENDING).with_for_update()
        )
        return invite

    async def is_active_member(self, email: str) -> bool:
        member_id = await self.session.scalar(
            select(WorkspaceMember.id)
            .join(Profile, Profile.id == WorkspaceMember.user_id)
            .where(
                WorkspaceMember.workspace_id == self.workspace_id,
                WorkspaceMember.status == "active",
                func.lower(Profile.email) == email,
            )
            .limit(1)
        )
        return member_id is not None

    async def department_names(self) -> dict[uuid.UUID, str]:
        rows = await self.session.execute(
            select(Department.id, Department.name).where(
                Department.workspace_id == self.workspace_id
            )
        )
        return {department_id: name for department_id, name in rows}

    def add(self, invite: Invite) -> None:
        self.session.add(invite)


async def expire_overdue_invites(session: AsyncSession, now: datetime) -> int:
    """For the expiry job, which runs across workspaces: marks every pending invite past its
    expiry as expired. Returns how many."""
    result = await session.execute(
        update(Invite)
        .where(Invite.status == PENDING, Invite.expires_at <= now)
        .values(status="expired")
        .returning(Invite.id)
    )
    return len(result.all())
