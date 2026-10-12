"""Applications (API.md "Applications & candidates"). Recruiters reach only applications in
their departments' pipelines and Hiring managers only shortlisted ones; anything else is 404.
Decisions come with their tasks."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter

from app.api.deps import JobQueueDep, Session, SettingsDep, StorageDep, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.core.permissions import Action
from app.schemas.application_profile import ApplicationProfile, RecordingUrl
from app.schemas.reinvites import ReinviteResult
from app.services import application_profile, interview_lifecycle

router = APIRouter(prefix="/applications", tags=["applications"], responses=PROBLEM_RESPONSES)

CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": Problem, "content": {PROBLEM_JSON: {}}}}

Decider = Annotated[RequestContext, require(Action.DECIDE_CANDIDATES)]
Viewer = Annotated[RequestContext, require(Action.VIEW_CANDIDATES)]


@router.get("/{application_id}", response_model=ApplicationProfile)
async def get_application(
    application_id: uuid.UUID, ctx: Viewer, session: Session
) -> ApplicationProfile:
    """The candidate profile (ASMT-004, FR-ASMT-07): the application with its résumé screen,
    latest interview and assessment (criteria with signals and evidence, topics, summary,
    strengths, probes, answer patterns), how it compares among the pipeline's assessed
    interviews, integrity checks and flags, the person's other applications the caller can see,
    and the journey. Hiring managers reach shortlisted applications only."""
    return await application_profile.profile(session, ctx, application_id)


@router.get("/{application_id}/recording-url", response_model=RecordingUrl)
async def get_recording_url(
    application_id: uuid.UUID, ctx: Viewer, session: Session, storage: StorageDep
) -> RecordingUrl:
    """Signed links (15 minutes) to the latest interview's recording and poster frame;
    `404 recording_not_ready` until the recording is finished."""
    return await application_profile.recording_url(session, storage, ctx, application_id)


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
