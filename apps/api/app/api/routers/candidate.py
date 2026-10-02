"""Candidate endpoints (API.md "Candidate"): a signed-in Google or Microsoft account, acting only
on its own applications. Pipelines are named by ID; drafts, cancelled and unknown ones are 404."""

import uuid

from fastapi import APIRouter, Request, Response, status

from app.api.deps import CandidateContextDep, JobQueueDep, Session, SettingsDep, StorageDep
from app.core.errors import PROBLEM_RESPONSES
from app.schemas.applications import (
    MyApplication,
    ResumeUpload,
    SubmitApplicationRequest,
    SubmittedApplication,
)
from app.services import applications as application_service

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
