"""Declarative base for the SQLAlchemy models. The models mirror supabase/migrations (the source
of truth); `scripts/check_schema_drift.py` fails when the two disagree."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, MetaData, Table, Uuid, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.ids import new_id


class Base(DeclarativeBase):
    metadata = MetaData()


# Supabase Auth's users table, declared only so profiles.id can reference it.
auth_users = Table("users", Base.metadata, Column("id", Uuid, primary_key=True), schema="auth")


def id_column() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=new_id, server_default=text("gen_random_uuid()"))


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())
