"""Audit log writes for one workspace (SECURITY.md §5). The table is append-only, so this only
inserts. Rows carry IDs and non-personal details, never emails or candidate data."""

import uuid
from typing import Any

from app.models import AuditLog
from app.repositories.base import WorkspaceRepository


class AuditRepository(WorkspaceRepository[AuditLog]):
    model = AuditLog

    def record(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                workspace_id=self.workspace_id,
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                data=data or {},
            )
        )
