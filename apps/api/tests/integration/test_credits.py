"""BILL-002: the credit ledger. Balances never go negative, the ledger always adds up to the
batches, credits are used plan → trial → extra, and concurrent applicants can't overspend."""

import asyncio
import random
import uuid
from collections.abc import Awaitable, Callable, Iterator
from datetime import UTC, datetime, timedelta

import asyncpg
import httpx2
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.errors import (
    AppError,
    InsufficientFreeCreditsError,
    PipelineNotAcceptingError,
)
from app.models import CreditBatch, CreditLedgerEntry, Pipeline
from app.services import credits
from tests.conftest import Supabase, delete_credit_rows

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)

Work = Callable[[async_sessionmaker[AsyncSession]], Awaitable[None]]


def run(supabase: Supabase, work: Work) -> None:
    """Runs `work` with a sessionmaker for the API role; each session commits what it keeps."""

    async def main() -> None:
        url = supabase.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(url, pool_size=25)
        try:
            await work(async_sessionmaker(engine, expire_on_commit=False))
        finally:
            await engine.dispose()

    asyncio.run(main())


@pytest.fixture
def workspace_id(supabase: Supabase) -> Iterator[uuid.UUID]:
    """A committed workspace with no credits, and its owner; both deleted afterwards."""
    email = f"bill002-{uuid.uuid4().hex[:12]}@example.com"
    response = httpx2.post(
        f"{supabase.url}/auth/v1/signup",
        headers={"apikey": supabase.anon_key},
        json={"email": email, "password": "test-password-1"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    user_id = uuid.UUID(body.get("id") or body["user"]["id"])
    created = uuid.uuid4()

    async def execute(query: str, *args: object) -> None:
        connection = await asyncpg.connect(supabase.database_url)
        try:
            await connection.execute(query, *args)
        finally:
            await connection.close()

    asyncio.run(
        execute(
            "insert into workspaces (id, name, slug, owner_id) values ($1, 'Credits', $2, $3)",
            created,
            f"credits-{created.hex[:12]}",
            user_id,
        )
    )
    yield created
    asyncio.run(delete_credit_rows(supabase, [created]))
    asyncio.run(execute("delete from workspaces where id = $1", created))
    httpx2.delete(
        f"{supabase.url}/auth/v1/admin/users/{user_id}",
        headers={"apikey": supabase.secret_key, "Authorization": f"Bearer {supabase.secret_key}"},
    )


async def add_pipeline(session: AsyncSession, workspace_id: uuid.UUID) -> uuid.UUID:
    pipeline_id = uuid.uuid4()
    pipeline = Pipeline(
        id=pipeline_id,
        workspace_id=workspace_id,
        status="live",
        slug=f"role-{pipeline_id.hex[:8]}",
        published_at=NOW,
    )
    session.add(pipeline)
    await session.flush()
    return pipeline.id


async def ledger_total(session: AsyncSession, workspace_id: uuid.UUID) -> int:
    total = await session.scalar(
        select(func.coalesce(func.sum(CreditLedgerEntry.amount), 0)).where(
            CreditLedgerEntry.workspace_id == workspace_id
        )
    )
    return int(total or 0)


async def batches_total(session: AsyncSession, workspace_id: uuid.UUID) -> int:
    total = await session.scalar(
        select(func.coalesce(func.sum(CreditBatch.remaining), 0)).where(
            CreditBatch.workspace_id == workspace_id
        )
    )
    return int(total or 0)


async def try_consume(
    sessionmaker: async_sessionmaker[AsyncSession],
    workspace_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    now: datetime,
) -> str:
    """One applicant in their own transaction, like a real request."""
    async with sessionmaker() as session:
        try:
            await credits.consume(session, workspace_id, pipeline_id, now=now)
        except AppError as error:
            await session.rollback()
            return error.code
        await session.commit()
        return "used"


def test_trial_is_20_credits_for_30_days_and_granted_once(
    supabase: Supabase, workspace_id: uuid.UUID
) -> None:
    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        async with sessionmaker() as session:
            batch = await credits.grant_trial(session, workspace_id, granted_at=NOW)
            assert batch is not None
            assert (batch.kind, batch.amount, batch.remaining) == ("trial", 20, 20)
            assert batch.expires_at == NOW + timedelta(days=30)
            assert await credits.grant_trial(session, workspace_id, granted_at=NOW) is None
            summary = await credits.summary(session, workspace_id, now=NOW)
            assert (summary.balance, summary.reserved, summary.free) == (20, 0, 20)
            assert (await credits.summary(session, workspace_id, now=batch.expires_at)).balance == 0
            await session.rollback()

    run(supabase, work)


def test_credits_are_used_plan_then_trial_then_extra_by_earliest_expiry(
    supabase: Supabase, workspace_id: uuid.UUID
) -> None:
    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        async with sessionmaker() as session:
            later_extra = await credits.grant_extra(session, workspace_id, credits=1, now=NOW)
            trial = await credits.grant_trial(session, workspace_id, granted_at=NOW)
            plan = await credits.grant_plan(
                session, workspace_id, credits=2, period_end=NOW + timedelta(days=20), now=NOW
            )
            earlier_extra = await credits.grant_extra(
                session, workspace_id, credits=1, now=NOW - timedelta(days=60)
            )
            assert trial is not None
            pipeline_id = await add_pipeline(session, workspace_id)
            await credits.reserve(session, workspace_id, pipeline_id, credits=24, now=NOW)

            used_from = [
                (await credits.consume(session, workspace_id, pipeline_id, now=NOW)).batch_id
                for _ in range(24)
            ]

            assert used_from == (
                [plan.id] * 2 + [trial.id] * 20 + [earlier_extra.id, later_extra.id]
            )
            await session.rollback()

    run(supabase, work)


def test_concurrent_applicants_never_use_more_than_the_reserve(
    supabase: Supabase, workspace_id: uuid.UUID
) -> None:
    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        async with sessionmaker() as session:
            await credits.grant_trial(session, workspace_id, granted_at=NOW)
            pipeline_id = await add_pipeline(session, workspace_id)
            await credits.reserve(session, workspace_id, pipeline_id, credits=5, now=NOW)
            await session.commit()

        results = await asyncio.gather(
            *(try_consume(sessionmaker, workspace_id, pipeline_id, NOW) for _ in range(20))
        )

        assert results.count("used") == 5
        assert results.count("pipeline_not_accepting") == 15
        async with sessionmaker() as session:
            pipeline = await session.get(Pipeline, pipeline_id)
            assert pipeline is not None
            assert (pipeline.credits_used, pipeline.status) == (5, "paused_no_credits")
            assert (await credits.summary(session, workspace_id, now=NOW)).balance == 15
            assert await ledger_total(session, workspace_id) == 15

    run(supabase, work)


def test_two_pipelines_racing_for_the_last_credit_use_it_once(
    supabase: Supabase, workspace_id: uuid.UUID
) -> None:
    """Reserves bigger than the balance after plan credits expire (BILLING.md §4)."""
    later = NOW + timedelta(days=15)

    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        async with sessionmaker() as session:
            await credits.grant_plan(
                session, workspace_id, credits=1, period_end=NOW + timedelta(days=10), now=NOW
            )
            await credits.grant_extra(session, workspace_id, credits=1, now=NOW)
            pipelines = [await add_pipeline(session, workspace_id) for _ in range(2)]
            for pipeline_id in pipelines:
                await credits.reserve(session, workspace_id, pipeline_id, credits=1, now=NOW)
            await session.commit()

        results = await asyncio.gather(
            *(try_consume(sessionmaker, workspace_id, p, later) for p in pipelines)
        )

        assert sorted(results) == ["pipeline_not_accepting", "used"]
        async with sessionmaker() as session:
            summary = await credits.summary(session, workspace_id, now=later)
            assert (summary.balance, summary.free) == (0, -1)
            statuses = await session.scalars(
                select(Pipeline.status).where(Pipeline.id.in_(pipelines))
            )
            assert set(statuses) == {"paused_no_credits"}

    run(supabase, work)


def test_reserve_top_up_and_release_move_free_credits(
    supabase: Supabase, workspace_id: uuid.UUID
) -> None:
    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        async with sessionmaker() as session:
            await credits.grant_trial(session, workspace_id, granted_at=NOW)
            pipeline_id = await add_pipeline(session, workspace_id)
            await credits.reserve(session, workspace_id, pipeline_id, credits=10, now=NOW)
            with pytest.raises(InsufficientFreeCreditsError):
                await credits.reserve(
                    session, workspace_id, pipeline_id, credits=11, top_up=True, now=NOW
                )
            await credits.reserve(
                session, workspace_id, pipeline_id, credits=5, top_up=True, now=NOW
            )
            await credits.consume(session, workspace_id, pipeline_id, now=NOW)
            assert (await credits.summary(session, workspace_id, now=NOW)).free == 5

            assert await credits.release(session, workspace_id, pipeline_id, now=NOW) == 14
            assert await credits.release(session, workspace_id, pipeline_id, now=NOW) == 0
            with pytest.raises(PipelineNotAcceptingError):
                await credits.consume(session, workspace_id, pipeline_id, now=NOW)
            summary = await credits.summary(session, workspace_id, now=NOW)
            assert (summary.balance, summary.reserved, summary.free) == (19, 0, 19)
            kinds = await session.scalars(
                select(CreditLedgerEntry.kind)
                .where(CreditLedgerEntry.workspace_id == workspace_id)
                .order_by(CreditLedgerEntry.created_at, CreditLedgerEntry.id)
            )
            assert list(kinds) == ["grant_trial", "reserve", "top_up", "consume", "release"]
            await session.rollback()

    run(supabase, work)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_random_credit_changes_keep_the_ledger_and_balances_consistent(
    supabase: Supabase, workspace_id: uuid.UUID, seed: int
) -> None:
    """Property test: after every operation in a random sequence, no balance is negative, the
    ledger adds up to the batches' remaining credits, and no pipeline uses more than its
    reserve. Fixed seeds keep failures reproducible."""
    rng = random.Random(seed)

    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        async with sessionmaker() as session:
            clock = NOW
            await credits.grant_trial(session, workspace_id, granted_at=clock)
            pipelines = [await add_pipeline(session, workspace_id) for _ in range(3)]
            for _ in range(80):
                operation = rng.choice(
                    ["plan", "extra", "reserve", "consume", "consume", "consume", "release",
                     "expire", "reopen", "wait"]
                )  # fmt: skip
                pipeline_id = rng.choice(pipelines)
                try:
                    async with session.begin_nested():
                        if operation == "plan":
                            await credits.grant_plan(
                                session,
                                workspace_id,
                                credits=rng.randint(1, 10),
                                period_end=clock + timedelta(days=rng.randint(1, 30)),
                                now=clock,
                            )
                        elif operation == "extra":
                            await credits.grant_extra(
                                session, workspace_id, credits=rng.randint(1, 5), now=clock
                            )
                        elif operation == "reserve":
                            await credits.reserve(
                                session,
                                workspace_id,
                                pipeline_id,
                                credits=rng.randint(1, 8),
                                top_up=rng.random() < 0.5,
                                now=clock,
                            )
                        elif operation == "consume":
                            await credits.consume(session, workspace_id, pipeline_id, now=clock)
                        elif operation == "release":
                            await credits.release(session, workspace_id, pipeline_id, now=clock)
                        elif operation == "expire":
                            await credits.expire_batches(session, now=clock)
                        elif operation == "reopen":
                            pipeline = await session.get(Pipeline, pipeline_id)
                            assert pipeline is not None
                            pipeline.status = "live"
                        else:
                            clock += timedelta(days=rng.randint(1, 10))
                except (InsufficientFreeCreditsError, PipelineNotAcceptingError):
                    pass

                summary = await credits.summary(session, workspace_id, now=clock)
                assert summary.balance >= 0
                assert all(batch.remaining >= 0 for batch in summary.batches)
                assert await ledger_total(session, workspace_id) == await batches_total(
                    session, workspace_id
                )
                for pipeline_id in pipelines:
                    pipeline = await session.get(Pipeline, pipeline_id)
                    assert pipeline is not None
                    assert 0 <= pipeline.credits_used <= pipeline.credits_reserved
            await session.rollback()

    run(supabase, work)


def test_expiry_zeroes_expired_batches_and_pauses_live_pipelines(
    supabase: Supabase, workspace_id: uuid.UUID
) -> None:
    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        async with sessionmaker() as session:
            await credits.grant_trial(session, workspace_id, granted_at=NOW)
            pipeline_id = await add_pipeline(session, workspace_id)
            await credits.reserve(session, workspace_id, pipeline_id, credits=5, now=NOW)

            assert await credits.expire_batches(session, now=NOW + timedelta(days=30)) >= 1

            summary = await credits.summary(session, workspace_id, now=NOW)
            assert summary.balance == 0
            assert await ledger_total(session, workspace_id) == 0
            pipeline = await session.get(Pipeline, pipeline_id)
            assert pipeline is not None
            assert pipeline.status == "paused_no_credits"
            await session.rollback()

    run(supabase, work)


def test_credit_ledger_is_append_only(supabase: Supabase, workspace_id: uuid.UUID) -> None:
    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        async with sessionmaker() as session:
            await credits.grant_trial(session, workspace_id, granted_at=NOW)
            await session.commit()

        connection = await asyncpg.connect(supabase.database_url)
        try:
            for statement in (
                "update credit_ledger set amount = 100 where workspace_id = $1",
                "delete from credit_ledger where workspace_id = $1",
            ):
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await connection.execute(statement, workspace_id)
        finally:
            await connection.close()

    run(supabase, work)
