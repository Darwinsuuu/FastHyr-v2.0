"""Email messages (DATABASE.md §2 Messaging): one row per email sent, rendered when queued.
Only services/emails.py writes them. Check constraints live only in the migration."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


class EmailMessage(Base):
    __tablename__ = "email_messages"
    __table_args__ = (
        Index("email_messages_workspace_id_created_at_idx", "workspace_id", "created_at"),
        Index(
            "email_messages_application_id_idx",
            "application_id",
            postgresql_where=text("application_id is not null"),
        ),
        Index(
            "email_messages_provider_message_id_key",
            "provider_message_id",
            unique=True,
            postgresql_where=text("provider_message_id is not null"),
        ),
        Index(
            "email_messages_scheduled_for_idx",
            "scheduled_for",
            postgresql_where=text("status = 'scheduled'"),
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"))
    application_id: Mapped[uuid.UUID | None] = mapped_column()
    template_key: Mapped[str] = mapped_column(Text)
    to_email: Mapped[str] = mapped_column(Text)
    from_name: Mapped[str] = mapped_column(Text)
    subject_rendered: Mapped[str] = mapped_column(Text)
    html_rendered: Mapped[str] = mapped_column(Text)
    text_rendered: Mapped[str] = mapped_column(Text)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(Text, server_default=text("'scheduled'"))
    provider_message_id: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
