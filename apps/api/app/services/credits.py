"""The credit ledger: the only code that changes credits (BILLING.md §2-4, ADR-010).

Every operation runs in the caller's transaction (the caller commits) and starts by locking the
workspace row, so credit changes in one workspace happen one at a time and two applicants can
never both take the last credit. Each change writes one `credit_ledger` row with the workspace
balance after it, so the ledger always adds up to the batches' remaining credits.

Balance = unexpired credits left. Reserved = unused reserve of open pipelines. Free = Balance -
Reserved, which can go negative after credits expire (BILLING.md §4).
"""

import calendar
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InsufficientFreeCreditsError, PipelineNotAcceptingError
from app.models import CreditBatch, CreditLedgerEntry, Pipeline
from app.repositories.credits import CreditRepository, workspaces_with_expired_batches

TRIAL_CREDITS = 20
TRIAL_DAYS = 30
EXTRA_CREDIT_MONTHS = 12


@dataclass(frozen=True)
class CreditSummary:
    balance: int
    reserved: int
    free: int
    batches: list[CreditBatch]


def add_months(moment: datetime, months: int) -> datetime:
    """Same day and time `months` later, or the month's last day when it is shorter."""
    month_index = moment.month - 1 + months
    year, month = moment.year + month_index // 12, month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)


def _positive(credits: int) -> None:
    if credits <= 0:
        raise ValueError("credits must be a positive whole number")


async def summary(
    session: AsyncSession, workspace_id: uuid.UUID, *, now: datetime | None = None
) -> CreditSummary:
    """Balance, reserved and free credits, and the batches with credits left (BILL-003, 006)."""
    now = _now(now)
    credits = CreditRepository(session, workspace_id)
    balance = await credits.balance(now)
    reserved = await credits.reserved()
    batches = list(await credits.live_batches(now))
    return CreditSummary(
        balance=balance, reserved=reserved, free=balance - reserved, batches=batches
    )


# ---------------------------------------------------------------------------
# Grants
# ---------------------------------------------------------------------------
async def grant_trial(
    session: AsyncSession, workspace_id: uuid.UUID, *, granted_at: datetime
) -> CreditBatch | None:
    """20 credits expiring 30 days after `granted_at` (FR-BILL-02). A workspace gets one trial
    ever, so a second call returns None and changes nothing."""
    credits = CreditRepository(session, workspace_id)
    await credits.lock_workspace()
    if await credits.trial_batch() is not None:
        return None
    return await _grant(
        credits,
        kind="trial",
        ledger_kind="grant_trial",
        amount=TRIAL_CREDITS,
        added_at=granted_at,
        expires_at=granted_at + timedelta(days=TRIAL_DAYS),
        note="Free trial",
    )


async def grant_plan(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    credits: int,
    period_end: datetime,
    stripe_invoice_id: str | None = None,
    now: datetime | None = None,
) -> CreditBatch:
    """A subscription period's credits, expiring when the period ends (BILL-001 calls this on
    `invoice.paid`)."""
    _positive(credits)
    repo = CreditRepository(session, workspace_id)
    await repo.lock_workspace()
    return await _grant(
        repo,
        kind="plan",
        ledger_kind="grant_plan",
        amount=credits,
        added_at=_now(now),
        expires_at=period_end,
        stripe_invoice_id=stripe_invoice_id,
    )


async def top_up_plan(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    credits: int,
    stripe_invoice_id: str | None = None,
    now: datetime | None = None,
    actor_id: uuid.UUID | None = None,
) -> CreditBatch:
    """Mid-period upgrade: adds the difference in plan credits to the current plan batch
    (BILL-004 calls this on the proration invoice). Without a current plan batch there is
    nothing to upgrade, which is a caller bug."""
    _positive(credits)
    now = _now(now)
    repo = CreditRepository(session, workspace_id)
    await repo.lock_workspace()
    batch = await repo.current_plan_batch(now)
    if batch is None:
        raise LookupError("no current plan batch to top up")
    batch.amount += credits
    batch.remaining += credits
    if stripe_invoice_id is not None:
        batch.stripe_invoice_id = stripe_invoice_id
    await session.flush()
    await repo.add_entry(
        kind="grant_plan",
        amount=credits,
        batch_id=batch.id,
        balance_after=await repo.balance(now),
        actor_id=actor_id,
    )
    return batch


async def grant_extra(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    credits: int,
    stripe_invoice_id: str | None = None,
    now: datetime | None = None,
    actor_id: uuid.UUID | None = None,
) -> CreditBatch:
    """A credit pack, expiring 12 months after purchase (BILL-005 calls this on
    `payment_intent.succeeded`)."""
    _positive(credits)
    now = _now(now)
    repo = CreditRepository(session, workspace_id)
    await repo.lock_workspace()
    return await _grant(
        repo,
        kind="extra",
        ledger_kind="purchase",
        amount=credits,
        added_at=now,
        expires_at=add_months(now, EXTRA_CREDIT_MONTHS),
        stripe_invoice_id=stripe_invoice_id,
        actor_id=actor_id,
    )


async def _grant(
    repo: CreditRepository,
    *,
    kind: str,
    ledger_kind: str,
    amount: int,
    added_at: datetime,
    expires_at: datetime,
    stripe_invoice_id: str | None = None,
    note: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> CreditBatch:
    batch = await repo.add_batch(
        kind=kind,
        amount=amount,
        added_at=added_at,
        expires_at=expires_at,
        stripe_invoice_id=stripe_invoice_id,
        note=note,
    )
    await repo.add_entry(
        kind=ledger_kind,
        amount=amount,
        batch_id=batch.id,
        balance_after=await repo.balance(added_at),
        actor_id=actor_id,
    )
    return batch


# ---------------------------------------------------------------------------
# Pipeline reserves
# ---------------------------------------------------------------------------
async def reserve(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    *,
    credits: int,
    top_up: bool = False,
    now: datetime | None = None,
    actor_id: uuid.UUID | None = None,
) -> Pipeline:
    """Sets `credits` aside for a pipeline from the workspace's free credits: on publish, or as a
    top-up (FR-BILL-04). More than the free credits raises `insufficient_free_credits`."""
    _positive(credits)
    now = _now(now)
    repo = CreditRepository(session, workspace_id)
    await repo.lock_workspace()
    pipeline = await repo.lock_pipeline(pipeline_id)
    balance = await repo.balance(now)
    if credits > balance - await repo.reserved():
        raise InsufficientFreeCreditsError()
    pipeline.credits_reserved += credits
    await session.flush()
    await repo.add_entry(
        kind="top_up" if top_up else "reserve",
        reserve_change=credits,
        pipeline_id=pipeline.id,
        balance_after=balance,
        actor_id=actor_id,
    )
    return pipeline


async def consume(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    *,
    application_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> CreditLedgerEntry:
    """Uses 1 credit for a submitted application (ADR-010): one of the pipeline's reserved
    credits, taken from the first batch in consumption order (plan → trial → extra by earliest
    expiry). A pipeline that isn't live, has used its reserve, or whose workspace has no credits
    left raises `pipeline_not_accepting`, and no credit is used.

    When the reserve runs out the pipeline pauses; when the balance reaches 0 every live pipeline
    in the workspace pauses (FR-BILL-04)."""
    now = _now(now)
    repo = CreditRepository(session, workspace_id)
    await repo.lock_workspace()
    pipeline = await repo.lock_pipeline(pipeline_id)
    if pipeline.status != "live" or pipeline.credits_used >= pipeline.credits_reserved:
        raise PipelineNotAcceptingError()
    batches = await repo.live_batches(now)
    if not batches:
        raise PipelineNotAcceptingError()
    batch = batches[0]
    batch.remaining -= 1
    pipeline.credits_used += 1
    if pipeline.credits_used == pipeline.credits_reserved:
        pipeline.status = "paused_no_credits"
    await session.flush()
    balance = await repo.balance(now)
    entry = await repo.add_entry(
        kind="consume",
        amount=-1,
        pipeline_id=pipeline.id,
        application_id=application_id,
        batch_id=batch.id,
        balance_after=balance,
    )
    if balance == 0:
        await repo.pause_live_pipelines()
    return entry


async def release(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    *,
    now: datetime | None = None,
    actor_id: uuid.UUID | None = None,
) -> int:
    """Returns a closing or cancelled pipeline's unused reserve to the free credits. Returns how
    many credits were released (0 when nothing was left)."""
    now = _now(now)
    repo = CreditRepository(session, workspace_id)
    await repo.lock_workspace()
    pipeline = await repo.lock_pipeline(pipeline_id)
    unused = pipeline.credits_reserved - pipeline.credits_used
    if unused == 0:
        return 0
    pipeline.credits_reserved = pipeline.credits_used
    await session.flush()
    await repo.add_entry(
        kind="release",
        reserve_change=-unused,
        pipeline_id=pipeline.id,
        balance_after=await repo.balance(now),
        actor_id=actor_id,
    )
    return unused


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------
async def expire_batches(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Zeroes expired batches that still have credits, one `expire` ledger row each, and pauses
    live pipelines in workspaces left with no credits. The hourly `expire_credit_batches` cron
    (FND-008) calls this and commits. Balance already ignores expired batches, so this only makes
    the ledger and the batches agree. Returns how many batches expired."""
    now = _now(now)
    expired = 0
    for workspace_id in await workspaces_with_expired_batches(session, now):
        repo = CreditRepository(session, workspace_id)
        await repo.lock_workspace()
        balance = await repo.balance(now)
        for batch in await repo.expired_batches(now):
            lost = batch.remaining
            batch.remaining = 0
            await session.flush()
            await repo.add_entry(
                kind="expire", amount=-lost, batch_id=batch.id, balance_after=balance
            )
            expired += 1
        if balance == 0:
            await repo.pause_live_pipelines()
    return expired
