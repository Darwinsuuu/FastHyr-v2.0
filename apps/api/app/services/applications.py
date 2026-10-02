"""Applying to a pipeline (FR-APPLY-03..05, WORKFLOW.md §3): the résumé upload, the submission
that uses one credit, and the candidate's own "Applied on" state.

A submission checks the résumé before any credit moves, so a bad file never costs one. Then one
transaction uses the credit (which locks the workspace and pipeline rows, so two applicants can't
both take the last credit), records the candidate and the application, and links the ledger
entry. Anything that loses a race rolls back and leaves no credit used and no file stored.
"""

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import CandidateContext
from app.core.errors import NotFoundError, PipelineNotAcceptingError
from app.core.ids import new_id
from app.integrations.storage import Bucket, Storage, resume_path
from app.jobs.queue import JobQueue
from app.jobs.screening import SCREEN_JOB
from app.models import Application
from app.repositories.applications import (
    ApplicationRepository,
    CandidateDetails,
    CandidatePipeline,
    candidate_pipeline,
)
from app.schemas.applications import (
    MyApplication,
    ResumeUpload,
    SubmitApplicationRequest,
    SubmittedApplication,
)
from app.services import consents, credits, files
from app.services.pdfs import MAX_PDF_BYTES, validate_pdf

logger = logging.getLogger("app.applications")


async def _pipeline(session: AsyncSession, pipeline_id: uuid.UUID) -> CandidatePipeline:
    pipeline = await candidate_pipeline(session, pipeline_id)
    if pipeline is None:
        raise NotFoundError()
    return pipeline


def _accepting(pipeline: CandidatePipeline) -> None:
    # A quick check before any work; the credit service checks again under the row lock.
    if pipeline.status != "live":
        raise PipelineNotAcceptingError()


async def create_resume_upload(
    session: AsyncSession, storage: Storage, pipeline_id: uuid.UUID
) -> ResumeUpload:
    """A signed URL for the résumé, while the pipeline is taking applications."""
    pipeline = await _pipeline(session, pipeline_id)
    _accepting(pipeline)
    pending = await files.create_upload(storage, Bucket.RESUMES, pipeline.workspace_id)
    return ResumeUpload(
        upload_id=pending.upload_id,
        url=pending.upload.url,
        path=pending.upload.path,
        token=pending.upload.token,
        max_bytes=MAX_PDF_BYTES,
    )


def consent_ip_hash(ip: str | None, key: str) -> str | None:
    """A keyed hash of the address the consent came from (FR-COMP-01). The IP itself is never
    stored, and without the key the hash can't be reversed by trying every address."""
    if not ip:
        return None
    secret = hashlib.sha256(f"consent-ip:{key}".encode()).digest()
    return hmac.new(secret, ip.encode(), hashlib.sha256).hexdigest()


async def submit(
    session: AsyncSession,
    ctx: CandidateContext,
    storage: Storage,
    queue: JobQueue,
    body: SubmitApplicationRequest,
    *,
    client_ip: str | None,
    ip_hash_key: str,
    now: datetime | None = None,
) -> SubmittedApplication:
    now = now or datetime.now(UTC)
    pipeline = await _pipeline(session, body.pipeline_id)
    applications = ApplicationRepository(session, pipeline.workspace_id)

    # Applying twice returns the first application unchanged: no second credit (FR-APPLY-05).
    existing = await applications.find_for_candidate(pipeline.id, ctx.user_id)
    if existing is not None:
        return _submitted(existing, created=False)
    _accepting(pipeline)
    consent = consents.accept("apply", body.consent_notice_id, now=now)

    application_id = new_id()
    destination = resume_path(pipeline.workspace_id, application_id)
    resume = await files.promote_pdf(
        storage,
        Bucket.RESUMES,
        workspace_id=pipeline.workspace_id,
        upload_id=body.upload_id,
        destination=destination,
    )
    info = validate_pdf(resume)

    try:
        entry = await credits.consume(
            session, pipeline.workspace_id, pipeline.id, application_id=application_id, now=now
        )
        candidate_id = await applications.upsert_candidate(
            ctx.user_id,
            CandidateDetails(
                email=ctx.email,
                full_name=body.full_name,
                phone_country_code=body.phone_country_code,
                phone=body.phone,
                city=body.city,
                profile_url=body.profile_url,
            ),
            now=now,
        )
        application = applications.add(
            Application(
                id=application_id,
                workspace_id=pipeline.workspace_id,
                pipeline_id=pipeline.id,
                candidate_id=candidate_id,
                source=body.source,
                resume_path=destination,
                resume_filename=body.resume_filename,
                resume_pages=info.pages,
                resume_bytes=info.size,
                consent_version=consent.notice_id,
                consent_at=consent.at,
                consent_ip_hash=consent_ip_hash(client_ip, ip_hash_key),
                stage="processing_resume",
                stage_changed_at=now,
                resume_status="pending",
                credit_ledger_id=entry.id,
                applied_at=now,
            )
        )
        await session.commit()
    except Exception as error:
        # Usually the pipeline stopped taking applications (the last credit went to someone
        # else), or this candidate's other submission won. Nothing is kept either way.
        await session.rollback()
        await storage.delete(Bucket.RESUMES, [destination])
        if isinstance(error, IntegrityError):
            existing = await applications.find_for_candidate(pipeline.id, ctx.user_id)
            if existing is not None:
                return _submitted(existing, created=False)
        raise

    await queue.enqueue(SCREEN_JOB, application.id, key=application.id)
    logger.info("application %s submitted to pipeline %s", application.id, pipeline.id)
    return _submitted(application, created=True)


def _submitted(application: Application, *, created: bool) -> SubmittedApplication:
    return SubmittedApplication(
        application_id=application.id, applied_at=application.applied_at, created=created
    )


async def my_application(
    session: AsyncSession, ctx: CandidateContext, pipeline_id: uuid.UUID
) -> MyApplication:
    pipeline = await _pipeline(session, pipeline_id)
    existing = await ApplicationRepository(session, pipeline.workspace_id).find_for_candidate(
        pipeline.id, ctx.user_id
    )
    return MyApplication(applied_at=existing.applied_at if existing else None)
