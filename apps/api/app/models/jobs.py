"""Report jobs (DATABASE.md §2 Ava and reports): progress of long jobs a user waits on, polled
through `GET /v1/jobs/{id}`. Check constraints live only in the migration."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


class ReportJob(Base):
    __tablename__ = "report_jobs"
    __table_args__ = (
        Index("report_jobs_workspace_id_requested_by_idx", "workspace_id", "requested_by"),
        Index(
            "report_jobs_queued_created_at_idx",
            "created_at",
            postgresql_where=text("status = 'queued'"),
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"))
    kind: Mapped[str] = mapped_column(Text)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'queued'"))
    step: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    steps_total: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    file_path: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
