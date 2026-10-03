"""SCREEN-003: after the résumé screen, in the real worker, a candidate who passed is invited
with a personal interview link, and one who didn't moves to `resume_not_match` with a rejection
scheduled 2 business days later that carries a human-review link, unless the pipeline turned
that email off. Repeats change nothing, and the sweeper finishes a screen whose step was lost."""

import asyncio
import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_days import end_of_day_after, format_local, zone_of
from app.integrations.storage import SupabaseStorage
from app.jobs.queue import JobQueue
from app.jobs.system import requeue_stuck_work
from app.services import candidate_emails
from app.worker import shutdown, startup
from tests.integration.test_applications import CandidateUser, candidates, clean_resumes
from tests.integration.test_emails import FakeSender
from tests.integration.test_pipelines import db_run, sql
from tests.integration.test_screening import (
    SPANS,
    ScreeningAI,
    application,
    queue_name,
    resume_pdf,
    submit,
    tenancy_app,
)
from tests.integration.worker import drain
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes", "queue_name", "tenancy_app"]


def miss(answer: dict[str, Any]) -> None:
    """A must-have the résumé doesn't show: the screen fails."""
    answer["must_haves"][0].update(met=False, evidence_quote="", strength=0)


def rows(tenancy: Tenancy, table: str, application_id: uuid.UUID) -> list[Any]:
    return sql(tenancy, f"select * from {table} where application_id = $1", application_id)


def token_in(html: str, path: str) -> str:
    match = re.search(rf"/{path}/([A-Za-z0-9_-]+)", html)
    assert match, f"no /{path}/ link in the email"
    return match.group(1)


def sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def owner_sql(tenancy: Tenancy, query: str, *args: object) -> None:
    """For settings a published pipeline locks: written as the table owner, triggers off."""

    async def main() -> None:
        connection = await asyncpg.connect(tenancy.supabase.owner_database_url)
        try:
            async with connection.transaction():
                await connection.execute("set local session_replication_role = replica")
                await connection.execute(query, *args)
        finally:
            await connection.close()

    asyncio.run(main())


def sweep(redis_url: str, queue_name: str) -> int:
    async def main() -> int:
        queue = JobQueue(redis_url, queue_name=queue_name)
        ctx: dict[str, Any] = {"redis": await queue.pool(), "queue_name": queue_name}
        await startup(ctx)
        try:
            requeued: int = await requeue_stuck_work(ctx)
            return requeued
        finally:
            await shutdown(ctx)
            await queue.close()

    return asyncio.run(main())


def test_a_passed_screen_invites_with_a_personal_link(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    sql(
        tenancy,
        "update company_profiles set timezone = 'Asia/Manila' where workspace_id = $1",
        tenancy.workspace("a").id,
    )
    sender = FakeSender()

    drain(redis_url, queue_name, storage=storage, ai=ScreeningAI(SPANS), email_sender=sender)

    row = application(tenancy, application_id)
    assert row["stage"] == "invited"
    [interview] = rows(tenancy, "interviews", application_id)
    [pipeline] = sql(tenancy, "select * from pipelines where id = $1", row["pipeline_id"])
    assert (interview["status"], interview["format"]) == (
        "not_started",
        pipeline["interview_format"],
    )
    manila = zone_of("Asia/Manila")
    assert interview["expires_at"] == end_of_day_after(
        interview["invited_at"], pipeline["link_expiry_days"], manila
    )

    # The invitation went out at once, with a link only this candidate has.
    [email] = rows(tenancy, "email_messages", application_id)
    assert (email["template_key"], email["status"], email["application_stage"]) == (
        "interview_invitation",
        "sent",
        "invited",
    )
    [sent] = sender.sent
    assert sent.to == candidates[0].email
    token = token_in(sent.html, "interview")
    assert sha256(token) == interview["token_hash"]
    assert format_local(interview["expires_at"], manila) in sent.text
    assert "[Interview." not in sent.text

    # A repeated plan job (or sweep) invites no one twice.
    async def enqueue() -> None:
        queue = JobQueue(redis_url, queue_name=queue_name)
        try:
            await queue.enqueue("plan_interview", application_id, key=application_id)
        finally:
            await queue.close()

    asyncio.run(enqueue())
    drain(redis_url, queue_name, storage=storage, ai=ScreeningAI(SPANS), email_sender=sender)
    assert len(rows(tenancy, "interviews", application_id)) == 1
    assert len(sender.sent) == 1


def test_a_failed_screen_schedules_a_rejection_with_a_review_link(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    sender = FakeSender()

    drain(redis_url, queue_name, storage=storage, ai=ScreeningAI(SPANS, miss), email_sender=sender)

    assert application(tenancy, application_id)["stage"] == "resume_not_match"
    assert rows(tenancy, "interviews", application_id) == []
    [assessment] = rows(tenancy, "resume_assessments", application_id)
    workspace_id = tenancy.workspace("a").id

    async def two_business_days_later(session: AsyncSession) -> datetime:
        return await candidate_emails.send_at(session, workspace_id, assessment["screened_at"], 2)

    due = db_run(tenancy, two_business_days_later)
    [email] = rows(tenancy, "email_messages", application_id)
    assert (email["template_key"], email["status"], email["scheduled_for"]) == (
        "reject_resume",
        "scheduled",
        due,
    )
    assert sender.sent == []

    # The review link is the candidate's own and works for 30 days after the email.
    [link] = rows(tenancy, "review_links", application_id)
    assert link["decision_type"] == "resume"
    assert sha256(token_in(email["html_rendered"], "review-request")) == link["token_hash"]
    assert link["expires_at"] == due + timedelta(days=30)


def test_no_rejection_email_when_the_pipeline_turned_it_off(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    owner_sql(
        tenancy,
        "update pipelines set email_resume_reject = false "
        "where id = (select pipeline_id from applications where id = $1)",
        application_id,
    )

    drain(
        redis_url,
        queue_name,
        storage=storage,
        ai=ScreeningAI(SPANS, miss),
        email_sender=FakeSender(),
    )

    assert application(tenancy, application_id)["stage"] == "resume_not_match"
    assert rows(tenancy, "email_messages", application_id) == []
    assert rows(tenancy, "review_links", application_id) == []


def test_sweeper_finishes_a_screen_whose_next_step_was_lost(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    application_id = submit(tenancy, candidates[0], resume_pdf())
    drain(
        redis_url,
        queue_name,
        storage=storage,
        ai=ScreeningAI(SPANS, miss),
        email_sender=FakeSender(),
    )
    # As if the worker stopped after the screen: no stage move, no email, screened a while ago.
    for table in ("email_messages", "review_links"):
        sql(tenancy, f"delete from {table} where application_id = $1", application_id)
    sql(
        tenancy, "update applications set stage = 'processing_resume' where id = $1", application_id
    )
    sql(
        tenancy,
        "update resume_assessments set screened_at = $2 where application_id = $1",
        application_id,
        datetime.now(UTC) - timedelta(minutes=15),
    )

    assert sweep(redis_url, queue_name) >= 1
    ai = ScreeningAI(SPANS, miss)
    drain(redis_url, queue_name, storage=storage, ai=ai, email_sender=FakeSender())

    assert application(tenancy, application_id)["stage"] == "resume_not_match"
    assert [row["template_key"] for row in rows(tenancy, "email_messages", application_id)] == [
        "reject_resume"
    ]
    # The screen itself wasn't run again.
    assert ai.assessed == []


def test_a_fallback_plan_still_invites(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    def leak(answer: dict[str, Any]) -> None:
        answer["topics"][1]["seeds"][0]["question"] = "What did you study at [SCHOOL]?"

    application_id = submit(tenancy, candidates[0], resume_pdf())

    drain(
        redis_url,
        queue_name,
        storage=storage,
        ai=ScreeningAI(SPANS, plan_change=leak),
        email_sender=FakeSender(),
    )

    assert rows(tenancy, "interview_plans", application_id)[0]["source"] == "fallback"
    assert application(tenancy, application_id)["stage"] == "invited"
    assert len(rows(tenancy, "interviews", application_id)) == 1
    # Queued without a worker queue: the dispatch cron sends it on its next tick.
    [email] = rows(tenancy, "email_messages", application_id)
    assert (email["template_key"], email["status"]) == ("interview_invitation", "scheduled")
