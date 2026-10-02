"""The arq worker (ADR-009): `python -m app.worker`, or `make worker` locally.

Every job function and cron is registered here. Functions go through `app.jobs.framework.job`,
which supplies the session and retries; arq's own `max_tries` is set from the same policy.
"""

from typing import Any, ClassVar

from arq import cron, run_worker
from arq.connections import RedisSettings
from arq.cron import CronJob
from arq.worker import Function, func

from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.core.logging import configure_logging
from app.core.observability import init_sentry
from app.integrations.email import sender_from_settings
from app.integrations.storage import storage_from_settings
from app.jobs.emails import send_email
from app.jobs.framework import WorkerFunction, retry_policy_of
from app.jobs.queue import DEFAULT_QUEUE, JobQueue
from app.jobs.reports import sample_report_job
from app.jobs.screening import screen_resume
from app.jobs.system import (
    expire_credit_batches,
    expire_invites,
    open_and_close_pipelines,
    remove_storage_orphans,
    requeue_stuck_work,
)

EVERY_10_MINUTES = {0, 10, 20, 30, 40, 50}


def register(function: WorkerFunction) -> Function:
    return func(function, name=function.__qualname__, max_tries=retry_policy_of(function).max_tries)


FUNCTIONS: list[Function] = [
    register(sample_report_job),
    register(send_email),
    register(screen_resume),
]

CRON_JOBS: list[CronJob] = [
    # Hourly crons run at different minutes so they don't all start at once.
    cron(expire_credit_batches, name="expire_credit_batches", minute=5),
    cron(expire_invites, name="expire_invites", minute=15),
    cron(requeue_stuck_work, name="requeue_stuck_work", minute=EVERY_10_MINUTES),
    # Every minute, so a scheduled pipeline opens within a minute of its date.
    cron(open_and_close_pipelines, name="open_and_close_pipelines"),
    # Daily, at a quiet hour (UTC).
    cron(remove_storage_orphans, name="remove_storage_orphans", hour=3, minute=25),
]


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.resolved_log_format)
    init_sentry(settings, "worker")
    engine = create_engine(settings)
    ctx["engine"] = engine
    ctx["sessionmaker"] = create_sessionmaker(engine)
    # Tests pass a fake email sender or storage, and their own queue's name in `ctx`.
    ctx.setdefault("email_sender", sender_from_settings(settings))
    ctx.setdefault("storage", storage_from_settings(settings))
    ctx["queue"] = JobQueue.from_pool(ctx["redis"], ctx.get("queue_name", DEFAULT_QUEUE))


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["engine"].dispose()


class WorkerSettings:
    functions: ClassVar[list[Function]] = FUNCTIONS
    cron_jobs: ClassVar[list[CronJob]] = CRON_JOBS
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    queue_name = DEFAULT_QUEUE
    on_startup = startup
    on_shutdown = shutdown
    # Results aren't kept in Redis: job state people see lives in Postgres. This also lets a
    # keyed job be enqueued again as soon as the previous one finished.
    keep_result = 0
    job_timeout = 600
    max_jobs = 10


if __name__ == "__main__":
    run_worker(WorkerSettings)  # type: ignore[arg-type]
