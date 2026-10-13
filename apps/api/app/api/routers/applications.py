"""Applications (API.md "Applications & candidates"). Recruiters reach only applications in
their departments' pipelines and Hiring managers only shortlisted ones; anything else is 404.
Hiring managers read; they never advance or reject (ADR-005)."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter

from app.api.deps import JobQueueDep, RealtimeDep, Session, SettingsDep, StorageDep, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.core.permissions import Action
from app.schemas.application_profile import ApplicationProfile, RecordingUrl
from app.schemas.decisions import AdvanceRequest, ApplicationDecision, RejectRequest
from app.schemas.reinvites import ReinviteResult
from app.services import application_profile, decisions, interview_lifecycle

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


@router.post("/{application_id}/advance", response_model=ApplicationDecision, responses=CONFLICT)
async def advance_application(
    application_id: uuid.UUID,
    body: AdvanceRequest,
    ctx: Decider,
    session: Session,
    queue: JobQueueDep,
    settings: SettingsDep,
) -> ApplicationDecision:
    """ "Advance to next round" (ADR-017): a Ready for review candidate moves to Advanced, with an
    optional note for the team, and gets the "Moving to the next stage" email unless
    `send_email` is false. Waiting automatic emails are cancelled. `409 flags_to_review` while
    integrity flags are open; `409 decision_not_allowed` from any other stage (Advanced and
    Rejected are final)."""
    return await decisions.advance(session, settings, queue, ctx, application_id, body)


@router.post("/{application_id}/reject", response_model=ApplicationDecision, responses=CONFLICT)
async def reject_application(
    application_id: uuid.UUID,
    body: RejectRequest,
    ctx: Decider,
    session: Session,
    queue: JobQueueDep,
    settings: SettingsDep,
    realtime: RealtimeDep,
) -> ApplicationDecision:
    """ "Reject candidate" (FR-PIPE-13): from Invited, Interview in progress or Ready for review
    (or an unreadable résumé), with a reason only the team sees. A running interview ends. The
    rejection email goes out now unless `send_email` is false: about the interview after a
    finished one, otherwise about the résumé, with a "Request a human review" link. Waiting
    automatic emails are cancelled. `409 decision_not_allowed` from any other stage."""
    return await decisions.reject(session, settings, queue, realtime, ctx, application_id, body)
