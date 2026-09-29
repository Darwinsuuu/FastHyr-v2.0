"""WS-003: members. Admins list members, change role and departments, and remove access; the owner
and your own access are locked; changes apply on the next request; last active is throttled."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg

from app.core.context import Role
from tests.tenancy.harness import Tenancy


def db(tenancy: Tenancy, query: str, *args: object) -> list[asyncpg.Record]:
    async def run() -> list[asyncpg.Record]:
        connection = await asyncpg.connect(tenancy.supabase.database_url)
        try:
            return list(await connection.fetch(query, *args))
        finally:
            await connection.close()

    return asyncio.run(run())


def members(tenancy: Tenancy, role: Role = Role.ADMIN) -> list[dict[str, Any]]:
    response = tenancy.client("a", role).get("/v1/members")
    assert response.status_code == 200, response.text
    result: list[dict[str, Any]] = response.json()["members"]
    return result


def member_url(tenancy: Tenancy, role: Role, workspace: str = "a") -> str:
    return f"/v1/members/{tenancy.member(workspace, role).member_id}"


def add_department(tenancy: Tenancy, name: str) -> str:
    response = tenancy.client("a", Role.ADMIN).post("/v1/departments", json={"name": name})
    assert response.status_code == 201, response.text
    department_id: str = response.json()["id"]
    return department_id


def test_admin_lists_active_members_owner_first(tenancy: Tenancy) -> None:
    body = members(tenancy)

    owner = body[0]
    assert owner["is_owner"] and owner["is_you"]
    assert owner["email"] == tenancy.member("a", Role.ADMIN).email
    assert owner["departments"] == []  # Admins see every department
    assert owner["last_active_at"] is not None  # this request counted as activity
    ids = {m["id"] for m in body}
    assert ids == {str(tenancy.member("a", role).member_id) for role in Role}
    recruiter = next(m for m in body if m["role"] == "recruiter")
    assert recruiter["departments"] == [
        {"id": str(tenancy.workspace("a").department_id), "name": "Engineering"}
    ]
    assert not recruiter["is_you"] and recruiter["status"] == "active"


def test_only_admins_manage_members(tenancy: Tenancy) -> None:
    for role in (Role.RECRUITER, Role.HIRING_MANAGER):
        client = tenancy.client("a", role)
        for response in (
            client.get("/v1/members"),
            client.patch(member_url(tenancy, Role.HIRING_MANAGER), json={"role": "admin"}),
            client.delete(member_url(tenancy, Role.HIRING_MANAGER)),
        ):
            assert response.status_code == 403, response.text
            assert response.json()["code"] == "forbidden"


def test_members_of_other_workspaces_are_hidden(tenancy: Tenancy) -> None:
    assert not {m["id"] for m in members(tenancy)} & {
        str(tenancy.member("b", role).member_id) for role in Role
    }
    # Members are Admin-only, so only the other workspace's Admin gets past the role check.
    other_admin = tenancy.client("b", Role.ADMIN)
    url = member_url(tenancy, Role.RECRUITER)
    for response in (
        other_admin.patch(url, json={"role": "hiring_manager"}),
        other_admin.delete(url),
    ):
        assert (response.status_code, response.json()["code"]) == (404, "not_found")
    recruiter = next(m for m in members(tenancy) if m["id"] == url.rsplit("/", 1)[1])
    assert recruiter["role"] == "recruiter"


def test_access_changes_apply_on_the_next_request(tenancy: Tenancy) -> None:
    admin = tenancy.client("a", Role.ADMIN)
    manager = tenancy.client("a", Role.HIRING_MANAGER)
    sales = add_department(tenancy, "Sales")
    assert manager.get("/v1/members").status_code == 403

    changed = admin.patch(
        member_url(tenancy, Role.HIRING_MANAGER),
        json={"role": "recruiter", "department_ids": [sales, sales]},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["role"] == "recruiter"
    assert changed.json()["departments"] == [{"id": sales, "name": "Sales"}]

    promoted = admin.patch(member_url(tenancy, Role.HIRING_MANAGER), json={"role": "admin"})
    assert promoted.json()["departments"] == []  # Admins see every department
    assert manager.get("/v1/members").status_code == 200

    audit = db(
        tenancy,
        "select action, data from audit_log where workspace_id = $1 and entity_id = $2",
        tenancy.workspace("a").id,
        tenancy.member("a", Role.HIRING_MANAGER).member_id,
    )
    assert [row["action"] for row in audit] == ["member.access_changed"] * 2


def test_departments_must_belong_to_the_workspace(tenancy: Tenancy) -> None:
    admin = tenancy.client("a", Role.ADMIN)
    other = str(tenancy.workspace("b").department_id)
    for department_ids in ([other], [str(uuid.uuid4())]):
        response = admin.patch(
            member_url(tenancy, Role.RECRUITER), json={"department_ids": department_ids}
        )
        assert (response.status_code, response.json()["code"]) == (422, "unknown_department")


def test_owner_and_own_access_are_locked(tenancy: Tenancy) -> None:
    owner = tenancy.client("a", Role.ADMIN)
    # A second Admin (the Recruiter, promoted) tries to change the owner and themselves.
    owner.patch(member_url(tenancy, Role.RECRUITER), json={"role": "admin"})
    second_admin = tenancy.client("a", Role.RECRUITER)

    for client, target, code in (
        (second_admin, Role.ADMIN, "owner_access_locked"),
        (owner, Role.ADMIN, "owner_access_locked"),
        (second_admin, Role.RECRUITER, "own_access_locked"),
    ):
        for response in (
            client.patch(member_url(tenancy, target), json={"role": "hiring_manager"}),
            client.delete(member_url(tenancy, target)),
        ):
            assert (response.status_code, response.json()["code"]) == (409, code)


def test_removed_members_lose_access_on_their_next_request(tenancy: Tenancy) -> None:
    admin = tenancy.client("a", Role.ADMIN)
    manager = tenancy.client("a", Role.HIRING_MANAGER)
    assert manager.get("/v1/departments").status_code == 200

    removed = admin.delete(member_url(tenancy, Role.HIRING_MANAGER))

    assert removed.status_code == 204
    refused = manager.get("/v1/departments")
    assert (refused.status_code, refused.json()["code"]) == (403, "not_a_member")
    assert str(tenancy.member("a", Role.HIRING_MANAGER).member_id) not in {
        m["id"] for m in members(tenancy)
    }
    assert admin.delete(member_url(tenancy, Role.HIRING_MANAGER)).status_code == 404
    rows = db(
        tenancy,
        "select status, (select count(*) from member_departments d where d.member_id = m.id) n"
        " from workspace_members m where id = $1",
        tenancy.member("a", Role.HIRING_MANAGER).member_id,
    )
    assert (rows[0]["status"], rows[0]["n"]) == ("removed", 0)


def test_last_active_is_written_at_most_every_five_minutes(tenancy: Tenancy) -> None:
    member_id = tenancy.member("a", Role.RECRUITER).member_id
    client = tenancy.client("a", Role.RECRUITER)

    def last_active() -> datetime:
        value: datetime = db(
            tenancy, "select last_active_at from workspace_members where id = $1", member_id
        )[0]["last_active_at"]
        return value

    def set_last_active(value: datetime | None) -> None:
        db(
            tenancy,
            "update workspace_members set last_active_at = $2 where id = $1",
            member_id,
            value,
        )

    set_last_active(None)
    client.get("/v1/departments")
    assert datetime.now(UTC) - last_active() < timedelta(minutes=1)

    recent = datetime.now(UTC) - timedelta(minutes=2)
    set_last_active(recent)
    client.get("/v1/departments")
    assert last_active() == recent

    set_last_active(datetime.now(UTC) - timedelta(minutes=10))
    client.get("/v1/departments")
    assert datetime.now(UTC) - last_active() < timedelta(minutes=1)
