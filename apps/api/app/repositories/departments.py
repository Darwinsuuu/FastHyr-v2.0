"""Departments of one workspace and the counts the Departments page shows (FR-WS-02)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Select, Uuid, any_, delete, func, literal, select, update

from app.core.context import Role
from app.models import Department, Invite, MemberDepartment, Pipeline, Profile, WorkspaceMember
from app.repositories.base import WorkspaceRepository

ACTIVE = "active"


@dataclass(frozen=True)
class MemberRow:
    member_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str | None
    avatar_url: str | None
    role: str


class DepartmentRepository(WorkspaceRepository[Department]):
    model = Department

    async def list_all(self) -> Sequence[Department]:
        rows = await self.session.scalars(
            self._scoped().order_by(func.lower(Department.name), Department.id)
        )
        return rows.all()

    async def get(self, department_id: uuid.UUID) -> Department:
        return await self._get_or_404(department_id)

    async def name_taken(self, name: str, *, excluding: uuid.UUID | None = None) -> bool:
        statement = self._scoped(select(Department.id)).where(
            func.lower(Department.name) == name.lower()
        )
        if excluding is not None:
            statement = statement.where(Department.id != excluding)
        return await self.session.scalar(statement.limit(1)) is not None

    async def add(self, *, name: str, description: str | None) -> Department:
        department = Department(workspace_id=self.workspace_id, name=name, description=description)
        self.session.add(department)
        await self.session.flush()
        await self.session.refresh(department)
        return department

    async def pipeline_status_counts(self) -> list[tuple[uuid.UUID | None, str, int]]:
        """(department_id, status, count) for every pipeline; a null department is No department."""
        rows = await self.session.execute(
            select(Pipeline.department_id, Pipeline.status, func.count())
            .where(Pipeline.workspace_id == self.workspace_id)
            .group_by(Pipeline.department_id, Pipeline.status)
        )
        return [(department_id, status, count) for department_id, status, count in rows]

    async def active_admins(self) -> list[MemberRow]:
        rows = await self.session.execute(
            self._members().where(WorkspaceMember.role == Role.ADMIN.value)
        )
        return [MemberRow(*row) for row in rows]

    async def assigned_members(self) -> list[tuple[uuid.UUID, MemberRow]]:
        """(department_id, member) for active Recruiters and Hiring managers with access."""
        rows = await self.session.execute(
            self._members()
            .add_columns(MemberDepartment.department_id)
            .join(
                MemberDepartment,
                (MemberDepartment.workspace_id == WorkspaceMember.workspace_id)
                & (MemberDepartment.member_id == WorkspaceMember.id),
            )
            .where(WorkspaceMember.role != Role.ADMIN.value)
        )
        return [(row[-1], MemberRow(*row[:-1])) for row in rows]

    def _members(self) -> Select[uuid.UUID, uuid.UUID, str | None, str | None, str]:
        return (
            select(
                WorkspaceMember.id,
                WorkspaceMember.user_id,
                Profile.full_name,
                Profile.avatar_url,
                WorkspaceMember.role,
            )
            .join(Profile, Profile.id == WorkspaceMember.user_id)
            .where(
                WorkspaceMember.workspace_id == self.workspace_id,
                WorkspaceMember.status == ACTIVE,
            )
            .order_by(WorkspaceMember.created_at, WorkspaceMember.id)
        )

    async def move_pipelines_to_no_department(self, department_id: uuid.UUID) -> int:
        result = await self.session.execute(
            update(Pipeline)
            .where(
                Pipeline.workspace_id == self.workspace_id,
                Pipeline.department_id == department_id,
            )
            .values(department_id=None)
            .execution_options(synchronize_session=False)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def remove_from_pending_invites(self, department_id: uuid.UUID) -> None:
        """Invites keep department IDs in an array (no FK), so drop this one by hand."""
        await self.session.execute(
            update(Invite)
            .where(
                Invite.workspace_id == self.workspace_id,
                Invite.status == "pending",
                literal(department_id, Uuid) == any_(Invite.department_ids),
            )
            .values(department_ids=func.array_remove(Invite.department_ids, department_id))
            .execution_options(synchronize_session=False)
        )

    async def delete(self, department: Department) -> None:
        """Member access goes with it (member_departments cascades)."""
        await self.session.execute(
            delete(Department).where(
                Department.workspace_id == self.workspace_id, Department.id == department.id
            )
        )
