"""Pipelines: setup, the state machine and scheduled open/close (FR-PIPE-07, WORKFLOW.md §2).

States and the actions that move between them:

    draft ──publish──▶ scheduled ──start now / opens_at──▶ live ◀──resume── paused
      │                    │                                 │ ──pause──────▶
      └──publish now───────┼────────────────────────────────▶│ ◀──credits added── paused_no_credits
                           └──cancel──▶ cancelled            └──close / closes_at──▶ closed

`TRANSITIONS` is the whole table; any other action raises `invalid_transition`. A pipeline is
locked from the moment it is live: its setup can't change (here and in the database trigger),
only its status and credits. Closing or cancelling returns the unused reserve to the free credits.
Credits move only through services/credits.py, in the same transaction.

Every action locks the workspace row, then the pipeline row, so it can't race an applicant
using a credit or another action on the same pipeline.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import (
    InvalidTransitionError,
    PipelineIncompleteError,
    PipelineLockedError,
    UnknownDepartmentError,
)
from app.core.slugs import slugify, unique_slug
from app.models import Pipeline as PipelineRow
from app.repositories.audit import AuditRepository
from app.repositories.pipelines import (
    PipelineRepository,
    due_to_close,
    due_to_open,
    out_of_credit_pipeline_ids,
)
from app.schemas.pipelines import Pipeline, PipelineSetup
from app.services import credits

# Action → the statuses it can start from (WORKFLOW.md §2). `open` is the cron at `opens_at`.
TRANSITIONS: dict[str, frozenset[str]] = {
    "publish": frozenset({"draft"}),
    "start_now": frozenset({"scheduled"}),
    "open": frozenset({"scheduled"}),
    "pause": frozenset({"live"}),
    "resume": frozenset({"paused"}),
    "credits_added": frozenset({"paused_no_credits"}),
    "close": frozenset({"live", "paused", "paused_no_credits"}),
    "cancel": frozenset({"scheduled"}),
    "archive": frozenset({"closed", "cancelled"}),
    "top_up": frozenset({"scheduled", "live", "paused", "paused_no_credits"}),
}

# Setup can be edited while these hold; scheduled only until it opens.
EDITABLE_STATUSES = frozenset({"draft", "scheduled"})

# The setup a duplicate copies (FR-PIPE-07: "Duplicate as new pipeline").
SETUP_COLUMNS = (
    "department_id",
    "title",
    "employment_type",
    "work_setup",
    "location",
    "jd_text",
    "must_haves",
    "nice_to_haves",
    "open_to",
    "resume_pass_bar",
    "interview_format",
    "tone",
    "seniority",
    "skills_to_probe",
    "link_expiry_days",
    "reminder_enabled",
    "integrity_enabled",
    "weight_technical",
    "weight_communication",
    "weight_culture",
    "pass_mark",
    "email_resume_reject",
    "email_post_interview",
    "open_mode",
    "duration_days",
    "credits_to_reserve",
)

MIN_MUST_HAVES = 3
MIN_SKILLS_TO_PROBE = 3
WEIGHTS = ("weight_technical", "weight_communication", "weight_culture")


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)


def _repo(session: AsyncSession, ctx: RequestContext) -> PipelineRepository:
    departments = None if ctx.sees_all_departments else ctx.department_ids
    return PipelineRepository(session, ctx.workspace_id, department_ids=departments)


def _check_transition(pipeline: PipelineRow, action: str) -> None:
    if pipeline.status not in TRANSITIONS[action]:
        raise InvalidTransitionError()


def _audit(
    session: AsyncSession,
    pipeline: PipelineRow,
    action: str,
    actor_id: uuid.UUID | None,
    **data: Any,
) -> None:
    AuditRepository(session, pipeline.workspace_id).record(
        actor_id=actor_id,
        action=f"pipeline.{action}",
        entity_type="pipeline",
        entity_id=pipeline.id,
        data=data,
    )


async def _done(session: AsyncSession, pipeline: PipelineRow) -> Pipeline:
    await session.commit()
    await session.refresh(pipeline)  # updated_at comes from the database trigger
    return Pipeline.model_validate(pipeline)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
async def get_pipeline(
    session: AsyncSession, ctx: RequestContext, pipeline_id: uuid.UUID
) -> Pipeline:
    return Pipeline.model_validate(await _repo(session, ctx).get(pipeline_id))


async def create_draft(session: AsyncSession, ctx: RequestContext, body: PipelineSetup) -> Pipeline:
    """A new draft owned by the caller, with whatever setup the wizard has so far."""
    repo = _repo(session, ctx)
    changes = body.changes()
    await _check_department(repo, ctx, changes.get("department_id"))
    pipeline = PipelineRow(workspace_id=ctx.workspace_id, owner_id=ctx.member_id)
    _apply(pipeline, changes)
    _check_weights(pipeline)
    pipeline = await repo.add(pipeline)
    _audit(session, pipeline, "created", ctx.user_id)
    return await _done(session, pipeline)


async def update_pipeline(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    body: PipelineSetup,
    *,
    now: datetime | None = None,
) -> Pipeline:
    """Edits a draft, or a scheduled pipeline until it opens (PIPE-003). A pipeline that has
    opened is locked: `pipeline_locked`."""
    now = _now(now)
    repo = _repo(session, ctx)
    pipeline = await repo.lock(pipeline_id)
    if pipeline.status not in EDITABLE_STATUSES:
        raise PipelineLockedError() if pipeline.locked_at else InvalidTransitionError()
    changes = body.changes()
    if "department_id" in changes and changes["department_id"] != pipeline.department_id:
        await _check_department(repo, ctx, changes["department_id"])
    if pipeline.status == "scheduled":
        _check_scheduled_changes(pipeline, changes, now)
    _apply(pipeline, changes)
    if pipeline.status == "scheduled":
        pipeline.closes_at = _closes_at(pipeline)
    _check_weights(pipeline)
    await session.flush()
    return await _done(session, pipeline)


def _apply(pipeline: PipelineRow, changes: dict[str, Any]) -> None:
    for name, value in changes.items():
        setattr(pipeline, name, value)


async def _check_department(
    repo: PipelineRepository, ctx: RequestContext, department_id: uuid.UUID | None
) -> None:
    """Admins file pipelines under any department or No department; Recruiters only under one
    of their own departments (SECURITY.md §2)."""
    if ctx.sees_all_departments:
        if department_id is not None and not await repo.department_exists(department_id):
            raise UnknownDepartmentError()
        return
    if department_id is None or department_id not in ctx.department_ids:
        raise UnknownDepartmentError()


def _check_scheduled_changes(pipeline: PipelineRow, changes: dict[str, Any], now: datetime) -> None:
    """A scheduled pipeline keeps its schedule mode and reserve: "Start now" opens it, and a
    top-up adds credits. A new opening date must still be in the future."""
    if changes.get("open_mode", "scheduled") != "scheduled":
        raise PipelineLockedError("Use Start now to open a scheduled pipeline")
    if "credits_to_reserve" in changes:
        raise PipelineLockedError("Top up the pipeline to reserve more credits")
    if "opens_at" in changes and (changes["opens_at"] is None or changes["opens_at"] <= now):
        raise PipelineIncompleteError(errors=[_error("opens_at", "in_past", "Pick a future date")])
    if "duration_days" in changes and changes["duration_days"] is None:
        raise PipelineIncompleteError(
            errors=[_error("duration_days", "missing", "Pick a duration")]
        )


def _check_weights(pipeline: PipelineRow) -> None:
    weights = [getattr(pipeline, name) for name in WEIGHTS]
    if None not in weights and sum(weights) != 100:
        raise PipelineIncompleteError(
            errors=[_error(name, "weights_total", "Weights must add up to 100") for name in WEIGHTS]
        )


def _error(field: str, kind: str, message: str) -> dict[str, Any]:
    return {"loc": [field], "type": kind, "msg": message}


def _missing_setup(pipeline: PipelineRow, now: datetime) -> list[dict[str, Any]]:
    """What a draft still needs before it can be published (FR-PIPE-01..04)."""
    errors = [
        _error(name, "missing", "Required")
        for name in (
            "title",
            "employment_type",
            "work_setup",
            "jd_text",
            "interview_format",
            "tone",
            "seniority",
            *WEIGHTS,
            "open_mode",
            "duration_days",
            "credits_to_reserve",
        )
        if getattr(pipeline, name) is None
    ]
    if pipeline.work_setup != "remote" and not pipeline.location:
        errors.append(_error("location", "missing", "Required unless the role is remote"))
    if len(pipeline.must_haves) < MIN_MUST_HAVES:
        errors.append(_error("must_haves", "too_short", "Add at least 3 must-haves"))
    if len(pipeline.skills_to_probe) < MIN_SKILLS_TO_PROBE:
        errors.append(_error("skills_to_probe", "too_short", "Add at least 3 skills to probe"))
    if pipeline.open_mode == "scheduled":
        if pipeline.opens_at is None:
            errors.append(_error("opens_at", "missing", "Pick the opening date"))
        elif pipeline.opens_at <= now:
            errors.append(_error("opens_at", "in_past", "Pick a future date"))
    return errors


def _closes_at(pipeline: PipelineRow) -> datetime | None:
    if pipeline.opens_at is None or pipeline.duration_days is None:
        return None
    return pipeline.opens_at + timedelta(days=pipeline.duration_days)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
async def publish(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Pipeline:
    """Draft → live (open now) or scheduled (FR-PIPE-05). Reserves `credits_to_reserve` from
    the free credits (`insufficient_free_credits` when there aren't enough) and fixes the slug."""
    now = _now(now)
    repo = _repo(session, ctx)
    pipeline = await repo.lock(pipeline_id)
    _check_transition(pipeline, "publish")
    _check_weights(pipeline)
    missing = _missing_setup(pipeline, now)
    if missing:
        raise PipelineIncompleteError(errors=missing)
    assert pipeline.credits_to_reserve is not None and pipeline.title is not None

    await credits.reserve(
        session,
        ctx.workspace_id,
        pipeline.id,
        credits=pipeline.credits_to_reserve,
        now=now,
        actor_id=ctx.user_id,
    )
    # The workspace row is locked, so no other publish in this workspace can take the slug.
    base = slugify(pipeline.title)
    slug = unique_slug(base, await repo.slugs_like(base))
    # Queries autoflush, so work out the new state first and set it in one go: the database
    # checks a published pipeline has its slug and is past draft in the same row update.
    opens_now = pipeline.open_mode == "now"
    status = await _live_status(session, pipeline, now) if opens_now else "scheduled"
    pipeline.slug = slug
    pipeline.published_at = now
    pipeline.published_by = ctx.member_id
    if opens_now:
        _open(pipeline, now, status=status, opens_at=now)
    else:
        pipeline.status = status
        pipeline.closes_at = _closes_at(pipeline)
    await session.flush()
    _audit(
        session,
        pipeline,
        "published",
        ctx.user_id,
        status=pipeline.status,
        credits_reserved=pipeline.credits_reserved,
    )
    return await _done(session, pipeline)


def _open(pipeline: PipelineRow, now: datetime, *, status: str, opens_at: datetime) -> None:
    """Goes live (`status` from `_live_status`, worked out before any change because the lock
    trigger refuses setup changes once `locked_at` is flushed) and locks the setup. `closes_at`
    counts from when it actually opens."""
    pipeline.opens_at = opens_at
    pipeline.closes_at = _closes_at(pipeline)
    pipeline.locked_at = now
    pipeline.status = status


async def _live_status(session: AsyncSession, pipeline: PipelineRow, now: datetime) -> str:
    """`live`, or `paused_no_credits` when its reserve is used up or the workspace has no
    credits left (BILLING.md §3)."""
    if pipeline.credits_used >= pipeline.credits_reserved:
        return "paused_no_credits"
    if (await credits.summary(session, pipeline.workspace_id, now=now)).balance <= 0:
        return "paused_no_credits"
    return "live"


async def start_now(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Pipeline:
    """Scheduled → live before its date; it runs its full duration from now."""
    now = _now(now)
    pipeline = await _repo(session, ctx).lock(pipeline_id)
    _check_transition(pipeline, "start_now")
    status = await _live_status(session, pipeline, now)
    pipeline.open_mode = "now"
    _open(pipeline, now, status=status, opens_at=now)
    _audit(session, pipeline, "started", ctx.user_id, status=pipeline.status)
    return await _done(session, pipeline)


async def pause(session: AsyncSession, ctx: RequestContext, pipeline_id: uuid.UUID) -> Pipeline:
    """Live → paused. `closes_at` stays where it was: pausing never extends a pipeline."""
    pipeline = await _repo(session, ctx).lock(pipeline_id)
    _check_transition(pipeline, "pause")
    pipeline.status = "paused"
    _audit(session, pipeline, "paused", ctx.user_id)
    return await _done(session, pipeline)


async def resume(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Pipeline:
    """Paused → live, or `paused_no_credits` if its credits ran out meanwhile."""
    now = _now(now)
    pipeline = await _repo(session, ctx).lock(pipeline_id)
    _check_transition(pipeline, "resume")
    pipeline.status = await _live_status(session, pipeline, now)
    _audit(session, pipeline, "resumed", ctx.user_id, status=pipeline.status)
    return await _done(session, pipeline)


async def close(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Pipeline:
    """Closed by hand; the unused reserve returns to the free credits. The optional "Role
    closed" email to candidates comes with PIPE-005 and MSG-003."""
    pipeline = await _repo(session, ctx).lock(pipeline_id)
    await _close(session, pipeline, "manual", _now(now), ctx.user_id)
    return await _done(session, pipeline)


async def _close(
    session: AsyncSession,
    pipeline: PipelineRow,
    reason: str,
    now: datetime,
    actor_id: uuid.UUID | None,
) -> None:
    _check_transition(pipeline, "close")
    released = await credits.release(
        session, pipeline.workspace_id, pipeline.id, now=now, actor_id=actor_id
    )
    pipeline.status = "closed"
    pipeline.closed_reason = reason
    _audit(session, pipeline, "closed", actor_id, reason=reason, credits_released=released)


async def cancel(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Pipeline:
    """Scheduled → cancelled; the whole reserve returns and the apply link stops working."""
    now = _now(now)
    pipeline = await _repo(session, ctx).lock(pipeline_id)
    _check_transition(pipeline, "cancel")
    released = await credits.release(
        session, ctx.workspace_id, pipeline.id, now=now, actor_id=ctx.user_id
    )
    pipeline.status = "cancelled"
    _audit(session, pipeline, "cancelled", ctx.user_id, credits_released=released)
    return await _done(session, pipeline)


async def archive(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> Pipeline:
    """Hides a closed or cancelled pipeline from the Pipelines list; its data stays."""
    pipeline = await _repo(session, ctx).lock(pipeline_id)
    _check_transition(pipeline, "archive")
    if pipeline.archived_at is not None:
        raise InvalidTransitionError()
    pipeline.archived_at = _now(now)
    _audit(session, pipeline, "archived", ctx.user_id)
    return await _done(session, pipeline)


async def duplicate(session: AsyncSession, ctx: RequestContext, pipeline_id: uuid.UUID) -> Pipeline:
    """A new draft with the same setup, owned by the caller. The schedule's date isn't copied:
    the old one has usually passed."""
    repo = _repo(session, ctx)
    source = await repo.get(pipeline_id)
    copy = PipelineRow(
        workspace_id=ctx.workspace_id,
        owner_id=ctx.member_id,
        duplicated_from_id=source.id,
        **{name: getattr(source, name) for name in SETUP_COLUMNS},
    )
    copy = await repo.add(copy)
    _audit(session, copy, "duplicated", ctx.user_id, duplicated_from_id=str(source.id))
    return await _done(session, copy)


async def top_up(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    credits_to_add: int,
    now: datetime | None = None,
) -> Pipeline:
    """Reserves more free credits for an open pipeline (FR-BILL-04). A pipeline paused for
    credits goes back to live."""
    now = _now(now)
    pipeline = await _repo(session, ctx).lock(pipeline_id)
    _check_transition(pipeline, "top_up")
    await credits.reserve(
        session,
        ctx.workspace_id,
        pipeline.id,
        credits=credits_to_add,
        top_up=True,
        now=now,
        actor_id=ctx.user_id,
    )
    _audit(session, pipeline, "topped_up", ctx.user_id, credits=credits_to_add)
    await _resume_if_credits(session, pipeline, now, ctx.user_id)
    return await _done(session, pipeline)


async def _resume_if_credits(
    session: AsyncSession, pipeline: PipelineRow, now: datetime, actor_id: uuid.UUID | None
) -> bool:
    if pipeline.status not in TRANSITIONS["credits_added"]:
        return False
    if await _live_status(session, pipeline, now) != "live":
        return False
    pipeline.status = "live"
    _audit(session, pipeline, "resumed", actor_id, reason="credits_added")
    return True


async def resume_after_credits_added(
    session: AsyncSession, workspace_id: uuid.UUID, *, now: datetime | None = None
) -> int:
    """Puts pipelines paused for credits back live when they have reserve left and the workspace
    has credits again. Call it in the transaction that granted credits (BILL-001, BILL-005);
    the caller commits. Returns how many resumed."""
    now = _now(now)
    repo = PipelineRepository(session, workspace_id, department_ids=None)
    resumed = 0
    for pipeline_id in await out_of_credit_pipeline_ids(session, workspace_id):
        pipeline = await repo.lock(pipeline_id)
        if await _resume_if_credits(session, pipeline, now, None):
            resumed += 1
    return resumed


# ---------------------------------------------------------------------------
# Schedule (cron)
# ---------------------------------------------------------------------------
async def open_due(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Opens scheduled pipelines whose `opens_at` has come, each in its own transaction.
    The every-minute `open_and_close_pipelines` cron calls this. Returns how many opened."""
    now = _now(now)
    opened = 0
    for workspace_id, pipeline_id in await due_to_open(session, now):
        repo = PipelineRepository(session, workspace_id, department_ids=None)
        pipeline = await repo.lock(pipeline_id)
        if pipeline.status in TRANSITIONS["open"]:  # unless an action got there first
            assert pipeline.opens_at is not None
            status = await _live_status(session, pipeline, now)
            _open(pipeline, now, status=status, opens_at=pipeline.opens_at)
            _audit(session, pipeline, "opened", None, status=pipeline.status)
            opened += 1
        await session.commit()
    return opened


async def close_due(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Closes open pipelines whose `closes_at` has passed ("Completed"), releasing their unused
    reserve, each in its own transaction. Returns how many closed."""
    now = _now(now)
    closed = 0
    for workspace_id, pipeline_id in await due_to_close(session, now):
        repo = PipelineRepository(session, workspace_id, department_ids=None)
        pipeline = await repo.lock(pipeline_id)
        if pipeline.status in TRANSITIONS["close"]:
            await _close(session, pipeline, "schedule", now, None)
            closed += 1
        await session.commit()
    return closed
