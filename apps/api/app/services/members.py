"""Members (FR-WS-04, FR-WS-05): Admins see who has access, change a member's role and
departments, or remove their access.

Changes apply on the member's next request, because `RequestContext` loads role and departments
on every request. The owner is always an Admin and can't be removed, and Admins can't change their
own access, so a workspace always keeps an Admin and nobody locks themselves out.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, Role
from app.core.errors import OwnAccessLockedError, OwnerAccessLockedError, UnknownDepartmentError
from app.models import WorkspaceMember
from app.repositories.audit import AuditRepository
from app.repositories.members import MemberRepository, MemberRow
from app.schemas.members import Member, MemberDepartment, MemberList, UpdateMemberRequest


async def list_members(session: AsyncSession, ctx: RequestContext) -> MemberList:
    repo = MemberRepository(session, ctx.workspace_id)
    departments = await repo.departments_by_member()
    return MemberList(
        members=[
            _member(ctx, row, departments.get(row.member.id, []))
            for row in await repo.list_active()
        ]
    )


async def update_member(
    session: AsyncSession, ctx: RequestContext, member_id: uuid.UUID, body: UpdateMemberRequest
) -> Member:
    repo = MemberRepository(session, ctx.workspace_id)
    member = await repo.get_active(member_id)
    _check_changeable(ctx, member)

    before = await repo.departments_by_member()
    old_role = member.role
    old_departments = sorted(str(d) for d, _ in before.get(member.id, []))

    role = body.role or Role(member.role)
    if role is Role.ADMIN:
        department_ids: list[uuid.UUID] = []  # Admins see every department
    elif body.department_ids is not None:
        department_ids = list(dict.fromkeys(body.department_ids))
        if await repo.existing_department_ids(department_ids) != set(department_ids):
            raise UnknownDepartmentError()
    else:
        department_ids = [d for d, _ in before.get(member.id, [])]

    member.role = role.value
    await repo.set_departments(member, department_ids)
    new_departments = sorted(str(d) for d in department_ids)
    if (old_role, old_departments) != (member.role, new_departments):
        AuditRepository(session, ctx.workspace_id).record(
            actor_id=ctx.user_id,
            action="member.access_changed",
            entity_type="workspace_member",
            entity_id=member.id,
            data={
                "from": {"role": old_role, "department_ids": old_departments},
                "to": {"role": member.role, "department_ids": new_departments},
            },
        )
    await session.commit()

    row = await repo.get_row(member.id)
    after = await repo.departments_by_member()
    return _member(ctx, row, after.get(member.id, []))


async def remove_member(session: AsyncSession, ctx: RequestContext, member_id: uuid.UUID) -> None:
    """Access ends on their next request. The row stays (status `removed`), so an invite can bring
    them back later and their past actions keep a name."""
    repo = MemberRepository(session, ctx.workspace_id)
    member = await repo.get_active(member_id)
    _check_changeable(ctx, member)
    await repo.mark_removed(member)
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action="member.removed",
        entity_type="workspace_member",
        entity_id=member.id,
        data={"role": member.role},
    )
    await session.commit()


def _check_changeable(ctx: RequestContext, member: WorkspaceMember) -> None:
    if member.is_owner:
        raise OwnerAccessLockedError()
    if member.id == ctx.member_id:
        raise OwnAccessLockedError()


def _member(
    ctx: RequestContext, row: MemberRow, departments: list[tuple[uuid.UUID, str]]
) -> Member:
    member = row.member
    role = Role(member.role)
    return Member(
        id=member.id,
        user_id=member.user_id,
        full_name=row.full_name,
        email=row.email,
        avatar_url=row.avatar_url,
        role=role,
        is_owner=member.is_owner,
        is_you=member.id == ctx.member_id,
        departments=[]
        if role is Role.ADMIN
        else [MemberDepartment(id=d, name=name) for d, name in departments],
        last_active_at=member.last_active_at,
        status="active",
        joined_at=member.created_at,
    )
