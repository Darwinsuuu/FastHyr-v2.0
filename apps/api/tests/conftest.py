"""Integration tests run against local Supabase (`make db-start`, then `make db-reset`).

They skip when the database isn't reachable, unless FASTHYR_REQUIRE_DB=1 (CI), which makes a
missing database a failure instead.
"""

import asyncio
import os
from dataclasses import dataclass

import asyncpg
import pytest

from app.core.config import get_settings

# Fixed keys every local Supabase install uses (`make db-status`); CI can override them.
LOCAL_PUBLISHABLE_KEY = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"
LOCAL_SECRET_KEY = "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"


@dataclass(frozen=True)
class Supabase:
    database_url: str
    url: str
    anon_key: str
    secret_key: str


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
    )
