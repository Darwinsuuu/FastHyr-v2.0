"""FND-009: errors reach Sentry tagged with request and job IDs and never carry personal data,
and log lines are structured and scrubbed the same way."""

import asyncio
import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from app.api.deps import CurrentUserDep
from app.core.config import Settings
from app.core.logging import configure_logging
from app.core.observability import init_sentry, scrub_event
from app.jobs.framework import JobRun, RetryPolicy, job
from app.main import create_app
from tests.unit.test_auth import USER_ID, VERIFIER, make_token
from tests.unit.test_jobs_framework import BoomError, FakeSessionmaker, ctx_for

# Personal data planted in the fixtures below; none of it may reach Sentry or a log line.
PERSONAL = ("ada@example.com", "Ada Lovelace", "+63 917 555 0101", "s3cret-pass", "eyJhbGciOi")


class MemoryTransport(Transport):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        event = envelope.get_event()
        if event is not None:
            self.events.append(dict(event))


@pytest.fixture
def sentry_events() -> Iterator[list[dict[str, Any]]]:
    transport = MemoryTransport()
    settings = Settings(sentry_dsn="https://public@sentry.invalid/1", git_sha="abc123")
    assert init_sentry(settings, "api", transport=transport)
    yield transport.events
    sentry_sdk.get_client().close()
    sentry_sdk.init()


def assert_no_personal_data(value: object) -> None:
    text = json.dumps(value, default=str)
    for planted in PERSONAL:
        assert planted not in text


def test_sentry_is_off_without_a_dsn() -> None:
    assert init_sentry(Settings(sentry_dsn=""), "api") is False


def test_scrub_event_removes_personal_data_from_every_part() -> None:
    jwt = "eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl"
    event: Any = {
        "message": "invite for ada@example.com failed",
        "request": {
            "method": "POST",
            "url": "https://api.fasthyr.com/v1/invites?email=ada@example.com",
            "query_string": "email=ada@example.com",
            "data": {"email": "ada@example.com", "name": "Ada Lovelace"},
            "cookies": {"sb": jwt},
            "headers": {
                "Authorization": f"Bearer {jwt}",
                "Cookie": f"sb={jwt}",
                "X-Request-Id": "req-12345678",
            },
        },
        "user": {"id": "u1", "email": "ada@example.com", "ip_address": "1.2.3.4"},
        "extra": {"candidate_email": "ada@example.com", "phone": "+63 917 555 0101", "n": 3},
        "tags": {"request_id": "req-12345678"},
        "contexts": {"invite": {"name": "Ada Lovelace", "password": "s3cret-pass"}},
        "exception": {
            "values": [
                {
                    "type": "RuntimeError",
                    "value": "no member ada@example.com",
                    "stacktrace": {"frames": [{"function": "f", "vars": {"x": "Ada Lovelace"}}]},
                }
            ]
        },
        "breadcrumbs": {
            "values": [
                {"message": "sent to ada@example.com", "data": {"to": "ada@example.com"}},
                {"category": "httplib", "data": {"url": "https://x.test/a?token=abc"}},
            ]
        },
        "server_name": "render-abc",
    }

    scrubbed: Any = scrub_event(event)

    assert_no_personal_data(scrubbed)
    assert scrubbed["user"] == {"id": "u1"}
    assert scrubbed["request"]["url"] == "https://api.fasthyr.com/v1/invites"
    assert scrubbed["request"]["headers"] == {"X-Request-Id": "req-12345678"}
    assert scrubbed["tags"] == {"request_id": "req-12345678"}
    assert scrubbed["extra"]["n"] == 3
    assert scrubbed["breadcrumbs"]["values"][1]["data"]["url"] == "https://x.test/a"
    assert "server_name" not in scrubbed


def test_unhandled_api_error_reaches_sentry_with_ids_only(
    sentry_events: list[dict[str, Any]],
) -> None:
    app = create_app(token_verifier=VERIFIER)

    @app.get("/boom-signed-in")
    async def boom_signed_in(user: CurrentUserDep) -> None:
        raise RuntimeError("lookup failed for ada@example.com")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/boom-signed-in?email=ada@example.com",
        headers={"Authorization": f"Bearer {make_token()}"},
    )
    sentry_sdk.flush()

    assert response.status_code == 500
    assert len(sentry_events) == 1
    event = sentry_events[0]
    assert event["tags"]["request_id"] == response.headers["x-request-id"]
    assert event["tags"]["user_id"] == str(USER_ID)
    assert event["tags"]["component"] == "api"
    assert event["user"] == {"id": str(USER_ID)}
    assert event["release"] == "abc123"
    assert event["exception"]["values"][-1]["value"] == "lookup failed for [email]"
    assert_no_personal_data(event)


def test_handled_errors_are_not_sent(sentry_events: list[dict[str, Any]]) -> None:
    client = TestClient(create_app(token_verifier=VERIFIER), raise_server_exceptions=False)

    assert client.get("/v1/me").status_code == 401
    sentry_sdk.flush()
    assert sentry_events == []


def test_only_the_last_failed_job_try_reaches_sentry(
    sentry_events: list[dict[str, Any]],
) -> None:
    @job(retry=RetryPolicy(max_tries=2))
    async def send_invite(run: JobRun, invite_id: str) -> None:
        raise BoomError("bounced for ada@example.com")

    sessionmaker = FakeSessionmaker()
    with pytest.raises(Exception):  # noqa: B017 (arq's Retry on the first try)
        asyncio.run(send_invite(ctx_for(1, sessionmaker), "inv-1"))
    sentry_sdk.flush()
    assert sentry_events == []

    with pytest.raises(BoomError):
        asyncio.run(send_invite(ctx_for(2, sessionmaker), "inv-1"))
    sentry_sdk.flush()

    assert len(sentry_events) == 1
    tags = sentry_events[0]["tags"]
    assert tags["job"] == "send_invite"
    assert tags["job_id"] == "j"
    assert tags["job_try"] == "2"
    assert_no_personal_data(sentry_events[0])


def test_log_lines_are_json_with_the_request_id_and_scrubbed() -> None:
    stream = io.StringIO()
    try:
        app = create_app(Settings(log_format="json"), token_verifier=VERIFIER)
        logging.getLogger("app").handlers[0].setStream(stream)  # type: ignore[attr-defined]

        @app.get("/log/{code}")
        async def log_something(code: str) -> None:
            logging.getLogger("app.test").info(
                "invite sent to %s", "ada@example.com", extra={"email": "ada@example.com"}
            )

        response = TestClient(app).get("/log/INVITE-SECRET-1?email=ada@example.com")
    finally:
        configure_logging()

    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    line = next(entry for entry in lines if entry["logger"] == "app.test")
    assert line["request_id"] == response.headers["x-request-id"]
    assert line["event"] == "invite sent to [email]"
    assert line["level"] == "info"
    assert line["email"] == "[Filtered]"
    request = next(entry for entry in lines if entry["logger"] == "app.request")
    assert request["route"] == "/log/{code}"
    assert request["status"] == 200
    assert request["request_id"] == line["request_id"]
    assert "INVITE-SECRET-1" not in stream.getvalue()
    assert_no_personal_data(lines)
