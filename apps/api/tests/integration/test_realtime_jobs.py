"""INTV-004: the live interview's jobs on the real arq worker. `run_realtime_session` holds the
sideband until the attempt's time is up; the every-minute `end_overdue_attempts` cron ends
attempts whose browser went quiet."""

import asyncio
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI

from app.ai.realtime import FakeRealtime
from app.integrations.storage import SupabaseStorage
from app.jobs.queue import JobQueue
from app.jobs.realtime import end_overdue_attempts
from app.main import create_app
from app.worker import shutdown, startup
from tests.integration.test_applications import CandidateUser, candidates, clean_resumes
from tests.integration.test_interview_sessions import age, attempts, interview, ready, start
from tests.integration.test_pipelines import ok, sql
from tests.integration.worker import drain
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes"]


@pytest.fixture
def queue_name() -> str:
    return f"arq:test:{uuid.uuid4().hex[:12]}"


@pytest.fixture
def realtime() -> FakeRealtime:
    return FakeRealtime()


@pytest.fixture
def tenancy_app(
    storage: SupabaseStorage, redis_url: str, queue_name: str, realtime: FakeRealtime
) -> Iterator[FastAPI]:
    yield create_app(
        storage=storage, job_queue=JobQueue(redis_url, queue_name=queue_name), realtime=realtime
    )


def test_the_sideband_job_runs_the_attempt_until_its_time_is_up(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    realtime: FakeRealtime,
    redis_url: str,
    queue_name: str,
) -> None:
    paolo = candidates[0]
    token, interview_id = ready(tenancy, paolo)
    session = ok(start(tenancy, token, paolo))
    # Two seconds of the cap left, so the queued job finishes quickly.
    sql(
        tenancy,
        "update interview_attempts set seconds_allowed = 2, started_at = now() where id = $1",
        uuid.UUID(session["attempt_id"]),
    )

    drain(redis_url, queue_name, realtime=realtime)

    [attempt] = attempts(tenancy, interview_id)
    assert attempt["end_reason"] == "time_cap"
    assert interview(tenancy, interview_id)["status"] == "completed"
    assert "rtc_fake_1" in realtime.hung_up
    [call] = sql(
        tenancy,
        "select * from ai_calls where entity_id = $1 and purpose = 'interview_realtime'",
        attempt["id"],
    )
    assert (call["model"], call["status"]) == ("fake", "ok")
    assert int(call["audio_seconds"]) == 2


def test_the_watchdog_ends_attempts_whose_browser_went_quiet(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    realtime: FakeRealtime,
    redis_url: str,
    queue_name: str,
) -> None:
    paolo = candidates[0]
    token, interview_id = ready(tenancy, paolo)
    session = ok(start(tenancy, token, paolo))
    age(tenancy, session["attempt_id"], seconds=90)

    async def sweep() -> int:
        queue = JobQueue(redis_url, queue_name=queue_name)
        pool = await queue.pool()
        ctx: dict[str, Any] = {"redis": pool, "queue_name": queue_name, "realtime": realtime}
        await startup(ctx)
        try:
            ended: int = await end_overdue_attempts(ctx)
            return ended
        finally:
            await shutdown(ctx)
            await queue.close()

    assert asyncio.run(sweep()) >= 1
    [attempt] = attempts(tenancy, interview_id)
    # Its browser never reported a connection: a failed connection, not a drop.
    assert attempt["end_reason"] == "error"
    assert "rtc_fake_1" in realtime.hung_up
