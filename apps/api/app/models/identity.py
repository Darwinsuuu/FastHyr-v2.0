"""Identity and workspaces (DATABASE.md §2). Check constraints live only in the migration."""

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, id_column


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    last_workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL", use_alter=True)
    )
    created_at: Mapped[datetime] = created_at_column()


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = id_column()
    name: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"))
    timezone: Mapped[str] = mapped_column(Text, server_default=text("'UTC'"))
    stripe_customer_id: Mapped[str | None] = mapped_column(Text, unique=True)
    trial_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_column()


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    company_name: Mapped[str] = mapped_column(Text)
    logo_path: Mapped[str | None] = mapped_column(Text)
    banner_path: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(Text)
    company_size: Mapped[str | None] = mapped_column(Text)
    hq_country: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str | None] = mapped_column(Text)
    about: Mapped[str | None] = mapped_column(Text)
    careers_url: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="departments_workspace_id_id_key"),
        Index(
            "departments_workspace_id_name_key",
            "workspace_id",
            func.lower(text("name")),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "user_id", name="workspace_members_workspace_id_user_id_key"
        ),
        UniqueConstraint("workspace_id", "id", name="workspace_members_workspace_id_id_key"),
        Index("workspace_members_user_id_idx", "user_id"),
        Index(
            "workspace_members_one_owner_idx",
            "workspace_id",
            unique=True,
            postgresql_where=text("is_owner"),
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"))
    role: Mapped[str] = mapped_column(Text)
    is_owner: Mapped[bool] = mapped_column(server_default=text("false"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'active'"))
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_column()


class MemberDepartment(Base):
    __tablename__ = "member_departments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "member_id"],
            ["workspace_members.workspace_id", "workspace_members.id"],
            name="member_departments_member_fkey",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "department_id"],
            ["departments.workspace_id", "departments.id"],
            name="member_departments_department_fkey",
            ondelete="CASCADE",
        ),
        Index("member_departments_department_id_idx", "department_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    member_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    department_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (
        Index(
            "invites_one_pending_per_email_idx",
            "workspace_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = id_column()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    email: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    department_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(Uuid), server_default=text("'{}'")
    )
    code: Mapped[str] = mapped_column(Text, unique=True)
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("(now() + interval '7 days')")
    )
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id"))
    created_at: Mapped[datetime] = created_at_column()
