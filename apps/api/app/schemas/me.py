import uuid

from pydantic import BaseModel

from app.core.context import Role


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str | None
    email_verified: bool
    full_name: str | None
    avatar_url: str | None
    last_workspace_id: uuid.UUID | None


class MyWorkspace(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    role: Role
    is_owner: bool
    member_count: int
