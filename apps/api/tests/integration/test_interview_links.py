"""INTV-002: the interview link page's state (S-01) from `GET /v1/candidate/interviews/{token}`.
Every state is reachable; nothing personal shows before the applying account signs in; another
account, a TA's password session or another workspace's candidate learns nothing about them."""

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
from tests.integration.test_pipelines import ok, sql
from tests.integration.test_post_screen import owner_sql
from tests.integration.test_screening import resume_pdf, submit
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes", "queue"]


@pytest.fixture
def tenancy_app(storage: SupabaseStorage, queue: RecordingQueue) -> FastAPI:
    return create_app(storage=storage, job_queue=queue)


def invite(tenancy: Tenancy, candidate: CandidateUser, **columns: Any) -> tuple[str, uuid.UUID]:
    """An application by `candidate` in workspace a with an interview link, as SCREEN-003 makes
    it. Returns the link token and the interview's ID."""
    application_id = submit(tenancy, candidate, resume_pdf())
    sql(tenancy, "update applications set stage = 'invited' where id = $1", application_id)
    token, token_hash = new_token()
    values = {
        "format": "video_voice",
        "expires_at": datetime.now(UTC) + timedelta(days=5),
        **columns,
    }
    names = ", ".join(values)
    placeholders = ", ".join(f"${index + 4}" for index in range(len(values)))
    [row] = sql(
        tenancy,
        f"insert into interviews (workspace_id, application_id, token_hash, {names}) "
        f"values ($1, $2, $3, {placeholders}) returning id",
        tenancy.workspace("a").id,
        application_id,
        token_hash,
        *values.values(),
    )
    return token, row["id"]


def link(tenancy: Tenancy, token: str, candidate: CandidateUser | None = None) -> dict[str, Any]:
    headers = candidate.headers if candidate else {}
    return ok(tenancy.anonymous().get(f"/v1/candidate/interviews/{token}", headers=headers))


def update(tenancy: Tenancy, interview_id: uuid.UUID, assignments: str, *args: object) -> None:
    sql(tenancy, f"update interviews set {assignments} where id = $1", interview_id, *args)


def stage(tenancy: Tenancy, interview_id: uuid.UUID, value: str) -> None:
    sql(
        tenancy,
        "update applications set stage = $2 "
        "where id = (select application_id from interviews where id = $1)",
        interview_id,
        value,
    )


def test_the_applying_account_sees_where_it_is_in_the_interview(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    paolo = candidates[0]
    token, interview_id = invite(tenancy, paolo)

    welcome = link(tenancy, token, paolo)
    assert welcome["state"] == "welcome"
    assert welcome["first_name"] == "Paolo"
    assert welcome["format"] == "video_voice"
    assert welcome["job_title"] and welcome["company"]["name"]
    assert welcome["expires_label"]
    assert welcome["masked_email"] is None and welcome["minutes_left"] is None

    # Left mid-interview with 11 minutes 40 seconds of talk: about 19 minutes of the 30 remain.
    update(tenancy, interview_id, "status = 'abandoned', talk_seconds = 700")
    resume = link(tenancy, token, paolo)
    assert (resume["state"], resume["minutes_left"]) == ("resume", 19)

    update(tenancy, interview_id, "drop_reason = 'technical_issue'")
    assert link(tenancy, token, paolo)["state"] == "technical_problem"

    # Finished: it stays finished after the link's expiry and whatever happens next.
    update(
        tenancy,
        interview_id,
        "status = 'completed', drop_reason = null, invited_at = now() - interval '6 days', expires_at = now() - interval '1 day'",
    )
    stage(tenancy, interview_id, "rejected")
    completed = link(tenancy, token, paolo)
    assert (completed["state"], completed["first_name"]) == ("completed", "Paolo")


def test_a_closed_or_expired_link_says_so_to_anyone(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    paolo = candidates[0]
    token, interview_id = invite(tenancy, paolo)

    update(
        tenancy,
        interview_id,
        "invited_at = now() - interval '6 days', expires_at = now() - interval '1 day'",
    )
    for viewer in (None, paolo, candidates[1]):
        expired = link(tenancy, token, viewer)
        assert expired["state"] == "expired"
        assert expired["first_name"] is None and expired["masked_email"] is None

    # Rejected before the interview, or the pipeline cancelled: no longer available.
    update(tenancy, interview_id, "expires_at = now() + interval '5 days'")
    stage(tenancy, interview_id, "rejected")
    assert link(tenancy, token)["state"] == "unavailable"
    stage(tenancy, interview_id, "invited")
    owner_sql(
        tenancy,
        "update pipelines set status = 'cancelled' where id = "
        "(select pipeline_id from applications a join interviews i on i.application_id = a.id "
        "where i.id = $1)",
        interview_id,
    )
    assert link(tenancy, token, paolo)["state"] == "unavailable"


def test_a_replaced_link_is_no_longer_available(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    paolo = candidates[0]
    token, interview_id = invite(tenancy, paolo)
    # A re-invite (INTV-007) points the old row at its replacement; written as the owner so
    # the test needs no second live row (one per application).
    owner_sql(
        tenancy,
        "update interviews set superseded_by = gen_random_uuid() where id = $1",
        interview_id,
    )
    assert link(tenancy, token, paolo)["state"] == "unavailable"


def test_only_the_applying_account_gets_past_sign_in(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    paolo, other = candidates[0], candidates[1]
    token, _ = invite(tenancy, paolo)

    signed_out = link(tenancy, token)
    assert signed_out["state"] == "sign_in"
    assert signed_out["masked_email"] == f"{paolo.email[0]}•••@example.com"
    assert signed_out["first_name"] is None

    wrong = link(tenancy, token, other)
    assert wrong["state"] == "wrong_account"
    assert wrong["first_name"] is None and wrong["masked_email"] is None

    # A TA's email + password session isn't a candidate sign-in, even for the hiring team.
    admin = tenancy.client("a", Role.ADMIN)
    assert ok(admin.get(f"/v1/candidate/interviews/{token}"))["state"] == "sign_in"
    # Another workspace's members and candidates are no different.
    outsider = tenancy.client("b", Role.ADMIN)
    assert ok(outsider.get(f"/v1/candidate/interviews/{token}"))["state"] == "sign_in"


def test_unknown_and_malformed_tokens_are_not_found(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    token, _ = invite(tenancy, candidates[0])
    client = tenancy.anonymous()
    for wrong in (token[:-1], token + "x", "nope"):
        response = client.get(f"/v1/candidate/interviews/{wrong}")
        assert response.status_code == 404, response.text
        assert response.json()["code"] == "interview_not_found"
    assert client.get(f"/v1/candidate/interviews/{'a' * 129}").status_code == 422
    # A session that fails its check is refused rather than read as signed out.
    response = client.get(
        f"/v1/candidate/interviews/{token}", headers={"Authorization": "Bearer not-a-token"}
    )
    assert response.status_code == 401
