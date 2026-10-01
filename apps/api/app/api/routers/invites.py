"""Member invites (API.md "Workspace admin"): Admins only. Accepting an invite is
`POST /invites/accept` in the workspaces router."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, status

from app.api.deps import JobQueueDep, Session, SettingsDep, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.core.permissions import Action
from app.schemas.invites import CreateInviteRequest, Invite, InviteList
from app.services import invites as invite_service

router = APIRouter(prefix="/invites", tags=["invites"], responses=PROBLEM_RESPONSES)

CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": Problem, "content": {PROBLEM_JSON: {}}}}

Admin = Annotated[RequestContext, require(Action.MANAGE_WORKSPACE)]


@router.get("", response_model=InviteList)
async def list_invites(ctx: Admin, session: Session) -> InviteList:
    """Pending invites that haven't expired, most recently sent first."""
    return await invite_service.list_invites(session, ctx)


@router.post("", response_model=Invite, status_code=status.HTTP_201_CREATED, responses=CONFLICT)
async def create_invite(
    body: CreateInviteRequest,
    ctx: Admin,
    session: Session,
    queue: JobQueueDep,
    settings: SettingsDep,
) -> Invite:
    """Invites an email with a role and departments for 7 days and emails them the link and
    code, replacing any pending invite for that email. Someone who already has access is
    `409 already_a_member`."""
    return await invite_service.create_invite(session, ctx, queue, settings, body)


@router.post("/{invite_id}/resend", response_model=Invite)
async def resend_invite(
    invite_id: uuid.UUID,
    ctx: Admin,
    session: Session,
    queue: JobQueueDep,
    settings: SettingsDep,
) -> Invite:
    """A new code, 7-day expiry and email; the previous link and code stop working."""
    return await invite_service.resend_invite(session, ctx, queue, settings, invite_id)


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(invite_id: uuid.UUID, ctx: Admin, session: Session) -> None:
    """The invite can no longer be accepted."""
    await invite_service.revoke_invite(session, ctx, invite_id)
