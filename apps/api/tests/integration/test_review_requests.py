"""ASMT-008: human review requests. The link's states, one request per link with the candidate's
acknowledgement and the owner's email, overriding a résumé (invited, with the invitation) or an
interview (Ready for review) decision, upholding, a person's own rejection only upheld, the
audit rows, the profile's banner and journey, and who reaches the team endpoints."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI

from app.core.context import Role
from app.core.tokens import new_token
from app.integrations.storage import SupabaseStorage
from app.main import create_app
from tests.integration.test_applications import (
    CandidateUser,
    RecordingQueue,
    candidates,
    clean_resumes,
    queue,
)
from tests.integration.test_decisions import application, assessed, emails, reject
from tests.integration.test_interview_sessions import refused
from tests.integration.test_pipelines import admin, ok, sql
from tests.integration.test_screening import resume_pdf, submit
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes", "queue"]


@pytest.fixture
def tenancy_app(storage: SupabaseStorage, queue: RecordingQueue) -> FastAPI:
    return create_app(storage=storage, job_queue=queue)


def review_link(
    tenancy: Tenancy, application_id: uuid.UUID, decision_type: str, *, days: int = 30
) -> str:
    """A review link as a rejection email makes it; returns the token."""
    token, token_hash = new_token()
    sql(
        tenancy,
        "insert into review_links (workspace_id, application_id, decision_type, token_hash, "
        "expires_at) values ($1, $2, $3, $4, $5)",
        tenancy.workspace("a").id,
        application_id,
        decision_type,
        token_hash,
        datetime.now(UTC) + timedelta(days=days),
    )
    return token


def not_a_match(tenancy: Tenancy, candidate: CandidateUser) -> uuid.UUID:
    application_id = submit(tenancy, candidate, resume_pdf())
    sql(
        tenancy,
        "update applications set stage = 'resume_not_match', resume_status = 'done' where id = $1",
        application_id,
    )
    return application_id


def page(tenancy: Tenancy, token: str) -> Any:
    return tenancy.anonymous().get(f"/v1/public/review-requests/{token}")


def ask(tenancy: Tenancy, token: str, **body: Any) -> Any:
    return tenancy.anonymous().post(f"/v1/public/review-requests/{token}", json=body)


def resolve(client: Any, request_id: str, outcome: str, note: str = "Looked again") -> Any:
    return client.post(
        f"/v1/review-requests/{request_id}/resolve", json={"outcome": outcome, "note": note}
    )


def open_request(tenancy: Tenancy, application_id: uuid.UUID) -> str:
    [row] = sql(
        tenancy,
        "select id from human_review_requests where application_id = $1 and status = 'open'",
        application_id,
    )
    return str(row["id"])


def test_a_resume_decision_is_reviewed_and_overridden(
    tenancy: Tenancy, candidates: list[CandidateUser], queue: RecordingQueue
) -> None:
    application_id = not_a_match(tenancy, candidates[0])
    token = review_link(tenancy, application_id, "resume")
    shown = ok(page(tenancy, token))
    assert shown["state"] == "open"
    assert set(shown) == {"state", "company", "job_title"}

    asked = ok(ask(tenancy, token, message="  I led a Kubernetes migration.  "))
    assert asked["state"] == "requested"
    # A repeat (a double click) changes nothing.
    assert ok(ask(tenancy, token))["state"] == "requested"
    assert ok(page(tenancy, token))["state"] == "requested"
    [request] = sql(
        tenancy, "select * from human_review_requests where application_id = $1", application_id
    )
    assert (request["decision_type"], request["candidate_message"], request["status"]) == (
        "resume",
        "I led a Kubernetes migration.",
        "open",
    )
    assert application(tenancy, application_id)["review_requested"] is True
    [ack] = emails(tenancy, application_id)
    assert ack["template_key"] == "review_received"
    [owner] = sql(
        tenancy,
        "select * from email_messages where workspace_id = $1 and template_key = 'review_request'",
        tenancy.workspace("a").id,
    )
    assert f"application={application_id}" in owner["html_rendered"]
    assert "Kubernetes" not in owner["html_rendered"]
    assert ("send_email", (ack["id"],)) in queue.enqueued

    profile = ok(admin(tenancy).get(f"/v1/applications/{application_id}"))
    assert profile["review_request"]["message"] == "I led a Kubernetes migration."
    assert profile["review_request"]["can_override"] is True
    listed = ok(admin(tenancy).get("/v1/review-requests"))
    assert [item["application_id"] for item in listed["items"]] == [str(application_id)]

    request_id = str(request["id"])
    refused(resolve(admin(tenancy), request_id, "override", note=" "), 422, "validation_failed")
    done = ok(resolve(admin(tenancy), request_id, "override", note="Has the experience"))
    assert (done["status"], done["stage"], done["emailed"]) == ("overridden", "invited", True)
    row = application(tenancy, application_id)
    assert (row["stage"], row["review_requested"]) == ("invited", False)
    [plan] = sql(tenancy, "select * from interview_plans where application_id = $1", application_id)
    assert plan["source"] == "fallback"
    [interview] = sql(tenancy, "select * from interviews where application_id = $1", application_id)
    assert interview["status"] == "not_started"
    templates = [message["template_key"] for message in emails(tenancy, application_id)]
    assert "interview_invitation" in templates

    [audit] = sql(
        tenancy,
        "select data from audit_log where action = 'review_request.resolved' and entity_id = $1",
        request["id"],
    )
    data = json.loads(audit["data"])
    assert (data["outcome"], data["from"], data["to"]) == (
        "overridden",
        "resume_not_match",
        "invited",
    )
    assert "experience" not in str(audit["data"])
    refused(resolve(admin(tenancy), request_id, "uphold"), 409, "review_request_resolved")

    profile = ok(admin(tenancy).get(f"/v1/applications/{application_id}"))
    assert profile["review_request"] is None
    kinds = [step["kind"] for step in profile["journey"]]
    assert kinds.index("review_requested") < kinds.index("review_overridden")
    assert profile["journey"][kinds.index("review_overridden")]["note"] == "Has the experience"
    # The link has done its job.
    assert ok(page(tenancy, token))["state"] == "requested"


def test_an_interview_decision_is_overridden_to_ready_for_review(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    application_id = assessed(tenancy, candidates[0])
    sql(tenancy, "update applications set stage = 'did_not_pass' where id = $1", application_id)
    token = review_link(tenancy, application_id, "interview")
    ok(ask(tenancy, token))
    done = ok(resolve(admin(tenancy), open_request(tenancy, application_id), "override"))
    assert (done["stage"], done["emailed"]) == ("ready_for_review", False)
    assert application(tenancy, application_id)["stage"] == "ready_for_review"


def test_upholding_sends_nothing(tenancy: Tenancy, candidates: list[CandidateUser]) -> None:
    application_id = not_a_match(tenancy, candidates[0])
    ok(ask(tenancy, review_link(tenancy, application_id, "resume")))
    before = len(emails(tenancy, application_id))
    done = ok(resolve(admin(tenancy), open_request(tenancy, application_id), "uphold"))
    assert (done["status"], done["stage"], done["emailed"]) == (
        "upheld",
        "resume_not_match",
        False,
    )
    row = application(tenancy, application_id)
    assert (row["stage"], row["review_requested"]) == ("resume_not_match", False)
    assert len(emails(tenancy, application_id)) == before


def test_a_persons_rejection_can_only_be_upheld(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    application_id = assessed(tenancy, candidates[0])
    ok(reject(admin(tenancy), application_id, reason="Needs more Kubernetes."))
    [sent] = [m for m in emails(tenancy, application_id) if m["template_key"] == "reject_interview"]
    token = sent["html_rendered"].split("/review-request/")[1].split('"')[0]
    ok(ask(tenancy, token))
    request_id = open_request(tenancy, application_id)
    profile = ok(admin(tenancy).get(f"/v1/applications/{application_id}"))
    assert profile["review_request"]["by_person"] is True
    assert profile["review_request"]["can_override"] is False
    refused(resolve(admin(tenancy), request_id, "override"), 409, "override_not_allowed")
    assert ok(resolve(admin(tenancy), request_id, "uphold"))["stage"] == "rejected"


def test_a_link_closes_when_it_expires_or_the_decision_moves_on(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    application_id = not_a_match(tenancy, candidates[0])
    expired = review_link(tenancy, application_id, "resume", days=-1)
    assert ok(page(tenancy, expired))["state"] == "expired"
    refused(ask(tenancy, expired), 409, "review_link_closed")

    other = not_a_match(tenancy, candidates[1])
    token = review_link(tenancy, other, "resume")
    sql(tenancy, "update applications set stage = 'invited' where id = $1", other)
    assert ok(page(tenancy, token))["state"] == "unavailable"
    refused(ask(tenancy, token), 409, "review_link_closed")
    assert (
        sql(tenancy, "select * from human_review_requests where application_id = $1", other) == []
    )

    refused(page(tenancy, "not-a-token"), 404, "review_link_not_found")
    refused(ask(tenancy, "x" * 200), 422, "validation_failed")
    refused(ask(tenancy, review_link(tenancy, other, "interview"), message="x" * 1001), 422,
            "validation_failed")  # fmt: skip


def test_who_resolves(tenancy: Tenancy, candidates: list[CandidateUser]) -> None:
    application_id = not_a_match(tenancy, candidates[0])
    ok(ask(tenancy, review_link(tenancy, application_id, "resume")))
    request_id = open_request(tenancy, application_id)
    manager = tenancy.client("a", Role.HIRING_MANAGER)
    refused(manager.get("/v1/review-requests"), 403, "forbidden")
    refused(resolve(manager, request_id, "uphold"), 403, "forbidden")
    for role in (Role.ADMIN, Role.RECRUITER):
        outsider = tenancy.client("b", role)
        refused(resolve(outsider, request_id, "uphold"), 404, "not_found")
        assert ok(outsider.get("/v1/review-requests"))["items"] == []
    refused(resolve(admin(tenancy), str(uuid.uuid4()), "uphold"), 404, "not_found")
    assert tenancy.anonymous().get("/v1/review-requests").status_code == 401
    assert application(tenancy, application_id)["review_requested"] is True
