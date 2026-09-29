"""Members (API.md "Workspace admin"): Admins only. Invites are WS-004."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, status

from app.api.deps import Session, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.core.permissions import Action
from app.schemas.members import Member, MemberList, UpdateMemberRequest
from app.services import members as member_service

router = APIRouter(prefix="/members", tags=["members"], responses=PROBLEM_RESPONSES)

CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": Problem, "content": {PROBLEM_JSON: {}}}}

Admin = Annotated[RequestContext, require(Action.MANAGE_WORKSPACE)]


@router.get("", response_model=MemberList)
async def list_members(ctx: Admin, session: Session) -> MemberList:
    """Every active member: the owner first, then by name."""
    return await member_service.list_members(session, ctx)


@router.patch("/{member_id}", response_model=Member, responses=CONFLICT)
async def update_member(
    member_id: uuid.UUID, body: UpdateMemberRequest, ctx: Admin, session: Session
) -> Member:
    """Changes role and departments, effective on the member's next request. Not the owner
    (`409 owner_access_locked`) or yourself (`409 own_access_locked`)."""
    return await member_service.update_member(session, ctx, member_id, body)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT, responses=CONFLICT)
async def remove_member(member_id: uuid.UUID, ctx: Admin, session: Session) -> None:
    """Removes the member's access to this workspace, effective on their next request."""
    await member_service.remove_member(session, ctx, member_id)
