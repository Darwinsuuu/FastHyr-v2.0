"""SQLAlchemy models. Import every model module here so `Base.metadata` is complete."""

from app.models.ai import AICall, AIDecision
from app.models.applications import Application, Candidate, ReviewLink
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.credits import CreditBatch, CreditLedgerEntry
from app.models.emails import EmailMessage, EmailTemplate, EmailTemplateVersion
from app.models.identity import (
    CompanyProfile,
    Department,
    Invite,
    MemberDepartment,
    Profile,
    Workspace,
    WorkspaceMember,
)
from app.models.interviews import (
    Interview,
    InterviewAttempt,
    InterviewEvent,
    InterviewPlan,
    RecordingChunk,
    TranscriptSegment,
)
from app.models.jobs import ReportJob
from app.models.pipelines import Pipeline
from app.models.screening import ResumeAssessment, ResumeText

__all__ = [
    "AICall",
    "AIDecision",
    "Application",
    "AuditLog",
    "Base",
    "Candidate",
    "CompanyProfile",
    "CreditBatch",
    "CreditLedgerEntry",
    "Department",
    "EmailMessage",
    "EmailTemplate",
    "EmailTemplateVersion",
    "Interview",
    "InterviewAttempt",
    "InterviewEvent",
    "InterviewPlan",
    "Invite",
    "MemberDepartment",
    "Pipeline",
    "Profile",
    "RecordingChunk",
    "ReportJob",
    "ResumeAssessment",
    "ResumeText",
    "ReviewLink",
    "TranscriptSegment",
    "Workspace",
    "WorkspaceMember",
]
