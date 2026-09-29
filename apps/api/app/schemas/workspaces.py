import uuid
from typing import Annotated

from pydantic import BaseModel, StringConstraints

# Same limit as the workspaces.name check in the migration.
WorkspaceName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
InviteCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class CreateWorkspaceRequest(BaseModel):
    name: WorkspaceName


class AcceptInviteRequest(BaseModel):
    code: InviteCode


class LastWorkspaceRequest(BaseModel):
    workspace_id: uuid.UUID
