"""FND-010: an email is logged with the change that causes it, sent by the worker through the
provider, retried on outages, failed without retries when rejected, re-queued when Redis lost
it, and moved to delivered or bounced by signed Resend webhooks."""

import asyncio
import json
import time
import uuid
from collections.abc import Iterator
from typing import Any

import asyncpg
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.core.context import Role
from app.integrations.email import EmailRejectedError, EmailUnavailableError, OutgoingEmail
from app.integrations.resend_webhook import sign
from app.jobs.queue import JobQueue
from app.jobs.system import requeue_stuck_work
from app.main import create_app
from app.worker import shutdown, startup
from tests.conftest import Supabase
from tests.integration.worker import drain
from tests.tenancy.harness import Tenancy

SECRET = "whsec_dGVzdC1zZWNyZXQtZm9yLWZhc3RoeXI="


class FakeSender:
    """Records sends; fails the first `failures` sends with `error`."""

    def __init__(self, failures: int = 0, error: Exception | None = None) -> None:
        self.sent: list[OutgoingEmail] = []
        self.failures = failures
        self.error = error or EmailUnavailableError()

    async def send(self, email: OutgoingEmail) -> str:
        if self.failures > 0:
            self.failures -= 1
            raise self.error
        self.sent.append(email)
        return f"re_{email.id.hex}"


@pytest.fixture
def queue_name() -> str:
    return f"arq:test:{uuid.uuid4().hex[:12]}"


@pytest.fixture
def tenancy_app(redis_url: str, queue_name: str) -> Iterator[FastAPI]:
    settings = Settings(resend_webhook_secret=SECRET, site_url="https://fasthyr.test")
    yield create_app(settings=settings, job_queue=JobQueue(redis_url, queue_name=queue_name))


async def _fetch(supabase: Supabase, query: str, *args: object) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(supabase.database_url)
    try:
        rows: list[asyncpg.Record] = await connection.fetch(query, *args)
        return rows
    finally:
        await connection.close()


def email_rows(supabase: Supabase, to_email: str) -> list[asyncpg.Record]:
    return asyncio.run(
        _fetch(
            supabase,
            "select id, status, error, provider_message_id, template_key, from_name "
            "from email_messages where to_email = $1 order by created_at",
            to_email,
        )
    )


def invite(tenancy: Tenancy) -> str:
    email = f"invitee-{uuid.uuid4().hex[:10]}@example.com"
    response = tenancy.client("a", Role.ADMIN).post(
        "/v1/invites", json={"email": email, "role": "recruiter", "department_ids": []}
    )
    assert response.status_code == 201, response.text
    return email


def test_invite_email_is_sent_by_the_worker(
    tenancy: Tenancy, supabase: Supabase, redis_url: str, queue_name: str
) -> None:
    email = invite(tenancy)
    [queued] = email_rows(supabase, email)
    assert (queued["status"], queued["template_key"]) == ("scheduled", "member_invite")

    sender = FakeSender()
    drain(redis_url, queue_name, email_sender=sender)

    [sent] = sender.sent
    assert sent.to == email
    assert sent.from_name == "FastHyr"
    assert "https://fasthyr.test/join/" in sent.text
    [row] = email_rows(supabase, email)
    assert row["status"] == "sent"
    assert row["provider_message_id"] == f"re_{sent.id.hex}"


def test_provider_outage_is_retried(
    tenancy: Tenancy, supabase: Supabase, redis_url: str, queue_name: str
) -> None:
    email = invite(tenancy)

    sender = FakeSender(failures=1)
    drain(redis_url, queue_name, email_sender=sender)  # the retry waits 10 s

    assert len(sender.sent) == 1
    assert email_rows(supabase, email)[0]["status"] == "sent"


def test_rejected_email_fails_without_retrying(
    tenancy: Tenancy, supabase: Supabase, redis_url: str, queue_name: str
) -> None:
    email = invite(tenancy)

    sender = FakeSender(failures=5, error=EmailRejectedError())
    drain(redis_url, queue_name, email_sender=sender)

    assert sender.failures == 4  # one try only
    [row] = email_rows(supabase, email)
    assert (row["status"], row["error"]) == ("failed", "provider_rejected")


def test_sweeper_requeues_due_emails_redis_lost(
    tenancy: Tenancy, supabase: Supabase, redis_url: str, queue_name: str
) -> None:
    email = invite(tenancy)
    [row] = email_rows(supabase, email)
    # As if the enqueue never reached Redis: drop it and make the email overdue.
    asyncio.run(
        _fetch(
            supabase,
            "update email_messages set scheduled_for = now() - interval '15 minutes' where id = $1",
            row["id"],
        )
    )

    async def lose_and_sweep() -> int:
        queue = JobQueue(redis_url, queue_name=queue_name)
        pool = await queue.pool()
        await pool.delete(queue_name, f"arq:job:send_email:{row['id']}")
        ctx: dict[str, Any] = {"redis": pool, "queue_name": queue_name, "email_sender": None}
        await startup(ctx)
        try:
            requeued: int = await requeue_stuck_work(ctx)
            return requeued
        finally:
            await shutdown(ctx)
            await queue.close()

    assert asyncio.run(lose_and_sweep()) >= 1
    sender = FakeSender()
    drain(redis_url, queue_name, email_sender=sender)

    assert [sent.to for sent in sender.sent if sent.to == email] == [email]
    assert email_rows(supabase, email)[0]["status"] == "sent"


def post_webhook(tenancy: Tenancy, event: dict[str, Any], *, secret: str = SECRET) -> int:
    body = json.dumps(event).encode()
    stamp = str(int(time.time()))
    message_id = f"msg_{uuid.uuid4().hex}"
    response = tenancy._app.post(  # no sign-in: Resend calls this
        "/v1/webhooks/resend",
        content=body,
        headers={
            "svix-id": message_id,
            "svix-timestamp": stamp,
            "svix-signature": sign(secret, message_id=message_id, timestamp=stamp, body=body),
            "content-type": "application/json",
        },
    )
    return response.status_code


def test_webhooks_update_delivery_status(
    tenancy: Tenancy, supabase: Supabase, redis_url: str, queue_name: str
) -> None:
    email = invite(tenancy)
    drain(redis_url, queue_name, email_sender=FakeSender())
    provider_id = email_rows(supabase, email)[0]["provider_message_id"]

    def event(kind: str) -> dict[str, Any]:
        return {"type": kind, "data": {"email_id": provider_id}}

    wrong_secret = "whsec_" + "b3RoZXItc2VjcmV0LXZhbHVlLWhlcmU="
    assert post_webhook(tenancy, event("email.bounced"), secret=wrong_secret) == 400
    assert email_rows(supabase, email)[0]["status"] == "sent"

    assert post_webhook(tenancy, event("email.delivered")) == 204
    assert email_rows(supabase, email)[0]["status"] == "delivered"
    assert post_webhook(tenancy, event("email.bounced")) == 204
    assert email_rows(supabase, email)[0]["status"] == "bounced"
    # A late delivered event never undoes a bounce; unknown events are ignored.
    assert post_webhook(tenancy, event("email.delivered")) == 204
    assert post_webhook(tenancy, event("email.opened")) == 204
    assert email_rows(supabase, email)[0]["status"] == "bounced"
