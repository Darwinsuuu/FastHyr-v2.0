"""Candidates and applications (DATABASE.md "Candidates and applications"). Check constraints
live only in the migration."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, id_column


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="candidates_workspace_id_id_key"),
        UniqueConstraint(
            "workspace_id", "auth_user_id", name="candidates_workspace_id_auth_user_id_key"
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    auth_user_id: Mapped[uuid.UUID] = mapped_column()
    email: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(Text)
    phone_country_code: Mapped[str] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    profile_url: Mapped[str | None] = mapped_column(Text)
    first_applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="applications_workspace_id_id_key"),
        UniqueConstraint(
            "pipeline_id", "candidate_id", name="applications_pipeline_id_candidate_id_key"
        ),
        ForeignKeyConstraint(
            ["workspace_id", "pipeline_id"],
            ["pipelines.workspace_id", "pipelines.id"],
            name="applications_pipeline_fkey",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "candidate_id"],
            ["candidates.workspace_id", "candidates.id"],
            name="applications_candidate_fkey",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "rejected_by"],
            ["workspace_members.workspace_id", "workspace_members.id"],
            name="applications_rejected_by_fkey",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "advanced_by"],
            ["workspace_members.workspace_id", "workspace_members.id"],
            name="applications_advanced_by_fkey",
        ),
        Index(
            "applications_workspace_id_pipeline_id_stage_idx",
            "workspace_id",
            "pipeline_id",
            "stage",
        ),
        Index("applications_workspace_id_candidate_id_idx", "workspace_id", "candidate_id"),
        Index("applications_pipeline_id_applied_at_idx", "pipeline_id", "applied_at"),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    pipeline_id: Mapped[uuid.UUID] = mapped_column()
    candidate_id: Mapped[uuid.UUID] = mapped_column()
    source: Mapped[str] = mapped_column(Text, server_default=text("'direct'::text"))
    resume_path: Mapped[str] = mapped_column(Text)
    resume_filename: Mapped[str] = mapped_column(Text)
    resume_pages: Mapped[int] = mapped_column(Integer)
    resume_bytes: Mapped[int] = mapped_column(Integer)
    consent_version: Mapped[str] = mapped_column(Text)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_ip_hash: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(Text, server_default=text("'processing_resume'::text"))
    stage_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resume_status: Mapped[str] = mapped_column(Text, server_default=text("'pending'::text"))
    fit: Mapped[str | None] = mapped_column(Text)
    overall_score: Mapped[int | None] = mapped_column(Integer)
    has_open_flags: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    review_requested: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    rejected_by: Mapped[uuid.UUID | None] = mapped_column()
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    advanced_note: Mapped[str | None] = mapped_column(Text)
    advanced_by: Mapped[uuid.UUID | None] = mapped_column()
    advanced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    credit_ledger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("credit_ledger.id"))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
