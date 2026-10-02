"""Résumé screening for one application (AI_PIPELINE.md §1), run by the `screen_resume` job.

`prepare_resume()` (SCREEN-001) extracts the PDF's text and redacts it. An unreadable résumé is
marked `unreadable` and waits in `processing_resume` for a person (WORKFLOW.md §3); it is never
rejected automatically. `assess_resume()` (SCREEN-002) then scores the redacted text, decides
pass or fail, and writes the assessment, its `ai_decisions` entry and `resume_status = done` in
one transaction. The stage stays `processing_resume`: SCREEN-003 acts on the decision (invite,
or `resume_not_match` and the rejection email).
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient
from app.integrations.storage import Bucket, Storage
from app.models import AIDecision, Pipeline, ResumeAssessment, ResumeText
from app.repositories import screening as screening_repo
from app.repositories.screening import DONE, PENDING, ScreeningRepository
from app.screening import assess as assessment
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


class Assessed(StrEnum):
    SKIPPED = "skipped"  # not pending, not redacted yet, or already assessed
    PASSED = "passed"
    FAILED = "failed"


def criteria_of(pipeline: Pipeline) -> assessment.Criteria:
    return assessment.Criteria(
        job_title=pipeline.title or "",
        job_description=pipeline.jd_text or "",
        must_haves=list(pipeline.must_haves),
        nice_to_haves=list(pipeline.nice_to_haves),
        seniority=pipeline.seniority,
        open_to=list(pipeline.open_to),
        pass_bar=pipeline.resume_pass_bar,
    )


async def assess_resume(session: AsyncSession, ai: AIClient, application_id: uuid.UUID) -> Assessed:
    """Scores the redacted résumé against the pipeline's locked criteria and records the
    decision, once. Model errors propagate for the job to retry; the transaction is closed
    before the model call."""
    application = await screening_repo.application_by_id(session, application_id)
    if application is None or application.resume_status != PENDING:
        return Assessed.SKIPPED
    repo = ScreeningRepository(session, application.workspace_id)
    text = await repo.text_of(application.id)
    if text is None or await repo.assessment_of(application.id) is not None:
        return Assessed.SKIPPED
    criteria = criteria_of(await repo.pipeline(application.pipeline_id))
    await session.commit()

    answer = await assessment.assess(
        ai,
        criteria,
        text.redacted_text,
        workspace_id=application.workspace_id,
        entity_id=application.id,
    )
    decision = assessment.score(answer, criteria)
    screened_at = datetime.now(UTC)
    duration_ms = max(0, round((screened_at - application.applied_at).total_seconds() * 1000))
    outcome = "pass" if decision.passed else "fail"
    repo.add_assessment(
        ResumeAssessment(
            application_id=application.id,
            workspace_id=application.workspace_id,
            score=decision.score,
            breakdown=decision.breakdown,
            must_have_results=decision.must_haves,
            nice_to_have_results=decision.nice_to_haves,
            impact=[item.model_dump() for item in answer.impact],
            claims=[item.model_dump() for item in answer.claims],
            experience_timeline=[item.model_dump() for item in answer.timeline],
            career_snapshot=answer.career_snapshot.model_dump(),
            pass_bar=criteria.pass_bar,
            passed=decision.passed,
            model=ai.model,
            prompt_version=assessment.PROMPT_VERSION,
            screened_at=screened_at,
            duration_ms=duration_ms,
        ),
        AIDecision(
            workspace_id=application.workspace_id,
            application_id=application.id,
            type="resume_screen",
            outcome=outcome,
            score=decision.score,
            threshold=criteria.pass_bar,
            model=ai.model,
            prompt_version=assessment.PROMPT_VERSION,
            input_ref=f"resume_texts:{application.id}@{text.redaction_version}",
            # Numbers and flags only: the log keeps no résumé text.
            output={
                "breakdown": {part: row["points"] for part, row in decision.breakdown.items()},
                "must_haves_met": [row["met"] for row in decision.must_haves],
                "nice_to_haves_found": [row["found"] for row in decision.nice_to_haves],
                "experience_score": answer.experience.score,
                "skill_depth_score": answer.skill_depth.score,
                "open_to": list(criteria.open_to),
            },
        ),
    )
    try:
        moved = await repo.set_resume_status(application.id, DONE)
        if not moved:
            await session.rollback()
            return Assessed.SKIPPED
        await session.commit()
    except IntegrityError:
        # Another run assessed it first.
        await session.rollback()
        return Assessed.SKIPPED
    logger.info(
        "resume screened: application %s, %s, %d ms after applying",
        application.id,
        outcome,
        duration_ms,
    )
    return Assessed.PASSED if decision.passed else Assessed.FAILED


async def record_failure(session: AsyncSession, application_id: uuid.UUID) -> None:
    """After the job's last try: `resume_status = error`, so the hiring team sees the résumé
    needs a person. The application is never rejected for it."""
    application = await screening_repo.application_by_id(session, application_id)
    if application is not None:
        await ScreeningRepository(session, application.workspace_id).set_resume_status(
            application.id, ERROR
        )
