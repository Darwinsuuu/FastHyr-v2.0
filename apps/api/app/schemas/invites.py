import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

from app.core.context import Role
from app.schemas.members import MemberDepartment

# A light check: the invite only works for someone who signs in with this exact email.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

InviteEmail = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=254, pattern=EMAIL_PATTERN),
    AfterValidator(str.lower),
]


class CreateInviteRequest(BaseModel):
    """Invites an email with a role and departments. Admins see every department, so theirs are
    ignored. An existing pending invite for the email is replaced."""

    email: InviteEmail
    role: Role
    department_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)


class Invite(BaseModel):
    """A pending invite (FR-WS-03). `code` is what the invitee enters to join; resending changes
    it. `sent_at` is the latest send or resend; the invite expires 7 days after it."""

    id: uuid.UUID
    email: str
    role: Role
    departments: list[MemberDepartment]
    code: str
    invited_by_name: str | None
    sent_at: datetime
    expires_at: datetime


class InviteList(BaseModel):
    invites: list[Invite]
