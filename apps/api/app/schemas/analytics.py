"""Dashboard payloads (DASH-003, API.md "Dashboard & analytics"). Every number respects the
caller's departments; Hiring managers see shortlist numbers only on the Overview and the
candidate pool, and the sections they can't see are null."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Range = Literal["week", "30d"]
DropReason = Literal["link_expired", "left_unfinished", "technical_issue"]
Fit = Literal["strong", "good"]


class Period(BaseModel):
    range: Range
    start: datetime
    end: datetime


class FlowSummary(BaseModel):
    """The Pipelines page band (FR-PIPE-08): applications to open pipelines that applied in the
    range, and where they are now."""

    period: Period
    applied: int
    # Against the period before; null when nobody applied then.
    applied_change_pct: int | None
    processing: int
    invited: int
    not_a_match: int
    interviewed: int
    in_progress: int
    not_started: int
    scoring: int
    ready_for_review: int
    flagged: int
    did_not_pass: int
    # Median hours from applying to the assessment, for assessments made in the range.
    median_hours_to_assessment: float | None


class OverviewKpis(BaseModel):
    """Applicants and time to screen follow the range (null for Hiring managers); the rest is
    the state right now."""

    applicants: int | None
    # Against the period before; null when nobody applied then.
    applicants_change_pct: int | None
    applicants_processing: int | None
    ready_for_review: int
    flagged: int
    advanced: int
    live_pipelines: int
    paused_pipelines: int
    scheduled_pipelines: int
    # Median days from applying to a finished interview, for interviews finished in the range,
    # and the change in days against the period before.
    median_days_to_screen: float | None
    median_days_to_screen_change: float | None


class OverviewFunnel(BaseModel):
    applied: int
    resume_matched: int
    finished_interview: int
    passed_interview: int
    # Finished interviews as a share of those invited, 0 to 100.
    interview_completion_pct: int | None


class WaitingCandidate(BaseModel):
    application_id: uuid.UUID
    pipeline_id: uuid.UUID
    name: str
    pipeline_title: str | None
    score: int
    fit: Fit | None
    waiting_since: datetime


class PipelineSoon(BaseModel):
    id: uuid.UUID
    title: str | None
    status: str
    closes_at: datetime | None
    applicants: int
    to_review: int


class WeekPoint(BaseModel):
    week_start: date
    applied: int
    passed: int


class SourceRow(BaseModel):
    source: str
    applicants: int
    # Share (0 to 100) that passed the interview; null with no applicants.
    pass_rate: int | None


class DropoffCounts(BaseModel):
    link_expired: int
    left_unfinished: int
    technical_issue: int


class ReviewQueue(BaseModel):
    count: int
    pipelines: int
    oldest_waiting_since: datetime | None


class FlaggedItem(BaseModel):
    name: str
    pipeline_title: str | None


class FlaggedQueue(BaseModel):
    count: int
    first: list[FlaggedItem]


class CreditAttention(BaseModel):
    pipeline_id: uuid.UUID
    title: str | None
    credits_left: int
    credits_reserved: int
    closes_at: datetime | None
    # Days of credits left at the last 14 days' pace (null when nobody applied in that time).
    days_of_credits: int | None


class PlanExpiry(BaseModel):
    credits: int
    expires_at: datetime


class InviteExpiry(BaseModel):
    pending: int
    expiring: int
    first_expires_at: datetime


class Attention(BaseModel):
    """FR-DASH-03, without human-review requests (ASMT-008 adds them)."""

    ready_for_review: ReviewQueue
    flagged: FlaggedQueue
    paused_for_credits: list[CreditAttention]
    running_low: list[CreditAttention]
    plan_credits_expiring: PlanExpiry | None
    invites_expiring: InviteExpiry | None


class CreditsCard(BaseModel):
    available: int
    reserved: int
    free: int
    plan_credits: int | None
    plan_credits_used: int | None


class Overview(BaseModel):
    period: Period
    timezone: str
    shortlist_only: bool
    kpis: OverviewKpis
    attention: Attention
    funnel: OverviewFunnel | None
    top_candidates: list[WaitingCandidate]
    closing_soon: list[PipelineSoon]
    weekly: list[WeekPoint] | None
    sources: list[SourceRow] | None
    # Last 30 days, whatever the range.
    dropoffs: DropoffCounts | None
    credits: CreditsCard | None


class DayPoint(BaseModel):
    day: date
    applicants: int


class ScoreBin(BaseModel):
    # 0, 10, … 90 (90 holds 90 to 100).
    start: int
    count: int


class PipelineSourceRow(BaseModel):
    source: str
    applicants: int
    # Share (0 to 100) of screened résumés that met the must-haves; null before any screen.
    resume_pass_rate: int | None


class PipelineFunnel(BaseModel):
    applied: int
    invited: int
    interviewed: int
    ready_for_review: int
    flagged: int


class PipelineKpis(BaseModel):
    candidates: int
    new_this_week: int
    ready_for_review: int
    median_days_to_assessment: float | None
    credits_used: int
    credits_reserved: int
    days_remaining: int | None
    closes_at: datetime | None


class PipelineDropoffs(DropoffCounts):
    invited: int
    # How many "Re-invite all" would send a new link to.
    reinvitable: int


class PipelineDashboard(BaseModel):
    pipeline_id: uuid.UUID
    timezone: str
    kpis: PipelineKpis
    funnel: PipelineFunnel
    daily: list[DayPoint]
    scores: list[ScoreBin]
    pass_mark: int
    interviewed: int
    passed: int
    sources: list[PipelineSourceRow]
    dropoffs: PipelineDropoffs


class MonthPoint(BaseModel):
    month: date
    candidates: int


class CandidateKpis(BaseModel):
    candidates: int
    new_this_month: int
    applied_more_than_once: int
    interviewed: int
    interviewed_pipelines: int
    passed_interview: int
    median_days_to_assessment: float | None


class Repeats(BaseModel):
    once: int
    twice: int
    three_times: int
    four_or_more: int
    # Share (0 to 100) of returning and first-time candidates who passed an interview.
    returning_pass_rate: int | None
    first_time_pass_rate: int | None


class PeopleSource(BaseModel):
    source: str
    people: int
    pass_rate: int | None


class CandidatesDashboard(BaseModel):
    timezone: str
    shortlist_only: bool
    kpis: CandidateKpis
    new_per_month: list[MonthPoint]
    repeats: Repeats
    # Applications per stage, every stage present.
    stages: dict[str, int]
    sources: list[PeopleSource]
