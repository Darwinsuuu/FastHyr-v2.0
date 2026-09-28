"""Endpoints for any signed-in user (API.md "Me")."""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, Session
from app.core.errors import PROBLEM_RESPONSES
from app.schemas.me import MeResponse, MyWorkspace
from app.services import me as me_service

router = APIRouter(prefix="/me", tags=["me"], responses=PROBLEM_RESPONSES)


@router.get("", response_model=MeResponse)
async def get_me(user: CurrentUserDep, session: Session) -> MeResponse:
    return await me_service.get_me(session, user)


@router.get("/workspaces", response_model=list[MyWorkspace])
async def list_my_workspaces(user: CurrentUserDep, session: Session) -> list[MyWorkspace]:
    return await me_service.list_my_workspaces(session, user)
