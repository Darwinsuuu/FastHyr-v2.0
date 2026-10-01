"""Cron jobs that keep the data tidy (BACKEND.md §4). Each runs across workspaces, calls one
service and commits. Later tasks add their crons here and register them in `app/worker.py`."""

import logging
from datetime import UTC, datetime, timedelta

from app.integrations.storage import Storage
from app.jobs.framework import NO_RETRY, JobRun, job
from app.repositories.emails import scheduled_before
from app.repositories.jobs import queued_report_jobs_before
from app.services import credits, emails, files, invites
from app.services.jobs import JOB_FUNCTIONS

logger = logging.getLogger("app.jobs")

# Work still waiting this long after it was due lost its enqueue.
STUCK_AFTER = timedelta(minutes=10)


@job(retry=NO_RETRY)
async def expire_credit_batches(run: JobRun) -> int:
    """Hourly: zeroes expired credit batches with ledger entries (BILL-002)."""
    expired = await credits.expire_batches(run.session)
    await run.session.commit()
    logger.info("expire_credit_batches: %d batches expired", expired)
    return expired


@job(retry=NO_RETRY)
async def expire_invites(run: JobRun) -> int:
    """Hourly: marks pending invites past their expiry as expired (WS-004)."""
    expired = await invites.expire_invites(run.session)
    await run.session.commit()
    logger.info("expire_invites: %d invites expired", expired)
    return expired


@job(retry=NO_RETRY)
async def requeue_stuck_work(run: JobRun) -> int:
    """Every 10 minutes: queues again work that Postgres says is waiting but Redis lost
    (ADR-009): report jobs and due emails; the application and interview tasks add theirs.
    Re-enqueueing is safe: enqueue is keyed by the row ID and job bodies skip finished work."""
    requeued = 0
    for stuck in await queued_report_jobs_before(run.session, datetime.now(UTC) - STUCK_AFTER):
        function = JOB_FUNCTIONS.get(stuck.kind)
        if function and await run.queue.enqueue(
            function, stuck.workspace_id, stuck.job_id, key=stuck.job_id
        ):
            requeued += 1
    for message_id in await scheduled_before(run.session, datetime.now(UTC) - STUCK_AFTER):
        if await run.queue.enqueue(emails.SEND_JOB, message_id, key=message_id):
            requeued += 1
    logger.info("requeue_stuck_work: %d jobs requeued", requeued)
    return requeued


@job(retry=NO_RETRY)
async def remove_storage_orphans(run: JobRun) -> int:
    """Daily: deletes abandoned temp uploads and demo files older than 24 hours (FND-011,
    STORAGE.md: Deletion)."""
    storage: Storage = run.ctx["storage"]
    deleted = await files.remove_orphans(storage)
    logger.info("remove_storage_orphans: %d files deleted", deleted)
    return deleted
