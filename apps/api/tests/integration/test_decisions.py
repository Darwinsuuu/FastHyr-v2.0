"""ASMT-007: advancing and rejecting a candidate. The stage rules and the flags gate, the email
each decision sends (or doesn't), waiting automatic emails cancelled, a running interview ended
by a rejection, both decisions final, the audit row, the profile's journey, and each caller's
reach on DASH-003's hand-counted applications."""

import json
import uuid
from typing import Any

import pytest
from fastapi import FastAPI

from app.ai.realtime import FakeRealtime
from app.core.context import Role
from app.core.tokens import hash_token
from app.integrations.storage import SupabaseStorage
from app.main import create_app
from tests.integration.test_analytics import get, world  # noqa: F401 (fixture)
from tests.integration.test_applications import (
    CandidateUser,
    RecordingQueue,
    candidates,
    clean_resumes,
    queue,
)
from tests.integration.test_interview_links import invite, link
from tests.integration.test_interview_sessions import attempts, ready, refused, start
from tests.integration.test_pipelines import admin, ok, sql
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes", "queue"]


@pytest.fixture
def realtime() -> FakeRealtime:
    return FakeRealtime()


@pytest.fixture
def tenancy_app(storage: SupabaseStorage, queue: RecordingQueue, realtime: FakeRealtime) -> FastAPI:
    return create_app(storage=storage, job_queue=queue, realtime=realtime)


def application_of(tenancy: Tenancy, interview_id: uuid.UUID) -> uuid.UUID:
    [row] = sql(tenancy, "select application_id from interviews where id = $1", interview_id)
    return uuid.UUID(str(row["application_id"]))


def application(tenancy: Tenancy, application_id: uuid.UUID) -> Any:
    [row] = sql(tenancy, "select * from applications where id = $1", application_id)
    return row


def emails(tenancy: Tenancy, application_id: uuid.UUID) -> list[Any]:
    return sql(
        tenancy,
        "select * from email_messages where application_id = $1 order by created_at",
        application_id,
    )


def advance(client: Any, application_id: uuid.UUID | str, **body: Any) -> Any:
    return client.post(f"/v1/applications/{application_id}/advance", json=body)


def reject(client: Any, application_id: uuid.UUID | str, **body: Any) -> Any:
    return client.post(f"/v1/applications/{application_id}/reject", json=body)


def assessed(tenancy: Tenancy, candidate: CandidateUser) -> uuid.UUID:
    """A candidate whose interview is finished and Ready for review, with an automatic email
    still waiting (the post-interview kind a decision must not contradict)."""
    _, interview_id = invite(tenancy, candidate, status="completed")
    application_id = application_of(tenancy, interview_id)
    sql(tenancy, "update applications set stage = 'ready_for_review' where id = $1", application_id)
    sql(
        tenancy,
        "insert into email_messages (workspace_id, application_id, template_key, to_email, "
        "from_name, subject_rendered, html_rendered, text_rendered, scheduled_for, "
        "application_stage, status) values ($1, $2, 'interview_received', 'c@x.test', 'Acme', "
        "'s', '<p>h</p>', 't', now() + interval '1 day', 'ready_for_review', 'scheduled')",
        tenancy.workspace("a").id,
        application_id,
    )
    return application_id


def test_advancing_sends_the_next_stage_email(
    tenancy: Tenancy, candidates: list[CandidateUser], queue: RecordingQueue
) -> None:
    application_id = assessed(tenancy, candidates[0])
    done = ok(advance(admin(tenancy), application_id, note=" Strong on systems. "))
    assert done == {"id": str(application_id), "stage": "advanced", "emailed": True}

    row = application(tenancy, application_id)
    assert (row["stage"], row["advanced_note"]) == ("advanced", "Strong on systems.")
    assert row["advanced_by"] == tenancy.member("a", Role.ADMIN).member_id
    waiting, sent = emails(tenancy, application_id)
    # The automatic email waiting for the old stage is cancelled; the decision's goes now.
    assert (waiting["status"], waiting["cancel_reason"]) == ("cancelled", "stage_changed")
    assert (sent["template_key"], sent["status"], sent["application_stage"]) == (
        "next_stage",
        "scheduled",
        "advanced",
    )
    assert ("send_email", (sent["id"],)) in queue.enqueued

    [audit] = sql(
        tenancy,
        "select * from audit_log where action = 'application.advanced' and entity_id = $1",
        application_id,
    )
    assert json.loads(audit["data"]) == {"from": "ready_for_review", "emailed": True}
    assert "Strong" not in str(audit["data"])

    journey = get(admin(tenancy), f"/v1/applications/{application_id}")["journey"]
    assert journey[-1]["kind"] == "advanced"
    assert journey[-1]["note"] == "Strong on systems."
    assert journey[-1]["by"]

    # Final: neither decision applies again.
    refused(advance(admin(tenancy), application_id), 409, "decision_not_allowed")
    refused(reject(admin(tenancy), application_id, reason="No"), 409, "decision_not_allowed")


def test_advance_waits_for_flags_and_the_email_can_be_unticked(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    application_id = assessed(tenancy, candidates[0])
    sql(tenancy, "update applications set has_open_flags = true where id = $1", application_id)
    refused(advance(admin(tenancy), application_id), 409, "flags_to_review")

    sql(tenancy, "update applications set has_open_flags = false where id = $1", application_id)
    done = ok(advance(admin(tenancy), application_id, send_email=False))
    assert (done["stage"], done["emailed"]) == ("advanced", False)
    assert [row["template_key"] for row in emails(tenancy, application_id)] == [
        "interview_received"
    ]
    assert application(tenancy, application_id)["advanced_note"] is None


def test_only_ready_for_review_advances(tenancy: Tenancy, candidates: list[CandidateUser]) -> None:
    _, interview_id = invite(tenancy, candidates[0])
    application_id = application_of(tenancy, interview_id)
    refused(advance(admin(tenancy), application_id), 409, "decision_not_allowed")
    for stage in ("did_not_pass", "resume_not_match", "scoring"):
        sql(tenancy, "update applications set stage = $2 where id = $1", application_id, stage)
        refused(advance(admin(tenancy), application_id), 409, "decision_not_allowed")
        refused(reject(admin(tenancy), application_id, reason="x"), 409, "decision_not_allowed")


def test_rejecting_after_the_interview_sends_the_interview_rejection(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    application_id = assessed(tenancy, candidates[0])
    # A flagged candidate can be rejected; only advancing waits for the review.
    sql(tenancy, "update applications set has_open_flags = true where id = $1", application_id)
    done = ok(reject(admin(tenancy), application_id, reason="  Needs more Kubernetes.  "))
    assert done == {"id": str(application_id), "stage": "rejected", "emailed": True}

    row = application(tenancy, application_id)
    assert (row["stage"], row["rejected_reason"]) == ("rejected", "Needs more Kubernetes.")
    waiting, sent = emails(tenancy, application_id)
    assert waiting["status"] == "cancelled"
    assert sent["template_key"] == "reject_interview"
    # Like every rejection, it offers a person's review, through a working link.
    token = sent["html_rendered"].split("/review-request/")[1].split('"')[0]
    [review] = sql(tenancy, "select * from review_links where application_id = $1", application_id)
    assert (review["decision_type"], review["token_hash"]) == ("interview", hash_token(token))
    assert "Kubernetes" not in sent["html_rendered"]

    [audit] = sql(
        tenancy, "select data from audit_log where action = 'application.rejected' "
        "and entity_id = $1", application_id,
    )  # fmt: skip
    assert json.loads(audit["data"]) == {"from": "ready_for_review", "emailed": True}
    journey = get(admin(tenancy), f"/v1/applications/{application_id}")["journey"]
    assert (journey[-1]["kind"], journey[-1]["note"]) == ("rejected", "Needs more Kubernetes.")
    refused(reject(admin(tenancy), application_id, reason="Again"), 409, "decision_not_allowed")


def test_rejecting_an_invited_candidate_closes_the_link(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    paolo = candidates[0]
    token, interview_id = invite(tenancy, paolo)
    application_id = application_of(tenancy, interview_id)
    ok(reject(admin(tenancy), application_id, reason="Role filled internally"))
    [sent] = emails(tenancy, application_id)
    assert sent["template_key"] == "reject_resume"
    [review] = sql(tenancy, "select * from review_links where application_id = $1", application_id)
    assert review["decision_type"] == "resume"
    assert link(tenancy, token, paolo)["state"] == "unavailable"

    # Unticked: no email, no review link.
    _, other = invite(tenancy, candidates[1])
    other_id = application_of(tenancy, other)
    done = ok(reject(admin(tenancy), other_id, reason="Role filled", send_email=False))
    assert done["emailed"] is False
    assert emails(tenancy, other_id) == []
    assert sql(tenancy, "select * from review_links where application_id = $1", other_id) == []


def test_rejecting_mid_interview_ends_the_call(
    tenancy: Tenancy, candidates: list[CandidateUser], realtime: FakeRealtime
) -> None:
    maria = candidates[0]
    token, interview_id = ready(tenancy, maria)
    session = ok(start(tenancy, token, maria))
    application_id = application_of(tenancy, interview_id)
    assert application(tenancy, application_id)["stage"] == "interview_in_progress"

    ok(reject(admin(tenancy), application_id, reason="Withdrew by phone"))
    [attempt] = attempts(tenancy, interview_id)
    assert attempt["ended_at"] is not None
    assert attempt["realtime_session_id"] in realtime.hung_up
    # The "Finish your interview" nudge never goes out; only the rejection does.
    statuses = {row["template_key"]: row["status"] for row in emails(tenancy, application_id)}
    assert statuses == {"finish_interview": "cancelled", "reject_resume": "scheduled"}
    assert link(tenancy, token, maria)["state"] == "unavailable"
    assert session["attempt_id"] == str(attempt["id"])


def test_an_unreadable_resume_can_be_rejected(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    _, interview_id = invite(tenancy, candidates[0])
    application_id = application_of(tenancy, interview_id)
    sql(
        tenancy,
        "update applications set stage = 'processing_resume', resume_status = $2 where id = $1",
        application_id,
        "pending",
    )
    refused(reject(admin(tenancy), application_id, reason="x"), 409, "decision_not_allowed")
    sql(
        tenancy,
        "update applications set resume_status = 'unreadable' where id = $1",
        application_id,
    )
    ok(reject(admin(tenancy), application_id, reason="Couldn't read it", send_email=False))


def test_a_reason_is_required(tenancy: Tenancy, candidates: list[CandidateUser]) -> None:
    application_id = assessed(tenancy, candidates[0])
    for body in ({}, {"reason": ""}, {"reason": "   "}, {"reason": "x" * 501}):
        refused(reject(admin(tenancy), application_id, **body), 422, "validation_failed")
    refused(advance(admin(tenancy), application_id, note="x" * 1001), 422, "validation_failed")
    assert application(tenancy, application_id)["stage"] == "ready_for_review"


def test_who_can_decide(tenancy: Tenancy, world: dict[str, Any]) -> None:  # noqa: F811
    def of(stage: str, title: str) -> str:
        rows = sql(
            tenancy,
            "select a.id from applications a join pipelines p on p.id = a.pipeline_id "
            "where a.workspace_id = $1 and a.stage = $2 and p.title = $3",
            tenancy.workspace("a").id,
            stage,
            title,
        )
        return str(rows[0]["id"])

    engineering = of("ready_for_review", "Backend Engineer")
    no_department = of("ready_for_review", "Office Manager")
    manager = tenancy.client("a", Role.HIRING_MANAGER)
    refused(advance(manager, engineering), 403, "forbidden")
    refused(reject(manager, engineering, reason="x"), 403, "forbidden")
    for role in (Role.ADMIN, Role.RECRUITER):
        outsider = tenancy.client("b", role)
        refused(advance(outsider, engineering), 404, "not_found")
        refused(reject(outsider, engineering, reason="x"), 404, "not_found")
    recruiter = tenancy.client("a", Role.RECRUITER)
    # No department is Admins only.
    refused(advance(recruiter, no_department), 404, "not_found")
    refused(advance(admin(tenancy), str(uuid.uuid4())), 404, "not_found")
    assert advance(tenancy.anonymous(), engineering).status_code == 401
    rows = sql(tenancy, "select stage from applications where id = $1", uuid.UUID(engineering))
    assert rows[0]["stage"] == "ready_for_review"

    ok(advance(recruiter, engineering, send_email=False))
    ok(reject(admin(tenancy), no_department, reason="Hired someone", send_email=False))
    listed = get(admin(tenancy), f"/v1/pipelines/{world['engineering']}/applications")
    assert listed["counts"]["advanced"] == 2
