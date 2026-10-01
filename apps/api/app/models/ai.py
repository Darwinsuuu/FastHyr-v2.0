"""AI call log (DATABASE.md §2, AI_PIPELINE.md §7): one row per model call, written only by
`app/ai/`. Check constraints live only in the migration."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text, text
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
