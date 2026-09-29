"""Pipelines (DATABASE.md §2 Pipelines). BILL-002 created the table with the credit columns only;
PIPE-001 adds setup, schedule and lifecycle. Check constraints live only in the migration."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


class Pipeline(Base):
    __tablename__ = "pipelines"
    __table_args__ = (UniqueConstraint("workspace_id", "id", name="pipelines_workspace_id_id_key"),)

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'draft'"))
    credits_reserved: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    credits_used: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
