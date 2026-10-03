"""FastAPI dependencies every router uses: the session, the caller and `require(action)`.

@router.get("/departments")
async def list_departments(ctx: Annotated[RequestContext, require(Action.VIEW_DEPARTMENTS)]):
    ...
"""

import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

import sentry_sdk
from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, TokenVerifier, bearer_token
from app.core.config import Settings
from app.core.context import CandidateContext, RequestContext, Role
from app.core.db import get_session
from app.core.errors import (
    CandidateSignInRequiredError,
    EmailNotVerifiedError,
    ForbiddenError,
    NotAMemberError,
    WorkspaceRequiredError,
)
from app.core.logging import bind_ids
from app.core.permissions import Action, can
from app.integrations.storage import Storage
from app.jobs.queue import JobQueue
from app.repositories.users import UserRepository

Session = Annotated[AsyncSession, Depends(get_session)]


def get_job_queue(request: Request) -> JobQueue:
    queue: JobQueue = request.app.state.job_queue
    return queue


JobQueueDep = Annotated[JobQueue, Depends(get_job_queue)]


def get_storage(request: Request) -> Storage:
    storage: Storage = request.app.state.storage
    return storage


StorageDep = Annotated[Storage, Depends(get_storage)]


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


async def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> CurrentUser:
    verifier: TokenVerifier = request.app.state.token_verifier
    user = await verifier.verify(bearer_token(authorization))
    bind_ids(user_id=user.user_id)
    sentry_sdk.set_user({"id": str(user.user_id)})
    return user


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


async def get_verified_user(user: CurrentUserDep) -> CurrentUser:
    """The caller, if their email is verified; else 403 `email_not_verified`. For endpoints that
    create or join a workspace (FR-AUTH-03). Google and Microsoft sign-ins arrive verified."""
    if not user.email_verified:
        raise EmailNotVerifiedError()
    return user


VerifiedUserDep = Annotated[CurrentUser, Depends(get_verified_user)]


async def get_request_context(
    user: CurrentUserDep,
    session: Session,
    x_workspace_id: Annotated[str | None, Header()] = None,
) -> RequestContext:
    """Binds a TA request to one workspace. A missing or malformed header is
    `workspace_required`; any workspace the user isn't an active member of is `not_a_member`."""
    if not x_workspace_id:
        raise WorkspaceRequiredError()
    try:
        workspace_id = uuid.UUID(x_workspace_id)
    except ValueError as error:
        raise NotAMemberError() from error

    users = UserRepository(session, user.user_id)
    member = await users.get_active_membership(workspace_id)
    if member is None:
        raise NotAMemberError()
    bind_ids(workspace_id=workspace_id)
    context = RequestContext(
        user_id=user.user_id,
        workspace_id=workspace_id,
        member_id=member.id,
        role=Role(member.role),
        is_owner=member.is_owner,
        department_ids=await users.department_ids(member),
    )
    await users.touch_last_active(member)
    return context


# ADR-014: candidates sign in with Google or Microsoft only.
CANDIDATE_PROVIDERS = frozenset({"google", "azure"})


async def get_candidate_context(user: CurrentUserDep) -> CandidateContext:
    """A signed-in candidate on `/candidate/*`. Only a Google or Microsoft account with an email
    counts; anything else (a TA's email + password session) is 403 `candidate_sign_in_required`.
    Being a candidate grants no TA access, and TA membership changes nothing here."""
    if not (user.providers & CANDIDATE_PROVIDERS) or not user.email:
        raise CandidateSignInRequiredError()
    return CandidateContext(user_id=user.user_id, email=user.email)


CandidateContextDep = Annotated[CandidateContext, Depends(get_candidate_context)]


async def get_optional_candidate(
    request: Request,
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> CandidateContext | None:
    """For pages a candidate opens before signing in (the interview link, INTV-002): no token, or
    a session that isn't Google or Microsoft, is None. A token that fails its check is still 401,
    so a stale session never reads as "signed out" by mistake."""
    if not authorization:
        return None
    user = await get_current_user(request, authorization)
    if not (user.providers & CANDIDATE_PROVIDERS) or not user.email:
        return None
    return CandidateContext(user_id=user.user_id, email=user.email)


OptionalCandidateDep = Annotated[CandidateContext | None, Depends(get_optional_candidate)]
RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]


def require(action: Action) -> Any:
    """Dependency: the caller's `RequestContext`, or 403 `forbidden` if their role may not take
    `action` at all. Resources outside their departments or stages are 404s, from repositories."""

    async def dependency(ctx: RequestContextDep) -> RequestContext:
        if can(ctx, action) is None:
            raise ForbiddenError()
        return ctx

    checker: Callable[[RequestContext], Coroutine[Any, Any, RequestContext]] = dependency
    return Depends(checker)
