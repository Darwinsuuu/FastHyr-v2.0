"""FND-003: the public Supabase keys can't reach business data; the schema keeps tenants apart."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable, Iterator

import asyncpg
import httpx2
import pytest

from app.core.ids import new_id
from tests.integration.conftest import Supabase


def run_in_db[T](supabase: Supabase, work: Callable[[asyncpg.Connection], Awaitable[T]]) -> T:
    """Run `work` as the API role inside a transaction that is always rolled back."""

    async def main() -> T:
        connection = await asyncpg.connect(supabase.database_url)
        transaction = connection.transaction()
        await transaction.start()
        try:
            return await work(connection)
        finally:
            await transaction.rollback()
            await connection.close()

    return asyncio.run(main())


def public_tables(supabase: Supabase) -> list[str]:
    async def work(connection: asyncpg.Connection) -> list[str]:
        rows = await connection.fetch(
            "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace"
            " where n.nspname = 'public' and c.relkind in ('r', 'p', 'v', 'm') order by 1"
        )
        return [row["relname"] for row in rows]

    return run_in_db(supabase, work)


@pytest.fixture
def user_id(supabase: Supabase) -> Iterator[uuid.UUID]:
    """A new auth user created through Supabase Auth; deleted afterwards."""
    email = f"fnd003-{uuid.uuid4().hex[:12]}@example.com"
    response = httpx2.post(
        f"{supabase.url}/auth/v1/signup",
        headers={"apikey": supabase.anon_key},
        json={"email": email, "password": "test-password-1", "data": {"full_name": "Test User"}},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    created = uuid.UUID(body.get("id") or body["user"]["id"])
    yield created
    httpx2.delete(
        f"{supabase.url}/auth/v1/admin/users/{created}",
        headers={"apikey": supabase.secret_key, "Authorization": f"Bearer {supabase.secret_key}"},
    )


def test_anon_key_cannot_select_from_any_table(supabase: Supabase) -> None:
    tables = public_tables(supabase)
    assert "workspaces" in tables

    for table in tables:
        response = httpx2.get(
            f"{supabase.url}/rest/v1/{table}?select=*",
            headers={"apikey": supabase.anon_key},
        )
        assert response.status_code in (401, 403, 404), f"{table}: {response.status_code}"


def test_every_table_is_locked_down(supabase: Supabase) -> None:
    """RLS on, no policies, no privileges for anon/authenticated, including future tables."""

    async def work(connection: asyncpg.Connection) -> list[asyncpg.Record]:
        return await connection.fetch(
            """
            select c.relname,
                   c.relrowsecurity as rls,
                   (select count(*) from pg_policies p
                     where p.schemaname = 'public' and p.tablename = c.relname) as policies,
                   has_table_privilege('anon', c.oid, 'select, insert, update, delete') as anon,
                   has_table_privilege('authenticated', c.oid, 'select, insert, update, delete')
                     as authenticated
              from pg_class c join pg_namespace n on n.oid = c.relnamespace
             where n.nspname = 'public' and c.relkind in ('r', 'p')
            """
        )

    rows = run_in_db(supabase, work)
    assert rows
    for row in rows:
        assert row["rls"], f"{row['relname']}: RLS is off"
        assert row["policies"] == 0, f"{row['relname']}: has policies"
        assert not row["anon"], f"{row['relname']}: anon has privileges"
        assert not row["authenticated"], f"{row['relname']}: authenticated has privileges"


def test_sign_up_creates_profile(supabase: Supabase, user_id: uuid.UUID) -> None:
    async def work(connection: asyncpg.Connection) -> asyncpg.Record | None:
        return await connection.fetchrow("select full_name from profiles where id = $1", user_id)

    profile = run_in_db(supabase, work)
    assert profile is not None
    assert profile["full_name"] == "Test User"


async def _create_workspace(connection: asyncpg.Connection, owner: uuid.UUID) -> uuid.UUID:
    workspace_id = new_id()
    await connection.execute(
        "insert into workspaces (id, name, slug, owner_id) values ($1, 'Test', $2, $3)",
        workspace_id,
        f"test-{workspace_id.hex[:12]}",
        owner,
    )
    return workspace_id


def test_member_cannot_link_to_another_workspaces_department(
    supabase: Supabase, user_id: uuid.UUID
) -> None:
    async def work(connection: asyncpg.Connection) -> None:
        workspace_a = await _create_workspace(connection, user_id)
        workspace_b = await _create_workspace(connection, user_id)
        member_a = new_id()
        await connection.execute(
            "insert into workspace_members (id, workspace_id, user_id, role, is_owner)"
            " values ($1, $2, $3, 'admin', true)",
            member_a,
            workspace_a,
            user_id,
        )
        department_b = new_id()
        await connection.execute(
            "insert into departments (id, workspace_id, name) values ($1, $2, 'Engineering')",
            department_b,
            workspace_b,
        )
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            await connection.execute(
                "insert into member_departments (workspace_id, member_id, department_id)"
                " values ($1, $2, $3)",
                workspace_a,
                member_a,
                department_b,
            )

    run_in_db(supabase, work)


def test_audit_log_is_append_only(supabase: Supabase, user_id: uuid.UUID) -> None:
    async def work(connection: asyncpg.Connection) -> None:
        workspace_id = await _create_workspace(connection, user_id)
        await connection.execute(
            "insert into audit_log (workspace_id, actor_id, action, entity_type)"
            " values ($1, $2, 'department.created', 'department')",
            workspace_id,
            user_id,
        )
        for statement in ("update audit_log set action = 'x'", "delete from audit_log"):
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                async with connection.transaction():  # savepoint keeps the outer one usable
                    await connection.execute(statement)

    run_in_db(supabase, work)
