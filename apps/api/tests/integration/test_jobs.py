"""FND-008: a job queued from an endpoint runs in the worker with visible progress, a failing
job retries with backoff then records its error, cancelling stops it, the sweeper re-queues
work Redis lost, and only the member who started a job can see it."""

import asyncio
import uuid
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import asyncpg
import pytest
from fastapi import FastAPI

from app.core.context import Role
from app.jobs.queue import JobQueue
from app.jobs.system import requeue_stuck_work
from app.main import create_app
from app.worker import shutdown, startup
from tests.conftest import Supabase
from tests.integration.worker import drain
from tests.tenancy.harness import Tenancy


@pytest.fixture
def queue_name() -> str:
    """Each test gets its own queue, so a local `make worker` never picks up test jobs."""
    return f"arq:test:{uuid.uuid4().hex[:12]}"


@pytest.fixture
def tenancy_app(redis_url: str, queue_name: str) -> Iterator[FastAPI]:
    yield create_app(job_queue=JobQueue(redis_url, queue_name=queue_name))


def start_sample(tenancy: Tenancy, **body: Any) -> dict[str, Any]:
    response = tenancy.client("a", Role.RECRUITER).post(
        "/v1/dev/sample-job", json={"step_seconds": 0, **body}
    )
    assert response.status_code == 202, response.text
    job: dict[str, Any] = response.json()
    assert job["status"] == "queued"
    return job


def get_job(tenancy: Tenancy, job_id: str) -> dict[str, Any]:
    response = tenancy.client("a", Role.RECRUITER).get(f"/v1/jobs/{job_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_job_queued_from_an_endpoint_runs_in_the_worker(
    tenancy: Tenancy, redis_url: str, queue_name: str
) -> None:
    job = start_sample(tenancy, steps=3)

    drain(redis_url, queue_name)

    done = get_job(tenancy, job["id"])
    assert done["status"] == "done"
    assert (done["step"], done["steps_total"]) == (3, 3)
    assert done["finished_at"] is not None


def test_failing_job_retries_then_recovers(
    tenancy: Tenancy, redis_url: str, queue_name: str
) -> None:
    job = start_sample(tenancy, steps=1, fail_tries=1)

    drain(redis_url, queue_name)

    assert get_job(tenancy, job["id"])["status"] == "done"


def test_job_failing_every_try_records_its_error(
    tenancy: Tenancy, redis_url: str, queue_name: str
) -> None:
    job = start_sample(tenancy, steps=1, fail_tries=10)

    drain(redis_url, queue_name)  # three tries, 1 s then 2 s apart

    failed = get_job(tenancy, job["id"])
    assert failed["status"] == "failed"
    assert failed["error"] == "job_failed"
    assert failed["finished_at"] is not None


def test_cancelled_job_does_not_run(tenancy: Tenancy, redis_url: str, queue_name: str) -> None:
    job = start_sample(tenancy, steps=2)

    response = tenancy.client("a", Role.RECRUITER).delete(f"/v1/jobs/{job['id']}")
    assert response.status_code == 204
    drain(redis_url, queue_name)

    cancelled = get_job(tenancy, job["id"])
    assert cancelled["status"] == "cancelled"
    assert cancelled["step"] == 0


def test_enqueue_is_idempotent_per_key(redis_url: str, queue_name: str) -> None:
    async def enqueue_twice() -> list[bool]:
        queue = JobQueue(redis_url, queue_name=queue_name)
        try:
            key = uuid.uuid4()
            first = await queue.enqueue("sample_report_job", key, key, key=key)
            second = await queue.enqueue("sample_report_job", key, key, key=key)
            pool = await queue.pool()
            await pool.delete(queue_name)
            return [first, second]
        finally:
            await queue.close()

    assert asyncio.run(enqueue_twice()) == [True, False]


def test_sweeper_requeues_jobs_redis_lost(
    tenancy: Tenancy, supabase: Supabase, redis_url: str, queue_name: str
) -> None:
    workspace = tenancy.workspace("a")
    member = tenancy.member("a", Role.RECRUITER)

    async def insert_lost_job() -> uuid.UUID:
        """A job row that never reached Redis, created before the sweeper's cut-off."""
        connection = await asyncpg.connect(supabase.database_url)
        try:
            job_id: uuid.UUID = await connection.fetchval(
                "insert into report_jobs (workspace_id, requested_by, kind, params, created_at) "
                "values ($1, $2, 'sample', '{\"step_seconds\": 0}', now() - $3::interval) "
                "returning id",
                workspace.id,
                member.user_id,
                timedelta(minutes=15),
            )
            return job_id
        finally:
            await connection.close()

    async def sweep() -> int:
        ctx: dict[str, Any] = {"redis": None, "queue_name": queue_name}
        queue = JobQueue(redis_url, queue_name=queue_name)
        ctx["redis"] = await queue.pool()
        await startup(ctx)
        try:
            requeued: int = await requeue_stuck_work(ctx)
            return requeued
        finally:
            await shutdown(ctx)
            await queue.close()

    job_id = asyncio.run(insert_lost_job())
    assert asyncio.run(sweep()) >= 1
    drain(redis_url, queue_name)

    assert get_job(tenancy, str(job_id))["status"] == "done"


def test_only_the_member_who_started_a_job_sees_it(tenancy: Tenancy) -> None:
    job = start_sample(tenancy)  # nothing runs it; it stays queued
    url = f"/v1/jobs/{job['id']}"

    tenancy.assert_hidden_from_other_workspace("GET", url)
    tenancy.assert_hidden_from_other_workspace("DELETE", url)
    for role in (Role.ADMIN, Role.HIRING_MANAGER):
        response = tenancy.client("a", role).get(url)
        assert response.status_code == 404, role
        assert tenancy.client("a", role).delete(url).status_code == 404, role
    assert get_job(tenancy, job["id"])["status"] == "queued"
