"""Email messages and workspace email templates (DATABASE.md §2 Messaging). Messages are one row
per email sent, rendered when queued; only services/emails.py writes them. Templates and their
versions are written only by services/email_templates.py. Check constraints live only in the
migrations."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
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
        Index(
            "email_messages_dedupe_key_key",
            "dedupe_key",
            unique=True,
            postgresql_where=text("dedupe_key is not null and status <> 'cancelled'"),
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"))
    application_id: Mapped[uuid.UUID | None] = mapped_column()
    # The stage a candidate email was written for (MSG-003); it is cancelled if the stage moves.
    application_stage: Mapped[str | None] = mapped_column(Text)
    dedupe_key: Mapped[str | None] = mapped_column(Text)
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


class EmailTemplate(Base):
    """A workspace's wording for one candidate email (MSG-001). Defaults: app/emails/defaults.py."""

    __tablename__ = "email_templates"
    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="email_templates_workspace_id_key_key"),
        UniqueConstraint("workspace_id", "id", name="email_templates_workspace_id_id_key"),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    key: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    body_html: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailTemplateVersion(Base):
    """One saved version of a template, for the change history (FR-MSG-02)."""

    __tablename__ = "email_template_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "template_id"],
            ["email_templates.workspace_id", "email_templates.id"],
            name="email_template_versions_template_fkey",
            ondelete="CASCADE",
        ),
        Index("email_template_versions_template_id_created_at_idx", "template_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    template_id: Mapped[uuid.UUID] = mapped_column()
    subject: Mapped[str] = mapped_column(Text)
    body_html: Mapped[str] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id"))
    created_at: Mapped[datetime] = created_at_column()
    note: Mapped[str | None] = mapped_column(Text)
