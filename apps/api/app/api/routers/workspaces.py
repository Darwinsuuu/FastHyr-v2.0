"""Creating and joining workspaces (API.md "Me"). Any verified signed-in user; no
`X-Workspace-Id`, since the caller isn't a member yet."""

from typing import Any

from fastapi import APIRouter, status

from app.api.deps import Session, VerifiedUserDep
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.schemas.me import MyWorkspace
from app.schemas.workspaces import AcceptInviteRequest, CreateWorkspaceRequest
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
    return await workspace_service.accept_invite(session, user, body.code)
