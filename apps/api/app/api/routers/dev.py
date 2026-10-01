"""Local-only endpoints for trying the foundations by hand. Mounted only when APP_ENV is
`local` and left out of the OpenAPI schema, so the API client never sees them."""

from fastapi import APIRouter, status

from app.api.deps import JobQueueDep, RequestContextDep, Session
from app.core.errors import PROBLEM_RESPONSES
from app.schemas.jobs import Job, SampleJobRequest
from app.services import jobs as job_service

router = APIRouter(
    prefix="/dev", tags=["dev"], responses=PROBLEM_RESPONSES, include_in_schema=False
)


@router.post("/sample-job", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
async def start_sample_job(
    body: SampleJobRequest, ctx: RequestContextDep, session: Session, queue: JobQueueDep
) -> Job:
    """Queues `sample_report_job`; poll `GET /v1/jobs/{id}` while `make worker` runs it."""
    return await job_service.start_sample_job(session, ctx, queue, body)
