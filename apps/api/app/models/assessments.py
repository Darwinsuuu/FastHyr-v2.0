"""Interview assessments (DATABASE.md "Interviews", ASMT-001). Check constraints live only in the
migration."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, ForeignKeyConstraint, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


class Assessment(Base):
    """The explainable assessment of one completed interview: criterion scores with signals and
    evidence, topics, summary, strengths, probes, résumé claims checked and answer patterns.
    The overall score, pass/fail and fit are computed in code (ADR-011)."""

    __tablename__ = "assessments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "application_id"],
            ["applications.workspace_id", "applications.id"],
            name="assessments_application_fkey",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "interview_id"],
            ["interviews.workspace_id", "interviews.id"],
            name="assessments_interview_fkey",
            ondelete="CASCADE",
        ),
        Index("assessments_workspace_id_application_id_idx", "workspace_id", "application_id"),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    application_id: Mapped[uuid.UUID] = mapped_column()
    interview_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    overall_score: Mapped[int] = mapped_column(Integer)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB)
    topics: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB)
    strengths: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    probes: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    claims_checked: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    answer_stats: Mapped[dict[str, Any]] = mapped_column(JSONB)
    rubric_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    passed: Mapped[bool] = mapped_column(Boolean)
    fit: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
