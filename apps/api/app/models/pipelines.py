"""Pipelines (DATABASE.md §2 Pipelines). BILL-002 created the table with the credit columns;
WS-002 added the department; PIPE-001 added setup, schedule and lifecycle. Check constraints and
the setup lock trigger live only in the migration."""

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
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

from app.models.base import Base, created_at_column, id_column


class Pipeline(Base):
    __tablename__ = "pipelines"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="pipelines_workspace_id_id_key"),
        # No ON DELETE action: the department service moves pipelines to No department first.
        ForeignKeyConstraint(
            ["workspace_id", "department_id"],
            ["departments.workspace_id", "departments.id"],
            name="pipelines_department_fkey",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "owner_id"],
            ["workspace_members.workspace_id", "workspace_members.id"],
            name="pipelines_owner_fkey",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "published_by"],
            ["workspace_members.workspace_id", "workspace_members.id"],
            name="pipelines_published_by_fkey",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "duplicated_from_id"],
            ["pipelines.workspace_id", "pipelines.id"],
            name="pipelines_duplicated_from_fkey",
        ),
        Index("pipelines_workspace_id_department_id_idx", "workspace_id", "department_id"),
        Index("pipelines_workspace_id_status_idx", "workspace_id", "status"),
        Index("pipelines_workspace_id_slug_key", "workspace_id", "slug", unique=True),
        Index("pipelines_opens_at_idx", "opens_at", postgresql_where=text("status = 'scheduled'")),
        Index(
            "pipelines_closes_at_idx",
            "closes_at",
            postgresql_where=text(
                "status = ANY (ARRAY['live'::text, 'paused'::text, 'paused_no_credits'::text])"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    # Null is "No department", which only Admins see (MULTI_TENANCY.md §2).
    department_id: Mapped[uuid.UUID | None] = mapped_column()
    # Workspace member IDs: who created it and who published it.
    owner_id: Mapped[uuid.UUID | None] = mapped_column()
    published_by: Mapped[uuid.UUID | None] = mapped_column()
    # Set on publish and never changed after (FR-PIPE-15).
    slug: Mapped[str | None] = mapped_column(Text)

    # Role (FR-PIPE-01)
    title: Mapped[str | None] = mapped_column(Text)
    employment_type: Mapped[str | None] = mapped_column(Text)
    work_setup: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    jd_text: Mapped[str | None] = mapped_column(Text)
    must_haves: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    nice_to_haves: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    open_to: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    resume_pass_bar: Mapped[int] = mapped_column(Integer, server_default=text("60"))

    # AI interview (FR-PIPE-02)
    interview_format: Mapped[str | None] = mapped_column(Text)
    tone: Mapped[str | None] = mapped_column(Text)
    seniority: Mapped[str | None] = mapped_column(Text)
    skills_to_probe: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    link_expiry_days: Mapped[int] = mapped_column(Integer, server_default=text("5"))
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    integrity_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    # Scoring (FR-PIPE-03)
    weight_technical: Mapped[int | None] = mapped_column(Integer)
    weight_communication: Mapped[int | None] = mapped_column(Integer)
    weight_culture: Mapped[int | None] = mapped_column(Integer)
    pass_mark: Mapped[int] = mapped_column(Integer, server_default=text("70"))
    email_resume_reject: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    email_post_interview: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    # Schedule & credits (FR-PIPE-04). credits_to_reserve is the wizard's choice, kept on the
    # draft; credits_reserved is what the credit service actually set aside.
    open_mode: Mapped[str | None] = mapped_column(Text)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_days: Mapped[int | None] = mapped_column(Integer)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    credits_to_reserve: Mapped[int | None] = mapped_column(Integer)
    credits_reserved: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    credits_used: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    # Lifecycle (WORKFLOW.md §2)
    status: Mapped[str] = mapped_column(Text, server_default=text("'draft'"))
    closed_reason: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # When it closed or was cancelled (PIPE-004); closes_at is only the planned date.
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duplicated_from_id: Mapped[uuid.UUID | None] = mapped_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
