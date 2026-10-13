"""ASMT-003: reviewing integrity flags on DASH-003's hand-counted applications. The flagged one
(didn't pass, with open flags) gets two flags and the returning candidate's No department one
gets a third: the overlay clears only after the last review, the note rule, the audit row, the
profile's review details, and each caller's reach."""

import uuid
from typing import Any

import pytest

from app.core.context import Role
from tests.integration.test_analytics import get, world  # noqa: F401 (fixture)
from tests.integration.test_pipelines import admin, ok, sql
from tests.tenancy.harness import Tenancy


def add_flag(tenancy: Tenancy, application_id: uuid.UUID, kind: str, start_ms: int) -> str:
    rows = sql(
        tenancy,
        "insert into integrity_flags (workspace_id, interview_id, application_id, type, "
        "start_ms, end_ms, confidence) select workspace_id, id, application_id, $2, $3, $3 + "
        "5000, 0.85 from interviews where application_id = $1 returning id",
        application_id,
        kind,
        start_ms,
    )
    sql(tenancy, "update applications set has_open_flags = true where id = $1", application_id)
    return str(rows[0]["id"])


def application_of(tenancy: Tenancy, name: str, title: str) -> uuid.UUID:
    rows = sql(
        tenancy,
        "select a.id from applications a join candidates c on c.id = a.candidate_id "
        "join pipelines p on p.id = a.pipeline_id where a.workspace_id = $1 "
        "and c.full_name = $2 and p.title = $3",
        tenancy.workspace("a").id,
        name,
        title,
    )
    return uuid.UUID(str(rows[0]["id"]))


@pytest.fixture
def flags(tenancy: Tenancy, world: dict[str, Any]) -> dict[str, Any]:  # noqa: F811
    flagged = application_of(tenancy, "Candidate 50", "Backend Engineer")
    other = application_of(tenancy, "Candidate 0", "Office Manager")
    return {
        "application": str(flagged),
        "voice": add_flag(tenancy, flagged, "second_voice", 60_000),
        "timing": add_flag(tenancy, flagged, "unusual_timing", 120_000),
        "other_application": str(other),
        "no_department": add_flag(tenancy, other, "read_aloud", 30_000),
    }


def resolve(client: Any, flag_id: str, **body: Any) -> Any:
    return client.patch(f"/v1/integrity-flags/{flag_id}", json=body)


def test_the_overlay_clears_after_the_last_review(tenancy: Tenancy, flags: dict[str, Any]) -> None:
    client = admin(tenancy)
    first = ok(resolve(client, flags["voice"], status="no_concern"))
    assert first["flag"]["status"] == "no_concern"
    assert first["flag"]["note"] is None
    assert first["flag"]["resolved_at"] is not None
    assert first["application"] == {"id": flags["application"], "flagged": True, "open_flags": 1}

    profile = get(client, f"/v1/applications/{flags['application']}")
    assert (profile["flagged"], profile["open_flags"], profile["stage"]) == (
        True,
        1,
        "did_not_pass",
    )

    last = ok(resolve(client, flags["timing"], status="concern_confirmed", note=" Read notes. "))
    assert last["flag"]["note"] == "Read notes."
    assert last["application"] == {"id": flags["application"], "flagged": False, "open_flags": 0}

    profile = get(client, f"/v1/applications/{flags['application']}")
    # The stage never changes; the application leaves the Flagged filter.
    assert (profile["flagged"], profile["open_flags"], profile["stage"]) == (
        False,
        0,
        "did_not_pass",
    )
    reviewed = {flag["type"]: flag for flag in profile["integrity"]["flags"]}
    assert reviewed["unusual_timing"]["status"] == "concern_confirmed"
    assert reviewed["unusual_timing"]["note"] == "Read notes."
    assert reviewed["unusual_timing"]["resolved_by"]
    listed = get(client, f"/v1/pipelines/{profile['pipeline']['id']}/applications", stage="flagged")
    assert listed["counts"]["flagged"] == 0

    # Reviewed again: the latest review stands and it never reopens.
    again = ok(resolve(client, flags["timing"], status="no_concern"))
    assert (again["flag"]["status"], again["flag"]["note"]) == ("no_concern", None)
    assert again["application"]["open_flags"] == 0


def test_a_concern_needs_a_note(tenancy: Tenancy, flags: dict[str, Any]) -> None:
    for body in ({"status": "concern_confirmed"}, {"status": "concern_confirmed", "note": "  "}):
        assert resolve(admin(tenancy), flags["voice"], **body).status_code == 422
    assert resolve(admin(tenancy), flags["voice"], status="open").status_code == 422
    long = resolve(admin(tenancy), flags["voice"], status="no_concern", note="x" * 1001)
    assert long.status_code == 422


def test_reviews_are_audited_without_the_note(tenancy: Tenancy, flags: dict[str, Any]) -> None:
    ok(resolve(admin(tenancy), flags["voice"], status="concern_confirmed", note="Someone spoke."))
    rows = sql(
        tenancy,
        "select action, actor_id, data from audit_log where entity_id = $1",
        uuid.UUID(flags["voice"]),
    )
    assert len(rows) == 1
    assert rows[0]["action"] == "integrity_flag.resolved"
    assert rows[0]["actor_id"] == tenancy.member("a", Role.ADMIN).user_id
    assert "Someone spoke" not in rows[0]["data"]


def test_who_can_review(tenancy: Tenancy, flags: dict[str, Any]) -> None:
    recruiter = tenancy.client("a", Role.RECRUITER)
    ok(resolve(recruiter, flags["voice"], status="no_concern"))
    # No department is Admins only.
    response = resolve(recruiter, flags["no_department"], status="no_concern")
    assert (response.status_code, response.json()["code"]) == (404, "not_found")
    manager = tenancy.client("a", Role.HIRING_MANAGER)
    assert resolve(manager, flags["timing"], status="no_concern").status_code == 403
    ok(resolve(admin(tenancy), flags["no_department"], status="no_concern"))

    for role in (Role.ADMIN, Role.RECRUITER):
        response = resolve(tenancy.client("b", role), flags["timing"], status="no_concern")
        assert (response.status_code, response.json()["code"]) == (404, "not_found")
    assert resolve(admin(tenancy), str(uuid.uuid4()), status="no_concern").status_code == 404
    assert resolve(tenancy.anonymous(), flags["timing"], status="no_concern").status_code == 401
    # Nothing outside the caller's reach changed.
    rows = sql(
        tenancy, "select status from integrity_flags where id = $1", uuid.UUID(flags["timing"])
    )
    assert rows[0]["status"] == "open"
