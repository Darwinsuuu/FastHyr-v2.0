"""Credit batches and the credit ledger (DATABASE.md §2 Billing, BILLING.md). Only
services/credits.py writes them. The ledger is append-only: the database rejects updates and
deletes. Check constraints live only in the migration."""

import uuid
from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


class CreditBatch(Base):
    __tablename__ = "credit_batches"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="credit_batches_workspace_id_id_key"),
        Index(
            "credit_batches_workspace_id_expires_at_idx",
            "workspace_id",
            "expires_at",
            postgresql_where=text("remaining > 0"),
        ),
        Index(
            "credit_batches_one_trial_idx",
            "workspace_id",
            unique=True,
            postgresql_where=text("kind = 'trial'"),
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    kind: Mapped[str] = mapped_column(Text)
    amount: Mapped[int] = mapped_column(Integer)
    remaining: Mapped[int] = mapped_column(Integer)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stripe_invoice_id: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)


class CreditLedgerEntry(Base):
    __tablename__ = "credit_ledger"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "pipeline_id"],
            ["pipelines.workspace_id", "pipelines.id"],
            name="credit_ledger_pipeline_fkey",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "batch_id"],
            ["credit_batches.workspace_id", "credit_batches.id"],
            name="credit_ledger_batch_fkey",
        ),
        # Checked at commit: a submission uses the credit before inserting the application.
        ForeignKeyConstraint(
            ["workspace_id", "application_id"],
            ["applications.workspace_id", "applications.id"],
            name="credit_ledger_application_fkey",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
        Index("credit_ledger_workspace_id_created_at_idx", "workspace_id", "created_at"),
        Index("credit_ledger_pipeline_id_idx", "pipeline_id"),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    kind: Mapped[str] = mapped_column(Text)
    amount: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    reserve_change: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column()
    application_id: Mapped[uuid.UUID | None] = mapped_column()
    batch_id: Mapped[uuid.UUID | None] = mapped_column()
    balance_after: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[uuid.UUID | None] = mapped_column()
    created_at: Mapped[datetime] = created_at_column()
