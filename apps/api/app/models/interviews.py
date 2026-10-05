"""AI interview rows (DATABASE.md "Interviews"). Check constraints live only in the migrations."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


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


class Interview(Base):
    """One interview link for an application (DATABASE.md "Interviews"). SCREEN-003 creates it
    with the invitation; the interview tasks fill in the rest."""

    __tablename__ = "interviews"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="interviews_workspace_id_id_key"),
        ForeignKeyConstraint(
            ["workspace_id", "application_id"],
            ["applications.workspace_id", "applications.id"],
            name="interviews_application_fkey",
            ondelete="CASCADE",
        ),
        Index(
            "interviews_application_id_live_key",
            "application_id",
            unique=True,
            postgresql_where=text("superseded_by IS NULL"),
        ),
        Index("interviews_status_expires_at_idx", "status", "expires_at"),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    application_id: Mapped[uuid.UUID] = mapped_column()
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    format: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'not_started'::text"))
    drop_reason: Mapped[str | None] = mapped_column(Text)
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    talk_seconds: Mapped[int | None] = mapped_column(Integer)
    consent_version: Mapped[str | None] = mapped_column(Text)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    biometric_consent_version: Mapped[str | None] = mapped_column(Text)
    recording_path: Mapped[str | None] = mapped_column(Text)
    recording_status: Mapped[str] = mapped_column(Text, server_default=text("'none'::text"))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    feedback_rating: Mapped[int | None] = mapped_column(Integer)
    feedback_comment: Mapped[str | None] = mapped_column(Text)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("interviews.id"))


class InterviewAttempt(Base):
    """One connection to the live AI interviewer (INTV-004). A reconnect or a resume is a new
    attempt; the interview's `talk_seconds` is the sum of its attempts'."""

    __tablename__ = "interview_attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "interview_id"],
            ["interviews.workspace_id", "interviews.id"],
            name="interview_attempts_interview_fkey",
            ondelete="CASCADE",
        ),
        Index("interview_attempts_interview_id_started_at_idx", "interview_id", "started_at"),
        Index(
            "interview_attempts_open_idx",
            "started_at",
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    interview_id: Mapped[uuid.UUID] = mapped_column()
    realtime_session_id: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[str | None] = mapped_column(Text)
    seconds_allowed: Mapped[int] = mapped_column(Integer)
    talk_seconds: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    resume_from: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    topic_index: Mapped[int | None] = mapped_column(Integer)
    wrap_up_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
