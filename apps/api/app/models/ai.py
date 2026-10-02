"""AI call log and AI decision log (DATABASE.md §2, AI_PIPELINE.md §7, ADR-015). `ai_calls` is
written only by `app/ai/`; `ai_decisions` is append-only. Check constraints and triggers live
only in the migrations."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


class AICall(Base):
    __tablename__ = "ai_calls"
    __table_args__ = (
        Index("ai_calls_workspace_id_created_at_idx", "workspace_id", "created_at"),
        Index("ai_calls_purpose_created_at_idx", "purpose", "created_at"),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"))
    purpose: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column()
    model: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    audio_seconds: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    latency_ms: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class AIDecision(Base):
    """One automated outcome (résumé pass/fail, interview pass/fail, integrity flag) with what it
    was made from. Append-only: the database rejects updates and deletes (ADR-015)."""

    __tablename__ = "ai_decisions"
    __table_args__ = (
        Index("ai_decisions_workspace_id_application_id_idx", "workspace_id", "application_id"),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    application_id: Mapped[uuid.UUID] = mapped_column()
    type: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer)
    threshold: Mapped[int | None] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    input_ref: Mapped[str] = mapped_column(Text)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = created_at_column()
