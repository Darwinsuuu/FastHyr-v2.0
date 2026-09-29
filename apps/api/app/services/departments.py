"""Departments (FR-WS-02): Admins create, rename and delete them; every member can list them.

Names are unique per workspace ignoring case, and "No department" is reserved for pipelines
without one. Deleting a department moves its pipelines to No department, removes it from members'
access and from pending invites, and never deletes a pipeline or candidate.
"""

import uuid
from collections import defaultdict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, Role
from app.core.errors import DepartmentNameReservedError, DepartmentNameTakenError
from app.core.permissions import Action, can
from app.models import Department as DepartmentRow
from app.repositories.audit import AuditRepository
from app.repositories.departments import DepartmentRepository, MemberRow
from app.schemas.departments import (
    CreateDepartmentRequest,
    Department,
    DepartmentList,
    DepartmentMember,
    DepartmentStats,
    PipelineCounts,
    UpdateDepartmentRequest,
)

RESERVED_NAME = "no department"

# Pipeline statuses (WORKFLOW.md §2) grouped as the Departments page shows them.
STATUS_GROUPS = {
    "live": "active",
    "paused": "active",
    "paused_no_credits": "active",
    "scheduled": "scheduled",
    "closed": "closed",
    "cancelled": "closed",
    "draft": "draft",
}


def is_reserved(name: str) -> bool:
    return " ".join(name.split()).casefold() == RESERVED_NAME


async def list_departments(session: AsyncSession, ctx: RequestContext) -> DepartmentList:
    repo = DepartmentRepository(session, ctx.workspace_id)
    rows = await repo.list_all()
    if can(ctx, Action.MANAGE_WORKSPACE) is None:
        return DepartmentList(departments=[_department(row) for row in rows])

    counts: dict[uuid.UUID | None, PipelineCounts] = defaultdict(PipelineCounts)
    for department_id, status, count in await repo.pipeline_status_counts():
        group = STATUS_GROUPS[status]
        setattr(counts[department_id], group, getattr(counts[department_id], group) + count)

    admins = [_member(row) for row in await repo.active_admins()]
    assigned: dict[uuid.UUID, list[DepartmentMember]] = defaultdict(list)
    for department_id, row in await repo.assigned_members():
        assigned[department_id].append(_member(row))

    def stats(department_id: uuid.UUID | None) -> DepartmentStats:
        members = admins if department_id is None else admins + assigned[department_id]
        return DepartmentStats(pipelines=counts[department_id], candidate_count=0, members=members)

    return DepartmentList(
        departments=[_department(row, stats(row.id)) for row in rows],
        no_department=stats(None),
    )


async def create_department(
    session: AsyncSession, ctx: RequestContext, body: CreateDepartmentRequest
) -> Department:
    repo = DepartmentRepository(session, ctx.workspace_id)
    await _check_name(repo, body.name)
    try:
        row = await repo.add(name=body.name, description=body.description or None)
    except IntegrityError as error:  # another request took the name in between
        raise DepartmentNameTakenError() from error
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action="department.created",
        entity_type="department",
        entity_id=row.id,
        data={"name": row.name},
    )
    await session.commit()
    return _department(row)


async def update_department(
    session: AsyncSession,
    ctx: RequestContext,
    department_id: uuid.UUID,
    body: UpdateDepartmentRequest,
) -> Department:
    repo = DepartmentRepository(session, ctx.workspace_id)
    row = await repo.get(department_id)
    old_name = row.name
    if body.name is not None and body.name != row.name:
        await _check_name(repo, body.name, excluding=row.id)
        row.name = body.name
    if "description" in body.model_fields_set:
        row.description = body.description or None
    try:
        await session.flush()
    except IntegrityError as error:
        raise DepartmentNameTakenError() from error
    if row.name != old_name:
        AuditRepository(session, ctx.workspace_id).record(
            actor_id=ctx.user_id,
            action="department.renamed",
            entity_type="department",
            entity_id=row.id,
            data={"from": old_name, "to": row.name},
        )
    await session.commit()
    return _department(row)


async def delete_department(
    session: AsyncSession, ctx: RequestContext, department_id: uuid.UUID
) -> None:
    repo = DepartmentRepository(session, ctx.workspace_id)
    row = await repo.get(department_id)
    moved = await repo.move_pipelines_to_no_department(row.id)
    await repo.remove_from_pending_invites(row.id)
    await repo.delete(row)
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action="department.deleted",
        entity_type="department",
        entity_id=row.id,
        data={"name": row.name, "pipelines_moved": moved},
    )
    await session.commit()


async def _check_name(
    repo: DepartmentRepository, name: str, *, excluding: uuid.UUID | None = None
) -> None:
    if is_reserved(name):
        raise DepartmentNameReservedError()
    if await repo.name_taken(name, excluding=excluding):
        raise DepartmentNameTakenError()


def _department(row: DepartmentRow, stats: DepartmentStats | None = None) -> Department:
    return Department(
        id=row.id,
        name=row.name,
        description=row.description,
        created_at=row.created_at,
        stats=stats,
    )


def _member(row: MemberRow) -> DepartmentMember:
    return DepartmentMember(
        member_id=row.member_id,
        user_id=row.user_id,
        full_name=row.full_name,
        avatar_url=row.avatar_url,
        role=Role(row.role),
    )
