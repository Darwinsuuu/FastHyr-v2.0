"""INTV-001: an application that passes the résumé screen gets a personal interview plan in the
real worker; a plan that leaks a personal detail or misquotes the résumé is never stored, and
when the model can't give a usable plan the plain skills plan is stored instead. The sweeper
picks up passed applications whose plan job Redis lost."""

import asyncio
import json
import uuid
from datetime import timedelta
from typing import Any

from app.integrations.storage import SupabaseStorage
from app.jobs.queue import JobQueue, job_key
from app.jobs.system import requeue_stuck_work
from app.worker import shutdown, startup
from tests.integration.test_applications import CandidateUser, candidates, clean_resumes
from tests.integration.test_pipelines import sql
from tests.integration.test_screening import (
    SPANS,
    FailingAI,
    ScreeningAI,
    application,
    queue_name,
    resume_pdf,
    resume_text,
    submit,
    tenancy_app,
)
from tests.integration.worker import drain
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes", "queue_name", "tenancy_app"]

SKILLS = ["API design", "Debugging", "Testing"]


def plan(tenancy: Tenancy, application_id: uuid.UUID) -> Any:
    rows = sql(tenancy, "select * from interview_plans where application_id = $1", application_id)
    return rows[0] if rows else None


def test_a_passed_screen_gets_a_personal_plan(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    ai = ScreeningAI(SPANS)

    drain(redis_url, queue_name, storage=storage, ai=ai)

    row = plan(tenancy, application_id)
    assert (row["source"], row["model"], row["prompt_version"]) == (
        "ai",
        "stub",
        "interview_plan@v1",
    )
    topics = json.loads(row["topics"])
    assert [topic["kind"] for topic in topics] == [
        "warm_up",
        "skills",
        "skills",
        "skills",
        "candidate_questions",
    ]
    assert [skill for topic in topics for skill in topic["skills"]] == SKILLS
    # Seeds quote the redacted résumé, and the claims carry their quote too.
    text = resume_text(tenancy, application_id)["redacted_text"]
    assert topics[1]["seeds"][0]["resume_quote"] in text
    assert json.loads(row["claims_to_verify"])[0]["resume_quote"] in text

    # The model was given the redacted résumé, the pipeline's settings and the screen's claims,
    # never the candidate's name.
    [variables] = ai.planned
    assert variables["resume_text"] == text
    assert variables["skills_to_probe"] == "1. API design\n2. Debugging\n3. Testing"
    assert variables["screening_claims"] != "None"
    assert not any("Paolo" in value for value in variables.values())

    # Inviting is SCREEN-003's; the stage doesn't move here.
    assert application(tenancy, application_id)["stage"] == "processing_resume"

    # Running again changes nothing and asks the model nothing.
    asyncio.run(_enqueue(redis_url, queue_name, application_id))
    drain(redis_url, queue_name, storage=storage, ai=ai)
    assert len(ai.planned) == 1


def test_a_failed_screen_gets_no_plan(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    def miss(answer: dict[str, Any]) -> None:
        answer["must_haves"][0].update(met=False, evidence_quote="", strength=0)

    application_id = submit(tenancy, candidates[0], resume_pdf())
    ai = ScreeningAI(SPANS, miss)

    drain(redis_url, queue_name, storage=storage, ai=ai)

    assert ai.planned == []
    assert plan(tenancy, application_id) is None


def test_a_plan_with_a_personal_detail_falls_back_to_the_skills_plan(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    def leak(answer: dict[str, Any]) -> None:
        answer["topics"][1]["seeds"][0]["question"] = "What did you study at [SCHOOL]?"

    application_id = submit(tenancy, candidates[0], resume_pdf())
    ai = ScreeningAI(SPANS, plan_change=leak)

    drain(redis_url, queue_name, storage=storage, ai=ai)

    # Asked once more, then the plain plan: every skill covered, nothing from the résumé.
    assert len(ai.planned) == 2
    row = plan(tenancy, application_id)
    assert (row["source"], row["model"], row["prompt_version"]) == (
        "fallback",
        "none",
        "interview_plan_fallback@v1",
    )
    topics = json.loads(row["topics"])
    assert [skill for topic in topics for skill in topic["skills"]] == SKILLS
    assert "[SCHOOL]" not in row["topics"]
    assert all(seed["resume_quote"] == "" for topic in topics for seed in topic["seeds"])
    assert json.loads(row["claims_to_verify"]) == []


def test_a_model_that_keeps_failing_still_leaves_a_plan(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    drain(redis_url, queue_name, storage=storage, ai=ScreeningAI(SPANS))
    sql(tenancy, "delete from interview_plans where application_id = $1", application_id)

    asyncio.run(_enqueue(redis_url, queue_name, application_id))
    drain(redis_url, queue_name, storage=storage, ai=FailingAI([]))

    assert plan(tenancy, application_id)["source"] == "fallback"


def test_sweeper_requeues_passed_applications_without_a_plan(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    drain(redis_url, queue_name, storage=storage, ai=ScreeningAI(SPANS))
    # Redis lost the plan job, and the screen passed before the sweeper's cut-off.
    sql(tenancy, "delete from interview_plans where application_id = $1", application_id)
    asyncio.run(_forget(redis_url, queue_name, application_id))
    sql(
        tenancy,
        "update resume_assessments set screened_at = now() - $2::interval "
        "where application_id = $1",
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

    assert plan(tenancy, application_id)["source"] == "ai"


async def _enqueue(redis_url: str, queue_name: str, application_id: uuid.UUID) -> None:
    queue = JobQueue(redis_url, queue_name=queue_name)
    try:
        await queue.enqueue("plan_interview", application_id, key=application_id)
    finally:
        await queue.close()


async def _forget(redis_url: str, queue_name: str, application_id: uuid.UUID) -> None:
    queue = JobQueue(redis_url, queue_name=queue_name)
    pool = await queue.pool()
    try:
        await pool.delete(queue_name, f"arq:job:{job_key('plan_interview', application_id)}")
    finally:
        await queue.close()
