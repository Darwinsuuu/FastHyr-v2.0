"""Endpoints for any signed-in user (API.md "Me")."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, Session
from app.core.errors import PROBLEM_RESPONSES
from app.schemas.me import MeResponse, MyWorkspace
from app.schemas.workspaces import LastWorkspaceRequest
from app.services import me as me_service
from app.services import workspaces as workspace_service

router = APIRouter(prefix="/me", tags=["me"], responses=PROBLEM_RESPONSES)


@router.get("", response_model=MeResponse)
async def get_me(user: CurrentUserDep, session: Session) -> MeResponse:
    return await me_service.get_me(session, user)


@router.get("/workspaces", response_model=list[MyWorkspace])
async def list_my_workspaces(user: CurrentUserDep, session: Session) -> list[MyWorkspace]:
    return await me_service.list_my_workspaces(session, user)


@router.put("/last-workspace", status_code=status.HTTP_204_NO_CONTENT)
async def set_last_workspace(
    body: LastWorkspaceRequest, user: CurrentUserDep, session: Session
) -> None:
    """Remembers the active workspace for the next sign-in, on any device (FR-AUTH-04)."""
    await workspace_service.set_last_workspace(session, user, body.workspace_id)
