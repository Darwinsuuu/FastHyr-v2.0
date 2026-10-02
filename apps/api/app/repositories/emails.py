"""Email messages (FND-010). Emails can belong to no workspace (the contact form) and the send
job and the Resend webhook find them by ID across workspaces, so these are plain functions
keyed by message ID rather than a workspace repository. Only services/emails.py calls them."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmailMessage

SCHEDULED, SENDING, SENT, FAILED = "scheduled", "sending", "sent", "failed"
DELIVERED, BOUNCED, COMPLAINED = "delivered", "bounced", "complained"


def add(session: AsyncSession, message: EmailMessage) -> EmailMessage:
    session.add(message)
    return message


async def claim(session: AsyncSession, message_id: uuid.UUID, now: datetime) -> EmailMessage | None:
    """Marks a due email as sending and returns it; None when it was cancelled, already sent or
    isn't due. A retry finds it `sending` and tries again (the provider drops duplicates)."""
    row: EmailMessage | None = await session.scalar(
        update(EmailMessage)
        .where(
            EmailMessage.id == message_id,
            EmailMessage.status.in_((SCHEDULED, SENDING)),
            EmailMessage.scheduled_for <= now,
        )
        .values(status=SENDING, status_updated_at=now)
        .returning(EmailMessage)
    )
    return row


async def set_status(
    session: AsyncSession,
    message_id: uuid.UUID,
    *,
    status: str,
    now: datetime,
    only_from: tuple[str, ...],
    **values: Any,
) -> bool:
    """Moves the email to `status` if it is in one of `only_from`. Returns whether it moved."""
    result = await session.execute(
        update(EmailMessage)
        .where(EmailMessage.id == message_id, EmailMessage.status.in_(only_from))
        .values(status=status, status_updated_at=now, **values)
        .returning(EmailMessage.id)
    )
    return result.first() is not None


async def set_status_by_provider_id(
    session: AsyncSession,
    provider_message_id: str,
    *,
    status: str,
    now: datetime,
    only_from: tuple[str, ...],
) -> bool:
    result = await session.execute(
        update(EmailMessage)
        .where(
            EmailMessage.provider_message_id == provider_message_id,
            EmailMessage.status.in_(only_from),
        )
        .values(status=status, status_updated_at=now)
        .returning(EmailMessage.id)
    )
    return result.first() is not None


async def scheduled_before(session: AsyncSession, before: datetime) -> list[uuid.UUID]:
    """For the requeue_stuck_work sweeper: emails due before `before` that never went out."""
    rows = await session.scalars(
        select(EmailMessage.id)
        .where(EmailMessage.status == SCHEDULED, EmailMessage.scheduled_for < before)
        .order_by(EmailMessage.scheduled_for)
        .limit(500)
    )
    return list(rows)
