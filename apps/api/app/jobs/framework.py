"""The job wrapper every arq function goes through: a database session, retries with
exponential backoff, and a failure hook once the last try fails.

    @job(retry=RetryPolicy(max_tries=3))
    async def screen_resume(run: JobRun, workspace_id: uuid.UUID, application_id: uuid.UUID):
        ...  # load by ID, call a service, commit

Job bodies are thin and idempotent (BACKEND.md §2): a retry, a duplicate enqueue or a sweeper
re-enqueue may run the same body again, so it checks the row's state before doing the work.
Exceptions are logged by class name only, never with arguments that could hold personal data.
Log lines and Sentry events from a job carry `job`, `job_id` and `job_try`; the last failed try
is sent to Sentry (FND-009).
"""

import functools
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Concatenate

import sentry_sdk
import structlog
from arq import Retry
from arq.typing import WorkerCoroutine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import bind_ids
from app.jobs.queue import JobQueue

logger = logging.getLogger("app.jobs")


@dataclass(frozen=True)
class RetryPolicy:
    """Try `max_tries` times in all, waiting `base_delay * 2 ** (try - 1)` between tries, capped at
    `max_delay`. The defaults fit calls to outside services: 10 s, 20 s, 40 s, 80 s."""

    max_tries: int = 5
    base_delay: timedelta = timedelta(seconds=10)
    max_delay: timedelta = timedelta(minutes=10)

    def delay(self, job_try: int) -> timedelta:
        """The wait after try number `job_try` (1-based) fails."""
        delay: timedelta = self.base_delay * 2 ** (job_try - 1)
        return min(delay, self.max_delay)


DEFAULT_RETRY = RetryPolicy()
# Crons don't retry: the next tick does the same work again.
NO_RETRY = RetryPolicy(max_tries=1)


class PermanentJobError(Exception):
    """Raised (or subclassed) by a job body when retrying can't help: the wrapper goes straight
    to the failure hook. Give subclasses a stable `code` for the failure record."""


@dataclass
class JobRun:
    """What a job body gets: an open session (the body commits), which try this is, the queue
    for follow-up jobs, and the worker context (shared clients such as the email sender)."""

    session: AsyncSession
    job_try: int
    job_id: str
    queue: JobQueue
    ctx: dict[Any, Any]


FailureHook = Callable[[AsyncSession, BaseException, tuple[Any, ...]], Awaitable[None]]
JobBody = Callable[Concatenate[JobRun, ...], Awaitable[Any]]
WorkerFunction = WorkerCoroutine


def job(
    *, retry: RetryPolicy = DEFAULT_RETRY, on_failure: FailureHook | None = None
) -> Callable[[JobBody], WorkerFunction]:
    """Turns a job body into an arq function. Each try runs in a fresh session. A failed try is
    rolled back and retried after `retry.delay()`; when the last try fails, `on_failure` runs in
    its own session (and is committed) so the error is recorded where people can see it, then the
    error is raised for arq to log."""

    def decorator(body: JobBody) -> WorkerFunction:
        @functools.wraps(body)
        async def run(ctx: dict[Any, Any], *args: Any, **kwargs: Any) -> Any:
            # Each job gets its own Sentry scope and log context, tagged with IDs only.
            with sentry_sdk.isolation_scope():
                structlog.contextvars.clear_contextvars()
                bind_ids(job=body.__name__, job_id=ctx.get("job_id") or None)
                sentry_sdk.set_tag("job_try", str(ctx.get("job_try", 1)))
                return await run_try(ctx, *args, **kwargs)

        async def run_try(ctx: dict[Any, Any], *args: Any, **kwargs: Any) -> Any:
            sessionmaker: async_sessionmaker[AsyncSession] = ctx["sessionmaker"]
            job_try: int = ctx.get("job_try", 1)
            name = body.__name__
            async with sessionmaker() as session:
                try:
                    return await body(
                        JobRun(session, job_try, ctx.get("job_id", ""), ctx["queue"], ctx),
                        *args,
                        **kwargs,
                    )
                except Retry:
                    raise
                except Exception as error:
                    await session.rollback()
                    if job_try < retry.max_tries and not isinstance(error, PermanentJobError):
                        delay = retry.delay(job_try)
                        logger.warning(
                            "job %s try %d failed (%s); retrying in %ds",
                            name,
                            job_try,
                            type(error).__name__,
                            delay.total_seconds(),
                        )
                        raise Retry(defer=delay) from error
                    logger.error(
                        "job %s failed after %d tries (%s)", name, job_try, type(error).__name__
                    )
                    sentry_sdk.capture_exception(error)
                    if on_failure is not None:
                        async with sessionmaker() as failure_session:
                            await on_failure(failure_session, error, args)
                            await failure_session.commit()
                    raise

        run.retry_policy = retry  # type: ignore[attr-defined]
        worker_function: WorkerFunction = run
        return worker_function

    return decorator


def retry_policy_of(function: WorkerFunction) -> RetryPolicy:
    policy: RetryPolicy = getattr(function, "retry_policy", DEFAULT_RETRY)
    return policy
