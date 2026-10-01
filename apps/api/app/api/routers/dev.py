"""Endpoints for trying the foundations by hand. Mounted only when APP_ENV is `local` or
`development` and left out of the OpenAPI schema, so the API client never sees them."""

import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.api.deps import JobQueueDep, RequestContextDep, Session, SettingsDep
from app.core.errors import PROBLEM_RESPONSES
from app.schemas.jobs import Job, SampleJobRequest
from app.services import emails as email_service
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


class TestEmailQueued(BaseModel):
    message_id: uuid.UUID


@router.post("/test-email", response_model=TestEmailQueued, status_code=status.HTTP_202_ACCEPTED)
async def send_test_email(
    ctx: RequestContextDep, session: Session, queue: JobQueueDep, settings: SettingsDep
) -> TestEmailQueued:
    """Queues the test email to the caller's own address (Mailpit locally, Resend when
    RESEND_API_KEY is set). Its status is in email_messages."""
    message_id = await email_service.send_test_email(session, ctx, queue, settings)
    return TestEmailQueued(message_id=message_id)
