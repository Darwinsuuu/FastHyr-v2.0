"""Interview scoring for one completed interview (AI_PIPELINE.md §4, FR-ASMT-02..05), run by the
`score_interview` job once its transcript is ready (INTV-008).

`score()` judges the transcript against the job with `interview_assessment@v1`
(`app/interview/assessment.py`), computes the overall score, pass/fail and fit in code, and
writes, in one transaction, the assessment, its `ai_decisions` entry and
`interviews.assessment_status = ready`. If the application is still in `scoring`, it moves to
`ready_for_review` (overall ≥ pass mark) or `did_not_pass`; a fail schedules `reject_interview`
3 business days after the interview with a "Request a human review" link (ADR-015), when the
pipeline's "Email candidates after their interview" is on. A person makes every hiring decision.

A transcript with no candidate speech is never scored: `assessment_status = failed`, and the
application waits in `scoring` for a person, like a scoring job that gave up.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient
from app.core.config import Settings
from app.core.tokens import new_token
from app.emails.defaults import TemplateKey
from app.interview import assessment
from app.models import AIDecision, Assessment, EmailMessage, Pipeline, ReviewLink
from app.repositories import screening as screening_repo
from app.repositories.assessments import AssessmentRepository, assessments_pending_before
from app.repositories.interviews import InterviewAttemptRepository, InterviewPlanRepository
from app.repositories.review_links import ReviewLinkRepository
from app.repositories.screening import ScreeningRepository
from app.repositories.transcripts import TranscriptSegmentRepository
from app.screening.redact import redact_rules
from app.services import candidate_emails, post_screen
from app.services.applications import move_stage

# The assessment's fit badge as the applications column stores it.
APPLICATION_FIT = {"strong_fit": "strong", "good_fit": "good"}

logger = logging.getLogger("app.interview")

SCORE_JOB = "score_interview"
SCORING = "scoring"
READY_FOR_REVIEW = "ready_for_review"
DID_NOT_PASS = "did_not_pass"
# NOTIFICATIONS.md §1: the interview rejection goes out 3 business days after the interview.
REJECTION_DELAY_BUSINESS_DAYS = 3


class Scored(StrEnum):
    SKIPPED = "skipped"  # not ready to score, already scored, or superseded
    NO_SPEECH = "no_speech"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class Outcome:
    scored: Scored
    # The emails to `emails.enqueue()` after the commit (a no-op for the ones due later).
    emails: list[EmailMessage] = field(default_factory=list)


def rubric_of(pipeline: Pipeline) -> assessment.Rubric:
    if None in (
        pipeline.weight_technical,
        pipeline.weight_communication,
        pipeline.weight_culture,
    ):
        raise ValueError("pipeline has no scoring weights")
    return assessment.Rubric(
        weight_technical=int(pipeline.weight_technical or 0),
        weight_communication=int(pipeline.weight_communication or 0),
        weight_culture=int(pipeline.weight_culture or 0),
        pass_mark=pipeline.pass_mark,
    )


async def score(
    session: AsyncSession,
    settings: Settings,
    ai: AIClient,
    workspace_id: uuid.UUID,
    interview_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Outcome:
    """Scores the interview, once. Model errors propagate for the job to retry; the transaction
    is closed before the model call. The caller enqueues `emails` after this commits."""
    attempts = InterviewAttemptRepository(session, workspace_id)
    interview = await attempts.get_interview(interview_id)
    if (
        interview is None
        or interview.superseded_by is not None
        or interview.status != "completed"
        or interview.transcript_status != "ready"
        or interview.assessment_status != "none"
    ):
        await session.rollback()
        return Outcome(Scored.SKIPPED)
    application = await screening_repo.application_by_id(session, interview.application_id)
    if application is None:
        await session.rollback()
        return Outcome(Scored.SKIPPED)
    screening = ScreeningRepository(session, workspace_id)
    pipeline = await screening.pipeline(application.pipeline_id)
    plan = await InterviewPlanRepository(session, workspace_id).plan_of(application.id)
    text = await screening.text_of(application.id)
    screen = await screening.assessment_of(application.id)
    name = await screening.candidate_name(application.candidate_id)
    lines = [
        assessment.Line(
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            speaker=segment.speaker,
            text=segment.text,
            topic_index=segment.topic_index,
        )
        for segment in await TranscriptSegmentRepository(session, workspace_id).of_interview(
            interview_id
        )
    ]
    completed_at = interview.completed_at or datetime.now(UTC)
    rubric = rubric_of(pipeline)
    context = assessment.Context(
        job_title=pipeline.title or "",
        job_description=pipeline.jd_text or "",
        seniority=pipeline.seniority,
        open_to=list(pipeline.open_to),
        skills_to_probe=list(pipeline.skills_to_probe or pipeline.must_haves),
        topics=[topic.get("title", "") for topic in (plan.topics if plan else [])],
        resume_text=text.redacted_text if text else "",
        claims=list(screen.claims) if screen else [],
        must_haves_met=screen is not None
        and all(row.get("met") for row in screen.must_have_results),
    )
    await session.commit()

    # The candidate's name and contact details are masked as in the résumé (G2).
    known = [name] if name else []
    turns = assessment.turns(lines, lambda line: redact_rules(line, known).text)
    if not any(turn.speaker == "candidate" for turn in turns):
        interview = await attempts.lock_interview(interview_id)
        if interview.assessment_status == "none":
            interview.assessment_status = "failed"
        await session.commit()
        logger.warning("interview %s has no candidate speech; not scored", interview_id)
        return Outcome(Scored.NO_SPEECH)

    answer = await assessment.assess(
        ai, context, turns, workspace_id=workspace_id, entity_id=interview_id
    )
    decision = assessment.decide(answer, context, turns, rubric)
    now = now or datetime.now(UTC)

    interview = await attempts.lock_interview(interview_id)
    if interview.assessment_status != "none" or interview.superseded_by is not None:
        await session.rollback()
        return Outcome(Scored.SKIPPED)
    application = await screening_repo.application_for_update(session, application.id)
    if application is None:
        await session.rollback()
        return Outcome(Scored.SKIPPED)
    outcome = "pass" if decision.passed else "fail"
    AssessmentRepository(session, workspace_id).add(
        Assessment(
            workspace_id=workspace_id,
            application_id=application.id,
            interview_id=interview_id,
            overall_score=decision.overall_score,
            criteria=decision.criteria,
            topics=decision.topics,
            summary=decision.summary,
            strengths=decision.strengths,
            probes=decision.probes,
            claims_checked=decision.claims_checked,
            answer_stats=decision.answer_stats,
            rubric_snapshot=decision.rubric_snapshot,
            passed=decision.passed,
            fit=decision.fit,
            model=ai.model,
            prompt_version=assessment.PROMPT_VERSION,
        ),
        AIDecision(
            workspace_id=workspace_id,
            application_id=application.id,
            type="interview_score",
            outcome=outcome,
            score=decision.overall_score,
            threshold=rubric.pass_mark,
            model=ai.model,
            prompt_version=assessment.PROMPT_VERSION,
            input_ref=f"transcript_segments:{interview_id}",
            # Numbers and flags only: the log keeps no transcript text.
            output={
                "criteria": {
                    name: {key: row[key] for key in ("score", "weight", "points")}
                    for name, row in decision.criteria.items()
                },
                "evidence": {name: len(row["evidence"]) for name, row in decision.criteria.items()},
                "topics": [topic["score"] for topic in decision.topics],
                "fit": decision.fit,
                "answer_stats": decision.answer_stats,
            },
        ),
    )
    interview.assessment_status = "ready"
    # Denormalised for the Candidates tab and other lists (DATABASE.md): ADR-011's badge.
    application.overall_score = decision.overall_score
    application.fit = APPLICATION_FIT.get(decision.fit or "")
    emails: list[EmailMessage] = []
    if application.stage == SCORING:
        stage = READY_FOR_REVIEW if decision.passed else DID_NOT_PASS
        await move_stage(session, workspace_id, application.id, stage, now=now)
        if not decision.passed and pipeline.email_post_interview:
            emails.append(
                await _schedule_rejection(
                    session, settings, application.id, workspace_id, completed_at
                )
            )
    else:
        logger.info("application %s left scoring before its score; stage unchanged", application.id)
    try:
        await session.commit()
    except IntegrityError:
        # Another run scored it first.
        await session.rollback()
        return Outcome(Scored.SKIPPED)
    minutes = (now - completed_at).total_seconds() / 60
    logger.info(
        "interview scored: application %s, %s, %.1f min after the interview",
        application.id,
        outcome,
        minutes,
    )
    return Outcome(Scored.PASSED if decision.passed else Scored.FAILED, emails)


async def _schedule_rejection(
    session: AsyncSession,
    settings: Settings,
    application_id: uuid.UUID,
    workspace_id: uuid.UUID,
    completed_at: datetime,
) -> EmailMessage:
    send_at = await candidate_emails.send_at(
        session, workspace_id, completed_at, REJECTION_DELAY_BUSINESS_DAYS
    )
    token, token_hash = new_token()
    ReviewLinkRepository(session, workspace_id).add(
        ReviewLink(
            workspace_id=workspace_id,
            application_id=application_id,
            decision_type="interview",
            token_hash=token_hash,
            expires_at=send_at + timedelta(days=post_screen.REVIEW_LINK_DAYS),
        )
    )
    scheduled = await candidate_emails.schedule(
        session,
        settings,
        workspace_id=workspace_id,
        application_id=application_id,
        key=TemplateKey.REJECT_INTERVIEW,
        at=send_at,
        values={"Review.link": post_screen.review_link(settings, token)},
    )
    return scheduled.message


async def mark_failed(
    session: AsyncSession, workspace_id: uuid.UUID, interview_id: uuid.UUID
) -> None:
    """For the job's failure hook: the interview couldn't be scored. The application stays in
    `scoring` for a person; it is never rejected for it."""
    interview = await InterviewAttemptRepository(session, workspace_id).lock_interview(interview_id)
    if interview.assessment_status == "none":
        interview.assessment_status = "failed"
    await session.commit()


async def pending_before(
    session: AsyncSession, before: datetime
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """For requeue_stuck_work: transcribed interviews still waiting for their score."""
    return await assessments_pending_before(session, before)
