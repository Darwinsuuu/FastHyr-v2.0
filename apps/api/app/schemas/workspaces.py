import uuid
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, StringConstraints, model_validator

from app.core.context import Role

# Same limit as the workspaces.name check in the migration.
WorkspaceName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
# Room for a pasted join link that carries a 43-character link token.
InviteCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class CreateWorkspaceRequest(BaseModel):
    name: WorkspaceName


class AcceptInviteRequest(BaseModel):
    """`code` is what people type or paste (a code in any case, or a `/join/<code>` link);
    `token` is the link token from the invite email (AUTH-004). Exactly one."""

    code: InviteCode | None = None
    token: InviteCode | None = None

    @model_validator(mode="after")
    def one_key(self) -> Self:
        if (self.code is None) == (self.token is None):
            raise ValueError("Send either code or token")
        return self

    @property
    def key(self) -> str:
        return self.code or self.token or ""


class InviteState(StrEnum):
    READY = "ready"
    ALREADY_MEMBER = "already_member"
    WRONG_EMAIL = "wrong_email"
    EXPIRED = "expired"
    INVALID = "invalid"


class InvitePreview(BaseModel):
    """What the join page (S-04) shows for an invite link. Details are only filled in for the
    person the invite is addressed to: `wrong_email` carries just the masked address, so they
    know which account to sign in with; `already_member` carries the workspace to open."""

    state: InviteState
    workspace_id: uuid.UUID | None = None
    workspace_name: str | None = None
    invited_by_name: str | None = None
    role: Role | None = None
    departments: list[str] = []
    masked_email: str | None = None


class LastWorkspaceRequest(BaseModel):
    workspace_id: uuid.UUID
