"""Pipelines (API.md "Pipelines"): the list (PIPE-004), draft setup and lifecycle actions. Share
links (PIPE-006) come with their task. Recruiters and Hiring managers reach only
pipelines in their departments; anything else is 404."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query, status

from app.api.deps import JobQueueDep, Session, SettingsDep, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.core.permissions import Action
from app.schemas.pipelines import (
    Pipeline,
    PipelineList,
    PipelineSetup,
    PipelineTab,
    PublishRequest,
    TopUpRequest,
)
from app.schemas.reinvites import ReinviteAllRequest, ReinviteResult
from app.services import interview_lifecycle
from app.services import pipelines as pipeline_service

router = APIRouter(prefix="/pipelines", tags=["pipelines"], responses=PROBLEM_RESPONSES)

CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": Problem, "content": {PROBLEM_JSON: {}}}}

Viewer = Annotated[RequestContext, require(Action.VIEW_PIPELINES)]
Editor = Annotated[RequestContext, require(Action.EDIT_PIPELINES)]
StatusChanger = Annotated[RequestContext, require(Action.CHANGE_PIPELINE_STATUS)]
TopUpper = Annotated[RequestContext, require(Action.TOP_UP_PIPELINE)]
Decider = Annotated[RequestContext, require(Action.DECIDE_CANDIDATES)]


@router.get("", response_model=PipelineList)
async def list_pipelines(
    ctx: Viewer,
    session: Session,
    tab: PipelineTab = "live",
    q: Annotated[str, Query(max_length=120)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    # The page offers 5, 10 or 25 rows.
    page_size: Annotated[int, Query(ge=1, le=25)] = 10,
) -> PipelineList:
    """The Pipelines page (FR-PIPE-08): one tab's pipelines, needing attention first, searched
    by title or department name. Live holds live and paused pipelines, Closed holds closed and
    cancelled ones, Scheduled and Drafts one status each; archived pipelines never show.
    `counts` are per tab before the search."""
    return await pipeline_service.list_pipelines(
        session, ctx, tab=tab, query=q, page=page, page_size=page_size
    )


@router.post("", response_model=Pipeline, status_code=status.HTTP_201_CREATED)
async def create_pipeline(body: PipelineSetup, ctx: Editor, session: Session) -> Pipeline:
    """A new draft with whatever setup the wizard has so far ("Save as draft")."""
    return await pipeline_service.create_draft(session, ctx, body)


@router.get("/{pipeline_id}", response_model=Pipeline)
async def get_pipeline(pipeline_id: uuid.UUID, ctx: Viewer, session: Session) -> Pipeline:
    return await pipeline_service.get_pipeline(session, ctx, pipeline_id)


@router.patch("/{pipeline_id}", response_model=Pipeline, responses=CONFLICT)
async def update_pipeline(
    pipeline_id: uuid.UUID, body: PipelineSetup, ctx: Editor, session: Session
) -> Pipeline:
    """Only the fields sent change. Drafts and scheduled pipelines only; once a pipeline has
    opened its setup is locked (`409 pipeline_locked`)."""
    return await pipeline_service.update_pipeline(session, ctx, pipeline_id, body)


@router.post("/{pipeline_id}/publish", response_model=Pipeline, responses=CONFLICT)
async def publish_pipeline(
    pipeline_id: uuid.UUID, body: PublishRequest, ctx: Editor, session: Session
) -> Pipeline:
    """Draft → live or scheduled. `422 pipeline_incomplete` lists the missing fields;
    `409 insufficient_free_credits` when the reserve is bigger than the free credits."""
    return await pipeline_service.publish(session, ctx, pipeline_id)


@router.post("/{pipeline_id}/start-now", response_model=Pipeline, responses=CONFLICT)
async def start_pipeline_now(
    pipeline_id: uuid.UUID, ctx: StatusChanger, session: Session
) -> Pipeline:
    return await pipeline_service.start_now(session, ctx, pipeline_id)


@router.post("/{pipeline_id}/pause", response_model=Pipeline, responses=CONFLICT)
async def pause_pipeline(pipeline_id: uuid.UUID, ctx: StatusChanger, session: Session) -> Pipeline:
    return await pipeline_service.pause(session, ctx, pipeline_id)


@router.post("/{pipeline_id}/resume", response_model=Pipeline, responses=CONFLICT)
async def resume_pipeline(pipeline_id: uuid.UUID, ctx: StatusChanger, session: Session) -> Pipeline:
    return await pipeline_service.resume(session, ctx, pipeline_id)


@router.post("/{pipeline_id}/close", response_model=Pipeline, responses=CONFLICT)
async def close_pipeline(pipeline_id: uuid.UUID, ctx: StatusChanger, session: Session) -> Pipeline:
    """The unused reserve returns to the free credits."""
    return await pipeline_service.close(session, ctx, pipeline_id)


@router.post("/{pipeline_id}/cancel", response_model=Pipeline, responses=CONFLICT)
async def cancel_pipeline(pipeline_id: uuid.UUID, ctx: StatusChanger, session: Session) -> Pipeline:
    """Scheduled pipelines only; the reserve returns to the free credits."""
    return await pipeline_service.cancel(session, ctx, pipeline_id)


@router.post("/{pipeline_id}/archive", response_model=Pipeline, responses=CONFLICT)
async def archive_pipeline(
    pipeline_id: uuid.UUID, ctx: StatusChanger, session: Session
) -> Pipeline:
    return await pipeline_service.archive(session, ctx, pipeline_id)


@router.post(
    "/{pipeline_id}/duplicate", response_model=Pipeline, status_code=status.HTTP_201_CREATED
)
async def duplicate_pipeline(pipeline_id: uuid.UUID, ctx: Editor, session: Session) -> Pipeline:
    """A new draft with the same setup."""
    return await pipeline_service.duplicate(session, ctx, pipeline_id)


@router.post("/{pipeline_id}/top-up", response_model=Pipeline, responses=CONFLICT)
async def top_up_pipeline(
    pipeline_id: uuid.UUID, body: TopUpRequest, ctx: TopUpper, session: Session
) -> Pipeline:
    """Reserves more free credits; a pipeline paused for credits goes back to live."""
    return await pipeline_service.top_up(session, ctx, pipeline_id, credits_to_add=body.credits)


@router.post("/{pipeline_id}/reinvite", response_model=ReinviteResult, responses=CONFLICT)
async def reinvite_unfinished(
    pipeline_id: uuid.UUID,
    body: ReinviteAllRequest,
    ctx: Decider,
    session: Session,
    queue: JobQueueDep,
    settings: SettingsDep,
) -> ReinviteResult:
    """The pipeline dashboard's "Re-invite all" (INTV-007, FR-PIPE-11): a new interview link and
    invitation for every candidate whose link expired, who left their interview unfinished, or
    who hit a technical issue. Candidates talking to the interviewer right now are left alone. A
    cancelled or archived pipeline is `409 reinvite_not_allowed`."""
    done = await interview_lifecycle.reinvite_unfinished(session, settings, queue, ctx, pipeline_id)
    return ReinviteResult(reinvited=len(done.application_ids))
