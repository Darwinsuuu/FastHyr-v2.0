"""Creating and joining workspaces: the writes that happen before the caller is a member, so
they can't go through a `WorkspaceRepository` (there is no workspace in the request yet).

Reads here are limited to what creating or joining needs: whether a slug is taken, and the
invite a signed-in user typed the code of. Services check the invite is addressed to them.
"""

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CompanyProfile,
    Department,
    Invite,
    MemberDepartment,
    Profile,
    Workspace,
    WorkspaceMember,
)


class WorkspaceSetupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def slugs_like(self, base: str) -> set[str]:
        """Taken slugs equal to `base` or starting with `base-`, to pick the next free one."""
        rows = await self.session.scalars(
            select(Workspace.slug).where(
                (Workspace.slug == base) | Workspace.slug.startswith(f"{base}-", autoescape=True)
            )
        )
        return set(rows)

    async def add_workspace(
        self, *, name: str, slug: str, owner_id: uuid.UUID, trial_granted_at: datetime
    ) -> Workspace:
        workspace = Workspace(
            name=name, slug=slug, owner_id=owner_id, trial_granted_at=trial_granted_at
        )
        self.session.add(workspace)
        await self.session.flush()
        self.session.add(CompanyProfile(workspace_id=workspace.id, company_name=name))
        return workspace

    async def get_invite_by_code(self, code: str) -> Invite | None:
        invite: Invite | None = await self.session.scalar(
            select(Invite).where(Invite.code == code).with_for_update()
        )
        return invite

    async def get_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        member: WorkspaceMember | None = await self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
            )
        )
        return member

    async def add_member(
        self, *, workspace_id: uuid.UUID, user_id: uuid.UUID, role: str, is_owner: bool = False
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id, user_id=user_id, role=role, is_owner=is_owner
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def set_member_departments(
        self, member: WorkspaceMember, department_ids: list[uuid.UUID]
    ) -> None:
        """Replaces the member's departments with those of `department_ids` that still exist in
        the member's workspace."""
        await self.session.execute(
            delete(MemberDepartment).where(MemberDepartment.member_id == member.id)
        )
        existing = await self.session.scalars(
            select(Department.id).where(
                Department.workspace_id == member.workspace_id, Department.id.in_(department_ids)
            )
        )
        for department_id in existing:
            self.session.add(
                MemberDepartment(
                    workspace_id=member.workspace_id,
                    member_id=member.id,
                    department_id=department_id,
                )
            )

    async def set_last_workspace(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
        profile = await self.session.get(Profile, user_id)
        if profile is not None:
            profile.last_workspace_id = workspace_id
