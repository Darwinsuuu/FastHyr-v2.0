import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.context import Role


class MemberDepartment(BaseModel):
    id: uuid.UUID
    name: str


class Member(BaseModel):
    """An active member of the workspace (FR-WS-05). Admins see every department, so their
    `departments` list is always empty."""

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str | None
    email: str | None
    avatar_url: str | None
    role: Role
    is_owner: bool
    is_you: bool
    departments: list[MemberDepartment]
    last_active_at: datetime | None
    status: Literal["active"]
    joined_at: datetime


class MemberList(BaseModel):
    members: list[Member]


class UpdateMemberRequest(BaseModel):
    """Only the fields sent change. Making someone an Admin clears their departments."""

    role: Role | None = None
    department_ids: list[uuid.UUID] | None = Field(default=None, max_length=200)
