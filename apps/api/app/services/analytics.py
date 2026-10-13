"""One analytics layer for every dashboard (DASH-003): the Pipelines page flow, Overview, a
pipeline's Dashboard tab and the candidate pool dashboard.

Numbers come from the views in DATABASE.md §4 through `AnalyticsRepository`, which applies the
caller's departments and, for Hiring managers on the Overview and the candidate pool, the
shortlist (SECURITY.md §2). Ranges: "week" is the last 7 days and "30d" the last 30, each
compared with the period just before; days, weeks (from Monday) and months are local to the
workspace's time zone.
"""

import math
import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.permissions import Access, Action, can
from app.repositories.analytics import (
    OPEN_STATUSES,
    AnalyticsRepository,
    StageCounts,
    Window,
)
from app.repositories.company_profiles import workspace_timezone
from app.repositories.pipelines import PipelineRepository
from app.schemas.analytics import (
    Attention,
    CandidateKpis,
    CandidatesDashboard,
    CreditAttention,
    CreditsCard,
    DayPoint,
    DropoffCounts,
    FlaggedItem,
    FlaggedQueue,
    FlowSummary,
    InviteExpiry,
    MonthPoint,
    Overview,
    OverviewFunnel,
    OverviewKpis,
    PeopleSource,
    Period,
    PipelineDashboard,
    PipelineDropoffs,
    PipelineFunnel,
    PipelineKpis,
    PipelineSoon,
    PipelineSourceRow,
    PlanExpiry,
    Range,
    Repeats,
    ReviewQueue,
    ScoreBin,
    SourceRow,
    WaitingCandidate,
    WeekPoint,
)
from app.services import credits

RANGE_DAYS: dict[Range, int] = {"week": 7, "30d": 30}
DROP_REASONS = ("link_expired", "left_unfinished", "technical_issue")
STAGES = (
    "processing_resume",
    "resume_not_match",
    "invited",
    "interview_in_progress",
    "scoring",
    "ready_for_review",
    "did_not_pass",
    "advanced",
    "rejected",
)
TOP_CANDIDATES = 5
CLOSING_SOON = 5
WEEKS = 8
DAYS = 14
MONTHS = 6
# "Running low" (FR-DASH-03): under 30 days of credits at the pace of the last 14 days.
LOW_DAYS = 30
PACE_DAYS = 14
PLAN_EXPIRY_DAYS = 7
INVITE_EXPIRY_DAYS = 3


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


async def _zone(session: AsyncSession, workspace_id: uuid.UUID) -> str:
    return await workspace_timezone(session, workspace_id) or "UTC"


def _repo(
    session: AsyncSession, ctx: RequestContext, *, shortlist_action: Action | None = None
) -> AnalyticsRepository:
    shortlist = shortlist_action is not None and can(ctx, shortlist_action) is Access.SHORTLIST
    return AnalyticsRepository(
        session,
        ctx.workspace_id,
        department_ids=None if ctx.sees_all_departments else ctx.department_ids,
        shortlist=shortlist,
    )


def _periods(range_: Range, now: datetime) -> tuple[Window, Window]:
    days = timedelta(days=RANGE_DAYS[range_])
    return Window(now - days, now), Window(now - 2 * days, now - days)


def _pct(part: int, whole: int) -> int | None:
    return None if whole <= 0 else round(part * 100 / whole)


def _change_pct(current: int, previous: int) -> int | None:
    return None if previous <= 0 else round((current - previous) * 100 / previous)


def _days(seconds: float | None) -> float | None:
    return None if seconds is None else round(seconds / 86400, 1)


def _local_midnight(day: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, time(0), tzinfo=zone).astimezone(UTC)


def _months_back(month: date, count: int) -> date:
    index = month.year * 12 + month.month - 1 - count
    return date(index // 12, index % 12 + 1, 1)


# -- Pipelines page -----------------------------------------------------------------------------
async def pipelines_flow(
    session: AsyncSession, ctx: RequestContext, range_: Range, *, now: datetime | None = None
) -> FlowSummary:
    """How candidates are moving through the caller's open pipelines."""
    now = _now(now)
    current, previous = _periods(range_, now)
    repo = _repo(session, ctx)
    counts = await repo.stage_counts(current, open_pipelines_only=True)
    before = await repo.stage_counts(previous, open_pipelines_only=True)
    median = await repo.median_seconds("assessment", current, open_pipelines_only=True)
    return FlowSummary(
        period=Period(range=range_, start=current.start or now, end=now),
        applied=counts.applied,
        applied_change_pct=_change_pct(counts.applied, before.applied),
        processing=counts.processing,
        invited=counts.invited,
        not_a_match=counts.not_a_match,
        interviewed=counts.interviewed,
        in_progress=counts.in_progress,
        not_started=counts.not_started,
        scoring=counts.scoring,
        ready_for_review=counts.ready_for_review,
        flagged=counts.flagged,
        did_not_pass=counts.did_not_pass,
        median_hours_to_assessment=None if median is None else round(median / 3600, 1),
    )


# -- Overview -----------------------------------------------------------------------------------
async def overview(
    session: AsyncSession, ctx: RequestContext, range_: Range, *, now: datetime | None = None
) -> Overview:
    now = _now(now)
    timezone = await _zone(session, ctx.workspace_id)
    zone = ZoneInfo(timezone)
    current, previous = _periods(range_, now)
    repo = _repo(session, ctx, shortlist_action=Action.VIEW_OVERVIEW)
    shortlist = repo.shortlist
    sees_credits = can(ctx, Action.VIEW_CREDIT_USAGE) is not None

    everything = await repo.stage_counts()
    statuses = await repo.pipeline_statuses()
    open_rows = await repo.open_pipelines(now - timedelta(days=PACE_DAYS))
    waiting = await repo.waiting_on_review(TOP_CANDIDATES)
    queue_count, queue_pipelines, oldest = await repo.review_queue()
    flagged_count, flagged_first = await repo.flagged(2)

    kpis = OverviewKpis(
        applicants=None,
        applicants_change_pct=None,
        applicants_processing=None,
        ready_for_review=everything.ready_for_review,
        flagged=everything.flagged,
        advanced=everything.advanced,
        live_pipelines=statuses.get("live", 0),
        paused_pipelines=statuses.get("paused", 0) + statuses.get("paused_no_credits", 0),
        scheduled_pipelines=statuses.get("scheduled", 0),
        median_days_to_screen=None,
        median_days_to_screen_change=None,
    )
    funnel = weekly = sources = dropoffs = None
    if not shortlist:
        cohort = await repo.stage_counts(current)
        before = await repo.stage_counts(previous)
        median_now = _days(await repo.median_seconds("interview", current))
        median_before = _days(await repo.median_seconds("interview", previous))
        kpis.applicants = cohort.applied
        kpis.applicants_change_pct = _change_pct(cohort.applied, before.applied)
        kpis.applicants_processing = cohort.processing
        kpis.median_days_to_screen = median_now
        if median_now is not None and median_before is not None:
            kpis.median_days_to_screen_change = round(median_now - median_before, 1)
        funnel = OverviewFunnel(
            applied=cohort.applied,
            resume_matched=cohort.invited,
            finished_interview=cohort.interviewed,
            passed_interview=cohort.passed,
            interview_completion_pct=_pct(cohort.interviewed, cohort.invited),
        )
        weekly = await _weekly(repo, timezone, zone, now)
        sources = [
            SourceRow(
                source=row.source,
                applicants=row.applicants,
                pass_rate=_pct(row.interview_passed, row.applicants),
            )
            for row in await repo.sources()
        ]
        dropoffs = _dropoff_counts(await repo.dropoffs(since=now - timedelta(days=30)))

    paused_for_credits: list[CreditAttention] = []
    running_low: list[CreditAttention] = []
    if sees_credits:
        for row in open_rows:
            left = max(row.credits_reserved - row.credits_used, 0)
            pace = row.recent_applicants / PACE_DAYS
            days_of_credits = math.floor(left / pace) if pace else None
            item = CreditAttention(
                pipeline_id=row.id,
                title=row.title,
                credits_left=left,
                credits_reserved=row.credits_reserved,
                closes_at=row.closes_at,
                days_of_credits=days_of_credits,
            )
            days_open = (row.closes_at - now).days if row.closes_at else None
            if row.status == "paused_no_credits":
                paused_for_credits.append(item)
            elif (
                row.status == "live"
                and days_of_credits is not None
                and days_of_credits < LOW_DAYS
                and (days_open is None or days_of_credits < days_open)
            ):
                running_low.append(item)
        running_low.sort(key=lambda item: item.days_of_credits or 0)

    plan_expiry = invite_expiry = None
    credits_card = None
    if sees_credits:
        expiring, first_expiry = await repo.plan_credits_expiring(
            now, now + timedelta(days=PLAN_EXPIRY_DAYS)
        )
        if expiring and first_expiry:
            plan_expiry = PlanExpiry(credits=expiring, expires_at=first_expiry)
        summary = await credits.summary(session, ctx.workspace_id, now=now)
        plan = await repo.current_plan_batch(now)
        credits_card = CreditsCard(
            available=summary.balance,
            reserved=summary.reserved,
            free=summary.free,
            plan_credits=plan[0] if plan else None,
            plan_credits_used=plan[0] - plan[1] if plan else None,
        )
    if can(ctx, Action.MANAGE_WORKSPACE) is not None:
        pending, expiring_invites, first = await repo.invites_expiring(
            now, now + timedelta(days=INVITE_EXPIRY_DAYS)
        )
        if expiring_invites and first:
            invite_expiry = InviteExpiry(
                pending=pending, expiring=expiring_invites, first_expires_at=first
            )

    return Overview(
        period=Period(range=range_, start=current.start or now, end=now),
        timezone=timezone,
        shortlist_only=shortlist,
        kpis=kpis,
        attention=Attention(
            ready_for_review=ReviewQueue(
                count=queue_count, pipelines=queue_pipelines, oldest_waiting_since=oldest
            ),
            flagged=FlaggedQueue(
                count=flagged_count,
                first=[FlaggedItem(name=n, pipeline_title=t) for n, t in flagged_first],
            ),
            paused_for_credits=paused_for_credits,
            running_low=running_low,
            plan_credits_expiring=plan_expiry,
            invites_expiring=invite_expiry,
            review_requests=None if shortlist else await repo.review_requests(),
        ),
        funnel=funnel,
        top_candidates=[
            WaitingCandidate(
                application_id=w.application_id,
                pipeline_id=w.pipeline_id,
                name=w.candidate_name,
                pipeline_title=w.pipeline_title,
                score=w.score,
                fit=w.fit,
                waiting_since=w.waiting_since,
            )
            for w in waiting
        ],
        closing_soon=[
            PipelineSoon(
                id=row.id,
                title=row.title,
                status=row.status,
                closes_at=row.closes_at,
                applicants=row.applicants,
                to_review=row.to_review,
            )
            for row in open_rows[:CLOSING_SOON]
        ],
        weekly=weekly,
        sources=sources,
        dropoffs=dropoffs,
        credits=credits_card,
    )


async def _weekly(
    repo: AnalyticsRepository, timezone: str, zone: ZoneInfo, now: datetime
) -> list[WeekPoint]:
    today = now.astimezone(zone).date()
    this_week = today - timedelta(days=today.weekday())
    weeks = [this_week - timedelta(weeks=n) for n in range(WEEKS - 1, -1, -1)]
    since = _local_midnight(weeks[0], zone)
    applied = await repo.applied_per_period("week", since, timezone)
    passed = await repo.passed_per_period("week", since, timezone)
    return [
        WeekPoint(week_start=week, applied=applied.get(week, 0), passed=passed.get(week, 0))
        for week in weeks
    ]


def _dropoff_counts(counts: dict[str, int]) -> DropoffCounts:
    return DropoffCounts(**{reason: counts.get(reason, 0) for reason in DROP_REASONS})


# -- Pipeline dashboard -------------------------------------------------------------------------
async def pipeline_dashboard(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> PipelineDashboard:
    """The Dashboard tab of one pipeline (FR-PIPE-11); 404 outside the caller's departments."""
    now = _now(now)
    departments = None if ctx.sees_all_departments else ctx.department_ids
    pipeline = await PipelineRepository(session, ctx.workspace_id, department_ids=departments).get(
        pipeline_id
    )
    timezone = await _zone(session, ctx.workspace_id)
    zone = ZoneInfo(timezone)
    repo = _repo(session, ctx)

    counts: StageCounts = await repo.stage_counts(pipeline_id=pipeline.id)
    today = now.astimezone(zone).date()
    days = [today - timedelta(days=n) for n in range(DAYS - 1, -1, -1)]
    per_day = await repo.applied_per_period(
        "day", _local_midnight(days[0], zone), timezone, pipeline_id=pipeline.id
    )
    histogram = await repo.score_histogram(pipeline.id)
    drops = await repo.dropoffs(pipeline_id=pipeline.id)
    days_remaining = None
    if pipeline.status in OPEN_STATUSES and pipeline.closes_at is not None:
        days_remaining = max(0, math.ceil((pipeline.closes_at - now).total_seconds() / 86400))

    return PipelineDashboard(
        pipeline_id=pipeline.id,
        timezone=timezone,
        kpis=PipelineKpis(
            candidates=counts.applied,
            new_this_week=await repo.applicants_of(pipeline.id, since=now - timedelta(days=7)),
            ready_for_review=counts.ready_for_review,
            median_days_to_assessment=_days(
                await repo.median_seconds("assessment", Window(), pipeline_id=pipeline.id)
            ),
            credits_used=pipeline.credits_used,
            credits_reserved=pipeline.credits_reserved,
            days_remaining=days_remaining,
            closes_at=pipeline.closes_at,
        ),
        funnel=PipelineFunnel(
            applied=counts.applied,
            invited=counts.invited,
            interviewed=counts.interviewed,
            ready_for_review=counts.ready_for_review,
            flagged=counts.flagged,
        ),
        daily=[DayPoint(day=day, applicants=per_day.get(day, 0)) for day in days],
        scores=[
            ScoreBin(start=start, count=histogram.get(start, 0)) for start in range(0, 100, 10)
        ],
        pass_mark=pipeline.pass_mark,
        interviewed=counts.interviewed,
        passed=counts.passed,
        sources=[
            PipelineSourceRow(
                source=row.source,
                applicants=row.applicants,
                resume_pass_rate=_pct(row.resume_passed, row.screened),
            )
            for row in await repo.sources(pipeline_id=pipeline.id)
        ],
        dropoffs=PipelineDropoffs(
            **_dropoff_counts(drops).model_dump(),
            invited=counts.invited,
            reinvitable=await repo.reinvitable(pipeline.id),
        ),
    )


# -- Candidate pool -----------------------------------------------------------------------------
async def candidates_dashboard(
    session: AsyncSession, ctx: RequestContext, *, now: datetime | None = None
) -> CandidatesDashboard:
    """The candidate pool's Dashboard tab (FR-CAND-03); the skills chart comes with CAND-002."""
    now = _now(now)
    timezone = await _zone(session, ctx.workspace_id)
    zone = ZoneInfo(timezone)
    repo = _repo(session, ctx, shortlist_action=Action.VIEW_CANDIDATE_POOL)

    this_month = now.astimezone(zone).date().replace(day=1)
    months = [_months_back(this_month, n) for n in range(MONTHS - 1, -1, -1)]
    people = await repo.candidate_counts(_local_midnight(this_month, zone))
    per_month = await repo.first_applied_per_month(_local_midnight(months[0], zone), timezone)
    repeats = await repo.applications_per_person()
    returning = people["returning"]
    first_timers = people["people"] - returning
    stages = await repo.stages()
    sources = [
        PeopleSource(source=source, people=count, pass_rate=_pct(passed, count))
        for source, count, passed in await repo.people_by_source()
    ]
    sources.sort(key=lambda s: (-(s.pass_rate or 0), -s.people, s.source))

    return CandidatesDashboard(
        timezone=timezone,
        shortlist_only=repo.shortlist,
        kpis=CandidateKpis(
            candidates=people["people"],
            new_this_month=people["new"],
            applied_more_than_once=returning,
            interviewed=people["interviewed"],
            interviewed_pipelines=await repo.interviewed_pipelines(),
            passed_interview=people["passed"],
            median_days_to_assessment=_days(await repo.median_seconds("assessment", Window())),
        ),
        new_per_month=[MonthPoint(month=m, candidates=per_month.get(m, 0)) for m in months],
        repeats=Repeats(
            once=repeats.get(1, 0),
            twice=repeats.get(2, 0),
            three_times=repeats.get(3, 0),
            four_or_more=repeats.get(4, 0),
            returning_pass_rate=_pct(people["returning_passed"], returning),
            first_time_pass_rate=_pct(people["first_time_passed"], first_timers),
        ),
        stages={stage: stages.get(stage, 0) for stage in STAGES},
        sources=sources,
    )
