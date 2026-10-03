"""Email messages (FND-010). Emails can belong to no workspace (the contact form) and the send
job and the Resend webhook find them by ID across workspaces, so these are plain functions
keyed by message ID rather than a workspace repository. Only services/emails.py calls them."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, EmailMessage

SCHEDULED, SENDING, SENT, FAILED = "scheduled", "sending", "sent", "failed"
DELIVERED, BOUNCED, COMPLAINED = "delivered", "bounced", "complained"
CANCELLED = "cancelled"

# Cancel reasons (MSG-003).
STAGE_CHANGED = "stage_changed"

# The application is still in the stage the email was written for (or it isn't about one).
_STAGE_UNCHANGED = or_(
    EmailMessage.application_stage.is_(None),
    exists().where(
        Application.id == EmailMessage.application_id,
        Application.stage == EmailMessage.application_stage,
    ),
)


def add(session: AsyncSession, message: EmailMessage) -> EmailMessage:
    session.add(message)
    return message


async def add_unless_duplicate(session: AsyncSession, message: EmailMessage) -> EmailMessage | None:
    """Inserts an email with a dedupe key; None when a live email with that key exists."""
    columns = {
        column.key: getattr(message, column.key)
        for column in EmailMessage.__table__.columns
        if getattr(message, column.key) is not None
    }
    row_id = await session.scalar(
        insert(EmailMessage)
        .values(**columns)
        .on_conflict_do_nothing(
            index_elements=[EmailMessage.dedupe_key],
            index_where=and_(
                EmailMessage.dedupe_key.is_not(None), EmailMessage.status != CANCELLED
            ),
        )
        .returning(EmailMessage.id)
    )
    if row_id is None:
        return None
    return await session.get(EmailMessage, row_id)


async def live_by_dedupe_key(session: AsyncSession, dedupe_key: str) -> EmailMessage | None:
    row: EmailMessage | None = await session.scalar(
        select(EmailMessage).where(
            EmailMessage.dedupe_key == dedupe_key, EmailMessage.status != CANCELLED
        )
    )
    return row


async def cancel_scheduled(
    session: AsyncSession, application_id: uuid.UUID, *, reason: str, now: datetime
) -> int:
    """Cancels the application's emails that haven't started sending."""
    result = await session.execute(
        update(EmailMessage)
        .where(EmailMessage.application_id == application_id, EmailMessage.status == SCHEDULED)
        .values(status=CANCELLED, cancel_reason=reason, status_updated_at=now)
        .returning(EmailMessage.id)
    )
    return len(result.all())


async def cancel_if_stage_changed(
    session: AsyncSession, message_id: uuid.UUID, now: datetime
) -> bool:
    """The send job's safety net: cancels a scheduled email whose application has moved on from
    the stage it was written for."""
    result = await session.execute(
        update(EmailMessage)
        .where(EmailMessage.id == message_id, EmailMessage.status == SCHEDULED, ~_STAGE_UNCHANGED)
        .values(status=CANCELLED, cancel_reason=STAGE_CHANGED, status_updated_at=now)
        .returning(EmailMessage.id)
    )
    return result.first() is not None


async def claim(session: AsyncSession, message_id: uuid.UUID, now: datetime) -> EmailMessage | None:
    """Marks a due email as sending and returns it; None when it was cancelled, already sent,
    isn't due, or its application has moved to another stage. A retry finds it `sending` and
    tries again (the provider drops duplicates)."""
    row: EmailMessage | None = await session.scalar(
        update(EmailMessage)
        .where(
            EmailMessage.id == message_id,
            EmailMessage.scheduled_for <= now,
            or_(
                EmailMessage.status == SENDING,
                and_(EmailMessage.status == SCHEDULED, _STAGE_UNCHANGED),
            ),
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
) -> EmailMessage | None:
    """Returns the email when it moved."""
    row: EmailMessage | None = await session.scalar(
        update(EmailMessage)
        .where(
            EmailMessage.provider_message_id == provider_message_id,
            EmailMessage.status.in_(only_from),
        )
        .values(status=status, status_updated_at=now)
        .returning(EmailMessage)
    )
    return row


async def due(session: AsyncSession, now: datetime) -> list[uuid.UUID]:
    """For the dispatch_scheduled_emails cron: scheduled emails whose time has come."""
    rows = await session.scalars(
        select(EmailMessage.id)
        .where(EmailMessage.status == SCHEDULED, EmailMessage.scheduled_for <= now)
        .order_by(EmailMessage.scheduled_for)
        .limit(500)
    )
    return list(rows)
