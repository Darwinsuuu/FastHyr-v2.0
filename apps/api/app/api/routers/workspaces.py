"""Creating and joining workspaces (API.md "Me"). Any verified signed-in user; no
`X-Workspace-Id`, since the caller isn't a member yet."""

from typing import Annotated, Any

from fastapi import APIRouter, Path, status

from app.api.deps import Session, VerifiedUserDep
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.schemas.me import MyWorkspace
from app.schemas.workspaces import AcceptInviteRequest, CreateWorkspaceRequest, InvitePreview
from app.services import workspaces as workspace_service

router = APIRouter(tags=["workspaces"], responses=PROBLEM_RESPONSES)

GONE: dict[int | str, dict[str, Any]] = {410: {"model": Problem, "content": {PROBLEM_JSON: {}}}}


@router.post("/workspaces", response_model=MyWorkspace, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: CreateWorkspaceRequest, user: VerifiedUserDep, session: Session
) -> MyWorkspace:
    return await workspace_service.create_workspace(session, user, body.name)


@router.post("/invites/accept", response_model=MyWorkspace, responses=GONE)
async def accept_invite(
    body: AcceptInviteRequest, user: VerifiedUserDep, session: Session
) -> MyWorkspace:
    """Joins with the invite's role and departments, by `code` or link `token`."""
    return await workspace_service.accept_invite(session, user, body.key)


@router.get("/invites/{key}", response_model=InvitePreview)
async def preview_invite(
    key: Annotated[str, Path(max_length=200)], user: VerifiedUserDep, session: Session
) -> InvitePreview:
    """The join page's view of an invite, by code or link token (S-04). Unknown keys are
    `404 invite_not_found`; details only show to the email the invite was sent to."""
    return await workspace_service.preview_invite(session, user, key)
