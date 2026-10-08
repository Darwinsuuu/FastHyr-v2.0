"""Cron jobs that keep the data tidy (BACKEND.md §4). Each runs across workspaces, calls one
service and commits. Later tasks add their crons here and register them in `app/worker.py`."""

import logging
from datetime import UTC, datetime, timedelta

from app.integrations.storage import Storage
from app.jobs.framework import NO_RETRY, JobRun, job
from app.jobs.interviews import PLAN_JOB
from app.jobs.screening import SCREEN_JOB
from app.repositories.interviews import (
    passed_without_plan_before,
    screened_awaiting_action_before,
)
from app.repositories.jobs import queued_report_jobs_before
from app.repositories.screening import pending_before
from app.services import (
    credits,
    emails,
    files,
    interview_lifecycle,
    invites,
    pipelines,
    transcripts,
)
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
async def expire_interview_links(run: JobRun) -> int:
    """Every 10 minutes: closes interview links past their expiry that were never started or
    were left unfinished, with their drop-off reason, and cancels their waiting reminder and
    "Finish your interview" emails (INTV-007)."""
    expired = await interview_lifecycle.expire_links(run.session)
    await run.session.commit()
    if expired:
        logger.info("expire_interview_links: %d links expired", expired)
    return expired


@job(retry=NO_RETRY)
async def open_and_close_pipelines(run: JobRun) -> int:
    """Every minute: opens scheduled pipelines at `opens_at` and closes open ones at `closes_at`
    (PIPE-001). Each pipeline commits on its own, so one failure doesn't hold up the rest."""
    opened = await pipelines.open_due(run.session)
    closed = await pipelines.close_due(run.session)
    if opened or closed:
        logger.info("open_and_close_pipelines: %d opened, %d closed", opened, closed)
    return opened + closed


@job(retry=NO_RETRY)
async def requeue_stuck_work(run: JobRun) -> int:
    """Every 10 minutes: queues again work that Postgres says is waiting but Redis lost
    (ADR-009): report jobs, résumé screens (SCREEN-001), interview plans (INTV-001) and the
    invitation or rejection after a screen (SCREEN-003) and interview transcripts (INTV-008);
    the other interview tasks add theirs.
    Due emails are `dispatch_scheduled_emails`' job. Re-enqueueing is safe: enqueue is keyed by the
    row ID and job bodies skip finished work."""
    requeued = 0
    for stuck in await queued_report_jobs_before(run.session, datetime.now(UTC) - STUCK_AFTER):
        function = JOB_FUNCTIONS.get(stuck.kind)
        if function and await run.queue.enqueue(
            function, stuck.workspace_id, stuck.job_id, key=stuck.job_id
        ):
            requeued += 1
    for application_id in await pending_before(run.session, datetime.now(UTC) - STUCK_AFTER):
        if await run.queue.enqueue(SCREEN_JOB, application_id, key=application_id):
            requeued += 1
    for application_id in await passed_without_plan_before(
        run.session, datetime.now(UTC) - STUCK_AFTER
    ):
        if await run.queue.enqueue(PLAN_JOB, application_id, key=application_id):
            requeued += 1
    # Screened but not yet invited or rejected: the job that acts on it runs again and skips
    # the steps already done.
    for application_id, passed in await screened_awaiting_action_before(
        run.session, datetime.now(UTC) - STUCK_AFTER
    ):
        function = PLAN_JOB if passed else SCREEN_JOB
        if await run.queue.enqueue(function, application_id, key=application_id):
            requeued += 1
    for workspace_id, interview_id in await transcripts.pending_before(
        run.session, datetime.now(UTC) - STUCK_AFTER
    ):
        if await run.queue.enqueue(
            transcripts.TRANSCRIBE_JOB, workspace_id, interview_id, key=interview_id
        ):
            requeued += 1
    logger.info("requeue_stuck_work: %d jobs requeued", requeued)
    return requeued


@job(retry=NO_RETRY)
async def dispatch_scheduled_emails(run: JobRun) -> int:
    """Every minute: queues the send of every scheduled email whose time has come (MSG-003),
    including any whose enqueue Redis lost. Emails wait in Postgres, not Redis, until then."""
    queued = await emails.dispatch_due(run.session, run.queue)
    if queued:
        logger.info("dispatch_scheduled_emails: %d emails queued", queued)
    return queued


@job(retry=NO_RETRY)
async def remove_storage_orphans(run: JobRun) -> int:
    """Daily: deletes abandoned temp uploads and demo files older than 24 hours (FND-011,
    STORAGE.md: Deletion)."""
    storage: Storage = run.ctx["storage"]
    deleted = await files.remove_orphans(storage)
    logger.info("remove_storage_orphans: %d files deleted", deleted)
    return deleted
