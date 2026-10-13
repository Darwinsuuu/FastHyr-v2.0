"""The candidate profile (ASMT-004, FR-ASMT-07, frame CandidateProfile): one application with how
its score was reached, the evidence behind it and how it compares in its pipeline.

Recruiters reach applications in their departments' pipelines; Hiring managers only shortlisted
ones (ready for review, flagged, advanced); anything else is 404 (SECURITY.md §2). Comparisons
are computed among every completed, assessed interview in the same pipeline, whoever asks: they
are aggregates and name nobody. Nothing here changes data.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from statistics import fmean
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import AppError
from app.core.permissions import Access, Action, can
from app.integrations.storage import (
    MAX_SIGNED_URL_TTL,
    Bucket,
    Storage,
    StorageObjectMissingError,
    StorageRejectedError,
    recording_file_path,
)
from app.models import (
    Application,
    Assessment,
    HumanReviewRequest,
    IntegrityFlag,
    Interview,
    ResumeAssessment,
)
from app.repositories.application_profile import (
    ApplicationProfileRepository,
    PipelineScore,
    ProfileRow,
)
from app.repositories.company_profiles import workspace_timezone
from app.repositories.integrity import member_names_by_member, reviewer_names
from app.repositories.pipeline_candidates import FLAGGABLE_STAGES
from app.repositories.review_requests import ReviewRequestRepository
from app.schemas.application_profile import (
    AnswerStats,
    AnswerStatsAverages,
    ApplicationProfile,
    Comparison,
    CriteriaComparison,
    CriterionComparison,
    CriterionResult,
    Evidence,
    HistoryItem,
    IntegrityChecks,
    JourneyStep,
    MustHave,
    Point,
    ProfileAssessment,
    ProfileCandidate,
    ProfileIntegrity,
    ProfileInterview,
    ProfilePipeline,
    ProfileResume,
    ProfileReviewRequest,
    RecordingUrl,
    ScoreBucket,
    Signal,
    Summary,
    TopicResult,
)
from app.schemas.application_profile import (
    Criteria as CriteriaResult,
)
from app.services import review_requests
from app.services.integrity_reviews import flag_result

CRITERIA = ("technical", "communication", "culture")
# The distribution's groups: under 50, then each ten, with 90 to 100 together.
BUCKETS = (0, 50, 60, 70, 80, 90)
FITS = {"strong_fit": "strong", "good_fit": "good"}


class RecordingNotReadyError(AppError):
    """No finished recording to play yet (or none at all)."""

    status = 404
    code = "recording_not_ready"
    title = "The recording isn't ready yet"


def _repository(session: AsyncSession, ctx: RequestContext) -> ApplicationProfileRepository:
    return ApplicationProfileRepository(
        session,
        ctx.workspace_id,
        department_ids=None if ctx.sees_all_departments else ctx.department_ids,
        shortlist=can(ctx, Action.VIEW_CANDIDATES) is Access.SHORTLIST,
    )


async def profile(
    session: AsyncSession, ctx: RequestContext, application_id: uuid.UUID
) -> ApplicationProfile:
    repo = _repository(session, ctx)
    row = await repo.application(application_id)
    application, candidate, pipeline = row.application, row.candidate, row.pipeline
    screen = await repo.resume_assessment(application.id)
    interview = await repo.interview(application.id)
    assessment = await repo.assessment(application.id)
    flags = await repo.flags(interview.id) if interview else []

    comparison: Comparison | None = None
    profile_assessment: ProfileAssessment | None = None
    if assessment is not None:
        scores = await repo.pipeline_scores(pipeline.id)
        plans = await repo.plan_topics(
            {application.id, *(score.application_id for score in scores)}
        )
        comparison = compare(assessment, scores)
        profile_assessment = assessment_of(
            assessment,
            pass_mark=_pass_mark(assessment, pipeline.pass_mark),
            plan=plans.get(application.id, []),
            averages=topic_averages(scores, plans, plans.get(application.id, [])),
        )

    history = await repo.history(candidate.id)
    open_flags = sum(1 for flag in flags if flag.status == "open")
    reviews = await ReviewRequestRepository(session, ctx.workspace_id).latest_of(application.id)
    open_review = next((review for review in reviews if review.status == "open"), None)
    return ApplicationProfile(
        id=application.id,
        stage=application.stage,
        flagged=application.has_open_flags and application.stage in FLAGGABLE_STAGES,
        open_flags=open_flags,
        review_requested=application.review_requested,
        review_request=(
            ProfileReviewRequest(
                id=open_review.id,
                decision_type="interview" if open_review.decision_type == "interview" else "resume",
                message=open_review.candidate_message,
                created_at=open_review.created_at,
                by_person=application.stage == "rejected",
                can_override=review_requests.can_override(application.stage),
            )
            if open_review
            else None
        ),
        fit=application.fit,
        source=application.source,
        applied_at=application.applied_at,
        candidate=ProfileCandidate(
            id=candidate.id, name=candidate.full_name, email=candidate.email
        ),
        pipeline=ProfilePipeline(
            id=pipeline.id,
            title=pipeline.title or "",
            status=pipeline.status,
            pass_mark=pipeline.pass_mark,
            interview_format=pipeline.interview_format,
            integrity_enabled=pipeline.integrity_enabled,
            rubric_locked_at=pipeline.published_at,
        ),
        workspace_name=row.workspace_name,
        timezone=await workspace_timezone(session, ctx.workspace_id) or "UTC",
        resume=_resume(application, screen),
        interview=_interview(interview) if interview else None,
        assessment=profile_assessment,
        comparison=comparison,
        integrity=(
            _integrity(interview, flags, await reviewer_names(session, flags))
            if interview and interview.completed_at
            else None
        ),
        history=[
            HistoryItem(
                application_id=item.application.id,
                pipeline_title=item.pipeline_title or "",
                stage=item.application.stage,
                overall_score=item.application.overall_score,
                applied_at=item.application.applied_at,
                current=item.application.id == application.id,
            )
            for item in history
        ],
        journey=journey(
            row,
            screen,
            interview,
            assessment,
            await _deciders(session, application, reviews),
            reviews,
        ),
    )


# --- The application's own parts ------------------------------------------------------------


def _resume(application: Application, screen: ResumeAssessment | None) -> ProfileResume:
    must_haves = [
        MustHave(name=str(result.get("criterion", "")), met=bool(result.get("met")))
        for result in (screen.must_have_results if screen else [])
        if isinstance(result, dict)
    ]
    return ProfileResume(
        status=application.resume_status,
        score=screen.score if screen else None,
        pass_bar=screen.pass_bar if screen else None,
        passed=screen.passed if screen else None,
        must_haves=must_haves,
        screened_at=screen.screened_at if screen else None,
    )


def _interview(interview: Interview) -> ProfileInterview:
    return ProfileInterview(
        status=interview.status,
        format=interview.format,
        invited_at=interview.invited_at,
        started_at=interview.started_at,
        completed_at=interview.completed_at,
        duration_seconds=interview.duration_seconds,
        recording_ready=interview.recording_status == "ready" and bool(interview.recording_path),
        assessment_status=interview.assessment_status,
        integrity_status=interview.integrity_status,
    )


def _pass_mark(assessment: Assessment, current: int | None) -> int:
    """The pass mark the interview was scored against (the rubric is locked on publish)."""
    snapshot = assessment.rubric_snapshot or {}
    value = snapshot.get("pass_mark")
    if isinstance(value, int):
        return value
    return current if current is not None else 0


def _evidence(rows: Any) -> list[Evidence]:
    found = []
    for row in rows or []:
        if not isinstance(row, dict) or row.get("source") not in ("interview", "resume"):
            continue
        interview = row["source"] == "interview"
        start = row.get("start_ms")
        found.append(
            Evidence(
                source=row["source"],
                quote=str(row.get("quote", "")),
                start_ms=int(start) if interview and isinstance(start, int) else None,
                label=str(row.get("source_label", "")),
            )
        )
    return found


def _criterion(row: Any) -> CriterionResult:
    row = row if isinstance(row, dict) else {}
    score = int(row.get("score") or 0)
    weight = int(row.get("weight") or 0)
    points = row.get("points")
    return CriterionResult(
        score=score,
        weight=weight,
        points=float(points) if isinstance(points, int | float) else round(score * weight / 100, 1),
        signals=[
            Signal(name=str(signal.get("name", "")), score=int(signal.get("score") or 0))
            for signal in row.get("signals") or []
            if isinstance(signal, dict)
        ],
        evidence=_evidence(row.get("evidence")),
        held_back=str(row.get("held_back") or ""),
    )


def _answer_stats(stats: dict[str, Any]) -> AnswerStats | None:
    if not stats or "avg_answer_ms" not in stats:
        return None
    return AnswerStats(
        avg_answer_ms=int(stats.get("avg_answer_ms") or 0),
        avg_response_delay_ms=int(stats.get("avg_response_delay_ms") or 0),
        questions=int(stats.get("questions") or 0),
        follow_ups=int(stats.get("follow_ups") or 0),
        candidate_questions=int(stats.get("candidate_questions") or 0),
        talk_time_pct=int(stats.get("talk_time_pct") or 0),
    )


def _points(rows: Any) -> list[Point]:
    return [
        Point(title=str(point.get("title", "")), reason=str(point.get("reason", "")))
        for point in rows or []
        if isinstance(point, dict)
    ]


def _kind(plan: Sequence[Any], index: int) -> Any:
    topic = plan[index] if 0 <= index < len(plan) else None
    kind = topic.get("kind") if isinstance(topic, dict) else None
    return kind if kind in ("warm_up", "skills", "candidate_questions") else None


def assessment_of(
    assessment: Assessment,
    *,
    pass_mark: int,
    plan: Sequence[Any],
    averages: dict[int, int | None],
) -> ProfileAssessment:
    criteria = {name: _criterion((assessment.criteria or {}).get(name)) for name in CRITERIA}
    summary = assessment.summary or {}
    return ProfileAssessment(
        overall_score=assessment.overall_score,
        passed=assessment.passed,
        fit=FITS.get(assessment.fit or ""),
        criteria=CriteriaResult(**criteria),
        pass_mark=pass_mark,
        topics=[
            TopicResult(
                index=int(topic.get("index", 0)),
                title=str(topic.get("title", "")),
                kind=_kind(plan, int(topic.get("index", 0))),
                start_ms=int(topic.get("start_ms") or 0),
                questions=int(topic.get("questions") or 0),
                follow_ups=int(topic.get("follow_ups") or 0),
                score=topic.get("score"),
                average=averages.get(int(topic.get("index", 0))),
            )
            for topic in assessment.topics or []
            if isinstance(topic, dict)
        ],
        summary=Summary(text=str(summary.get("text", "")), refs=_evidence(summary.get("refs"))),
        strengths=_points(assessment.strengths),
        probes=_points(assessment.probes),
        answer_stats=_answer_stats(assessment.answer_stats or {}),
        evidence_count=sum(len(criterion.evidence) for criterion in criteria.values()),
        assessed_at=assessment.created_at,
    )


# --- Comparisons in the pipeline ------------------------------------------------------------


def _whole(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def bucket_of(score: int) -> int:
    return max(start for start in BUCKETS if score >= start)


def _criterion_score(score: PipelineScore, name: str) -> int | None:
    row = score.criteria.get(name)
    value = row.get("score") if isinstance(row, dict) else None
    return value if isinstance(value, int) else None


def compare(assessment: Assessment, scores: Sequence[PipelineScore]) -> Comparison:
    """How this interview sits among every assessed interview in the pipeline (it is one of
    them)."""
    if not any(score.application_id == assessment.application_id for score in scores):
        scores = [
            *scores,
            PipelineScore(
                assessment.application_id,
                assessment.overall_score,
                assessment.passed,
                assessment.criteria or {},
                assessment.topics or [],
                assessment.answer_stats or {},
            ),
        ]
    overall = [score.overall_score for score in scores]
    criteria = {}
    for name in CRITERIA:
        everyone = [v for s in scores if (v := _criterion_score(s, name)) is not None]
        passed = [v for s in scores if s.passed and (v := _criterion_score(s, name)) is not None]
        criteria[name] = CriterionComparison(
            average=_whole(fmean(everyone)) if everyone else 0,
            passed_average=_whole(fmean(passed)) if passed else None,
        )
    return Comparison(
        interviewed=len(scores),
        rank=1 + sum(1 for value in overall if value > assessment.overall_score),
        average=_whole(fmean(overall)),
        passed=sum(1 for score in scores if score.passed),
        distribution=[
            ScoreBucket(start=start, count=sum(1 for v in overall if bucket_of(v) == start))
            for start in BUCKETS
        ],
        criteria=CriteriaComparison(**criteria),
        answer_stats=_stats_averages([score.answer_stats for score in scores]),
    )


def _stats_averages(rows: Sequence[dict[str, Any]]) -> AnswerStatsAverages | None:
    rows = [row for row in rows if row and "avg_answer_ms" in row]
    if not rows:
        return None

    def mean(key: str) -> float:
        return fmean(float(row.get(key) or 0) for row in rows)

    return AnswerStatsAverages(
        avg_answer_ms=_whole(mean("avg_answer_ms")),
        avg_response_delay_ms=_whole(mean("avg_response_delay_ms")),
        follow_ups=round(mean("follow_ups"), 1),
        candidate_questions=round(mean("candidate_questions"), 1),
        talk_time_pct=_whole(mean("talk_time_pct")),
    )


def _topic_keys(plan: Sequence[Any], index: int) -> set[str]:
    """What makes topics comparable across personal plans: the warm-up and the candidate's
    questions by kind, the others by the skills to probe they cover."""
    if not 0 <= index < len(plan) or not isinstance(plan[index], dict):
        return set()
    topic = plan[index]
    kind = topic.get("kind")
    if kind in ("warm_up", "candidate_questions"):
        return {f"kind:{kind}"}
    return {f"skill:{skill}" for skill in topic.get("skills") or [] if isinstance(skill, str)}


def topic_averages(
    scores: Sequence[PipelineScore],
    plans: dict[uuid.UUID, list[Any]],
    own_plan: Sequence[Any],
) -> dict[int, int | None]:
    """For each topic of this candidate's plan, the mean score of every scored topic in the
    pipeline that shares a key with it (`_topic_keys`); None when no topic does."""
    scored: list[tuple[set[str], int]] = []
    for score in scores:
        plan = plans.get(score.application_id, [])
        for topic in score.topics:
            if not isinstance(topic, dict) or not isinstance(topic.get("score"), int):
                continue
            keys = _topic_keys(plan, int(topic.get("index", -1)))
            if keys:
                scored.append((keys, topic["score"]))
    averages: dict[int, int | None] = {}
    for index in range(len(own_plan)):
        keys = _topic_keys(own_plan, index)
        values = [value for other, value in scored if keys & other]
        averages[index] = _whole(fmean(values)) if values else None
    return averages


# --- Integrity and journey ------------------------------------------------------------------

_CHECK_VALUES = {
    "face": ("ran", "no_consent", "voice_only", "no_video"),
    "second_voice": ("ran",),
    "timing": ("ran", "too_short"),
    "read_aloud": ("ran", "too_short", "failed"),
}


def _integrity(
    interview: Interview, flags: Sequence[IntegrityFlag], reviewers: dict[uuid.UUID, str]
) -> ProfileIntegrity:
    checks = None
    if interview.integrity_checks:
        checks = IntegrityChecks(
            **{
                name: value if (value := interview.integrity_checks.get(name)) in allowed else None
                for name, allowed in _CHECK_VALUES.items()
            }
        )
    return ProfileIntegrity(
        status=interview.integrity_status,
        checks=checks,
        flags=[flag_result(flag, reviewers) for flag in flags],
    )


def journey(
    row: ProfileRow,
    screen: ResumeAssessment | None,
    interview: Interview | None,
    assessment: Assessment | None,
    deciders: dict[uuid.UUID, str] | None = None,
    reviews: Sequence[HumanReviewRequest] = (),
) -> list[JourneyStep]:
    """What happened to the application, in order; `deciders` names who advanced, rejected or
    resolved a review request (by member ID)."""
    deciders = deciders or {}
    application = row.application
    steps = [JourneyStep(kind="applied", at=application.applied_at)]
    if screen is not None:
        steps.append(
            JourneyStep(
                kind="resume_matched" if screen.passed else "resume_not_matched",
                at=screen.screened_at,
            )
        )
    if interview is not None:
        steps.append(JourneyStep(kind="invited", at=interview.invited_at))
        if interview.completed_at is not None:
            steps.append(JourneyStep(kind="interview_finished", at=interview.completed_at))
    if assessment is not None:
        steps.append(
            JourneyStep(
                kind="ready_for_review" if assessment.passed else "did_not_pass",
                at=assessment.created_at,
            )
        )
    if application.stage == "advanced" and application.advanced_at:
        steps.append(
            JourneyStep(
                kind="advanced",
                at=application.advanced_at,
                by=deciders.get(application.advanced_by) if application.advanced_by else None,
                note=application.advanced_note,
            )
        )
    if application.stage == "rejected" and application.rejected_at:
        steps.append(
            JourneyStep(
                kind="rejected",
                at=application.rejected_at,
                by=deciders.get(application.rejected_by) if application.rejected_by else None,
                note=application.rejected_reason,
            )
        )
    # Review steps go in by time; the steps above keep their order.
    for review in reviews:
        _insert(steps, JourneyStep(kind="review_requested", at=review.created_at))
        if review.resolved_at is not None:
            _insert(
                steps,
                JourneyStep(
                    kind="review_overridden" if review.status == "overridden" else "review_upheld",
                    at=review.resolved_at,
                    by=deciders.get(review.resolved_by) if review.resolved_by else None,
                    note=review.resolution_note,
                ),
            )
    return steps


def _insert(steps: list[JourneyStep], step: JourneyStep) -> None:
    """Before the first later step, else last."""
    index = next((i for i, other in enumerate(steps) if other.at > step.at), len(steps))
    steps.insert(index, step)


async def _deciders(
    session: AsyncSession, application: Application, reviews: Sequence[HumanReviewRequest]
) -> dict[uuid.UUID, str]:
    """Who advanced or rejected the application (ASMT-007) and resolved its review requests."""
    ids = {application.advanced_by, application.rejected_by}
    ids |= {review.resolved_by for review in reviews}
    return await member_names_by_member(session, {id_ for id_ in ids if id_ is not None})


# --- Recording ------------------------------------------------------------------------------


async def recording_url(
    session: AsyncSession, storage: Storage, ctx: RequestContext, application_id: uuid.UUID
) -> RecordingUrl:
    """Signed links to the live interview's finished recording and its poster frame."""
    repo = _repository(session, ctx)
    await repo.application(application_id)
    interview = await repo.interview(application_id)
    await session.commit()
    if interview is None or interview.recording_status != "ready" or not interview.recording_path:
        raise RecordingNotReadyError()
    expires_at = datetime.now(UTC) + MAX_SIGNED_URL_TTL - timedelta(seconds=30)
    try:
        url = await storage.signed_download_url(Bucket.RECORDINGS, interview.recording_path)
    except StorageObjectMissingError as error:
        raise RecordingNotReadyError() from error
    video = interview.format == "video_voice"
    poster_url = None
    if video:
        poster = recording_file_path(interview.workspace_id, interview.id, "poster.jpg")
        try:
            poster_url = await storage.signed_download_url(Bucket.RECORDINGS, poster)
        except (StorageObjectMissingError, StorageRejectedError):
            poster_url = None
    return RecordingUrl(
        url=url,
        poster_url=poster_url,
        kind="video" if video else "audio",
        duration_seconds=interview.duration_seconds,
        expires_at=expires_at,
    )
