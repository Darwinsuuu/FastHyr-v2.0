"""SCREEN-001 and SCREEN-002: the screening job turns an applicant's PDF into redacted text and
then a fit score and decision in the real worker, logged to ai_decisions; an unreadable résumé
waits for a person instead of being rejected, a failed model answer marks the résumé as an
error, and the sweeper picks up applications Redis lost."""

import asyncio
import json
import uuid
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from app.ai import fakes
from app.ai.client import AIOutputError
from app.ai.prompts import Prompt
from app.ai.schemas.resume_assessment import ResumeAssessment
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


class ScreeningAI(StubAI):
    """Answers redaction with `spans` and the assessment with `change(answer)` applied to the
    fake answer for the prompt (every must-have met, quoting the résumé)."""

    def __init__(self, spans: list[dict[str, str]], change: Any = None) -> None:
        super().__init__(spans)
        self.change = change
        self.assessed: list[dict[str, str]] = []

    async def structured[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt: Prompt,
        variables: dict[str, str],
        schema: type[T],
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        temperature: float | None = None,
    ) -> T:
        if schema is not ResumeAssessment:
            return await super().structured(
                purpose=purpose, prompt=prompt, variables=variables, schema=schema
            )
        self.assessed.append(variables)
        answer = fakes.resume_assessment(variables)
        if self.change:
            self.change(answer)
        return schema.model_validate(answer)


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


def assessment(tenancy: Tenancy, application_id: uuid.UUID) -> Any:
    rows = sql(
        tenancy, "select * from resume_assessments where application_id = $1", application_id
    )
    return rows[0] if rows else None


def decisions(tenancy: Tenancy, application_id: uuid.UUID) -> list[Any]:
    return sql(tenancy, "select * from ai_decisions where application_id = $1", application_id)


def test_a_readable_resume_is_stored_redacted(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    ai = ScreeningAI(SPANS)

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
    # The assessment read the same redacted text and nothing else about the person.
    assert ai.assessed[0]["resume_text"] == text
    assert "Backend Engineer" in ai.assessed[0]["job_title"]

    # Running again changes nothing and asks the model nothing.
    asyncio.run(_enqueue(redis_url, queue_name, application_id))
    drain(redis_url, queue_name, storage=storage, ai=ai)
    assert (len(ai.seen), len(ai.assessed)) == (1, 1)
    assert len(decisions(tenancy, application_id)) == 1


def test_a_passing_resume_is_scored_and_logged(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())

    drain(redis_url, queue_name, storage=storage, ai=ScreeningAI(SPANS))

    row = assessment(tenancy, application_id)
    # Three must-haves met, no nice-to-haves (their 20% redistributed), experience 80, skill
    # depth 75: 50 + 25 + 14.06 = 89.
    assert (row["score"], row["passed"], row["pass_bar"]) == (89, True, 60)
    breakdown = json.loads(row["breakdown"])
    assert set(breakdown) == {"must_haves", "experience", "skill_depth"}
    musts = json.loads(row["must_have_results"])
    assert [must["criterion"] for must in musts] == ["Python", "SQL", "REST APIs"]
    assert all(must["evidence_quote"] for must in musts)
    assert row["prompt_version"] == "resume_assessment@v1"
    assert row["model"] == "stub"
    assert row["duration_ms"] >= 0

    [decision] = decisions(tenancy, application_id)
    assert (decision["type"], decision["outcome"], decision["score"], decision["threshold"]) == (
        "resume_screen",
        "pass",
        89,
        60,
    )
    assert decision["input_ref"].startswith(f"resume_texts:{application_id}@")
    # The decision log holds numbers and flags, never résumé text.
    assert "evidence_quote" not in decision["output"]

    # SCREEN-003 acts on the decision; until then the stage doesn't move.
    saved = application(tenancy, application_id)
    assert (saved["stage"], saved["resume_status"]) == ("processing_resume", "done")


def test_a_missing_must_have_fails_the_screen_whatever_the_score(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    def miss_sql(answer: dict[str, Any]) -> None:
        answer["must_haves"][1].update(met=False, evidence_quote="", strength=0)
        answer["experience"]["score"] = 100
        answer["skill_depth"]["score"] = 100

    application_id = submit(tenancy, candidates[0], resume_pdf())

    drain(redis_url, queue_name, storage=storage, ai=ScreeningAI(SPANS, miss_sql))

    row = assessment(tenancy, application_id)
    # 33.3 + 31.25 + 18.75 = 83, above the bar, but SQL isn't shown.
    assert (row["score"], row["passed"]) == (83, False)
    assert [decision["outcome"] for decision in decisions(tenancy, application_id)] == ["fail"]
    saved = application(tenancy, application_id)
    assert (saved["stage"], saved["resume_status"], saved["rejected_at"]) == (
        "processing_resume",
        "done",
        None,
    )


def test_invented_evidence_is_never_used(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    def invent(answer: dict[str, Any]) -> None:
        answer["must_haves"][0]["evidence_quote"] = "Ten years of Python at Google"

    application_id = submit(tenancy, candidates[0], resume_pdf())
    ai = ScreeningAI(SPANS, invent)

    drain(redis_url, queue_name, storage=storage, ai=ai)

    # Asked once more, then the résumé needs a person; the redacted text is kept.
    assert len(ai.assessed) == 2
    saved = application(tenancy, application_id)
    assert (saved["stage"], saved["resume_status"]) == ("processing_resume", "error")
    assert assessment(tenancy, application_id) is None
    assert decisions(tenancy, application_id) == []
    assert resume_text(tenancy, application_id) is not None


def test_ai_decisions_are_append_only(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    drain(redis_url, queue_name, storage=storage, ai=ScreeningAI(SPANS))

    for statement in (
        "update ai_decisions set outcome = 'pass' where application_id = $1",
        "delete from ai_decisions where application_id = $1",
    ):
        with pytest.raises(Exception, match=r"permission denied|append-only"):
            sql(tenancy, statement, application_id)


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
    drain(redis_url, queue_name, storage=storage, ai=ScreeningAI(SPANS))

    assert resume_text(tenancy, application_id) is not None
    assert assessment(tenancy, application_id) is not None


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
