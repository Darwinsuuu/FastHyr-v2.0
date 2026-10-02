"""Tests that need local Supabase (`make db-start`, then `make db-reset`) or local Redis
(`make redis-start`).

They skip when the database or Redis isn't reachable, unless FASTHYR_REQUIRE_DB=1 or
FASTHYR_REQUIRE_REDIS=1 (CI), which makes a missing service a failure instead.
"""

import asyncio
import os
import uuid
from dataclasses import dataclass

import asyncpg
import httpx2
import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.integrations.storage import SupabaseStorage

# Fixed keys every local Supabase install uses (`make db-status`); CI can override them.
LOCAL_PUBLISHABLE_KEY = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"
LOCAL_SECRET_KEY = "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"
# The table owner, for test cleanup the API role may not do (the credit ledger is append-only).
LOCAL_OWNER_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"


@dataclass(frozen=True)
class Supabase:
    database_url: str
    url: str
    anon_key: str
    secret_key: str
    owner_database_url: str


async def _ping(database_url: str) -> None:
    connection = await asyncpg.connect(database_url, timeout=3)
    await connection.close()


@pytest.fixture(scope="session")
def supabase() -> Supabase:
    settings = get_settings()
    try:
        asyncio.run(_ping(settings.database_url))
    except (OSError, asyncpg.PostgresError, TimeoutError) as error:
        message = f"local Supabase is not reachable ({type(error).__name__}); run `make db-start`"
        if os.environ.get("FASTHYR_REQUIRE_DB") == "1":
            pytest.fail(message)
        pytest.skip(message)
    return Supabase(
        database_url=settings.database_url,
        url=settings.supabase_url,
        anon_key=os.environ.get("SUPABASE_ANON_KEY", LOCAL_PUBLISHABLE_KEY),
        secret_key=settings.supabase_service_role_key or LOCAL_SECRET_KEY,
        owner_database_url=os.environ.get("SUPABASE_DB_URL", LOCAL_OWNER_DATABASE_URL),
    )


async def delete_credit_rows(supabase: Supabase, workspace_ids: list[uuid.UUID]) -> None:
    """Removes test workspaces' emails, report jobs, AI call log, audit log, applications,
    candidates, ledger, batches and pipelines so the workspaces can be deleted. The audit log
    and ledger reject deletes, so this connects as the table owner with triggers switched off
    for the transaction."""
    connection = await asyncpg.connect(supabase.owner_database_url)
    try:
        async with connection.transaction():
            await connection.execute("set local session_replication_role = replica")
            for table in (
                "email_messages",
                "report_jobs",
                "ai_calls",
                "audit_log",
                "applications",
                "candidates",
                "credit_ledger",
                "credit_batches",
                "pipelines",
            ):
                await connection.execute(
                    f"delete from {table} where workspace_id = any($1::uuid[])", workspace_ids
                )
    finally:
        await connection.close()


@pytest.fixture(scope="session")
def storage(supabase: Supabase) -> SupabaseStorage:
    """Local Supabase Storage, called with the service key. Skips when it isn't running
    (`supabase start -x storage-api`), unless FASTHYR_REQUIRE_DB=1 (CI)."""
    try:
        response = httpx2.get(f"{supabase.url}/storage/v1/status", timeout=3)
        response.raise_for_status()
    except httpx2.HTTPError as error:
        message = f"local Supabase Storage is not reachable ({type(error).__name__})"
        if os.environ.get("FASTHYR_REQUIRE_DB") == "1":
            pytest.fail(message)
        pytest.skip(message)
    return SupabaseStorage(supabase.url, supabase.secret_key)


@pytest.fixture(scope="session")
def redis_url() -> str:
    """Local Redis for job tests (`make redis-start`). Skips when it isn't reachable, unless
    FASTHYR_REQUIRE_REDIS=1 (CI)."""
    url = get_settings().redis_url

    async def ping() -> None:
        client = Redis.from_url(url, socket_connect_timeout=3)
        try:
            await client.ping()
        finally:
            await client.aclose()

    try:
        asyncio.run(ping())
    except (OSError, RedisError) as error:
        message = f"local Redis is not reachable ({type(error).__name__}); run `make redis-start`"
        if os.environ.get("FASTHYR_REQUIRE_REDIS") == "1":
            pytest.fail(message)
        pytest.skip(message)
    return url


# The tenancy harness (two workspaces, every role) for any test folder: see tests/tenancy.
pytest_plugins = ["tests.tenancy.harness"]
