"""AUTH-003: create a workspace, join one with an invite code, remember the active workspace."""

import asyncio
import hashlib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import asyncpg
import httpx2
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.auth import CurrentUser
from app.core.context import Role
from app.core.ids import new_id
from app.main import create_app
from tests.conftest import Supabase, delete_credit_rows
from tests.tenancy.harness import (
    Tenancy,
    _auth_admin_headers,
    _create_user,
    _sign_in,
)


@dataclass
class User:
    id: uuid.UUID
    email: str
    headers: dict[str, str]


async def _fetch(supabase: Supabase, query: str, *args: object) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(supabase.database_url)
    try:
        return await connection.fetch(query, *args)
    finally:
        await connection.close()


def fetch(supabase: Supabase, query: str, *args: object) -> list[asyncpg.Record]:
    return asyncio.run(_fetch(supabase, query, *args))


async def _delete_workspaces_of(supabase: Supabase, users: list["User"]) -> None:
    """Deletes what the tests made: the users' own workspaces, memberships and invites."""
    user_ids = [user.id for user in users]
    emails = [user.email.lower() for user in users]
    connection = await asyncpg.connect(supabase.database_url)
    try:
        async with connection.transaction():
            ids = [
                row["id"]
                for row in await connection.fetch(
                    "select id from workspaces where owner_id = any($1::uuid[])", user_ids
                )
            ]
            await delete_credit_rows(supabase, ids)
            await connection.execute(
                "delete from workspace_members where user_id = any($1::uuid[])", user_ids
            )
            await connection.execute("delete from invites where email = any($1::text[])", emails)
            for table in ("company_profiles", "workspace_members", "invites"):
                await connection.execute(
                    f"delete from {table} where workspace_id = any($1::uuid[])", ids
                )
            await connection.execute("delete from workspaces where id = any($1::uuid[])", ids)
    finally:
        await connection.close()


@pytest.fixture
def users(supabase: Supabase) -> Iterator[list[User]]:
    """Two signed-in, verified users with no workspace. Tests that also use `tenancy` list it
    first, so these users' invites and memberships are gone before its workspaces are deleted."""
    created: list[User] = []
    for _ in range(2):
        email = f"ws-{uuid.uuid4().hex[:10]}@example.com"
        user_id = _create_user(supabase, email)
        token = _sign_in(supabase, email)
        created.append(User(user_id, email, {"Authorization": f"Bearer {token}"}))
    yield created
    asyncio.run(_delete_workspaces_of(supabase, created))
    for user in created:
        httpx2.delete(
            f"{supabase.url}/auth/v1/admin/users/{user.id}",
            headers=_auth_admin_headers(supabase),
        )


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def add_invite(
    supabase: Supabase,
    workspace_id: uuid.UUID,
    email: str,
    *,
    role: str = "recruiter",
    department_ids: list[uuid.UUID] | None = None,
    status: str = "pending",
    expires_in: timedelta = timedelta(days=7),
    token: str | None = None,
) -> str:
    code = f"{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}".upper()
    token_hash = hashlib.sha256(token.encode()).hexdigest() if token else uuid.uuid4().hex
    inviter = fetch(supabase, "select owner_id from workspaces where id = $1", workspace_id)[0][0]
    fetch(
        supabase,
        "insert into invites (id, workspace_id, email, role, department_ids, code, token_hash,"
        " invited_by, status, expires_at) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
        new_id(),
        workspace_id,
        email.lower(),
        role,
        department_ids or [],
        code,
        token_hash,
        inviter,
        status,
        datetime.now(UTC) + expires_in,
    )
    return code


# --- Create --------------------------------------------------------------------------------


def test_create_makes_the_caller_owner_with_trial_and_profile(
    client: TestClient, users: list[User], supabase: Supabase
) -> None:
    user = users[0]

    response = client.post(
        "/v1/workspaces", json={"name": "  Café Talent, Inc.  "}, headers=user.headers
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Café Talent, Inc."
    assert body["slug"].startswith("cafe-talent-inc")
    assert body["role"] == "admin"
    assert body["is_owner"] is True
    assert body["member_count"] == 1
    workspace_id = uuid.UUID(body["id"])
    [row] = fetch(
        supabase,
        "select w.owner_id, w.trial_granted_at, c.company_name, p.last_workspace_id"
        " from workspaces w join company_profiles c on c.workspace_id = w.id"
        " join profiles p on p.id = w.owner_id where w.id = $1",
        workspace_id,
    )
    assert row["owner_id"] == user.id
    assert row["trial_granted_at"] is not None
    assert row["company_name"] == "Café Talent, Inc."
    assert row["last_workspace_id"] == workspace_id
    [trial] = fetch(
        supabase,
        "select b.amount, b.remaining, b.expires_at, l.kind from credit_batches b"
        " join credit_ledger l on l.batch_id = b.id where b.workspace_id = $1",
        workspace_id,
    )
    assert (trial["amount"], trial["remaining"], trial["kind"]) == (20, 20, "grant_trial")
    assert trial["expires_at"] == row["trial_granted_at"] + timedelta(days=30)


def test_create_gives_every_workspace_a_unique_url_safe_slug(
    client: TestClient, users: list[User]
) -> None:
    name = f"Acme {uuid.uuid4().hex[:6]}"
    slugs = [
        client.post("/v1/workspaces", json={"name": name}, headers=users[0].headers).json()["slug"],
        client.post("/v1/workspaces", json={"name": name}, headers=users[1].headers).json()["slug"],
        client.post("/v1/workspaces", json={"name": "!!!"}, headers=users[1].headers).json()[
            "slug"
        ],
    ]

    base = name.lower().replace(" ", "-")
    assert slugs[:2] == [base, f"{base}-2"]
    assert slugs[2].startswith("workspace")


@pytest.mark.parametrize("name", ["", "   ", "x" * 121])
def test_create_rejects_a_blank_or_long_name(
    client: TestClient, users: list[User], name: str
) -> None:
    response = client.post("/v1/workspaces", json={"name": name}, headers=users[0].headers)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


def test_unverified_email_cannot_create_or_join(users: list[User]) -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=users[0].id, email=users[0].email, email_verified=False
    )
    with TestClient(app) as unverified:
        created = unverified.post("/v1/workspaces", json={"name": "Nope"})
        joined = unverified.post("/v1/invites/accept", json={"code": "AB12-CD34"})

    for response in (created, joined):
        assert response.status_code == 403
        assert response.json()["code"] == "email_not_verified"


# --- Join ----------------------------------------------------------------------------------


def test_join_with_a_code_adds_the_invites_role_and_departments(
    tenancy: Tenancy, client: TestClient, users: list[User], supabase: Supabase
) -> None:
    workspace = tenancy.workspace("a")
    user = users[0]
    code = add_invite(
        supabase, workspace.id, user.email.upper(), department_ids=[workspace.department_id]
    )

    # Pasted as a full link, in lowercase.
    response = client.post(
        "/v1/invites/accept",
        json={"code": f"https://fasthyr.com/join/{code.lower()}"},
        headers=user.headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(workspace.id)
    assert response.json()["role"] == "recruiter"
    [member] = fetch(
        supabase,
        "select m.role, m.is_owner, array_agg(d.department_id) as departments"
        " from workspace_members m join member_departments d on d.member_id = m.id"
        " where m.workspace_id = $1 and m.user_id = $2 group by m.id",
        workspace.id,
        user.id,
    )
    assert (member["role"], member["is_owner"]) == ("recruiter", False)
    assert member["departments"] == [workspace.department_id]
    [invite] = fetch(supabase, "select status, accepted_by from invites where code = $1", code)
    assert (invite["status"], invite["accepted_by"]) == ("accepted", user.id)
    [profile] = fetch(supabase, "select last_workspace_id from profiles where id = $1", user.id)
    assert profile[0] == workspace.id

    # Accepting again is harmless: the user is already a member.
    again = client.post("/v1/invites/accept", json={"code": code}, headers=user.headers)
    assert again.status_code == 200


@pytest.mark.parametrize(
    ("status", "expires_in", "code"),
    [
        ("pending", timedelta(seconds=-1), "invite_expired"),
        ("expired", timedelta(days=1), "invite_expired"),
        ("revoked", timedelta(days=1), "invite_invalid"),
        ("accepted", timedelta(days=1), "invite_invalid"),
    ],
)
def test_join_refuses_an_invite_that_cannot_be_used(
    tenancy: Tenancy,
    client: TestClient,
    users: list[User],
    supabase: Supabase,
    status: str,
    expires_in: timedelta,
    code: str,
) -> None:
    invite = add_invite(
        supabase, tenancy.workspace("a").id, users[0].email, status=status, expires_in=expires_in
    )

    response = client.post("/v1/invites/accept", json={"code": invite}, headers=users[0].headers)

    assert response.status_code == 410
    assert response.json()["code"] == code


def test_join_only_with_an_invite_addressed_to_you(
    tenancy: Tenancy, client: TestClient, users: list[User], supabase: Supabase
) -> None:
    # Even a revoked invite for someone else only says "different email", nothing more.
    invite = add_invite(supabase, tenancy.workspace("a").id, users[0].email, status="revoked")

    wrong = client.post("/v1/invites/accept", json={"code": invite}, headers=users[1].headers)
    unknown = client.post(
        "/v1/invites/accept", json={"code": "ZZZZ-0000"}, headers=users[1].headers
    )

    assert (wrong.status_code, wrong.json()["code"]) == (403, "invite_wrong_email")
    assert (unknown.status_code, unknown.json()["code"]) == (404, "invite_not_found")
    assert "example.com" not in wrong.text


def test_join_with_the_link_token(
    tenancy: Tenancy, client: TestClient, users: list[User], supabase: Supabase
) -> None:
    token = f"tok_{uuid.uuid4().hex}-Mixed_Case"
    add_invite(supabase, tenancy.workspace("a").id, users[0].email, token=token)

    # Tokens are exact: the same token in upper case is no invite.
    wrong_case = client.post(
        "/v1/invites/accept", json={"token": token.upper()}, headers=users[0].headers
    )
    joined = client.post(
        "/v1/invites/accept",
        json={"token": f"https://fasthyr.com/join/{token}"},
        headers=users[0].headers,
    )
    both = client.post(
        "/v1/invites/accept", json={"code": "AB12-CD34", "token": token}, headers=users[0].headers
    )

    assert (wrong_case.status_code, wrong_case.json()["code"]) == (404, "invite_not_found")
    assert joined.status_code == 200, joined.text
    assert joined.json()["id"] == str(tenancy.workspace("a").id)
    assert both.status_code == 422


# --- Join page preview ---------------------------------------------------------------------


def test_preview_shows_the_invite_to_its_addressee(
    tenancy: Tenancy, client: TestClient, users: list[User], supabase: Supabase
) -> None:
    workspace = tenancy.workspace("a")
    token = f"tok_{uuid.uuid4().hex}"
    code = add_invite(
        supabase,
        workspace.id,
        users[0].email,
        department_ids=[workspace.department_id],
        token=token,
    )

    by_code = client.get(f"/v1/invites/{code.lower()}", headers=users[0].headers)
    by_token = client.get(f"/v1/invites/{token}", headers=users[0].headers)

    assert by_code.status_code == 200, by_code.text
    assert by_code.json() == by_token.json()
    body = by_code.json()
    assert body["state"] == "ready"
    assert body["workspace_id"] == str(workspace.id)
    assert body["workspace_name"]
    assert body["invited_by_name"]
    assert body["role"] == "recruiter"
    assert body["departments"] == ["Engineering"]
    assert body["masked_email"] is None


def test_preview_tells_another_account_only_the_masked_email(
    tenancy: Tenancy, client: TestClient, users: list[User], supabase: Supabase
) -> None:
    code = add_invite(supabase, tenancy.workspace("a").id, users[0].email)
    # A member of the invite's own workspace is still the wrong account.
    other_member = tenancy.client("a", Role.RECRUITER)

    wrong = client.get(f"/v1/invites/{code}", headers=users[1].headers)
    member = other_member.get(f"/v1/invites/{code}")
    unknown = client.get("/v1/invites/ZZZZ-0000", headers=users[1].headers)

    for response in (wrong, member):
        assert response.status_code == 200
        assert response.json() == {
            "state": "wrong_email",
            "workspace_id": None,
            "workspace_name": None,
            "invited_by_name": None,
            "role": None,
            "departments": [],
            "masked_email": f"{users[0].email[0]}•••@example.com",
        }
    assert (unknown.status_code, unknown.json()["code"]) == (404, "invite_not_found")


@pytest.mark.parametrize(
    ("status", "expires_in", "state"),
    [
        ("pending", timedelta(seconds=-1), "expired"),
        ("expired", timedelta(days=1), "expired"),
        ("revoked", timedelta(days=1), "invalid"),
        ("accepted", timedelta(days=1), "invalid"),
    ],
)
def test_preview_of_an_invite_that_cannot_be_used(
    tenancy: Tenancy,
    client: TestClient,
    users: list[User],
    supabase: Supabase,
    status: str,
    expires_in: timedelta,
    state: str,
) -> None:
    code = add_invite(
        supabase, tenancy.workspace("a").id, users[0].email, status=status, expires_in=expires_in
    )

    response = client.get(f"/v1/invites/{code}", headers=users[0].headers)

    assert response.status_code == 200
    assert response.json()["state"] == state
    assert response.json()["workspace_name"] is None


def test_preview_after_joining_points_to_the_workspace(
    tenancy: Tenancy, client: TestClient, users: list[User], supabase: Supabase
) -> None:
    code = add_invite(supabase, tenancy.workspace("a").id, users[0].email, role="admin")
    assert client.get(f"/v1/invites/{code}", headers=users[0].headers).json()["departments"] == []
    client.post("/v1/invites/accept", json={"code": code}, headers=users[0].headers)

    response = client.get(f"/v1/invites/{code}", headers=users[0].headers)

    assert response.json()["state"] == "already_member"
    assert response.json()["workspace_id"] == str(tenancy.workspace("a").id)


# --- Last workspace ------------------------------------------------------------------------


def test_last_workspace_is_remembered_only_for_my_own_workspaces(
    tenancy: Tenancy, supabase: Supabase
) -> None:
    member = tenancy.member("a", Role.RECRUITER)
    client = tenancy.client("a", Role.RECRUITER)

    mine = client.put(
        "/v1/me/last-workspace", json={"workspace_id": str(tenancy.workspace("a").id)}
    )
    other = client.put(
        "/v1/me/last-workspace", json={"workspace_id": str(tenancy.workspace("b").id)}
    )

    assert mine.status_code == 204
    assert (other.status_code, other.json()["code"]) == (404, "not_found")
    [profile] = fetch(
        supabase, "select last_workspace_id from profiles where id = $1", member.user_id
    )
    assert profile[0] == tenancy.workspace("a").id
    assert client.get("/v1/me").json()["last_workspace_id"] == str(tenancy.workspace("a").id)
