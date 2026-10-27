"""PIPE-005: closing a pipeline with "Let candidates who haven't heard back know". Exactly the
applications with nothing more coming get the "Role closed" email, at once and after the commit;
nobody's stage moves; without the tick nothing is sent; another workspace's pipeline is 404."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import Role
from app.repositories.pipelines import not_heard_back
from tests.integration.test_applications import (
    CandidateUser,
    RecordingQueue,
    apply,
    candidates,
    clean_resumes,
    queue,
    tenancy_app,
)
from tests.integration.test_pipelines import admin, db_run, grant, ok, pipeline_in, sql
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes", "queue", "tenancy_app"]


def applied(tenancy: Tenancy, candidates: list[CandidateUser]) -> tuple[str, list[uuid.UUID]]:
    """A live pipeline in workspace a that every candidate applied to."""
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    ids = [
        uuid.UUID(ok(apply(tenancy, candidate, pipeline["id"]), 201)["application_id"])
        for candidate in candidates
    ]
    return pipeline["id"], ids


def set_stage(tenancy: Tenancy, application_id: uuid.UUID, stage: str, **columns: Any) -> None:
    assignments = "".join(f", {name} = ${index + 3}" for index, name in enumerate(columns))
    sql(
        tenancy,
        f"update applications set stage = $2{assignments} where id = $1",
        application_id,
        stage,
        *columns.values(),
    )


def interview(tenancy: Tenancy, application_id: uuid.UUID, status: str) -> None:
    sql(
        tenancy,
        "insert into interviews (workspace_id, application_id, token_hash, format, expires_at, "
        "status) values ($1, $2, $3, 'video_voice', $4, $5)",
        tenancy.workspace("a").id,
        application_id,
        uuid.uuid4().hex,
        datetime.now(UTC) + (timedelta(days=-1) if status == "expired" else timedelta(days=5)),
        status,
    )


def outcome_email(tenancy: Tenancy, application_id: uuid.UUID, key: str, status: str) -> None:
    sql(
        tenancy,
        "insert into email_messages (workspace_id, application_id, template_key, to_email, "
        "from_name, subject_rendered, html_rendered, text_rendered, scheduled_for, "
        "application_stage, status) values ($1, $2, $3, 'c@x.test', 'Acme', 's', '<p>h</p>', "
        "'t', now() + interval '1 day', 'did_not_pass', $4)",
        tenancy.workspace("a").id,
        application_id,
        key,
        status,
    )


def waiting(tenancy: Tenancy, pipeline_id: str) -> list[uuid.UUID]:
    async def work(session: AsyncSession) -> list[uuid.UUID]:
        return list(
            await not_heard_back(session, tenancy.workspace("a").id, uuid.UUID(pipeline_id))
        )

    return db_run(tenancy, work)


def role_closed(tenancy: Tenancy, pipeline_id: str) -> list[Any]:
    return sql(
        tenancy,
        "select m.* from email_messages m join applications a on a.id = m.application_id "
        "where a.pipeline_id = $1 and m.template_key = 'role_closed' order by m.created_at",
        uuid.UUID(pipeline_id),
    )


def test_closing_with_notify_tells_only_candidates_who_havent_heard_back(
    tenancy: Tenancy, candidates: list[CandidateUser], queue: RecordingQueue
) -> None:
    pipeline_id, (ready, rejected_soon, mid_interview) = applied(tenancy, candidates)
    set_stage(tenancy, ready, "ready_for_review")
    # A rejection is already on its way: that is how this one hears back.
    set_stage(tenancy, rejected_soon, "did_not_pass")
    outcome_email(tenancy, rejected_soon, "reject_interview", "scheduled")
    # Still talking to the interviewer: closing lets them finish.
    set_stage(tenancy, mid_interview, "interview_in_progress")

    other = tenancy.client("b", Role.ADMIN)
    assert other.post(f"/v1/pipelines/{pipeline_id}/close", json={"notify": True}).status_code == 404

    closed = ok(admin(tenancy).post(f"/v1/pipelines/{pipeline_id}/close", json={"notify": True}))
    assert (closed["status"], closed["closed_reason"], closed["notified"]) == ("closed", "manual", 1)

    [email] = role_closed(tenancy, pipeline_id)
    assert (email["application_id"], email["status"]) == (ready, "scheduled")
    assert email["to_email"] == candidates[0].email
    assert "Backend Engineer" in email["subject_rendered"]
    assert ("send_email", (email["id"],)) in queue.enqueued

    stages = sql(
        tenancy,
        "select id, stage from applications where pipeline_id = $1",
        uuid.UUID(pipeline_id),
    )
    assert {row["id"]: row["stage"] for row in stages} == {
        ready: "ready_for_review",
        rejected_soon: "did_not_pass",
        mid_interview: "interview_in_progress",
    }
    [audit] = sql(
        tenancy,
        "select data from audit_log where action = 'pipeline.closed' and entity_id = $1",
        uuid.UUID(pipeline_id),
    )
    assert json.loads(audit["data"])["notified"] == 1

    refused = admin(tenancy).post(f"/v1/pipelines/{pipeline_id}/close", json={"notify": True})
    assert refused.status_code == 409
    assert len(role_closed(tenancy, pipeline_id)) == 1


def test_closing_without_notify_sends_nothing(
    tenancy: Tenancy, candidates: list[CandidateUser], queue: RecordingQueue
) -> None:
    pipeline_id, (first, *_) = applied(tenancy, candidates[:1])
    set_stage(tenancy, first, "ready_for_review")
    closed = ok(admin(tenancy).post(f"/v1/pipelines/{pipeline_id}/close"))
    assert (closed["status"], closed["notified"]) == ("closed", 0)
    assert role_closed(tenancy, pipeline_id) == []


def test_who_hasnt_heard_back(tenancy: Tenancy, candidates: list[CandidateUser]) -> None:
    pipeline_id, (one, two, three) = applied(tenancy, candidates)
    # Fresh applications are still being screened.
    assert waiting(tenancy, pipeline_id) == []

    set_stage(tenancy, one, "processing_resume", resume_status="unreadable")
    set_stage(tenancy, two, "resume_not_match")
    set_stage(tenancy, three, "invited")
    interview(tenancy, three, "not_started")
    assert set(waiting(tenancy, pipeline_id)) == {one, two}

    # An expired link means nothing more comes unless the team re-invites.
    sql(tenancy, "update interviews set status = 'expired' where application_id = $1", three)
    assert set(waiting(tenancy, pipeline_id)) == {one, two, three}

    # A rejection that went (or waits) counts as hearing back; a cancelled one doesn't.
    outcome_email(tenancy, two, "reject_resume", "sent")
    outcome_email(tenancy, three, "reject_resume", "cancelled")
    assert set(waiting(tenancy, pipeline_id)) == {one, three}

    # A person's decision is final, and so is an address that bounced.
    set_stage(tenancy, one, "rejected")
    sql(
        tenancy,
        "update candidates set email_undeliverable_at = now() "
        "where id = (select candidate_id from applications where id = $1)",
        three,
    )
    assert waiting(tenancy, pipeline_id) == []
