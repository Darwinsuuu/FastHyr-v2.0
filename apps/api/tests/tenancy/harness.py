"""Tenancy harness: two workspaces with every role, signed in for real (MULTI_TENANCY.md §4).

Use the `tenancy` fixture in any test:

    def test_pipeline_is_hidden_from_other_workspace(tenancy: Tenancy) -> None:
        pipeline_id = ...  # create it in workspace "a"
        tenancy.assert_hidden_from_other_workspace("GET", f"/v1/pipelines/{pipeline_id}")

    def test_hiring_manager_cannot_publish(tenancy: Tenancy) -> None:
        response = tenancy.client("a", Role.HIRING_MANAGER).post(...)

Each workspace ("a" and "b") has one department ("Engineering") and an Admin (the owner), a
Recruiter and a Hiring manager, both assigned to that department. Everything is created through
Supabase Auth and the API database role, and deleted again when the test ends.
"""

import asyncio
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import asyncpg
import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.context import Role
from app.core.ids import new_id
from app.main import create_app
from tests.conftest import Supabase, delete_credit_rows

PASSWORD = "tenancy-password-1"
WORKSPACES = ("a", "b")


@dataclass
class Member:
    user_id: uuid.UUID
    member_id: uuid.UUID
    email: str
    access_token: str


@dataclass
class TenantWorkspace:
    key: str
    id: uuid.UUID
    department_id: uuid.UUID
    members: dict[Role, Member] = field(default_factory=dict)


class Tenancy:
    def __init__(self, supabase: Supabase, app_client: TestClient) -> None:
        self.supabase = supabase
        self._app = app_client
        self.workspaces: dict[str, TenantWorkspace] = {}

    def workspace(self, key: str) -> TenantWorkspace:
        return self.workspaces[key]

    def member(self, workspace: str, role: Role) -> Member:
        return self.workspaces[workspace].members[role]

    def headers(
        self, workspace: str, role: Role, *, as_workspace: str | None = None
    ) -> dict[str, str]:
        """Auth headers for `role` in `workspace`, optionally sending another workspace's ID."""
        target = self.workspaces[as_workspace or workspace]
        return {
            "Authorization": f"Bearer {self.member(workspace, role).access_token}",
            "X-Workspace-Id": str(target.id),
        }

    def client(self, workspace: str, role: Role) -> "RoleClient":
        """Calls the app signed in as `role`, with `workspace` in `X-Workspace-Id`."""
        return RoleClient(self._app, self.headers(workspace, role))

    def assert_hidden_from_other_workspace(
        self, method: str, url: str, *, owner: str = "a", json: object = None
    ) -> None:
        """Every role in the other workspace gets 404 for a resource `owner` holds."""
        other = "b" if owner == "a" else "a"
        for role in Role:
            response = self._app.request(method, url, json=json, headers=self.headers(other, role))
            assert response.status_code == 404, (role, response.status_code, response.text)
            assert response.json()["code"] == "not_found"


class RoleClient:
    """A thin wrapper over the shared test client that adds one member's headers."""

    def __init__(self, app_client: TestClient, headers: dict[str, str]) -> None:
        self._app = app_client
        self.headers = headers

    def request(self, method: str, url: str, **kwargs: Any) -> httpx2.Response:
        headers = {**self.headers, **kwargs.pop("headers", {})}
        return self._app.request(method, url, headers=headers, **kwargs)

    def get(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("PATCH", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx2.Response:
        return self.request("DELETE", url, **kwargs)


def _auth_admin_headers(supabase: Supabase) -> dict[str, str]:
    return {"apikey": supabase.secret_key, "Authorization": f"Bearer {supabase.secret_key}"}


def _create_user(supabase: Supabase, email: str) -> uuid.UUID:
    response = httpx2.post(
        f"{supabase.url}/auth/v1/admin/users",
        headers=_auth_admin_headers(supabase),
        json={"email": email, "password": PASSWORD, "email_confirm": True},
    )
    assert response.status_code == 200, response.text
    return uuid.UUID(response.json()["id"])


def _sign_in(supabase: Supabase, email: str) -> str:
    response = httpx2.post(
        f"{supabase.url}/auth/v1/token?grant_type=password",
        headers={"apikey": supabase.anon_key},
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


async def _insert_workspace(
    supabase: Supabase, workspace: TenantWorkspace, owner: uuid.UUID
) -> None:
    connection = await asyncpg.connect(supabase.database_url)
    try:
        async with connection.transaction():
            await connection.execute(
                "insert into workspaces (id, name, slug, owner_id) values ($1, $2, $3, $4)",
                workspace.id,
                f"Tenancy {workspace.key.upper()}",
                f"tenancy-{workspace.id.hex[:12]}",
                owner,
            )
            await connection.execute(
                "insert into departments (id, workspace_id, name) values ($1, $2, 'Engineering')",
                workspace.department_id,
                workspace.id,
            )
            for role, member in workspace.members.items():
                await connection.execute(
                    "insert into workspace_members (id, workspace_id, user_id, role, is_owner)"
                    " values ($1, $2, $3, $4, $5)",
                    member.member_id,
                    workspace.id,
                    member.user_id,
                    role.value,
                    role is Role.ADMIN,
                )
                if role is not Role.ADMIN:
                    await connection.execute(
                        "insert into member_departments (workspace_id, member_id, department_id)"
                        " values ($1, $2, $3)",
                        workspace.id,
                        member.member_id,
                        workspace.department_id,
                    )
    finally:
        await connection.close()


async def _delete_workspaces(supabase: Supabase, ids: list[uuid.UUID]) -> None:
    await delete_credit_rows(supabase, ids)
    connection = await asyncpg.connect(supabase.database_url)
    try:
        async with connection.transaction():
            for table in ("invites", "member_departments", "workspace_members", "departments"):
                await connection.execute(
                    f"delete from {table} where workspace_id = any($1::uuid[])", ids
                )
            await connection.execute("delete from workspaces where id = any($1::uuid[])", ids)
    finally:
        await connection.close()


@pytest.fixture
def tenancy_app() -> FastAPI:
    """The app the harness calls. Override in a test module to add test-only routes."""
    return create_app()


@pytest.fixture
def tenancy(supabase: Supabase, tenancy_app: FastAPI) -> Iterator[Tenancy]:
    user_ids: list[uuid.UUID] = []
    with TestClient(tenancy_app) as app_client:
        harness = Tenancy(supabase, app_client)
        try:
            for key in WORKSPACES:
                workspace = TenantWorkspace(key=key, id=new_id(), department_id=new_id())
                for role in Role:
                    email = f"tenancy-{key}-{role.value}-{uuid.uuid4().hex[:8]}@example.com"
                    user_id = _create_user(supabase, email)
                    user_ids.append(user_id)
                    workspace.members[role] = Member(
                        user_id=user_id,
                        member_id=new_id(),
                        email=email,
                        access_token=_sign_in(supabase, email),
                    )
                asyncio.run(
                    _insert_workspace(supabase, workspace, workspace.members[Role.ADMIN].user_id)
                )
                harness.workspaces[key] = workspace
            yield harness
        finally:
            asyncio.run(_delete_workspaces(supabase, [w.id for w in harness.workspaces.values()]))
            for user_id in user_ids:
                httpx2.delete(
                    f"{supabase.url}/auth/v1/admin/users/{user_id}",
                    headers=_auth_admin_headers(supabase),
                )
