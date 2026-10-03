"""The only code that queues and sends email (BACKEND.md §3, NOTIFICATIONS.md).

Callers render an email (`app/emails/`), `queue_email()` it inside their own transaction, commit,
then `enqueue()` it, so an email exists exactly when the change that caused it does. Candidate
emails are scheduled through `services/candidate_emails.py`. The `send_email` job claims the row,
sends it through the configured provider and records the provider's ID; Resend's webhook then
moves it to delivered, bounced or complained. Emails due later, and any enqueue Redis lost, are
queued by the every-minute `dispatch_scheduled_emails` cron.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.context import RequestContext
from app.core.ids import new_id
from app.emails import system
from app.emails.render import RenderedEmail
from app.integrations.email import EmailSender, OutgoingEmail
from app.jobs.queue import JobQueue
from app.models import EmailMessage
from app.repositories import emails as email_repo
from app.repositories.applications import mark_email_undeliverable
from app.repositories.emails import (
    BOUNCED,
    COMPLAINED,
    DELIVERED,
    FAILED,
    SCHEDULED,
    SENDING,
    SENT,
)
from app.repositories.users import UserRepository
from app.services import company_profile

SEND_JOB = "send_email"

# Resend webhook event → status, and the statuses each may replace. Delivery events can arrive
# out of order, so a bounce or complaint wins over delivered but never the other way round.
WEBHOOK_EVENTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "email.delivered": (DELIVERED, (SENDING, SENT)),
    "email.bounced": (BOUNCED, (SENDING, SENT, DELIVERED)),
    "email.complained": (COMPLAINED, (SENDING, SENT, DELIVERED)),
    "email.failed": (FAILED, (SENDING, SENT)),
}


def queue_email(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID | None,
    template_key: str,
    to_email: str,
    from_name: str,
    email: RenderedEmail,
    application_id: uuid.UUID | None = None,
    scheduled_for: datetime | None = None,
) -> EmailMessage:
    """Adds the email to the session; the caller commits, then calls `enqueue()`."""
    return email_repo.add(
        session,
        _message(
            workspace_id=workspace_id,
            template_key=template_key,
            to_email=to_email,
            from_name=from_name,
            email=email,
            application_id=application_id,
            scheduled_for=scheduled_for,
        ),
    )


async def queue_unique_email(
    session: AsyncSession,
    *,
    dedupe_key: str,
    application_stage: str | None,
    **fields: Any,
) -> tuple[EmailMessage, bool]:
    """Like `queue_email()`, but writes the row now and keeps one live email per `dedupe_key`:
    a repeat returns the email already there and False. The caller commits, then enqueues."""
    message = _message(**fields)
    message.dedupe_key = dedupe_key
    message.application_stage = application_stage
    added = await email_repo.add_unless_duplicate(session, message)
    if added is not None:
        return added, True
    existing = await email_repo.live_by_dedupe_key(session, dedupe_key)
    if existing is None:  # cancelled between the insert and the read: try once more
        return await queue_unique_email(
            session, dedupe_key=dedupe_key, application_stage=application_stage, **fields
        )
    return existing, False


def _message(
    *,
    workspace_id: uuid.UUID | None,
    template_key: str,
    to_email: str,
    from_name: str,
    email: RenderedEmail,
    application_id: uuid.UUID | None = None,
    scheduled_for: datetime | None = None,
) -> EmailMessage:
    return EmailMessage(
        id=new_id(),
        workspace_id=workspace_id,
        application_id=application_id,
        template_key=template_key,
        to_email=to_email,
        from_name=from_name,
        subject_rendered=email.subject,
        html_rendered=email.html,
        text_rendered=email.text,
        scheduled_for=scheduled_for or datetime.now(UTC),
        status=SCHEDULED,
    )


async def enqueue(queue: JobQueue, message: EmailMessage) -> None:
    """Queues the send of an email that is already due. Call after the commit. Emails due later
    wait in Postgres; the `dispatch_scheduled_emails` cron queues them when their time comes, so
    a delay of days never lives in Redis."""
    if message.status == SCHEDULED and message.scheduled_for <= datetime.now(UTC):
        await queue.enqueue(SEND_JOB, message.id, key=message.id)


async def dispatch_due(session: AsyncSession, queue: JobQueue) -> int:
    """The cron's work: queues every scheduled email whose time has come. Keyed by the email's
    ID, so an email already queued or being sent isn't queued twice."""
    queued = 0
    for message_id in await email_repo.due(session, datetime.now(UTC)):
        if await queue.enqueue(SEND_JOB, message_id, key=message_id):
            queued += 1
    return queued


async def cancel_scheduled(
    session: AsyncSession, application_id: uuid.UUID, *, reason: str = email_repo.STAGE_CHANGED
) -> int:
    """Cancels the application's emails still waiting to be sent (FR-MSG-05), in the caller's
    transaction. Returns how many were cancelled."""
    return await email_repo.cancel_scheduled(
        session, application_id, reason=reason, now=datetime.now(UTC)
    )


async def deliver(session: AsyncSession, sender: EmailSender, message_id: uuid.UUID) -> bool:
    """The send job's work: claim, send, record. Returns False when there was nothing to send
    (cancelled, already sent, or not yet due). Provider errors propagate for the job to retry."""
    now = datetime.now(UTC)
    await email_repo.cancel_if_stage_changed(session, message_id, now)
    message = await email_repo.claim(session, message_id, now)
    await session.commit()
    if message is None:
        return False
    provider_id = await sender.send(
        OutgoingEmail(
            id=message.id,
            to=message.to_email,
            from_name=message.from_name,
            subject=message.subject_rendered,
            html=message.html_rendered,
            text=message.text_rendered,
        )
    )
    await email_repo.set_status(
        session,
        message.id,
        status=SENT,
        now=datetime.now(UTC),
        only_from=(SENDING,),
        provider_message_id=provider_id,
        sent_at=datetime.now(UTC),
    )
    await session.commit()
    return True


async def record_failure(session: AsyncSession, message_id: uuid.UUID, code: str) -> None:
    await email_repo.set_status(
        session,
        message_id,
        status=FAILED,
        now=datetime.now(UTC),
        only_from=(SCHEDULED, SENDING),
        error=code,
    )


async def apply_webhook_event(
    session: AsyncSession, event_type: str, provider_id: str, *, hard_bounce: bool = True
) -> bool:
    """Applies a verified Resend webhook event. Unknown events and emails are ignored. A hard
    bounce of a candidate email marks the candidate's address undeliverable (NOTIFICATIONS.md
    §5)."""
    if event_type not in WEBHOOK_EVENTS:
        return False
    status, only_from = WEBHOOK_EVENTS[event_type]
    now = datetime.now(UTC)
    message = await email_repo.set_status_by_provider_id(
        session, provider_id, status=status, now=now, only_from=only_from
    )
    if message is not None and status == BOUNCED and hard_bounce and message.application_id:
        await mark_email_undeliverable(session, message.application_id, message.to_email, now)
    await session.commit()
    return message is not None


def via_fasthyr(company: str) -> str:
    """The sender name of company emails (ADR-008)."""
    return f"{company} via FastHyr"


async def send_test_email(
    session: AsyncSession, ctx: RequestContext, queue: JobQueue, settings: Settings
) -> uuid.UUID:
    """Sends the test email to the caller's own address. Returns the email's ID."""
    profile = await UserRepository(session, ctx.user_id).get_profile()
    if profile is None or not profile.email:
        raise LookupError("signed-in user has no profile email")
    brand = await company_profile.branding(session, ctx.workspace_id, api_url=settings.api_url)
    message = queue_email(
        session,
        workspace_id=ctx.workspace_id,
        template_key="test",
        to_email=profile.email,
        from_name=via_fasthyr(brand.company_name),
        email=system.test_email(site_url=settings.site_url, branding=brand),
    )
    await session.commit()
    await enqueue(queue, message)
    return message.id
