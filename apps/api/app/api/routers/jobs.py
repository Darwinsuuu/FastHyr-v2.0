"""Long-job progress (API.md "Jobs"): the member who started a job polls and can cancel it."""

import uuid

from fastapi import APIRouter, status

from app.api.deps import RequestContextDep, Session
from app.core.errors import PROBLEM_RESPONSES
from app.schemas.jobs import Job
from app.services import jobs as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"], responses=PROBLEM_RESPONSES)


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: uuid.UUID, ctx: RequestContextDep, session: Session) -> Job:
    """Only the member who started the job sees it; anyone else gets 404."""
    return await job_service.get_job(session, ctx, job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(job_id: uuid.UUID, ctx: RequestContextDep, session: Session) -> None:
    """Cancels a queued or running job; a finished one stays as it is."""
    await job_service.cancel_job(session, ctx, job_id)
