"""Audit log (DATABASE.md §2 Compliance and ops). Append-only: the database rejects updates and
deletes, so services only ever insert rows."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("audit_log_workspace_id_created_at_idx", "workspace_id", "created_at"),)

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    actor_id: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column()
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at_column()
