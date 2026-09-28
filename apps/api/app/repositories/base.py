"""Base for workspace-scoped repositories (MULTI_TENANCY.md §2).

A repository is built for one workspace and every query it runs goes through `_scoped()`, which
adds `WHERE <table>.workspace_id = :workspace_id`. A row in another workspace therefore reads as
missing, and `_get_or_404()` turns that into a 404, so other workspaces stay invisible.
"""

import uuid
from typing import Any, ClassVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Base


class WorkspaceRepository[ModelT: Base]:
    model: ClassVar[type[Any]]

    def __init__(self, session: AsyncSession, workspace_id: uuid.UUID) -> None:
        if not isinstance(workspace_id, uuid.UUID):
            raise TypeError("a workspace-scoped repository needs a workspace_id")
        self.session = session
        self.workspace_id = workspace_id

    def _scoped(self, statement: Select[Any] | None = None) -> Select[Any]:
        statement = statement if statement is not None else select(self.model)
        return statement.where(self.model.workspace_id == self.workspace_id)

    async def _get_or_404(self, row_id: uuid.UUID) -> ModelT:
        row: ModelT | None = await self.session.scalar(
            self._scoped().where(self.model.id == row_id)
        )
        if row is None:
            raise NotFoundError()
        return row
