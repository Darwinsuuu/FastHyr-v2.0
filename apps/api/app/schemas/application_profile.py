"""The candidate profile (ASMT-004, FR-ASMT-07, frame CandidateProfile): one application with its
résumé screen, interview assessment, how it compares in its pipeline, integrity checks, the
person's other applications and the journey. TA users only: candidates never see scores, signals
or flags (hard rule 5)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.ai.schemas.interview_plan import TopicKind
from app.integrity.flags import FlagType
from app.schemas.applications import SourceTag
from app.schemas.pipeline_candidates import ApplicationStage

Fit = Literal["strong", "good"]


class ProfileCandidate(BaseModel):
    id: uuid.UUID
    name: str
    email: str


class ProfilePipeline(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    pass_mark: int | None
    interview_format: Literal["video_voice", "voice_only"] | None
    integrity_enabled: bool
    # When the rubric was locked: the pipeline's publication.
    rubric_locked_at: datetime | None


class MustHave(BaseModel):
    name: str
    met: bool


class ProfileResume(BaseModel):
    """The résumé screen (SCREEN-002); `score` and the rest are null until it has run."""

    status: Literal["pending", "done", "unreadable", "error"]
    score: int | None
    pass_bar: int | None
    passed: bool | None
    must_haves: list[MustHave]
    screened_at: datetime | None


class ProfileInterview(BaseModel):
    """The application's latest interview link."""

    status: str
    format: Literal["video_voice", "voice_only"]
    invited_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: int | None
    recording_ready: bool
    assessment_status: str
    integrity_status: str


class Evidence(BaseModel):
    source: Literal["interview", "resume"]
    quote: str
    # Where the quote starts on the recording's clock; null for a résumé quote.
    start_ms: int | None
    # What it shows or answers, e.g. "System design question".
    label: str


class Signal(BaseModel):
    name: str
    score: int


class CriterionResult(BaseModel):
    score: int
    # The pipeline's weight (percent) when scored, and score x weight / 100.
    weight: int
    points: float
    signals: list[Signal]
    evidence: list[Evidence]
    held_back: str


class Criteria(BaseModel):
    technical: CriterionResult
    communication: CriterionResult
    culture: CriterionResult


class TopicResult(BaseModel):
    index: int
    title: str
    kind: TopicKind | None
    start_ms: int
    questions: int
    follow_ups: int
    # Null when the candidate didn't answer in this topic.
    score: int | None
    # The pipeline's average for topics of the same kind or skills; null when there is none.
    average: int | None


class Summary(BaseModel):
    # Cites `refs` as [1], [2]… in order.
    text: str
    refs: list[Evidence]


class Point(BaseModel):
    title: str
    reason: str


class AnswerStats(BaseModel):
    avg_answer_ms: int
    avg_response_delay_ms: int
    questions: int
    follow_ups: int
    candidate_questions: int
    talk_time_pct: int


class ProfileAssessment(BaseModel):
    """The latest interview assessment (ASMT-001)."""

    overall_score: int
    passed: bool
    fit: Fit | None
    criteria: Criteria
    # The pass mark it was scored against.
    pass_mark: int
    topics: list[TopicResult]
    summary: Summary
    strengths: list[Point]
    probes: list[Point]
    answer_stats: AnswerStats | None
    evidence_count: int
    assessed_at: datetime


class ScoreBucket(BaseModel):
    # 0 for under 50, then 50, 60, 70, 80 and 90 (90 to 100).
    start: int
    count: int


class CriterionComparison(BaseModel):
    average: int
    # Null when nobody in the pipeline passed.
    passed_average: int | None


class CriteriaComparison(BaseModel):
    technical: CriterionComparison
    communication: CriterionComparison
    culture: CriterionComparison


class AnswerStatsAverages(BaseModel):
    avg_answer_ms: int
    avg_response_delay_ms: int
    follow_ups: float
    candidate_questions: float
    talk_time_pct: int


class Comparison(BaseModel):
    """Among every completed, assessed interview in the pipeline (FR-ASMT-07). Aggregates only."""

    interviewed: int
    # 1 for the highest score; equal scores share a place.
    rank: int
    average: int
    passed: int
    distribution: list[ScoreBucket]
    criteria: CriteriaComparison
    answer_stats: AnswerStatsAverages | None


FlagStatus = Literal["open", "no_concern", "concern_confirmed"]


class IntegrityFlag(BaseModel):
    id: uuid.UUID
    type: FlagType
    start_ms: int
    end_ms: int
    confidence: float
    status: FlagStatus
    # Set once a person reviewed it (ASMT-003): when, who (name, or email without one) and
    # their note, for the team only.
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    note: str | None = None


class IntegrityChecks(BaseModel):
    face: Literal["ran", "no_consent", "voice_only", "no_video"] | None
    second_voice: Literal["ran"] | None
    timing: Literal["ran", "too_short"] | None
    read_aloud: Literal["ran", "too_short", "failed"] | None


class ProfileIntegrity(BaseModel):
    # none: not run yet · off: the pipeline doesn't check · ready · failed.
    status: Literal["none", "off", "ready", "failed"]
    checks: IntegrityChecks | None
    flags: list[IntegrityFlag]


class HistoryItem(BaseModel):
    """One of the person's applications in this workspace that the caller can see."""

    application_id: uuid.UUID
    pipeline_title: str
    stage: ApplicationStage
    overall_score: int | None
    applied_at: datetime
    current: bool


JourneyKind = Literal[
    "applied",
    "resume_matched",
    "resume_not_matched",
    "invited",
    "interview_finished",
    "ready_for_review",
    "did_not_pass",
    "advanced",
    "rejected",
]


class JourneyStep(BaseModel):
    kind: JourneyKind
    at: datetime
    # Advanced and rejected (ASMT-007): who decided, and the note or reason (the team's only).
    by: str | None = None
    note: str | None = None


class ApplicationProfile(BaseModel):
    id: uuid.UUID
    stage: ApplicationStage
    # Open integrity flags on a ready or did-not-pass application (the Flagged filter).
    flagged: bool
    open_flags: int
    review_requested: bool
    fit: Fit | None
    source: SourceTag
    applied_at: datetime
    candidate: ProfileCandidate
    pipeline: ProfilePipeline
    workspace_name: str
    # The workspace's time zone, for dates and times.
    timezone: str
    resume: ProfileResume
    interview: ProfileInterview | None
    assessment: ProfileAssessment | None
    comparison: Comparison | None
    integrity: ProfileIntegrity | None
    history: list[HistoryItem]
    journey: list[JourneyStep]


class RecordingUrl(BaseModel):
    """Signed links to the interview recording, valid until `expires_at`."""

    url: str
    poster_url: str | None
    kind: Literal["video", "audio"]
    duration_seconds: int | None
    expires_at: datetime
