"""Applications (API.md "Applications & candidates"). Recruiters reach only applications in
their departments' pipelines; anything else is 404. The profile and decisions come with their
tasks."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter

from app.api.deps import JobQueueDep, Session, SettingsDep, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.core.permissions import Action
from app.schemas.reinvites import ReinviteResult
from app.services import interview_lifecycle

router = APIRouter(prefix="/applications", tags=["applications"], responses=PROBLEM_RESPONSES)

CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": Problem, "content": {PROBLEM_JSON: {}}}}

Decider = Annotated[RequestContext, require(Action.DECIDE_CANDIDATES)]


@router.post("/{application_id}/reinvite", response_model=ReinviteResult, responses=CONFLICT)
async def reinvite_application(
    application_id: uuid.UUID,
    ctx: Decider,
    session: Session,
    queue: JobQueueDep,
    settings: SettingsDep,
) -> ReinviteResult:
    """A new interview link for a candidate who hasn't finished their interview (INTV-007): the
    old link stops working, the new one gets a fresh expiry and the full 30 minutes, and the
    invitation goes out now. The application keeps its credit. A finished or running interview,
    or a cancelled pipeline, is `409 reinvite_not_allowed`."""
    done = await interview_lifecycle.reinvite(session, settings, queue, ctx, application_id)
    return ReinviteResult(reinvited=len(done.application_ids))
