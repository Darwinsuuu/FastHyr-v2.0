"""AI interview rows (DATABASE.md "Interviews"). Check constraints live only in the migrations."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column


class InterviewPlan(Base):
    """The personal plan the AI interviewer follows for one application (INTV-001): ordered
    topics with résumé-anchored question seeds, and claims to verify."""

    __tablename__ = "interview_plans"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "application_id"],
            ["applications.workspace_id", "applications.id"],
            name="interview_plans_application_fkey",
            ondelete="CASCADE",
        ),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    topics: Mapped[list[Any]] = mapped_column(JSONB)
    claims_to_verify: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    source: Mapped[str] = mapped_column(Text)
    instructions_version: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
