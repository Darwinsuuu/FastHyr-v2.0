"""SQLAlchemy models. Import every model module here so `Base.metadata` is complete."""

from app.models.audit import AuditLog
from app.models.base import Base
from app.models.identity import (
    CompanyProfile,
    Department,
    Invite,
    MemberDepartment,
    Profile,
    Workspace,
    WorkspaceMember,
)

__all__ = [
    "AuditLog",
    "Base",
    "CompanyProfile",
    "Department",
    "Invite",
    "MemberDepartment",
    "Profile",
    "Workspace",
    "WorkspaceMember",
]
