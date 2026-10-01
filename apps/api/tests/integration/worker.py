"""Runs the real arq worker in burst mode for integration tests: it exits once its queue,
deferred retries included, is empty."""

import asyncio
from typing import Any

from arq.connections import RedisSettings
from arq.worker import Worker

from app.worker import FUNCTIONS, shutdown, startup


async def _run(redis_url: str, queue_name: str, ctx: dict[str, Any]) -> None:
    worker = Worker(
        functions=FUNCTIONS,
        redis_settings=RedisSettings.from_dsn(redis_url),
        queue_name=queue_name,
        burst=True,
        handle_signals=False,
        on_startup=startup,
        on_shutdown=shutdown,
        keep_result=0,
        poll_delay=0.05,
        ctx={"queue_name": queue_name, **ctx},
    )
    try:
        await worker.main()
    finally:
        await worker.close()


def drain(redis_url: str, queue_name: str, **ctx: Any) -> None:
    """Runs every job queued on `queue_name`; `ctx` overrides worker clients (email_sender)."""
    asyncio.run(_run(redis_url, queue_name, ctx))
