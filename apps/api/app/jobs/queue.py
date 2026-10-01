"""Enqueueing jobs. Services call `JobQueue.enqueue()` after they commit, so the worker always
finds the rows it is given.

`key` makes an enqueue idempotent per entity: while a job with the same function and key is
queued, deferred for a retry or running, enqueueing it again does nothing and returns False.
Use the entity ID (`key=application_id`) for work that must run once per entity at a time.
"""

import uuid
from typing import Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

DEFAULT_QUEUE = "arq:queue"


def job_key(function: str, key: uuid.UUID | str) -> str:
    return f"{function}:{key}"


class JobQueue:
    """Connects to Redis on first use, so the API starts (and serves everything else) while
    Redis is down; only enqueueing fails then."""

    def __init__(
        self,
        redis_url: str,
        *,
        queue_name: str = DEFAULT_QUEUE,
        pool: ArqRedis | None = None,
    ) -> None:
        self.redis_settings = RedisSettings.from_dsn(redis_url)
        self.queue_name = queue_name
        self._pool = pool

    @classmethod
    def from_pool(cls, pool: ArqRedis, queue_name: str = DEFAULT_QUEUE) -> "JobQueue":
        """For jobs, which reuse the worker's connection."""
        queue = cls("redis://unused", queue_name=queue_name, pool=pool)
        return queue

    async def pool(self) -> ArqRedis:
        if self._pool is None:
            self._pool = await create_pool(self.redis_settings, default_queue_name=self.queue_name)
        return self._pool

    async def enqueue(self, function: str, *args: Any, key: uuid.UUID | str | None = None) -> bool:
        """Queues `function(*args)` for the worker. Returns False if `key` is already queued."""
        pool = await self.pool()
        job = await pool.enqueue_job(
            function,
            *args,
            _job_id=job_key(function, key) if key is not None else None,
            _queue_name=self.queue_name,
        )
        return job is not None

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None
