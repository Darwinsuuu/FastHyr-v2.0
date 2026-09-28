"""Who is calling and on whose behalf (MULTI_TENANCY.md §2).

- `RequestContext`: a TA member acting in one workspace (`X-Workspace-Id`).
- `CandidateContext`: a signed-in candidate on `/candidate/*`; sees only their own applications.
- `PublicContext`: no sign-in (apply page); only candidate-safe published fields.
- `SystemContext`: background jobs, bound to the workspace of the entity being processed.
"""

import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"


@dataclass(frozen=True)
class RequestContext:
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    member_id: uuid.UUID
    role: Role
    is_owner: bool
    # The member's assigned departments. Ignored for Admins, who see every department.
    department_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)

    @property
    def sees_all_departments(self) -> bool:
        """Admins see every department and "No department"; others only their own."""
        return self.role is Role.ADMIN


@dataclass(frozen=True)
class CandidateContext:
    user_id: uuid.UUID


@dataclass(frozen=True)
class PublicContext:
    pass


@dataclass(frozen=True)
class SystemContext:
    workspace_id: uuid.UUID
