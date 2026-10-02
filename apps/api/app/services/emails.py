"""The only code that queues and sends email (BACKEND.md §3, NOTIFICATIONS.md).

Callers render an email (`app/emails/`), `queue_email()` it inside their own transaction, commit,
then `enqueue()` it, so an email exists exactly when the change that caused it does. The
`send_email` job claims the row, sends it through the configured provider and records the
provider's ID; Resend's webhook then moves it to delivered, bounced or complained. A lost
enqueue is picked up by the `requeue_stuck_work` cron.
"""

import uuid
from datetime import UTC, datetime

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
        EmailMessage(
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
        ),
    )


async def enqueue(queue: JobQueue, message: EmailMessage) -> None:
    """Queues the send for the email's scheduled time. Call after the commit."""
    defer = message.scheduled_for if message.scheduled_for > datetime.now(UTC) else None
    await queue.enqueue(SEND_JOB, message.id, key=message.id, defer_until=defer)


async def deliver(session: AsyncSession, sender: EmailSender, message_id: uuid.UUID) -> bool:
    """The send job's work: claim, send, record. Returns False when there was nothing to send
    (cancelled, already sent, or not yet due). Provider errors propagate for the job to retry."""
    now = datetime.now(UTC)
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


async def apply_webhook_event(session: AsyncSession, event_type: str, provider_id: str) -> bool:
    """Applies a verified Resend webhook event. Unknown events and emails are ignored."""
    if event_type not in WEBHOOK_EVENTS:
        return False
    status, only_from = WEBHOOK_EVENTS[event_type]
    changed = await email_repo.set_status_by_provider_id(
        session, provider_id, status=status, now=datetime.now(UTC), only_from=only_from
    )
    await session.commit()
    return changed


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
