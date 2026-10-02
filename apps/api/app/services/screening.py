"""Résumé screening for one application (AI_PIPELINE.md §1), run by the `screen_resume` job.

SCREEN-001 covers steps 1 and 2: extract the PDF's text and redact it. An unreadable résumé is
marked `unreadable` and waits in `processing_resume` for a person (WORKFLOW.md §3); it is never
rejected automatically. SCREEN-002 adds the assessment after `prepare_resume()`.
"""

import asyncio
import logging
import uuid
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient
from app.integrations.storage import Bucket, Storage
from app.models import ResumeText
from app.repositories import screening as screening_repo
from app.repositories.screening import PENDING, ScreeningRepository
from app.screening import redact as redaction
from app.screening.extract import characters, extract_text

logger = logging.getLogger("app.screening")

UNREADABLE = "unreadable"
ERROR = "error"


class Prepared(StrEnum):
    SKIPPED = "skipped"  # not pending, or the text is already redacted
    UNREADABLE = "unreadable"
    REDACTED = "redacted"


async def prepare_resume(
    session: AsyncSession, storage: Storage, ai: AIClient, application_id: uuid.UUID
) -> Prepared:
    """Extracts and redacts the application's résumé, once. Storage and model errors propagate
    for the job to retry; the transaction is closed before each outside call."""
    application = await screening_repo.application_by_id(session, application_id)
    if application is None or application.resume_status != PENDING:
        return Prepared.SKIPPED
    repo = ScreeningRepository(session, application.workspace_id)
    if await repo.text_of(application.id) is not None:
        return Prepared.SKIPPED
    name = await repo.candidate_name(application.candidate_id)
    await session.commit()

    data = await storage.download(Bucket.RESUMES, application.resume_path)
    extraction = await asyncio.to_thread(extract_text, data)
    if not extraction.readable:
        await repo.set_resume_status(application.id, UNREADABLE)
        await session.commit()
        logger.info("resume unreadable: application %s", application.id)
        return Prepared.UNREADABLE

    redacted = await redaction.redact(
        ai,
        extraction.text,
        known_names=[name] if name else [],
        workspace_id=application.workspace_id,
        entity_id=application.id,
    )
    repo.add_text(
        ResumeText(
            application_id=application.id,
            workspace_id=application.workspace_id,
            redacted_text=redacted.text,
            characters=characters(extraction.text),
            pages=extraction.pages,
            column_pages=extraction.column_pages,
            masked=dict(redacted.masked),
            redaction_version=redaction.VERSION,
        )
    )
    await session.commit()
    logger.info("resume redacted: application %s", application.id)
    return Prepared.REDACTED


async def record_failure(session: AsyncSession, application_id: uuid.UUID) -> None:
    """After the job's last try: `resume_status = error`, so the hiring team sees the résumé
    needs a person. The application is never rejected for it."""
    application = await screening_repo.application_by_id(session, application_id)
    if application is not None:
        await ScreeningRepository(session, application.workspace_id).set_resume_status(
            application.id, ERROR
        )
