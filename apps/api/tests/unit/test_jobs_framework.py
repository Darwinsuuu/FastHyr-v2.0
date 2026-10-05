"""FND-008: the job wrapper retries with backoff, records the failure after the last try, and
the worker registers every job and cron on the documented schedule."""

import asyncio
from datetime import timedelta
from typing import Any

import pytest
from arq import Retry

from app.jobs.framework import JobRun, RetryPolicy, job
from app.jobs.queue import JobQueue
from app.worker import CRON_JOBS, EVERY_10_MINUTES, FUNCTIONS


class FakeSession:
    def __init__(self) -> None:
        self.rolled_back = False
        self.committed = False

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def rollback(self) -> None:
        self.rolled_back = True

    async def commit(self) -> None:
        self.committed = True


class FakeSessionmaker:
    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        self.sessions.append(FakeSession())
        return self.sessions[-1]


class BoomError(Exception):
    pass


def ctx_for(job_try: int, sessionmaker: FakeSessionmaker) -> dict[str, Any]:
    return {"sessionmaker": sessionmaker, "job_try": job_try, "job_id": "j", "queue": None}


def test_backoff_doubles_up_to_the_cap() -> None:
    policy = RetryPolicy(
        max_tries=6, base_delay=timedelta(seconds=10), max_delay=timedelta(seconds=60)
    )
    assert [policy.delay(t).total_seconds() for t in range(1, 6)] == [10, 20, 40, 60, 60]


def test_failed_try_is_rolled_back_and_retried_with_backoff() -> None:
    failures: list[BaseException] = []

    async def record(session: Any, error: BaseException, args: tuple[Any, ...]) -> None:
        failures.append(error)

    @job(retry=RetryPolicy(max_tries=3, base_delay=timedelta(seconds=5)), on_failure=record)
    async def flaky(run: JobRun, entity: str) -> None:
        raise BoomError()

    sessionmaker = FakeSessionmaker()
    with pytest.raises(Retry) as retry:
        asyncio.run(flaky(ctx_for(2, sessionmaker), "entity-1"))

    assert retry.value.defer_score == 10_000  # 5 s * 2 after the second try, in ms
    assert sessionmaker.sessions[0].rolled_back
    assert failures == []


def test_last_try_records_the_failure_then_raises() -> None:
    recorded: list[tuple[BaseException, tuple[Any, ...]]] = []

    async def record(session: Any, error: BaseException, args: tuple[Any, ...]) -> None:
        recorded.append((error, args))

    @job(retry=RetryPolicy(max_tries=3), on_failure=record)
    async def flaky(run: JobRun, entity: str) -> None:
        raise BoomError()

    sessionmaker = FakeSessionmaker()
    with pytest.raises(BoomError):
        asyncio.run(flaky(ctx_for(3, sessionmaker), "entity-1"))

    assert len(recorded) == 1
    assert isinstance(recorded[0][0], BoomError)
    assert recorded[0][1] == ("entity-1",)
    # The failure is recorded in its own session, which is committed.
    assert sessionmaker.sessions[1].committed


def test_successful_job_returns_its_result() -> None:
    @job()
    async def works(run: JobRun, value: int) -> int:
        return value * 2

    assert asyncio.run(works(ctx_for(1, FakeSessionmaker()), 21)) == 42


def test_worker_registers_jobs_with_their_retry_policy() -> None:
    by_name = {function.name: function for function in FUNCTIONS}
    assert by_name["sample_report_job"].max_tries == 3
    # A live interview's sideband outlasts the default timeout: the cap plus room (INTV-004).
    assert by_name["run_realtime_session"].timeout_s == 35 * 60


def test_crons_run_on_the_documented_schedule() -> None:
    schedule = {cron.name: cron for cron in CRON_JOBS}
    assert set(schedule) == {
        "expire_credit_batches",
        "expire_invites",
        "requeue_stuck_work",
        "remove_storage_orphans",
        "open_and_close_pipelines",
        "dispatch_scheduled_emails",
        "end_overdue_attempts",
        "finalize_recordings",
    }
    # Every minute, so a scheduled pipeline opens within a minute of its date (PIPE-001), a
    # scheduled email goes out within a minute of its time (MSG-003), no live interview runs
    # more than a minute past its cap (INTV-004) and a recording is put together soon after it
    # can be (INTV-006).
    for name in (
        "open_and_close_pipelines",
        "dispatch_scheduled_emails",
        "end_overdue_attempts",
        "finalize_recordings",
    ):
        every_minute = schedule[name]
        assert (every_minute.minute, every_minute.hour, every_minute.second) == (None, None, 0)
    # Hourly crons name one minute of the hour; the sweeper runs every 10 minutes.
    assert isinstance(schedule["expire_credit_batches"].minute, int)
    assert isinstance(schedule["expire_invites"].minute, int)
    assert schedule["requeue_stuck_work"].minute == EVERY_10_MINUTES
    # Daily crons name one hour and minute.
    assert isinstance(schedule["remove_storage_orphans"].hour, int)
    assert isinstance(schedule["remove_storage_orphans"].minute, int)
    for cron in CRON_JOBS:
        assert cron.unique  # one run per tick even with several workers


def test_enqueue_without_redis_returns_false_instead_of_failing_the_request() -> None:
    async def enqueue() -> bool:
        queue = JobQueue("redis://127.0.0.1:1")  # nothing listens here
        return await queue.enqueue("send_email", "id", key="id")

    assert asyncio.run(enqueue()) is False
