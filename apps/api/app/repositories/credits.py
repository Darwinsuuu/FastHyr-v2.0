"""Credit batches, the credit ledger and pipeline reserves for one workspace (BILLING.md).

Only services/credits.py uses this. Every write happens after `lock_workspace()`, which holds the
workspace row `FOR UPDATE` until the transaction ends, so credit changes in one workspace run one
at a time.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import CreditBatch, CreditLedgerEntry, Pipeline, Workspace
from app.repositories.base import WorkspaceRepository

# Statuses whose unused reserve still counts as reserved (BILLING.md §2).
OPEN_STATUSES = ("scheduled", "live", "paused", "paused_no_credits")

# Consumption order: plan → trial → extra, then earliest expiry (FR-BILL-03).
_KIND_ORDER = case({"plan": 0, "trial": 1, "extra": 2}, value=CreditBatch.kind)


class CreditRepository(WorkspaceRepository[CreditBatch]):
    model = CreditBatch

    async def lock_workspace(self) -> None:
        locked = await self.session.scalar(
            select(Workspace.id).where(Workspace.id == self.workspace_id).with_for_update()
        )
        if locked is None:
            raise NotFoundError()

    async def lock_pipeline(self, pipeline_id: uuid.UUID) -> Pipeline:
        pipeline: Pipeline | None = await self.session.scalar(
            select(Pipeline)
            .where(Pipeline.workspace_id == self.workspace_id, Pipeline.id == pipeline_id)
            .with_for_update()
        )
        if pipeline is None:
            raise NotFoundError()
        return pipeline

    async def balance(self, now: datetime) -> int:
        total = await self.session.scalar(
            self._scoped(select(func.coalesce(func.sum(CreditBatch.remaining), 0))).where(
                CreditBatch.expires_at > now
            )
        )
        return int(total or 0)

    async def reserved(self) -> int:
        total = await self.session.scalar(
            select(
                func.coalesce(func.sum(Pipeline.credits_reserved - Pipeline.credits_used), 0)
            ).where(Pipeline.workspace_id == self.workspace_id, Pipeline.status.in_(OPEN_STATUSES))
        )
        return int(total or 0)

    async def live_batches(self, now: datetime) -> Sequence[CreditBatch]:
        """Unexpired batches with credits left, in consumption order."""
        rows = await self.session.scalars(
            self._scoped()
            .where(CreditBatch.remaining > 0, CreditBatch.expires_at > now)
            .order_by(_KIND_ORDER, CreditBatch.expires_at, CreditBatch.added_at)
        )
        return rows.all()

    async def expired_batches(self, now: datetime) -> Sequence[CreditBatch]:
        rows = await self.session.scalars(
            self._scoped()
            .where(CreditBatch.remaining > 0, CreditBatch.expires_at <= now)
            .order_by(CreditBatch.expires_at)
        )
        return rows.all()

    async def trial_batch(self) -> CreditBatch | None:
        batch: CreditBatch | None = await self.session.scalar(
            self._scoped().where(CreditBatch.kind == "trial")
        )
        return batch

    async def current_plan_batch(self, now: datetime) -> CreditBatch | None:
        """The plan batch for the current billing period (the unexpired one ending last)."""
        batch: CreditBatch | None = await self.session.scalar(
            self._scoped()
            .where(CreditBatch.kind == "plan", CreditBatch.expires_at > now)
            .order_by(CreditBatch.expires_at.desc())
            .limit(1)
        )
        return batch

    async def add_batch(
        self,
        *,
        kind: str,
        amount: int,
        added_at: datetime,
        expires_at: datetime,
        stripe_invoice_id: str | None = None,
        note: str | None = None,
    ) -> CreditBatch:
        batch = CreditBatch(
            workspace_id=self.workspace_id,
            kind=kind,
            amount=amount,
            remaining=amount,
            added_at=added_at,
            expires_at=expires_at,
            stripe_invoice_id=stripe_invoice_id,
            note=note,
        )
        self.session.add(batch)
        await self.session.flush()
        return batch

    async def add_entry(
        self,
        *,
        kind: str,
        balance_after: int,
        amount: int = 0,
        reserve_change: int = 0,
        pipeline_id: uuid.UUID | None = None,
        application_id: uuid.UUID | None = None,
        batch_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> CreditLedgerEntry:
        entry = CreditLedgerEntry(
            workspace_id=self.workspace_id,
            kind=kind,
            amount=amount,
            reserve_change=reserve_change,
            pipeline_id=pipeline_id,
            application_id=application_id,
            batch_id=batch_id,
            balance_after=balance_after,
            actor_id=actor_id,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def pause_live_pipelines(self) -> None:
        """Out of credits: every live pipeline stops accepting applications (FR-BILL-04)."""
        await self.session.execute(
            update(Pipeline)
            .where(Pipeline.workspace_id == self.workspace_id, Pipeline.status == "live")
            .values(status="paused_no_credits")
            .execution_options(synchronize_session="fetch")
        )


async def workspaces_with_expired_batches(session: AsyncSession, now: datetime) -> list[uuid.UUID]:
    """For the expiry job, which runs across workspaces before scoping to each one."""
    rows = await session.scalars(
        select(CreditBatch.workspace_id)
        .where(CreditBatch.remaining > 0, CreditBatch.expires_at <= now)
        .distinct()
    )
    return list(rows)
