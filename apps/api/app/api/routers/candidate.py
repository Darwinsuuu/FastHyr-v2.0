"""Candidate endpoints (API.md "Candidate"): a signed-in Google or Microsoft account, acting only
on its own applications. Pipelines are named by ID; drafts, cancelled and unknown ones are 404.
Interview links are named by their token and also answer signed-out visitors (INTV-002)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Request, Response, status

from app.api.deps import (
    CandidateContextDep,
    JobQueueDep,
    OptionalCandidateDep,
    RealtimeDep,
    Session,
    SettingsDep,
    StorageDep,
)
from app.core.errors import PROBLEM_RESPONSES
from app.schemas.applications import (
    MyApplication,
    ResumeUpload,
    SubmitApplicationRequest,
    SubmittedApplication,
)
from app.schemas.interviews import (
    InterviewCompleted,
    InterviewCompleteRequest,
    InterviewConsent,
    InterviewConsentRequest,
    InterviewHeartbeat,
    InterviewHeartbeatRequest,
    InterviewLink,
    InterviewSession,
    InterviewSessionRequest,
    RecordingChunkRegistered,
    RecordingChunkRequest,
    RecordingChunkUrls,
    RecordingChunkUrlsRequest,
)
from app.services import applications as application_service
from app.services import interview_links, interview_sessions, recordings

router = APIRouter(prefix="/candidate", tags=["candidate"], responses=PROBLEM_RESPONSES)


@router.post("/pipelines/{pipeline_id}/resume-upload", response_model=ResumeUpload)
async def create_resume_upload(
    pipeline_id: uuid.UUID, ctx: CandidateContextDep, session: Session, storage: StorageDep
) -> ResumeUpload:
    """A signed upload URL for the résumé PDF, while the pipeline takes applications
    (`409 pipeline_not_accepting` otherwise)."""
    return await application_service.create_resume_upload(session, storage, pipeline_id)


@router.post(
    "/applications",
    response_model=SubmittedApplication,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": SubmittedApplication, "description": "Already applied"}},
)
async def submit_application(
    body: SubmitApplicationRequest,
    request: Request,
    response: Response,
    ctx: CandidateContextDep,
    session: Session,
    storage: StorageDep,
    queue: JobQueueDep,
    settings: SettingsDep,
) -> SubmittedApplication:
    """Applies with the uploaded résumé and uses 1 credit (FR-APPLY-04). Idempotent: applying
    again to the same pipeline returns the first application with `200` and uses nothing."""
    submitted = await application_service.submit(
        session,
        ctx,
        storage,
        queue,
        body,
        client_ip=request.client.host if request.client else None,
        ip_hash_key=settings.supabase_service_role_key,
    )
    if not submitted.created:
        response.status_code = status.HTTP_200_OK
    return submitted


@router.get("/pipelines/{pipeline_id}/my-application", response_model=MyApplication)
async def get_my_application(
    pipeline_id: uuid.UUID, ctx: CandidateContextDep, session: Session
) -> MyApplication:
    """Whether the signed-in candidate has applied, and when ("Applied on {date}")."""
    return await application_service.my_application(session, ctx, pipeline_id)


@router.get("/interviews/{token}", response_model=InterviewLink)
async def get_interview_link(
    token: Annotated[str, Path(min_length=1, max_length=128)],
    candidate: OptionalCandidateDep,
    session: Session,
    settings: SettingsDep,
) -> InterviewLink:
    """The interview link page (S-01). Sign-in is optional here: a signed-out visitor gets
    `sign_in` (with the applying account's masked email) unless the link has expired or closed,
    and a different account gets `wrong_account`. Unknown tokens are `404 interview_not_found`."""
    return await interview_links.interview_link(session, token, candidate, api_url=settings.api_url)


@router.post("/interviews/{token}/consent", response_model=InterviewConsent)
async def record_interview_consent(
    token: Annotated[str, Path(min_length=1, max_length=128)],
    body: InterviewConsentRequest,
    ctx: CandidateContextDep,
    session: Session,
) -> InterviewConsent:
    """The device check's consent (FR-INTV-03): the interview notice, plus the biometric notice
    when `face_check` (`422 biometric_consent_required` without it). Another account gets
    `404 interview_not_found`; an expired, closed or finished link `409 interview_not_open`."""
    return await interview_links.record_consent(session, token, ctx, body)


@router.post("/interviews/{token}/session", response_model=InterviewSession)
async def start_interview_session(
    token: Annotated[str, Path(min_length=1, max_length=128)],
    body: InterviewSessionRequest,
    ctx: CandidateContextDep,
    session: Session,
    realtime: RealtimeDep,
    queue: JobQueueDep,
    settings: SettingsDep,
) -> InterviewSession:
    """Starts the live interview, or a new attempt after a drop or reload (FR-INTV-04/06): the
    API opens the Realtime call with the browser's SDP offer and returns the answer (ADR-021).
    Needs the device check's consent (`409 interview_consent_required`); a link that can't
    start is `409 interview_not_open`; three failed connections in 5 minutes are
    `409 interview_technical_issue`."""
    return await interview_sessions.start(session, realtime, queue, settings, token, ctx, body)


@router.post("/interviews/{token}/heartbeat", response_model=InterviewHeartbeat)
async def interview_heartbeat(
    token: Annotated[str, Path(min_length=1, max_length=128)],
    body: InterviewHeartbeatRequest,
    ctx: CandidateContextDep,
    session: Session,
    realtime: RealtimeDep,
) -> InterviewHeartbeat:
    """Every 15 s during the interview: talk time on the server's clock, and `ended` once the
    attempt is over (its time ran out, the interviewer ended it, or a newer attempt began)."""
    return await interview_sessions.heartbeat(session, realtime, token, ctx, body)


@router.post("/interviews/{token}/complete", response_model=InterviewCompleted)
async def complete_interview(
    token: Annotated[str, Path(min_length=1, max_length=128)],
    body: InterviewCompleteRequest,
    ctx: CandidateContextDep,
    session: Session,
    realtime: RealtimeDep,
) -> InterviewCompleted:
    """The candidate ends the interview: the call is hung up and the interview is complete.
    Ending it again is harmless."""
    return await interview_sessions.complete(session, realtime, token, ctx, body)


@router.post("/interviews/{token}/chunk-urls", response_model=RecordingChunkUrls)
async def recording_chunk_urls(
    token: Annotated[str, Path(min_length=1, max_length=128)],
    body: RecordingChunkUrlsRequest,
    ctx: CandidateContextDep,
    session: Session,
    storage: StorageDep,
) -> RecordingChunkUrls:
    """Signed upload URLs for an attempt's next recording chunks (INTV-006): PUT each chunk's
    bytes to its URL once. The first request fixes the attempt's type (`webm` or `mp4`); another
    type later is `409 recording_type_mismatch`. Once the recording is being put together,
    `409 recording_finalized`."""
    return await recordings.chunk_urls(session, storage, token, ctx, body)


@router.post("/interviews/{token}/chunks", response_model=RecordingChunkRegistered)
async def register_recording_chunk(
    token: Annotated[str, Path(min_length=1, max_length=128)],
    body: RecordingChunkRequest,
    ctx: CandidateContextDep,
    session: Session,
    storage: StorageDep,
    queue: JobQueueDep,
) -> RecordingChunkRegistered:
    """Registers an uploaded chunk (INTV-006); `last` says the attempt's recorder stopped.
    Registering it again is harmless. Not uploaded yet `422 recording_chunk_missing`; over
    50 MB `422 recording_chunk_too_large` (and deleted); once the recording is being put
    together `409 recording_finalized`."""
    return await recordings.register_chunk(session, storage, queue, token, ctx, body)
