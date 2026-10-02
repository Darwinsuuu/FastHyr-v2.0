"""SQLAlchemy models. Import every model module here so `Base.metadata` is complete."""

from app.models.ai import AICall
from app.models.applications import Application, Candidate
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.credits import CreditBatch, CreditLedgerEntry
from app.models.emails import EmailMessage
from app.models.identity import (
    CompanyProfile,
    Department,
    Invite,
    MemberDepartment,
    Profile,
    Workspace,
    WorkspaceMember,
)
from app.models.jobs import ReportJob
from app.models.pipelines import Pipeline

__all__ = [
    "AICall",
    "Application",
    "AuditLog",
    "Base",
    "Candidate",
    "CompanyProfile",
    "CreditBatch",
    "CreditLedgerEntry",
    "Department",
    "EmailMessage",
    "Invite",
    "MemberDepartment",
    "Pipeline",
    "Profile",
    "ReportJob",
    "Workspace",
    "WorkspaceMember",
]
