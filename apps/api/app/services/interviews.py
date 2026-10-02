"""Interview plans (AI_PIPELINE.md §2, FR-INTV-01), built by the `plan_interview` job after an
application passes the résumé screen.

`plan_interview()` asks the model for a personal plan and stores it once it passes every check
(`app/interview/plan.py`). When the model can't give a usable plan, the job's failure hook calls
`record_fallback()`, which stores a plain plan built from the pipeline's skills to probe, so the
candidate's invitation (SCREEN-003) never waits on the model.
"""

import logging
import uuid
from enum import StrEnum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient
from app.ai.schemas.interview_plan import InterviewPlan as PlanAnswer
from app.interview import plan as planning
from app.models import Application, InterviewPlan
from app.repositories import screening as screening_repo
from app.repositories.interviews import PLANNABLE_STAGES, InterviewPlanRepository
from app.repositories.screening import ScreeningRepository

logger = logging.getLogger("app.interview")


class Planned(StrEnum):
    SKIPPED = "skipped"  # gone, past the interview stage, or already planned
    PLANNED = "planned"


async def _plannable(session: AsyncSession, application_id: uuid.UUID) -> Application | None:
    application = await screening_repo.application_by_id(session, application_id)
    if application is None or application.stage not in PLANNABLE_STAGES:
        return None
    if await InterviewPlanRepository(session, application.workspace_id).plan_of(application.id):
        return None
    return application


async def _context(session: AsyncSession, application: Application) -> planning.Context:
    screening = ScreeningRepository(session, application.workspace_id)
    pipeline = await screening.pipeline(application.pipeline_id)
    text = await screening.text_of(application.id)
    assessment = await screening.assessment_of(application.id)
    about = await InterviewPlanRepository(session, application.workspace_id).company_about()
    return planning.Context(
        job_title=pipeline.title or "",
        job_description=pipeline.jd_text or "",
        seniority=pipeline.seniority,
        tone=pipeline.tone,
        interview_format=pipeline.interview_format,
        skills_to_probe=list(pipeline.skills_to_probe),
        must_haves=list(pipeline.must_haves),
        open_to=list(pipeline.open_to),
        company_about=about,
        resume_text=text.redacted_text if text else "",
        screening_claims=list(assessment.claims) if assessment else [],
    )


async def _store(
    session: AsyncSession,
    application: Application,
    answer: PlanAnswer,
    *,
    source: str,
    model: str,
    prompt_version: str,
) -> bool:
    InterviewPlanRepository(session, application.workspace_id).add(
        InterviewPlan(
            application_id=application.id,
            workspace_id=application.workspace_id,
            topics=[topic.model_dump() for topic in answer.topics],
            claims_to_verify=[claim.model_dump() for claim in answer.claims_to_verify],
            source=source,
            model=model,
            prompt_version=prompt_version,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        # Another run planned it first.
        await session.rollback()
        return False
    return True


async def plan_interview(session: AsyncSession, ai: AIClient, application_id: uuid.UUID) -> Planned:
    """Builds and stores the application's interview plan, once. Model errors propagate for the
    job to retry; the transaction is closed before the model call."""
    application = await _plannable(session, application_id)
    if application is None:
        return Planned.SKIPPED
    context = await _context(session, application)
    name = await ScreeningRepository(session, application.workspace_id).candidate_name(
        application.candidate_id
    )
    await session.commit()

    answer = await planning.generate(
        ai,
        context,
        candidate_name=name,
        workspace_id=application.workspace_id,
        entity_id=application.id,
    )
    stored = await _store(
        session,
        application,
        answer,
        source="ai",
        model=ai.model,
        prompt_version=planning.PROMPT_VERSION,
    )
    if not stored:
        return Planned.SKIPPED
    logger.info("interview planned: application %s, %d topics", application.id, len(answer.topics))
    return Planned.PLANNED


async def record_fallback(session: AsyncSession, application_id: uuid.UUID) -> Planned:
    """After the job's last try: a plain plan from the pipeline's skills to probe, so the
    candidate can still be invited."""
    application = await _plannable(session, application_id)
    if application is None:
        return Planned.SKIPPED
    answer = planning.fallback(await _context(session, application))
    stored = await _store(
        session,
        application,
        answer,
        source="fallback",
        model="none",
        prompt_version=planning.FALLBACK_VERSION,
    )
    if not stored:
        return Planned.SKIPPED
    logger.warning("interview plan fell back to the skills plan: application %s", application.id)
    return Planned.PLANNED
