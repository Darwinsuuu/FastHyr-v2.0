"""Résumé screening (DATABASE.md "Candidates and applications"). Check constraints live only in
the migration."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column


class ResumeText(Base):
    """The redacted résumé text every scoring step reads (SCREEN-001). One row per readable
    résumé; the original text is never stored."""

    __tablename__ = "resume_texts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "application_id"],
            ["applications.workspace_id", "applications.id"],
            name="resume_texts_application_fkey",
            ondelete="CASCADE",
        ),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    redacted_text: Mapped[str] = mapped_column(Text)
    characters: Mapped[int] = mapped_column(Integer)
    pages: Mapped[int] = mapped_column(Integer)
    column_pages: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    masked: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    redaction_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
