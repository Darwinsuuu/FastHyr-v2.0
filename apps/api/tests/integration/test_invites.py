"""WS-004: member invites. Admins invite by email with a role and departments, resend (the old
code stops working) and revoke; inviting the same email again replaces the pending invite; revoked
and expired invites can't be accepted."""

import asyncio
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.core.context import Role
from app.services import invites as invite_service
from tests.tenancy.harness import Tenancy

CODE = re.compile(r"^[A-HJ-KM-NP-Z2-9]{4}-[A-HJ-KM-NP-Z2-9]{4}$")


def db(tenancy: Tenancy, query: str, *args: object) -> list[asyncpg.Record]:
    async def run() -> list[asyncpg.Record]:
        connection = await asyncpg.connect(tenancy.supabase.database_url)
        try:
            return list(await connection.fetch(query, *args))
        finally:
            await connection.close()

    return asyncio.run(run())


def invite(tenancy: Tenancy, email: str, role: str = "recruiter", **body: Any) -> dict[str, Any]:
    response = tenancy.client("a", Role.ADMIN).post(
        "/v1/invites", json={"email": email, "role": role, **body}
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def pending(tenancy: Tenancy) -> list[dict[str, Any]]:
    response = tenancy.client("a", Role.ADMIN).get("/v1/invites")
    assert response.status_code == 200, response.text
    result: list[dict[str, Any]] = response.json()["invites"]
    return result


def accept(tenancy: Tenancy, code: str, role: Role = Role.RECRUITER) -> tuple[int, str | None]:
    """Workspace B's `role` accepts an invite to workspace A with their own (verified) email."""
    response = tenancy.client("b", role).post("/v1/invites/accept", json={"code": code})
    return response.status_code, response.json().get("code")


def invitee(tenancy: Tenancy, role: Role = Role.RECRUITER) -> str:
    """Someone from workspace B, so they can sign in and accept an invite to workspace A."""
    return tenancy.member("b", role).email


def test_admin_invites_with_a_role_and_departments(tenancy: Tenancy) -> None:
    department = tenancy.workspace("a").department_id
    email = invitee(tenancy)

    created = invite(tenancy, email.upper(), department_ids=[str(department)] * 2)

    assert created["email"] == email
    assert created["role"] == "recruiter"
    assert created["departments"] == [{"id": str(department), "name": "Engineering"}]
    assert CODE.match(created["code"])
    sent = datetime.fromisoformat(created["sent_at"])
    assert datetime.fromisoformat(created["expires_at"]) - sent == timedelta(days=7)
    assert abs(datetime.now(UTC) - sent) < timedelta(minutes=1)
    assert pending(tenancy) == [created]

    # Admins see every department, so an Admin invite carries none.
    admin = invite(tenancy, invitee(tenancy, Role.HIRING_MANAGER), "admin")
    assert admin["departments"] == []
    [row] = db(tenancy, "select department_ids, token_hash from invites where id = $1", admin["id"])
    assert row["department_ids"] == []
    assert len(row["token_hash"]) == 64  # only the token's SHA-256 is stored

    audit = db(
        tenancy,
        "select action, data from audit_log where entity_id = $1",
        uuid.UUID(created["id"]),
    )
    assert [r["action"] for r in audit] == ["member.invited"]
    assert email not in audit[0]["data"]  # no personal data in the audit log

    status, _ = accept(tenancy, created["code"])
    assert status == 200
    assert pending(tenancy) == [admin]


def test_only_admins_manage_invites(tenancy: Tenancy) -> None:
    created = invite(tenancy, invitee(tenancy))
    for role in (Role.RECRUITER, Role.HIRING_MANAGER):
        client = tenancy.client("a", role)
        for response in (
            client.get("/v1/invites"),
            client.post("/v1/invites", json={"email": "x@example.com", "role": "recruiter"}),
            client.post(f"/v1/invites/{created['id']}/resend"),
            client.delete(f"/v1/invites/{created['id']}"),
        ):
            assert (response.status_code, response.json()["code"]) == (403, "forbidden")


def test_invites_of_other_workspaces_are_hidden(tenancy: Tenancy) -> None:
    created = invite(tenancy, invitee(tenancy))
    other_admin = tenancy.client("b", Role.ADMIN)

    assert other_admin.get("/v1/invites").json()["invites"] == []
    for response in (
        other_admin.post(f"/v1/invites/{created['id']}/resend"),
        other_admin.delete(f"/v1/invites/{created['id']}"),
    ):
        assert (response.status_code, response.json()["code"]) == (404, "not_found")
    assert pending(tenancy) == [created]
    # Departments must be this workspace's.
    response = tenancy.client("a", Role.ADMIN).post(
        "/v1/invites",
        json={
            "email": "someone@example.com",
            "role": "recruiter",
            "department_ids": [str(tenancy.workspace("b").department_id)],
        },
    )
    assert (response.status_code, response.json()["code"]) == (422, "unknown_department")


def test_inviting_the_same_email_again_replaces_the_invite(tenancy: Tenancy) -> None:
    email = invitee(tenancy)
    first = invite(tenancy, email, department_ids=[str(tenancy.workspace("a").department_id)])

    second = invite(tenancy, f"  {email.upper()} ", "hiring_manager")

    assert second["id"] == first["id"]
    assert second["code"] != first["code"]
    assert (second["role"], second["departments"]) == ("hiring_manager", [])
    assert pending(tenancy) == [second]
    assert accept(tenancy, first["code"]) == (404, "invite_not_found")
    assert accept(tenancy, second["code"]) == (200, None)
    [member] = db(
        tenancy,
        "select role from workspace_members where workspace_id = $1 and user_id = $2",
        tenancy.workspace("a").id,
        tenancy.member("b", Role.RECRUITER).user_id,
    )
    assert member["role"] == "hiring_manager"


def test_members_and_bad_emails_cannot_be_invited(tenancy: Tenancy) -> None:
    admin = tenancy.client("a", Role.ADMIN)
    member = admin.post(
        "/v1/invites",
        json={"email": tenancy.member("a", Role.RECRUITER).email.upper(), "role": "recruiter"},
    )
    assert (member.status_code, member.json()["code"]) == (409, "already_a_member")

    for email in ("", "not-an-email", "a@b", "two@@example.com"):
        response = admin.post("/v1/invites", json={"email": email, "role": "recruiter"})
        assert (response.status_code, response.json()["code"]) == (422, "validation_failed")
        assert email not in response.text or not email  # submitted values are never echoed
    assert pending(tenancy) == []


def test_resend_invalidates_the_old_code(tenancy: Tenancy) -> None:
    created = invite(tenancy, invitee(tenancy))
    db(
        tenancy,
        "update invites set expires_at = now() + interval '1 day' where id = $1",
        uuid.UUID(created["id"]),
    )

    response = tenancy.client("a", Role.ADMIN).post(f"/v1/invites/{created['id']}/resend")

    assert response.status_code == 200, response.text
    resent = response.json()
    assert resent["id"] == created["id"]
    assert resent["code"] != created["code"]
    assert datetime.fromisoformat(resent["expires_at"]) > datetime.now(UTC) + timedelta(days=6)
    assert accept(tenancy, created["code"]) == (404, "invite_not_found")
    assert accept(tenancy, resent["code"]) == (200, None)
    # Accepted invites can't be resent or revoked.
    again = tenancy.client("a", Role.ADMIN).post(f"/v1/invites/{created['id']}/resend")
    assert again.status_code == 404


def test_revoked_invites_cannot_be_accepted(tenancy: Tenancy) -> None:
    created = invite(tenancy, invitee(tenancy))
    admin = tenancy.client("a", Role.ADMIN)

    assert admin.delete(f"/v1/invites/{created['id']}").status_code == 204

    assert pending(tenancy) == []
    assert accept(tenancy, created["code"]) == (410, "invite_invalid")
    assert admin.post(f"/v1/invites/{created['id']}/resend").status_code == 404
    assert admin.delete(f"/v1/invites/{created['id']}").status_code == 404
    actions = db(
        tenancy,
        "select action from audit_log where entity_id = $1 order by created_at",
        uuid.UUID(created["id"]),
    )
    assert [r["action"] for r in actions] == ["member.invited", "member.invite_revoked"]
    # A new invite to the same email is a fresh one.
    assert invite(tenancy, created["email"])["id"] != created["id"]


def test_expired_invites_are_hidden_swept_and_refused(tenancy: Tenancy) -> None:
    email = invitee(tenancy)
    created = invite(tenancy, email)
    db(
        tenancy,
        "update invites set expires_at = now() - interval '1 minute' where id = $1",
        uuid.UUID(created["id"]),
    )

    assert pending(tenancy) == []
    assert accept(tenancy, created["code"]) == (410, "invite_expired")
    admin = tenancy.client("a", Role.ADMIN)
    assert admin.post(f"/v1/invites/{created['id']}/resend").status_code == 404

    async def sweep() -> int:
        engine = create_async_engine(get_settings().async_database_url)
        try:
            async with AsyncSession(engine) as session:
                count = await invite_service.expire_invites(session)
                await session.commit()
                return count
        finally:
            await engine.dispose()

    assert asyncio.run(sweep()) >= 1
    [row] = db(tenancy, "select status from invites where id = $1", uuid.UUID(created["id"]))
    assert row["status"] == "expired"
    assert accept(tenancy, created["code"]) == (410, "invite_expired")
    assert invite(tenancy, email)["id"] != created["id"]
