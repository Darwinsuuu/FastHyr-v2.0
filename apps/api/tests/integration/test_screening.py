"""SCREEN-001: the screening job turns an applicant's PDF into redacted text in the real worker,
an unreadable résumé waits for a person instead of being rejected, a failed model answer marks
the résumé as an error, and the sweeper picks up applications Redis lost."""

import asyncio
import json
import uuid
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from app.ai.client import AIOutputError
from app.integrations.storage import SupabaseStorage
from app.jobs.queue import JobQueue, job_key
from app.jobs.system import requeue_stuck_work
from app.main import create_app
from app.worker import shutdown, startup
from tests.integration.test_applications import (
    CandidateUser,
    candidates,
    clean_resumes,
    form,
    upload,
)
from tests.integration.test_pipelines import grant, ok, pipeline_in, sql
from tests.integration.worker import drain
from tests.pdf_fixtures import plain_pdf, text_pdf
from tests.tenancy.harness import Tenancy
from tests.unit.test_resume_redaction import StubAI

__all__ = ["candidates", "clean_resumes"]  # fixtures used from test_applications

RESUME = [
    "Paolo Reyes",
    "Senior Backend Engineer",
    "paolo.reyes@example.com | +63 917 123 4567",
    "Address: 12 Mabini Street, Quezon City",
    "Experience",
    "Senior Backend Engineer, Lakbay Logistics, March 2019 - present",
    "Moved the order service to Python services on Kubernetes, cutting p95 latency to 180 ms.",
    "Designed PostgreSQL partitioning for 1.2 billion shipment events.",
    "Education",
    "University of the Philippines Diliman",
    "BS Computer Science, 2014",
    "Skills",
    "Python, Go, PostgreSQL, Redis, Kafka, Kubernetes",
]
SPANS = [{"kind": "school", "text": "University of the Philippines Diliman"}]


class FailingAI(StubAI):
    async def structured[T: BaseModel](self, **kwargs: Any) -> T:
        raise AIOutputError()


@pytest.fixture
def queue_name() -> str:
    return f"arq:test:{uuid.uuid4().hex[:12]}"


@pytest.fixture
def tenancy_app(storage: SupabaseStorage, redis_url: str, queue_name: str) -> Iterator[FastAPI]:
    yield create_app(storage=storage, job_queue=JobQueue(redis_url, queue_name=queue_name))


def resume_pdf() -> bytes:
    return text_pdf([(72, 72 + index * 16, line) for index, line in enumerate(RESUME)])


def submit(tenancy: Tenancy, candidate: CandidateUser, data: bytes) -> uuid.UUID:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    upload_id = upload(tenancy, candidate, pipeline["id"], data)
    response = tenancy.anonymous().post(
        "/v1/candidate/applications",
        json=form(pipeline["id"], upload_id),
        headers=candidate.headers,
    )
    return uuid.UUID(ok(response, 201)["application_id"])


def application(tenancy: Tenancy, application_id: uuid.UUID) -> Any:
    return sql(tenancy, "select * from applications where id = $1", application_id)[0]


def resume_text(tenancy: Tenancy, application_id: uuid.UUID) -> Any:
    rows = sql(tenancy, "select * from resume_texts where application_id = $1", application_id)
    return rows[0] if rows else None


def test_a_readable_resume_is_stored_redacted(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    ai = StubAI(SPANS)

    drain(redis_url, queue_name, storage=storage, ai=ai)

    row = resume_text(tenancy, application_id)
    text: str = row["redacted_text"]
    for detail in ("Paolo", "Reyes", "paolo.reyes@", "917 123", "Mabini", "Diliman", "2014"):
        assert detail not in text, detail
    for evidence in ("March 2019 - present", "PostgreSQL partitioning", "Kubernetes"):
        assert evidence in text, evidence
    assert "Paolo" not in ai.seen[0]
    assert row["redaction_version"] == "rules@v1+resume_redaction@v1"
    assert json.loads(row["masked"])["school"] == 1
    assert row["pages"] == 1
    # Scoring (SCREEN-002) continues from here; the application is still waiting for it.
    saved = application(tenancy, application_id)
    assert (saved["stage"], saved["resume_status"]) == ("processing_resume", "pending")

    # Running again changes nothing and asks the model nothing.
    asyncio.run(_enqueue(redis_url, queue_name, application_id))
    drain(redis_url, queue_name, storage=storage, ai=ai)
    assert len(ai.seen) == 1


def test_an_unreadable_resume_waits_for_a_person(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    # One word of text, like a scanned résumé.
    application_id = submit(tenancy, candidates[0], plain_pdf())
    ai = StubAI(SPANS)

    drain(redis_url, queue_name, storage=storage, ai=ai)

    saved = application(tenancy, application_id)
    assert (saved["stage"], saved["resume_status"]) == ("processing_resume", "unreadable")
    assert saved["rejected_at"] is None
    assert resume_text(tenancy, application_id) is None
    assert ai.seen == []


def test_an_invalid_model_answer_marks_the_resume_as_an_error(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())

    drain(redis_url, queue_name, storage=storage, ai=FailingAI([]))

    saved = application(tenancy, application_id)
    assert (saved["stage"], saved["resume_status"]) == ("processing_resume", "error")
    assert resume_text(tenancy, application_id) is None


def test_sweeper_requeues_applications_redis_lost(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    # Redis lost the job, and the application has waited past the sweeper's cut-off.
    asyncio.run(_forget(redis_url, queue_name, application_id))
    sql(
        tenancy,
        "update applications set applied_at = now() - $2::interval where id = $1",
        application_id,
        timedelta(minutes=15),
    )

    async def sweep() -> int:
        queue = JobQueue(redis_url, queue_name=queue_name)
        ctx: dict[str, Any] = {"redis": await queue.pool(), "queue_name": queue_name}
        await startup(ctx)
        try:
            requeued: int = await requeue_stuck_work(ctx)
            return requeued
        finally:
            await shutdown(ctx)
            await queue.close()

    assert asyncio.run(sweep()) >= 1
    drain(redis_url, queue_name, storage=storage, ai=StubAI(SPANS))

    assert resume_text(tenancy, application_id) is not None


async def _enqueue(redis_url: str, queue_name: str, application_id: uuid.UUID) -> None:
    queue = JobQueue(redis_url, queue_name=queue_name)
    try:
        await queue.enqueue("screen_resume", application_id, key=application_id)
    finally:
        await queue.close()


async def _forget(redis_url: str, queue_name: str, application_id: uuid.UUID) -> None:
    queue = JobQueue(redis_url, queue_name=queue_name)
    pool = await queue.pool()
    try:
        await pool.delete(queue_name, f"arq:job:{job_key('screen_resume', application_id)}")
    finally:
        await queue.close()
