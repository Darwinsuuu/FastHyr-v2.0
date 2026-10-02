import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.core.context import Role

# The Departments form's limits (frame Departments); the migration allows longer names.
DepartmentName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
]
DepartmentDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]


class CreateDepartmentRequest(BaseModel):
    name: DepartmentName
    description: DepartmentDescription | None = None


class UpdateDepartmentRequest(BaseModel):
    """Only the fields sent change; `description: null` or "" clears it."""

    name: DepartmentName | None = None
    description: DepartmentDescription | None = None


class PipelineCounts(BaseModel):
    """Pipelines by where they are in their lifecycle (WORKFLOW.md §2)."""

    active: int = 0  # live, or paused
    scheduled: int = 0
    closed: int = 0  # closed or cancelled
    draft: int = 0


class DepartmentMember(BaseModel):
    """A member who can see the department's pipelines: every Admin, plus Recruiters and Hiring
    managers assigned to it."""

    member_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str | None
    avatar_url: str | None
    role: Role


class DepartmentStats(BaseModel):
    pipelines: PipelineCounts
    # Applicants across the department's pipelines. Always 0 until APPLY-003 adds applications.
    candidate_count: int
    members: list[DepartmentMember]


class Department(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    # Whether the caller works in this department: true for every department for Admins, and for
    # a Recruiter or Hiring manager's own departments. Pipelines can only be filed under these.
    assigned: bool
    # Only for Admins (the Departments page); other roles get names for pickers and filters.
    stats: DepartmentStats | None = None


class DepartmentList(BaseModel):
    """Every department in the workspace by name. `no_department` is the built-in "No department"
    (pipelines without one); like `stats`, only Admins get it."""

    departments: list[Department]
    no_department: DepartmentStats | None = None
