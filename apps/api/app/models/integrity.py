"""Integrity flags (DATABASE.md "Interviews", ASMT-002, ADR-016). Check constraints live only in
the migration."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, Text
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


class IntegrityFlag(Base):
    """A moment of possible impersonation for a person to review: a different face, no face, a
    second voice, answers that sounded read aloud or unusual response timing. A flag never
    rejects anyone; a person resolves it (ASMT-003)."""

    __tablename__ = "integrity_flags"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "application_id"],
            ["applications.workspace_id", "applications.id"],
            name="integrity_flags_application_fkey",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "interview_id"],
            ["interviews.workspace_id", "interviews.id"],
            name="integrity_flags_interview_fkey",
            ondelete="CASCADE",
        ),
        Index("integrity_flags_interview_id_start_ms_idx", "interview_id", "start_ms"),
        Index(
            "integrity_flags_open_idx",
            "workspace_id",
            "application_id",
            postgresql_where=sql_text("status = 'open'::text"),
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    interview_id: Mapped[uuid.UUID] = mapped_column()
    application_id: Mapped[uuid.UUID] = mapped_column()
    type: Mapped[str] = mapped_column(Text)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=sql_text("'{}'::jsonb"))
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    status: Mapped[str] = mapped_column(Text, server_default=sql_text("'open'::text"))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
