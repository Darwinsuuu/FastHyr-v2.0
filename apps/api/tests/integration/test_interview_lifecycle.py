"""INTV-007: around a live interview. The "Finish your interview" email held while an attempt
runs and scheduled when the candidate leaves, link expiry with drop-off reasons, and re-invites
through the API (one candidate, or "Re-invite all" for a pipeline)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.realtime import FakeRealtime
from app.core.config import get_settings
from app.core.context import Role
from app.core.tokens import hash_token
from app.integrations.storage import SupabaseStorage
from app.main import create_app
from app.models import Application, Interview, Pipeline
from app.services import interview_lifecycle, interview_sessions
from tests.integration.test_applications import (
    CandidateUser,
    RecordingQueue,
    candidates,
    clean_resumes,
    queue,
)
from tests.integration.test_interview_links import invite, link, update
from tests.integration.test_interview_sessions import (
    age,
    attempts,
    heartbeat,
    interview,
    post,
    ready,
    refused,
    start,
)
from tests.integration.test_pipelines import CONFIRM, db_run, draft, ok, sql
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes", "queue"]


@pytest.fixture
def realtime() -> FakeRealtime:
    return FakeRealtime()


@pytest.fixture
def tenancy_app(storage: SupabaseStorage, queue: RecordingQueue, realtime: FakeRealtime) -> FastAPI:
    return create_app(storage=storage, job_queue=queue, realtime=realtime)


def lapsed(when: datetime) -> dict[str, datetime]:
    """Columns for a link that expired at `when` (it was sent five days before)."""
    return {"invited_at": when - timedelta(days=5), "expires_at": when}


def emails(tenancy: Tenancy, interview_id: uuid.UUID, key: str | None = None) -> list[Any]:
    """The interview's application's emails, oldest first, optionally of one template."""
    found = sql(
        tenancy,
        "select * from email_messages where application_id = "
        "(select application_id from interviews where id = $1) order by created_at",
        interview_id,
    )
    return [row for row in found if key is None or row["template_key"] == key]


def finish_email(tenancy: Tenancy, interview_id: uuid.UUID) -> Any:
    [row] = emails(tenancy, interview_id, "finish_interview")
    return row


def watchdog(tenancy: Tenancy, realtime: FakeRealtime, interview_id: uuid.UUID) -> None:
    """Runs the watchdog over the interview's running attempt."""
    workspace_id = interview(tenancy, interview_id)["workspace_id"]
    [running] = [a for a in attempts(tenancy, interview_id) if a["ended_at"] is None]

    async def work(db: AsyncSession) -> str | None:
        return await interview_sessions.end_if_overdue(db, realtime, workspace_id, running["id"])

    db_run(tenancy, work)


def expire(tenancy: Tenancy) -> int:
    async def work(db: AsyncSession) -> int:
        expired = await interview_lifecycle.expire_links(db)
        await db.commit()
        return expired

    return db_run(tenancy, work)


def application_of(tenancy: Tenancy, interview_id: uuid.UUID) -> uuid.UUID:
    application_id: uuid.UUID = interview(tenancy, interview_id)["application_id"]
    return application_id


def admin(tenancy: Tenancy) -> Any:
    return tenancy.client("a", Role.ADMIN)


def test_leaving_the_interview_schedules_the_finish_email_once(
    tenancy: Tenancy, candidates: list[CandidateUser], realtime: FakeRealtime
) -> None:
    paolo = candidates[0]
    token, interview_id = ready(tenancy, paolo)

    # Starting writes the email with the link, on hold.
    session = ok(start(tenancy, token, paolo))
    heartbeat(tenancy, token, paolo, session["attempt_id"])
    held = finish_email(tenancy, interview_id)
    assert (held["status"], held["application_stage"]) == ("held", "interview_in_progress")
    assert f"/interview/{token}" in held["html_rendered"]

    # The browser goes quiet: left unfinished, the email goes an hour later.
    age(tenancy, session["attempt_id"], seconds=61)
    watchdog(tenancy, realtime, interview_id)
    row = interview(tenancy, interview_id)
    assert (row["status"], row["drop_reason"]) == ("abandoned", "left_unfinished")
    scheduled = finish_email(tenancy, interview_id)
    assert scheduled["status"] == "scheduled"
    in_an_hour = datetime.now(UTC) + timedelta(hours=1)
    assert abs(scheduled["scheduled_for"] - in_an_hour) < timedelta(minutes=1)

    # Back before it went: on hold again, and no longer a drop-off.
    session = ok(start(tenancy, token, paolo))
    assert finish_email(tenancy, interview_id)["status"] == "held"
    assert interview(tenancy, interview_id)["drop_reason"] is None

    # Once it has been sent, leaving again sends nothing more.
    sql(
        tenancy,
        "update email_messages set status = 'sent' where id = $1",
        finish_email(tenancy, interview_id)["id"],
    )
    age(tenancy, session["attempt_id"], seconds=61)
    watchdog(tenancy, realtime, interview_id)
    ok(start(tenancy, token, paolo))
    assert [e["status"] for e in emails(tenancy, interview_id, "finish_interview")] == ["sent"]

    # Finishing clears the reason.
    ok(post(tenancy, token, "complete", paolo, {}))
    row = interview(tenancy, interview_id)
    assert (row["status"], row["drop_reason"]) == ("completed", None)


def test_finishing_or_a_closing_link_cancels_the_finish_email(
    tenancy: Tenancy, candidates: list[CandidateUser], realtime: FakeRealtime
) -> None:
    paolo, maria = candidates[0], candidates[1]

    token, interview_id = ready(tenancy, paolo)
    ok(start(tenancy, token, paolo))
    ok(post(tenancy, token, "complete", paolo, {}))
    assert finish_email(tenancy, interview_id)["status"] == "cancelled"

    # Left 30 minutes before the link closes: an email an hour later would come too late.
    token, interview_id = ready(
        tenancy, maria, expires_at=datetime.now(UTC) + timedelta(minutes=30)
    )
    session = ok(start(tenancy, token, maria))
    age(tenancy, session["attempt_id"], seconds=61)
    watchdog(tenancy, realtime, interview_id)
    assert finish_email(tenancy, interview_id)["status"] == "cancelled"


def test_expired_links_record_why_the_interview_was_not_finished(
    tenancy: Tenancy, candidates: list[CandidateUser], realtime: FakeRealtime
) -> None:
    paolo, maria, jun = candidates
    past = datetime.now(UTC) - timedelta(minutes=5)

    _, never_started = invite(tenancy, paolo, **lapsed(past))
    token, left = ready(tenancy, maria)
    session = ok(start(tenancy, token, maria))
    age(tenancy, session["attempt_id"], seconds=61)
    watchdog(tenancy, realtime, left)
    token, running = ready(tenancy, jun)
    ok(start(tenancy, token, jun))
    for interview_id in (left, running):
        update(
            tenancy,
            interview_id,
            "invited_at = $2, expires_at = $3",
            past - timedelta(days=5),
            past,
        )

    assert expire(tenancy) == 2
    assert (interview(tenancy, never_started)["status"], interview(tenancy, never_started)[
        "drop_reason"]) == ("expired", "link_expired")  # fmt: skip
    assert (interview(tenancy, left)["status"], interview(tenancy, left)["drop_reason"]) == (
        "expired",
        "left_unfinished",
    )
    assert finish_email(tenancy, left)["status"] == "cancelled"
    # Someone talking to the interviewer right now is left alone; the watchdog ends it first.
    assert interview(tenancy, running)["status"] == "in_progress"
    assert expire(tenancy) == 0

    # The drop-offs the dashboards count.
    reasons = sql(
        tenancy,
        "select interview_id, drop_reason, dropped_at from v_dropoff_reasons "
        "where workspace_id = $1",
        tenancy.workspace("a").id,
    )
    by_interview = {row["interview_id"]: row for row in reasons}
    assert by_interview[never_started]["drop_reason"] == "link_expired"
    assert by_interview[never_started]["dropped_at"] == past
    assert by_interview[left]["drop_reason"] == "left_unfinished"
    assert by_interview[left]["dropped_at"] == attempts(tenancy, left)[-1]["ended_at"]
    assert running not in by_interview


def test_a_technical_issue_stays_the_reason_after_expiry(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    _, interview_id = invite(
        tenancy,
        candidates[0],
        drop_reason="technical_issue",
        **lapsed(datetime.now(UTC) - timedelta(minutes=1)),
    )
    assert expire(tenancy) == 1
    row = interview(tenancy, interview_id)
    assert (row["status"], row["drop_reason"]) == ("expired", "technical_issue")


def test_reinviting_replaces_the_link_and_sends_a_new_invitation(
    tenancy: Tenancy, candidates: list[CandidateUser], queue: RecordingQueue
) -> None:
    paolo = candidates[0]
    old_token, old_id = invite(tenancy, paolo, **lapsed(datetime.now(UTC) - timedelta(hours=1)))
    expire(tenancy)
    application_id = application_of(tenancy, old_id)

    done = ok(admin(tenancy).post(f"/v1/applications/{application_id}/reinvite"))
    assert done == {"reinvited": 1}

    old = interview(tenancy, old_id)
    [new] = sql(
        tenancy,
        "select * from interviews where application_id = $1 and superseded_by is null",
        application_id,
    )
    assert old["superseded_by"] == new["id"]
    assert (new["status"], new["drop_reason"], new["talk_seconds"]) == ("not_started", None, None)
    assert new["expires_at"] > datetime.now(UTC) + timedelta(days=2)
    # The old link now says it was replaced; the analytics no longer count it.
    assert link(tenancy, old_token, paolo)["state"] == "unavailable"
    assert sql(tenancy, "select * from v_dropoff_reasons where interview_id = $1", old_id) == []

    invitation = emails(tenancy, new["id"], "interview_invitation")[-1]
    token = invitation["html_rendered"].split("/interview/")[1].split('"')[0]
    assert hash_token(token) == new["token_hash"]
    assert link(tenancy, token, paolo)["state"] == "welcome"
    assert ("send_email", (invitation["id"],)) in queue.enqueued
    [reminder] = emails(tenancy, new["id"], "interview_reminder")
    assert reminder["scheduled_for"] == new["expires_at"] - timedelta(hours=24)

    [audit] = sql(
        tenancy,
        "select * from audit_log where action = 'application.reinvited' and entity_id = $1",
        application_id,
    )
    assert audit["actor_id"] == tenancy.member("a", Role.ADMIN).user_id


def test_reinviting_from_a_left_interview_goes_back_to_invited(
    tenancy: Tenancy, candidates: list[CandidateUser], realtime: FakeRealtime
) -> None:
    maria = candidates[0]
    token, interview_id = ready(tenancy, maria)
    session = ok(start(tenancy, token, maria))
    application_id = application_of(tenancy, interview_id)

    # Not while the candidate is talking to the interviewer.
    url = f"/v1/applications/{application_id}/reinvite"
    refused(admin(tenancy).post(url), 409, "reinvite_not_allowed")

    age(tenancy, session["attempt_id"], seconds=61)
    watchdog(tenancy, realtime, interview_id)
    assert finish_email(tenancy, interview_id)["status"] == "scheduled"

    ok(admin(tenancy).post(url))
    [row] = sql(tenancy, "select stage from applications where id = $1", application_id)
    assert row["stage"] == "invited"
    # The old link's nudge won't go out with a dead link.
    assert finish_email(tenancy, interview_id)["status"] == "cancelled"


def test_finished_interviews_are_not_reinvited(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    _, interview_id = invite(tenancy, candidates[0])
    update(tenancy, interview_id, "status = 'completed'")
    sql(
        tenancy,
        "update applications set stage = 'scoring' where id = $1",
        application_of(tenancy, interview_id),
    )
    url = f"/v1/applications/{application_of(tenancy, interview_id)}/reinvite"
    refused(admin(tenancy).post(url), 409, "reinvite_not_allowed")


def test_reinvite_all_covers_everyone_who_did_not_finish(
    tenancy: Tenancy, candidates: list[CandidateUser], realtime: FakeRealtime
) -> None:
    paolo, maria, jun = candidates
    past = datetime.now(UTC) - timedelta(minutes=5)
    _, expired_id = invite(tenancy, paolo, **lapsed(past))
    _, waiting_id = invite(tenancy, maria)
    _, tech_id = invite(tenancy, jun, drop_reason="technical_issue")
    pipeline_id = interview_pipeline(tenancy, expired_id)
    for other in (waiting_id, tech_id):
        sql(
            tenancy,
            "update applications set pipeline_id = $2 where id = $1",
            application_of(tenancy, other),
            pipeline_id,
        )

    url = f"/v1/pipelines/{pipeline_id}/reinvite"
    refused(admin(tenancy).post(url, json={"scope": "everyone"}), 422, "validation_failed")
    done = ok(admin(tenancy).post(url, json={"scope": "all_unfinished"}))

    # The link still waiting to be used is left as it is.
    assert done == {"reinvited": 2}
    assert interview(tenancy, expired_id)["superseded_by"] is not None
    assert interview(tenancy, tech_id)["superseded_by"] is not None
    assert interview(tenancy, waiting_id)["superseded_by"] is None
    # Nothing left to re-invite.
    assert ok(admin(tenancy).post(url, json={"scope": "all_unfinished"})) == {"reinvited": 0}


def test_reinvites_follow_workspaces_departments_and_roles(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    _, interview_id = invite(tenancy, candidates[0], **lapsed(datetime.now(UTC)))
    application_id = application_of(tenancy, interview_id)
    pipeline_id = interview_pipeline(tenancy, interview_id)
    one = f"/v1/applications/{application_id}/reinvite"
    every = f"/v1/pipelines/{pipeline_id}/reinvite"
    body = {"scope": "all_unfinished"}

    # Admins and Recruiters of another workspace learn nothing (Hiring managers can't re-invite).
    for role in (Role.ADMIN, Role.RECRUITER):
        outsider = tenancy.client("b", role)
        refused(outsider.post(one), 404, "not_found")
        refused(outsider.post(every, json=body), 404, "not_found")
    hiring_manager = tenancy.client("a", Role.HIRING_MANAGER)
    refused(hiring_manager.post(one), 403, "forbidden")
    refused(hiring_manager.post(every, json=body), 403, "forbidden")

    # A Recruiter reaches only their departments' pipelines (this one is in No department).
    recruiter = tenancy.client("a", Role.RECRUITER)
    refused(recruiter.post(one), 404, "not_found")
    refused(recruiter.post(every, json=body), 404, "not_found")
    engineering = draft(tenancy, department_id=str(tenancy.workspace("a").department_id))
    ok(admin(tenancy).post(f"/v1/pipelines/{engineering['id']}/publish", json=CONFIRM))
    sql(
        tenancy,
        "update applications set pipeline_id = $2 where id = $1",
        application_id,
        uuid.UUID(engineering["id"]),
    )
    assert ok(recruiter.post(one)) == {"reinvited": 1}
    assert ok(recruiter.post(f"/v1/pipelines/{engineering['id']}/reinvite", json=body)) == {
        "reinvited": 0
    }


def test_the_reminder_follows_the_pipeline_toggle(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    _, interview_id = invite(tenancy, candidates[0])
    application_id = application_of(tenancy, interview_id)
    pipeline_id = interview_pipeline(tenancy, interview_id)

    async def issue(db: AsyncSession) -> list[str]:
        application = await db.get(Application, application_id)
        stored = await db.get(Pipeline, pipeline_id)
        assert application is not None and stored is not None
        # The setup is locked once live, so a copy with the toggle off stands in.
        pipeline = Pipeline(
            link_expiry_days=stored.link_expiry_days,
            interview_format=stored.interview_format,
            reminder_enabled=False,
        )
        # Room for a new live interview; rolled back below.
        await db.execute(delete(Interview).where(Interview.application_id == application_id))
        issued = await interview_lifecycle.issue_link(
            db, get_settings(), application, pipeline, datetime.now(UTC),
            interview_id=uuid.uuid4(),
        )  # fmt: skip
        keys = [message.template_key for message in issued.emails]
        await db.rollback()
        return keys

    assert db_run(tenancy, issue) == ["interview_invitation"]


def interview_pipeline(tenancy: Tenancy, interview_id: uuid.UUID) -> uuid.UUID:
    [row] = sql(
        tenancy,
        "select a.pipeline_id from interviews i join applications a on a.id = i.application_id "
        "where i.id = $1",
        interview_id,
    )
    pipeline_id: uuid.UUID = row["pipeline_id"]
    return pipeline_id
