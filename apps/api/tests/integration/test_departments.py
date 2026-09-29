"""WS-002: departments. Admins create, rename and delete them; names are unique and "No department"
is reserved; deleting one moves its pipelines to No department and removes member access."""

import asyncio
import uuid
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


def add_pipeline(tenancy: Tenancy, key: str, department_id: uuid.UUID | None, status: str) -> None:
    db(
        tenancy,
        "insert into pipelines (workspace_id, department_id, status) values ($1, $2, $3)",
        tenancy.workspace(key).id,
        department_id,
        status,
    )


def create(tenancy: Tenancy, name: str, **body: Any) -> dict[str, Any]:
    response = tenancy.client("a", Role.ADMIN).post("/v1/departments", json={"name": name, **body})
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def listing(tenancy: Tenancy, role: Role = Role.ADMIN) -> dict[str, Any]:
    response = tenancy.client("a", role).get("/v1/departments")
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


def by_name(body: dict[str, Any], name: str) -> dict[str, Any]:
    return next(d for d in body["departments"] if d["name"] == name)


def test_admin_lists_departments_with_counts(tenancy: Tenancy) -> None:
    engineering = tenancy.workspace("a").department_id
    sales = uuid.UUID(create(tenancy, "  Sales ", description=" SDRs ")["id"])
    for status in ("live", "paused", "scheduled", "closed", "cancelled", "draft"):
        add_pipeline(tenancy, "a", engineering, status)
    add_pipeline(tenancy, "a", None, "live")
    add_pipeline(tenancy, "b", None, "live")  # another workspace: never counted

    body = listing(tenancy)

    assert [d["name"] for d in body["departments"]] == ["Engineering", "Sales"]
    stats = by_name(body, "Engineering")["stats"]
    assert stats["pipelines"] == {"active": 2, "scheduled": 1, "closed": 2, "draft": 1}
    # The Admin sees everything; the Recruiter and Hiring manager are assigned to Engineering.
    assert sorted(m["role"] for m in stats["members"]) == ["admin", "hiring_manager", "recruiter"]
    sales_row = by_name(body, "Sales")
    assert sales_row["id"] == str(sales)
    assert sales_row["description"] == "SDRs"
    assert sales_row["stats"]["pipelines"] == {"active": 0, "scheduled": 0, "closed": 0, "draft": 0}
    assert [m["role"] for m in sales_row["stats"]["members"]] == ["admin"]
    assert body["no_department"]["pipelines"]["active"] == 1
    assert [m["role"] for m in body["no_department"]["members"]] == ["admin"]


def test_other_roles_see_names_only_and_cannot_write(tenancy: Tenancy) -> None:
    department_id = tenancy.workspace("a").department_id
    for role in (Role.RECRUITER, Role.HIRING_MANAGER):
        body = listing(tenancy, role)
        assert body["no_department"] is None
        assert [(d["name"], d["stats"]) for d in body["departments"]] == [("Engineering", None)]

        client = tenancy.client("a", role)
        for response in (
            client.post("/v1/departments", json={"name": "Sales"}),
            client.patch(f"/v1/departments/{department_id}", json={"name": "Eng"}),
            client.delete(f"/v1/departments/{department_id}"),
        ):
            assert response.status_code == 403, response.text
            assert response.json()["code"] == "forbidden"


def test_names_are_unique_and_no_department_is_reserved(tenancy: Tenancy) -> None:
    admin = tenancy.client("a", Role.ADMIN)
    sales = create(tenancy, "Sales")

    taken = admin.post("/v1/departments", json={"name": "engineering"})
    reserved = admin.post("/v1/departments", json={"name": " No  Department "})
    too_long = admin.post("/v1/departments", json={"name": "x" * 41})
    renamed_to_taken = admin.patch(f"/v1/departments/{sales['id']}", json={"name": "ENGINEERING"})
    recased = admin.patch(f"/v1/departments/{sales['id']}", json={"name": "SALES"})
    # Same name in another workspace is fine.
    other = tenancy.client("b", Role.ADMIN).post("/v1/departments", json={"name": "Sales"})

    assert (taken.status_code, taken.json()["code"]) == (409, "department_name_taken")
    assert (reserved.status_code, reserved.json()["code"]) == (422, "department_name_reserved")
    assert (too_long.status_code, too_long.json()["code"]) == (422, "validation_failed")
    assert renamed_to_taken.status_code == 409
    assert recased.status_code == 200 and recased.json()["name"] == "SALES"
    assert other.status_code == 201


def test_edit_renames_and_clears_description(tenancy: Tenancy) -> None:
    sales = create(tenancy, "Sales", description="SDRs")
    admin = tenancy.client("a", Role.ADMIN)

    renamed = admin.patch(f"/v1/departments/{sales['id']}", json={"name": "Revenue"}).json()
    cleared = admin.patch(f"/v1/departments/{sales['id']}", json={"description": ""}).json()

    assert (renamed["name"], renamed["description"]) == ("Revenue", "SDRs")
    assert (cleared["name"], cleared["description"]) == ("Revenue", None)
    audit = db(
        tenancy,
        "select action, data::text from audit_log where entity_id = $1 order by created_at",
        uuid.UUID(sales["id"]),
    )
    assert [row["action"] for row in audit] == ["department.created", "department.renamed"]


def test_delete_moves_pipelines_and_removes_access(tenancy: Tenancy) -> None:
    workspace = tenancy.workspace("a")
    engineering = workspace.department_id
    add_pipeline(tenancy, "a", engineering, "live")
    add_pipeline(tenancy, "a", engineering, "closed")
    db(
        tenancy,
        "insert into invites (workspace_id, email, role, department_ids, code, token_hash,"
        " invited_by) values ($1, $2, 'recruiter', $3, $4, $5, $6)",
        workspace.id,
        f"invitee-{uuid.uuid4().hex[:8]}@example.com",
        [engineering, uuid.uuid4()],
        f"T{uuid.uuid4().hex[:8].upper()}",
        uuid.uuid4().hex,
        tenancy.member("a", Role.ADMIN).user_id,
    )

    response = tenancy.client("a", Role.ADMIN).delete(f"/v1/departments/{engineering}")

    assert response.status_code == 204, response.text
    body = listing(tenancy)
    assert body["departments"] == []
    assert body["no_department"]["pipelines"] == {
        "active": 1,
        "scheduled": 0,
        "closed": 1,
        "draft": 0,
    }
    assert (
        db(tenancy, "select 1 from member_departments where department_id = $1", engineering) == []
    )
    invites = db(
        tenancy, "select department_ids from invites where workspace_id = $1", workspace.id
    )
    assert engineering not in invites[0]["department_ids"]


def test_departments_are_hidden_from_other_workspaces(tenancy: Tenancy) -> None:
    department_id = tenancy.workspace("a").department_id
    other_admin = tenancy.client("b", Role.ADMIN)

    # Writes are Admin-only, so only the other workspace's Admin gets past the role check.
    renamed = other_admin.patch(f"/v1/departments/{department_id}", json={"name": "Taken over"})
    deleted = other_admin.delete(f"/v1/departments/{department_id}")

    assert (renamed.status_code, renamed.json()["code"]) == (404, "not_found")
    assert (deleted.status_code, deleted.json()["code"]) == (404, "not_found")
    other_ids = [d["id"] for d in other_admin.get("/v1/departments").json()["departments"]]
    assert str(department_id) not in other_ids
    assert by_name(listing(tenancy), "Engineering")["id"] == str(department_id)
