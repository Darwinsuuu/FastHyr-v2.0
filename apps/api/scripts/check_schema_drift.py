"""Fail when the SQLAlchemy models and the migrated database disagree.

Run after applying supabase/migrations (e.g. `make db-reset`), from apps/api:
    uv run python scripts/check_schema_drift.py
Compares tables, columns, types, nullability, defaults, keys and indexes in the `public` schema
against `app.models`. Check constraints and triggers are not compared; they live only in SQL.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.models import Base


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    # Only the public schema is ours; auth.users is declared just for the profiles FK.
    return not (type_ == "table" and getattr(obj, "schema", None) is not None)


def diff(connection: Connection) -> list[Any]:
    context = MigrationContext.configure(
        connection,
        opts={
            "compare_type": True,
            "compare_server_default": True,
            "include_object": include_object,
        },
    )
    return list(compare_metadata(context, Base.metadata))


async def main() -> int:
    url = get_settings().database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            changes = await connection.run_sync(diff)
    finally:
        await engine.dispose()
    if changes:
        print("Schema drift between supabase/migrations and app/models:")
        for change in changes:
            print(f"  {change}")
        return 1
    print("No drift: the models match the database.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
