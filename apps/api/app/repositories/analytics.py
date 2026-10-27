"""Dashboard numbers (DASH-003) from the analytics views (DATABASE.md §4).

An `AnalyticsRepository` is built for one workspace and the caller's reach: `department_ids`
(None for Admins, who also see "No department") and `shortlist` (Hiring managers on the Overview
and the candidate pool, who only see shortlisted applications: ready for review, advanced, or
flagged after the interview, SECURITY.md §2). Every query here applies both, so a number never
counts what the caller couldn't open.
"""

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean as BooleanType
from sqlalchemy import (
    ColumnElement,
    Date,
    DateTime,
    Integer,
    Select,
    String,
    Uuid,
    and_,
    case,
    column,
    func,
    literal,
    or_,
    select,
    table,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, Candidate, CreditBatch, Invite, Pipeline

funnel = table(
    "v_pipeline_funnel",
    column("workspace_id", Uuid),
    column("pipeline_id", Uuid),
    column("department_id", Uuid),
    column("application_id", Uuid),
    column("candidate_id", Uuid),
    column("source", String),
    column("applied_at", DateTime(timezone=True)),
    column("stage", String),
    column("stage_changed_at", DateTime(timezone=True)),
    column("has_open_flags", BooleanType),
    column("resume_passed", BooleanType),
    column("invited", BooleanType),
    column("interview_completed_at", DateTime(timezone=True)),
    column("interview_score", Integer),
    column("interview_passed", BooleanType),
    column("assessed_at", DateTime(timezone=True)),
)
source_stats = table(
    "v_source_stats",
    column("workspace_id", Uuid),
    column("pipeline_id", Uuid),
    column("department_id", Uuid),
    column("source", String),
    column("applicants", Integer),
    column("screened", Integer),
    column("resume_passed", Integer),
    column("interviewed", Integer),
    column("interview_passed", Integer),
)
time_to_screen = table(
    "v_time_to_screen",
    column("workspace_id", Uuid),
    column("pipeline_id", Uuid),
    column("department_id", Uuid),
    column("application_id", Uuid),
    column("interview_completed_at", DateTime(timezone=True)),
    column("assessed_at", DateTime(timezone=True)),
    column("seconds_to_interview", Integer),
    column("seconds_to_assessment", Integer),
)
dropoffs = table(
    "v_dropoff_reasons",
    column("workspace_id", Uuid),
    column("pipeline_id", Uuid),
    column("department_id", Uuid),
    column("application_id", Uuid),
    column("drop_reason", String),
    column("dropped_at", DateTime(timezone=True)),
)

OPEN_STATUSES = ("live", "paused", "paused_no_credits")
# Where a re-invite is allowed (INTV-007): the candidate hasn't finished an interview yet.
REINVITABLE_STAGES = ("invited", "interview_in_progress")
# Flags overlay these two stages until a person resolves them (WORKFLOW.md §3).
FLAGGABLE_STAGES = ("ready_for_review", "did_not_pass")


@dataclass(frozen=True)
class Window:
    """[start, end) on the server clock; None means unbounded."""

    start: datetime | None = None
    end: datetime | None = None


@dataclass(frozen=True)
class StageCounts:
    """Where a set of applications has got to (see `stage_counts`)."""

    applied: int
    processing: int
    not_a_match: int
    invited: int
    not_started: int
    in_progress: int
    interviewed: int
    scoring: int
    ready_for_review: int
    flagged: int
    did_not_pass: int
    passed: int
    advanced: int
    rejected: int


@dataclass(frozen=True)
class SourceRow:
    source: str
    applicants: int
    screened: int
    resume_passed: int
    interviewed: int
    interview_passed: int


@dataclass(frozen=True)
class WaitingCandidate:
    application_id: uuid.UUID
    candidate_name: str
    pipeline_id: uuid.UUID
    pipeline_title: str | None
    score: int
    fit: str | None
    waiting_since: datetime


@dataclass(frozen=True)
class OpenPipelineRow:
    id: uuid.UUID
    title: str | None
    status: str
    department_id: uuid.UUID | None
    closes_at: datetime | None
    credits_reserved: int
    credits_used: int
    applicants: int
    to_review: int
    recent_applicants: int


class AnalyticsRepository:
    def __init__(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        *,
        department_ids: Collection[uuid.UUID] | None,
        shortlist: bool = False,
    ) -> None:
        if not isinstance(workspace_id, uuid.UUID):
            raise TypeError("an analytics repository needs a workspace_id")
        self.session = session
        self.workspace_id = workspace_id
        self.department_ids = None if department_ids is None else list(department_ids)
        self.shortlist = shortlist

    # -- Scope -----------------------------------------------------------------------------------
    def _scope(self, view: Any) -> list[ColumnElement[bool]]:
        """The workspace and the caller's departments, for any view with those columns."""
        clauses: list[ColumnElement[bool]] = [view.c.workspace_id == self.workspace_id]
        if self.department_ids is not None:
            clauses.append(view.c.department_id.in_(self.department_ids))
        return clauses

    def _funnel_scope(self) -> list[ColumnElement[bool]]:
        clauses = self._scope(funnel)
        if self.shortlist:
            clauses.append(
                or_(
                    funnel.c.stage.in_(("ready_for_review", "advanced")),
                    and_(funnel.c.has_open_flags, funnel.c.stage.in_(FLAGGABLE_STAGES)),
                )
            )
        return clauses

    def _pipeline_scope(self) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = [Pipeline.workspace_id == self.workspace_id]
        if self.department_ids is not None:
            clauses.append(Pipeline.department_id.in_(self.department_ids))
        return clauses

    def _open_pipelines(self) -> Select[Any]:
        return select(Pipeline.id).where(
            *self._pipeline_scope(), Pipeline.status.in_(OPEN_STATUSES)
        )

    # -- Funnel ----------------------------------------------------------------------------------
    async def stage_counts(
        self,
        applied: Window | None = None,
        *,
        pipeline_id: uuid.UUID | None = None,
        open_pipelines_only: bool = False,
    ) -> StageCounts:
        """Applications that applied in `applied` and where they are now. Flagged candidates
        are counted as flagged, not as ready for review or didn't pass, until a person resolves
        their flags; `passed` counts every passed interview whatever happened next."""
        f = funnel.c
        flagged = and_(f.has_open_flags, f.stage.in_(FLAGGABLE_STAGES))
        statement = select(
            func.count(),
            func.count().filter(f.stage == "processing_resume"),
            func.count().filter(f.resume_passed.is_(False), f.invited.is_(False)),
            func.count().filter(f.invited),
            func.count().filter(f.stage == "invited"),
            func.count().filter(f.stage == "interview_in_progress"),
            func.count().filter(f.interview_completed_at.is_not(None)),
            func.count().filter(f.stage == "scoring"),
            func.count().filter(f.stage == "ready_for_review", ~flagged),
            func.count().filter(flagged),
            func.count().filter(f.stage == "did_not_pass", ~flagged),
            func.count().filter(f.interview_passed),
            func.count().filter(f.stage == "advanced"),
            func.count().filter(f.stage == "rejected"),
        ).where(*self._funnel_scope(), *_within(f.applied_at, applied or Window()))
        if pipeline_id is not None:
            statement = statement.where(f.pipeline_id == pipeline_id)
        if open_pipelines_only:
            statement = statement.where(f.pipeline_id.in_(self._open_pipelines()))
        row = (await self.session.execute(statement)).one()
        return StageCounts(*(int(value) for value in row))

    async def applied_per_period(
        self,
        unit: str,
        since: datetime,
        timezone: str,
        *,
        pipeline_id: uuid.UUID | None = None,
    ) -> dict[Any, int]:
        """Applications per local day, week (from Monday) or month since `since`, keyed by the
        local date the period starts on."""
        bucket = _local_bucket(unit, funnel.c.applied_at, timezone)
        statement = (
            select(bucket, func.count())
            .where(*self._funnel_scope(), funnel.c.applied_at >= since)
            .group_by(bucket)
        )
        if pipeline_id is not None:
            statement = statement.where(funnel.c.pipeline_id == pipeline_id)
        return {day: count for day, count in await self.session.execute(statement)}

    async def passed_per_period(self, unit: str, since: datetime, timezone: str) -> dict[Any, int]:
        """Interviews passed per local period, by when they were assessed."""
        bucket = _local_bucket(unit, funnel.c.assessed_at, timezone)
        statement = (
            select(bucket, func.count())
            .where(
                *self._funnel_scope(),
                funnel.c.interview_passed.is_(True),
                funnel.c.assessed_at >= since,
            )
            .group_by(bucket)
        )
        return {day: count for day, count in await self.session.execute(statement)}

    async def score_histogram(self, pipeline_id: uuid.UUID) -> dict[int, int]:
        """Interview scores of a pipeline in tens (0, 10, … 90; 100 counts with the 90s)."""
        bucket = func.least(funnel.c.interview_score // 10 * 10, 90)
        rows = await self.session.execute(
            select(bucket, func.count())
            .where(
                *self._funnel_scope(),
                funnel.c.pipeline_id == pipeline_id,
                funnel.c.interview_score.is_not(None),
            )
            .group_by(bucket)
        )
        return {int(start): count for start, count in rows}

    # -- Time to screen --------------------------------------------------------------------------
    async def median_seconds(
        self,
        measure: str,
        window: Window,
        *,
        pipeline_id: uuid.UUID | None = None,
        open_pipelines_only: bool = False,
    ) -> float | None:
        """Median of `seconds_to_interview` (applications whose interview finished in the
        window) or `seconds_to_assessment` (assessed in the window)."""
        t = time_to_screen.c
        value = t.seconds_to_interview if measure == "interview" else t.seconds_to_assessment
        moment = t.interview_completed_at if measure == "interview" else t.assessed_at
        statement = select(func.percentile_cont(0.5).within_group(value)).where(
            *self._scope(time_to_screen), *_within(moment, window)
        )
        if self.shortlist:
            statement = statement.where(
                t.application_id.in_(select(funnel.c.application_id).where(*self._funnel_scope()))
            )
        if pipeline_id is not None:
            statement = statement.where(t.pipeline_id == pipeline_id)
        if open_pipelines_only:
            statement = statement.where(t.pipeline_id.in_(self._open_pipelines()))
        median = await self.session.scalar(statement)
        return None if median is None else float(median)

    # -- Sources ---------------------------------------------------------------------------------
    async def sources(self, *, pipeline_id: uuid.UUID | None = None) -> list[SourceRow]:
        """Applications per apply-link source, all time, most applicants first."""
        s = source_stats.c
        statement = (
            select(
                s.source,
                func.sum(s.applicants),
                func.sum(s.screened),
                func.sum(s.resume_passed),
                func.sum(s.interviewed),
                func.sum(s.interview_passed),
            )
            .where(*self._scope(source_stats))
            .group_by(s.source)
            .order_by(func.sum(s.applicants).desc(), s.source)
        )
        if pipeline_id is not None:
            statement = statement.where(s.pipeline_id == pipeline_id)
        rows = await self.session.execute(statement)
        return [SourceRow(row[0], *(int(v) for v in row[1:])) for row in rows]

    async def people_by_source(self) -> list[tuple[str, int, int]]:
        """(source, people, people who passed an interview) for the candidate pool: a person
        counts once per source they applied through."""
        f = funnel.c
        rows = await self.session.execute(
            select(
                f.source,
                func.count(f.candidate_id.distinct()),
                func.count(f.candidate_id.distinct()).filter(f.interview_passed),
            )
            .where(*self._funnel_scope())
            .group_by(f.source)
        )
        return [(source, int(people), int(passed)) for source, people, passed in rows]

    # -- Drop-offs -------------------------------------------------------------------------------
    async def dropoffs(
        self, *, since: datetime | None = None, pipeline_id: uuid.UUID | None = None
    ) -> dict[str, int]:
        """Unfinished interviews per drop-off reason (INTV-007)."""
        d = dropoffs.c
        statement = (
            select(d.drop_reason, func.count())
            .where(*self._scope(dropoffs))
            .group_by(d.drop_reason)
        )
        if since is not None:
            statement = statement.where(d.dropped_at >= since)
        if pipeline_id is not None:
            statement = statement.where(d.pipeline_id == pipeline_id)
        return {reason: count for reason, count in await self.session.execute(statement)}

    async def reinvitable(self, pipeline_id: uuid.UUID) -> int:
        """Candidates "Re-invite all" would send a new link to: an unfinished interview with a
        drop-off reason, still in a stage a re-invite allows."""
        d = dropoffs.c
        count = await self.session.scalar(
            select(func.count())
            .select_from(dropoffs)
            .join(
                Application,
                and_(
                    Application.workspace_id == d.workspace_id,
                    Application.id == d.application_id,
                ),
            )
            .where(
                *self._scope(dropoffs),
                d.pipeline_id == pipeline_id,
                Application.stage.in_(REINVITABLE_STAGES),
            )
        )
        return int(count or 0)

    # -- Candidates ------------------------------------------------------------------------------
    async def waiting_on_review(self, limit: int) -> list[WaitingCandidate]:
        """The strongest candidates ready for review (not flagged), best score first."""
        f = funnel.c
        rows = await self.session.execute(
            select(
                f.application_id,
                Candidate.full_name,
                f.pipeline_id,
                Pipeline.title,
                f.interview_score,
                Application.fit,
                f.stage_changed_at,
            )
            .select_from(funnel)
            .join(
                Candidate,
                and_(Candidate.workspace_id == f.workspace_id, Candidate.id == f.candidate_id),
            )
            .join(
                Application,
                and_(
                    Application.workspace_id == f.workspace_id, Application.id == f.application_id
                ),
            )
            .join(
                Pipeline,
                and_(Pipeline.workspace_id == f.workspace_id, Pipeline.id == f.pipeline_id),
            )
            .where(
                *self._funnel_scope(),
                f.stage == "ready_for_review",
                f.has_open_flags.is_(False),
                f.interview_score.is_not(None),
                Candidate.deleted_at.is_(None),
            )
            .order_by(f.interview_score.desc(), f.stage_changed_at, f.application_id)
            .limit(limit)
        )
        return [WaitingCandidate(*row) for row in rows]

    async def review_queue(self) -> tuple[int, int, datetime | None]:
        """(candidates ready for review, pipelines they are in, when the longest-waiting one
        became ready)."""
        f = funnel.c
        row = (
            await self.session.execute(
                select(
                    func.count(), func.count(f.pipeline_id.distinct()), func.min(f.stage_changed_at)
                ).where(
                    *self._funnel_scope(),
                    f.stage == "ready_for_review",
                    f.has_open_flags.is_(False),
                )
            )
        ).one()
        return int(row[0]), int(row[1]), row[2]

    async def flagged(self, limit: int) -> tuple[int, list[tuple[str, str | None]]]:
        """Flagged interviews waiting on a person: how many, and the first few as
        (candidate name, pipeline title), oldest first."""
        f = funnel.c
        where = (*self._funnel_scope(), f.has_open_flags, f.stage.in_(FLAGGABLE_STAGES))
        total = await self.session.scalar(select(func.count()).select_from(funnel).where(*where))
        rows = await self.session.execute(
            select(Candidate.full_name, Pipeline.title)
            .select_from(funnel)
            .join(
                Candidate,
                and_(Candidate.workspace_id == f.workspace_id, Candidate.id == f.candidate_id),
            )
            .join(
                Pipeline,
                and_(Pipeline.workspace_id == f.workspace_id, Pipeline.id == f.pipeline_id),
            )
            .where(*where)
            .order_by(f.stage_changed_at, f.application_id)
            .limit(limit)
        )
        return int(total or 0), [(name, title) for name, title in rows]

    async def review_requests(self) -> int:
        """Open human review requests (ASMT-008): applications marked Review requested in the
        caller's pipelines whose candidate wasn't deleted."""
        total = await self.session.scalar(
            select(func.count())
            .select_from(Application)
            .join(
                Pipeline,
                and_(
                    Pipeline.workspace_id == Application.workspace_id,
                    Pipeline.id == Application.pipeline_id,
                ),
            )
            .join(
                Candidate,
                and_(
                    Candidate.workspace_id == Application.workspace_id,
                    Candidate.id == Application.candidate_id,
                ),
            )
            .where(
                *self._pipeline_scope(),
                Application.review_requested,
                Candidate.deleted_at.is_(None),
            )
        )
        return int(total or 0)

    async def candidate_counts(self, since_month: datetime) -> dict[str, int]:
        """The candidate pool's headline numbers: people, people who first applied (within the
        caller's reach) on or after `since_month`, people with more than one application,
        people interviewed and people who passed an interview."""
        f = funnel.c
        per_person = (
            select(
                f.candidate_id,
                func.count().label("applications"),
                func.min(f.applied_at).label("first_applied"),
                func.bool_or(f.interview_completed_at.is_not(None)).label("interviewed"),
                func.coalesce(func.bool_or(f.interview_passed), False).label("passed"),
            )
            .where(*self._funnel_scope())
            .group_by(f.candidate_id)
            .subquery()
        )
        p = per_person.c
        row = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(p.first_applied >= since_month),
                    func.count().filter(p.applications > 1),
                    func.count().filter(p.interviewed),
                    func.count().filter(p.passed),
                    func.count().filter(p.applications > 1, p.passed),
                    func.count().filter(p.applications == 1, p.passed),
                )
            )
        ).one()
        keys = ("people", "new", "returning", "interviewed", "passed", "returning_passed")
        counts = dict(zip(keys, (int(v) for v in row[:6]), strict=True))
        counts["first_time_passed"] = int(row[6])
        return counts

    async def interviewed_pipelines(self) -> int:
        f = funnel.c
        count = await self.session.scalar(
            select(func.count(f.pipeline_id.distinct())).where(
                *self._funnel_scope(), f.interview_completed_at.is_not(None)
            )
        )
        return int(count or 0)

    async def applications_per_person(self) -> dict[int, int]:
        """How many people applied once, twice, three times and four or more (key 4)."""
        f = funnel.c
        per_person = (
            select(func.least(func.count(), 4).label("n"))
            .where(*self._funnel_scope())
            .group_by(f.candidate_id)
            .subquery()
        )
        rows = await self.session.execute(
            select(per_person.c.n, func.count()).group_by(per_person.c.n)
        )
        return {int(n): count for n, count in rows}

    async def first_applied_per_month(self, since: datetime, timezone: str) -> dict[Any, int]:
        """People per local month of their first application within the caller's reach."""
        f = funnel.c
        first = (
            select(func.min(f.applied_at).label("first_applied"))
            .where(*self._funnel_scope())
            .group_by(f.candidate_id)
            .subquery()
        )
        bucket = _local_bucket("month", first.c.first_applied, timezone)
        rows = await self.session.execute(
            select(bucket, func.count()).where(first.c.first_applied >= since).group_by(bucket)
        )
        return {month: count for month, count in rows}

    async def stages(self) -> dict[str, int]:
        """Applications per stage (the candidate pool's "Where applications ended up")."""
        f = funnel.c
        rows = await self.session.execute(
            select(f.stage, func.count()).where(*self._funnel_scope()).group_by(f.stage)
        )
        return {stage: count for stage, count in rows}

    # -- Pipelines -------------------------------------------------------------------------------
    async def pipeline_statuses(self) -> dict[str, int]:
        rows = await self.session.execute(
            select(Pipeline.status, func.count())
            .where(*self._pipeline_scope(), Pipeline.archived_at.is_(None))
            .group_by(Pipeline.status)
        )
        return {status: count for status, count in rows}

    async def open_pipelines(self, recent_since: datetime) -> list[OpenPipelineRow]:
        """Open pipelines (live or paused), closing soonest first, with their applicants, how
        many wait on a review and how many applied since `recent_since` (their pace)."""
        f = funnel.c
        counts = (
            select(
                f.pipeline_id,
                func.count().label("applicants"),
                func.count()
                .filter(f.stage == "ready_for_review", f.has_open_flags.is_(False))
                .label("to_review"),
                func.count().filter(f.applied_at >= recent_since).label("recent"),
            )
            .where(*self._funnel_scope())
            .group_by(f.pipeline_id)
            .subquery()
        )
        rows = await self.session.execute(
            select(
                Pipeline.id,
                Pipeline.title,
                Pipeline.status,
                Pipeline.department_id,
                Pipeline.closes_at,
                Pipeline.credits_reserved,
                Pipeline.credits_used,
                func.coalesce(counts.c.applicants, 0),
                func.coalesce(counts.c.to_review, 0),
                func.coalesce(counts.c.recent, 0),
            )
            .outerjoin(counts, counts.c.pipeline_id == Pipeline.id)
            .where(
                *self._pipeline_scope(),
                Pipeline.status.in_(OPEN_STATUSES),
                Pipeline.archived_at.is_(None),
            )
            .order_by(Pipeline.closes_at.asc().nulls_last(), Pipeline.created_at, Pipeline.id)
        )
        return [OpenPipelineRow(*row) for row in rows]

    async def applicants_of(self, pipeline_id: uuid.UUID, since: datetime | None = None) -> int:
        f = funnel.c
        statement = select(func.count()).where(*self._funnel_scope(), f.pipeline_id == pipeline_id)
        if since is not None:
            statement = statement.where(f.applied_at >= since)
        return int(await self.session.scalar(statement) or 0)

    # -- Workspace-wide (no department scope: callers check the role) -----------------------------
    async def plan_credits_expiring(
        self, now: datetime, before: datetime
    ) -> tuple[int, datetime | None]:
        """Unused plan credits that expire between now and `before`, and the first expiry."""
        row = (
            await self.session.execute(
                select(
                    func.coalesce(func.sum(CreditBatch.remaining), 0),
                    func.min(CreditBatch.expires_at),
                ).where(
                    CreditBatch.workspace_id == self.workspace_id,
                    CreditBatch.kind == "plan",
                    CreditBatch.remaining > 0,
                    CreditBatch.expires_at > now,
                    CreditBatch.expires_at <= before,
                )
            )
        ).one()
        return int(row[0]), row[1]

    async def current_plan_batch(self, now: datetime) -> tuple[int, int] | None:
        """(credits granted, credits left) of the plan batch in use now, if any."""
        row = (
            await self.session.execute(
                select(CreditBatch.amount, CreditBatch.remaining)
                .where(
                    CreditBatch.workspace_id == self.workspace_id,
                    CreditBatch.kind == "plan",
                    CreditBatch.added_at <= now,
                    or_(CreditBatch.expires_at.is_(None), CreditBatch.expires_at > now),
                )
                .order_by(CreditBatch.added_at.desc())
                .limit(1)
            )
        ).one_or_none()
        return None if row is None else (int(row[0]), int(row[1]))

    async def invites_expiring(
        self, now: datetime, before: datetime
    ) -> tuple[int, int, datetime | None]:
        """(pending invites, those expiring before `before`, the first expiry among them)."""
        row = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count().filter(Invite.expires_at <= before),
                    func.min(case((Invite.expires_at <= before, Invite.expires_at))),
                ).where(
                    Invite.workspace_id == self.workspace_id,
                    Invite.status == "pending",
                    Invite.expires_at > now,
                )
            )
        ).one()
        return int(row[0]), int(row[1]), row[2]


def _within(moment: ColumnElement[Any], window: Window) -> list[ColumnElement[bool]]:
    clauses: list[ColumnElement[bool]] = []
    if window.start is not None:
        clauses.append(moment >= window.start)
    if window.end is not None:
        clauses.append(moment < window.end)
    return clauses


def _local_bucket(unit: str, moment: ColumnElement[Any], timezone: str) -> ColumnElement[Any]:
    """The local date a day, week (Monday) or month starts on, in `timezone`."""
    return func.date_trunc(unit, func.timezone(literal(timezone), moment)).cast(Date)
