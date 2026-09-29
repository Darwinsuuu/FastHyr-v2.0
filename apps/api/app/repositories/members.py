"""Members of one workspace and their department access (FR-WS-04, FR-WS-05)."""

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import Select, delete, func, select

from app.core.errors import NotFoundError
from app.models import Department, MemberDepartment, Profile, WorkspaceMember
from app.repositories.base import WorkspaceRepository

ACTIVE = "active"
REMOVED = "removed"


@dataclass(frozen=True)
class MemberRow:
    member: WorkspaceMember
    full_name: str | None
    email: str | None
    avatar_url: str | None


class MemberRepository(WorkspaceRepository[WorkspaceMember]):
    model = WorkspaceMember

    async def list_active(self) -> list[MemberRow]:
        rows = await self.session.execute(
            self._with_profiles()
            .where(WorkspaceMember.status == ACTIVE)
            .order_by(
                WorkspaceMember.is_owner.desc(),
                func.lower(func.coalesce(Profile.full_name, Profile.email)),
                WorkspaceMember.id,
            )
        )
        return [MemberRow(member, name, email, avatar) for member, name, email, avatar in rows]

    async def get_active(self, member_id: uuid.UUID) -> WorkspaceMember:
        """The active member, or 404: removed members and other workspaces' read as missing."""
        member: WorkspaceMember | None = await self.session.scalar(
            self._scoped().where(WorkspaceMember.id == member_id, WorkspaceMember.status == ACTIVE)
        )
        if member is None:
            raise NotFoundError()
        return member

    async def get_row(self, member_id: uuid.UUID) -> MemberRow:
        rows = await self.session.execute(
            self._with_profiles().where(WorkspaceMember.id == member_id)
        )
        member, name, email, avatar = rows.one()
        return MemberRow(member, name, email, avatar)

    def _with_profiles(
        self,
    ) -> Select[WorkspaceMember, str | None, str | None, str | None]:
        return (
            select(WorkspaceMember, Profile.full_name, Profile.email, Profile.avatar_url)
            .join(Profile, Profile.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == self.workspace_id)
        )

    async def departments_by_member(self) -> dict[uuid.UUID, list[tuple[uuid.UUID, str]]]:
        """Each member's departments as (id, name), sorted by name."""
        rows = await self.session.execute(
            select(MemberDepartment.member_id, Department.id, Department.name)
            .join(
                Department,
                (Department.workspace_id == MemberDepartment.workspace_id)
                & (Department.id == MemberDepartment.department_id),
            )
            .where(MemberDepartment.workspace_id == self.workspace_id)
            .order_by(func.lower(Department.name), Department.id)
        )
        result: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = {}
        for member_id, department_id, name in rows:
            result.setdefault(member_id, []).append((department_id, name))
        return result

    async def existing_department_ids(self, ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
        wanted = list(set(ids))
        if not wanted:
            return set()
        rows = await self.session.scalars(
            select(Department.id).where(
                Department.workspace_id == self.workspace_id, Department.id.in_(wanted)
            )
        )
        return set(rows)

    async def set_departments(
        self, member: WorkspaceMember, department_ids: Sequence[uuid.UUID]
    ) -> None:
        await self.session.execute(
            delete(MemberDepartment).where(
                MemberDepartment.workspace_id == self.workspace_id,
                MemberDepartment.member_id == member.id,
            )
        )
        self.session.add_all(
            MemberDepartment(
                workspace_id=self.workspace_id, member_id=member.id, department_id=department_id
            )
            for department_id in dict.fromkeys(department_ids)
        )
        await self.session.flush()

    async def mark_removed(self, member: WorkspaceMember) -> None:
        member.status = REMOVED
        await self.set_departments(member, [])
