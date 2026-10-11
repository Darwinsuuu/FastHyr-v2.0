"""MSG-003: candidate emails are rendered from the workspace's template and sent at their time in
the workspace's time zone; one whose application has moved to another stage is cancelled, never
sent; scheduling again (a retried job) never adds a second copy; a hard bounce marks the
candidate's address undeliverable."""

import asyncio
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.emails.candidate import MissingParameterError
from app.emails.defaults import TemplateKey
from app.emails.render import RenderedEmail
from app.integrations.storage import SupabaseStorage
from app.jobs.queue import JobQueue
from app.jobs.system import dispatch_scheduled_emails
from app.main import create_app
from app.services import applications, candidate_emails, emails
from app.worker import shutdown, startup
from tests.integration.test_applications import CandidateUser, candidates, clean_resumes
from tests.integration.test_emails import SECRET, FakeSender, post_webhook
from tests.integration.test_pipelines import db_run, sql
from tests.integration.test_screening import resume_pdf, submit
from tests.integration.worker import drain
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes"]

SETTINGS = Settings(site_url="https://fasthyr.test", api_url="https://api.fasthyr.test")
REVIEW = {"Review.link": "https://fasthyr.test/review-request/tok"}
MANILA_FRIDAY = datetime(2026, 10, 2, 2, 0, tzinfo=UTC)  # Fri 10:00 in Manila


@pytest.fixture
def screening_queue() -> str:
    """Applying queues a résumé screen; it goes to its own queue so the drains here only run
    the email jobs."""
    return f"arq:test:{uuid.uuid4().hex[:12]}"


@pytest.fixture
def queue_name() -> str:
    return f"arq:test:{uuid.uuid4().hex[:12]}"


@pytest.fixture
def tenancy_app(
    storage: SupabaseStorage, redis_url: str, screening_queue: str
) -> Iterator[FastAPI]:
    settings = Settings(resend_webhook_secret=SECRET)
    yield create_app(
        settings=settings,
        storage=storage,
        job_queue=JobQueue(redis_url, queue_name=screening_queue),
    )


def apply(tenancy: Tenancy, candidate: CandidateUser) -> uuid.UUID:
    application_id = submit(tenancy, candidate, resume_pdf())
    sql(
        tenancy,
        "update company_profiles set timezone = 'Asia/Manila' where workspace_id = $1",
        tenancy.workspace("a").id,
    )
    return application_id


def schedule(
    tenancy: Tenancy,
    application_id: uuid.UUID,
    key: TemplateKey = TemplateKey.REJECT_RESUME,
    *,
    at: datetime | None = None,
    values: dict[str, str] | None = None,
    stage: str | None = "resume_not_match",
) -> candidate_emails.ScheduledEmail:
    workspace_id = tenancy.workspace("a").id

    async def work(session: AsyncSession) -> candidate_emails.ScheduledEmail:
        if stage:
            await applications.move_stage(session, workspace_id, application_id, stage)
        result = await candidate_emails.schedule(
            session,
            SETTINGS,
            workspace_id=workspace_id,
            application_id=application_id,
            key=key,
            at=at,
            values=REVIEW if values is None else values,
        )
        await session.commit()
        return result

    return db_run(tenancy, work)


def move(tenancy: Tenancy, application_id: uuid.UUID, stage: str) -> None:
    async def work(session: AsyncSession) -> None:
        await applications.move_stage(session, tenancy.workspace("a").id, application_id, stage)
        await session.commit()

    db_run(tenancy, work)


def rows(tenancy: Tenancy, application_id: uuid.UUID) -> list[Any]:
    return sql(
        tenancy,
        "select * from email_messages where application_id = $1 order by created_at",
        application_id,
    )


def dispatch(redis_url: str, queue_name: str) -> int:
    async def main() -> int:
        queue = JobQueue(redis_url, queue_name=queue_name)
        ctx: dict[str, Any] = {
            "redis": await queue.pool(),
            "queue_name": queue_name,
            "email_sender": None,
        }
        await startup(ctx)
        try:
            queued: int = await dispatch_scheduled_emails(ctx)
            return queued
        finally:
            await shutdown(ctx)
            await queue.close()

    return asyncio.run(main())


def make_due(tenancy: Tenancy, application_id: uuid.UUID) -> None:
    sql(
        tenancy,
        "update email_messages set scheduled_for = now() - interval '1 minute' "
        "where application_id = $1",
        application_id,
    )


def test_a_rejection_goes_out_two_business_days_later(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    application_id = apply(tenancy, candidates[0])
    workspace_id = tenancy.workspace("a").id

    async def tuesday(session: AsyncSession) -> datetime:
        return await candidate_emails.send_at(session, workspace_id, MANILA_FRIDAY, 2)

    send_at = db_run(tenancy, tuesday)
    assert send_at == datetime(2026, 10, 6, 2, 0, tzinfo=UTC)  # Tue 10:00 in Manila

    later = datetime.now(UTC) + timedelta(days=2)
    first = schedule(tenancy, application_id, at=later)
    # A retried job schedules nothing new.
    again = schedule(tenancy, application_id, at=later, stage=None)
    assert first.created and not again.created
    assert again.message.id == first.message.id
    [row] = rows(tenancy, application_id)
    assert (row["status"], row["template_key"], row["application_stage"]) == (
        "scheduled",
        "reject_resume",
        "resume_not_match",
    )

    # Not due yet: the cron leaves it in Postgres.
    assert dispatch(redis_url, queue_name) == 0
    make_due(tenancy, application_id)
    assert dispatch(redis_url, queue_name) >= 1
    sender = FakeSender()
    drain(redis_url, queue_name, email_sender=sender)

    [sent] = [email for email in sender.sent if email.id == first.message.id]
    assert sent.to == candidates[0].email
    assert sent.from_name.endswith(" via FastHyr")
    assert "Hi Paolo," in sent.text
    assert "Backend Engineer" in sent.text
    assert "https://fasthyr.test/review-request/tok" in sent.html
    assert rows(tenancy, application_id)[0]["status"] == "sent"


def test_a_rejection_is_cancelled_when_the_screen_is_overridden(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    application_id = apply(tenancy, candidates[0])
    rejection = schedule(tenancy, application_id)  # due now

    move(tenancy, application_id, "invited")

    [row] = rows(tenancy, application_id)
    assert (row["status"], row["cancel_reason"]) == ("cancelled", "stage_changed")
    dispatch(redis_url, queue_name)
    sender = FakeSender()
    drain(redis_url, queue_name, email_sender=sender)
    assert all(email.id != rejection.message.id for email in sender.sent)

    # The new stage's email can be scheduled, and a later rejection isn't blocked by the
    # cancelled one.
    invitation = schedule(
        tenancy,
        application_id,
        TemplateKey.INTERVIEW_INVITATION,
        values={"Interview.link": "https://fasthyr.test/i/x", "Interview.expiry": "Fri"},
        stage=None,
    )
    assert invitation.created
    assert schedule(tenancy, application_id).created


def test_an_email_whose_stage_moved_is_never_sent(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    application_id = apply(tenancy, candidates[0])
    rejection = schedule(tenancy, application_id)
    # A stage change that skipped move_stage(): the send job still won't send.
    sql(tenancy, "update applications set stage = 'invited' where id = $1", application_id)

    async def enqueue() -> None:
        queue = JobQueue(redis_url, queue_name=queue_name)
        try:
            await emails.enqueue(queue, rejection.message)
        finally:
            await queue.close()

    asyncio.run(enqueue())
    sender = FakeSender()
    drain(redis_url, queue_name, email_sender=sender)

    assert sender.sent == []
    [row] = rows(tenancy, application_id)
    assert (row["status"], row["cancel_reason"]) == ("cancelled", "stage_changed")


def test_a_rejection_without_its_review_link_is_refused(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    application_id = apply(tenancy, candidates[0])

    with pytest.raises(MissingParameterError, match=r"Review\.link"):
        schedule(tenancy, application_id, values={})
    assert rows(tenancy, application_id) == []


def test_a_hard_bounce_marks_the_candidate_undeliverable(
    tenancy: Tenancy, candidates: list[CandidateUser], redis_url: str, queue_name: str
) -> None:
    soft_id = apply(tenancy, candidates[0])
    hard_id = apply(tenancy, candidates[1])
    for application_id in (soft_id, hard_id):
        schedule(tenancy, application_id)
    dispatch(redis_url, queue_name)
    drain(redis_url, queue_name, email_sender=FakeSender())

    def bounce(application_id: uuid.UUID, kind: str) -> None:
        provider_id = rows(tenancy, application_id)[0]["provider_message_id"]
        event = {
            "type": "email.bounced",
            "data": {"email_id": provider_id, "bounce": {"type": kind}},
        }
        assert post_webhook(tenancy, event) == 204

    bounce(soft_id, "Transient")
    bounce(hard_id, "Permanent")

    def undeliverable(application_id: uuid.UUID) -> Any:
        return sql(
            tenancy,
            "select c.email_undeliverable_at from candidates c "
            "join applications a on a.candidate_id = c.id where a.id = $1",
            application_id,
        )[0]["email_undeliverable_at"]

    assert rows(tenancy, soft_id)[0]["status"] == "bounced"
    assert undeliverable(soft_id) is None
    assert undeliverable(hard_id) is not None


def test_many_unique_emails_on_one_connection(tenancy: Tenancy) -> None:
    """Re-invite all queues one unique email per candidate on one connection. Past five inserts
    asyncpg's prepared statement takes a generic plan, and the dedupe insert must still find its
    partial index (PIPE-007 found it failing there)."""
    workspace_id = tenancy.workspace("a").id
    keys = [f"pipe-007-test:{uuid.uuid4()}" for _ in range(8)]

    async def work(session: AsyncSession) -> list[bool]:
        created = []
        for key in keys:
            _, added = await emails.queue_unique_email(
                session,
                dedupe_key=key,
                application_stage=None,
                workspace_id=workspace_id,
                template_key="interview_invitation",
                to_email="candidate@example.test",
                from_name="Acme",
                email=RenderedEmail(subject="Hello", html="<p>Hi</p>", text="Hi"),
            )
            created.append(added)
        # A repeat of the last one is still caught.
        _, again = await emails.queue_unique_email(
            session,
            dedupe_key=keys[-1],
            application_stage=None,
            workspace_id=workspace_id,
            template_key="interview_invitation",
            to_email="candidate@example.test",
            from_name="Acme",
            email=RenderedEmail(subject="Hello", html="<p>Hi</p>", text="Hi"),
        )
        await session.rollback()
        return [*created, again]

    assert db_run(tenancy, work) == [True] * 8 + [False]
