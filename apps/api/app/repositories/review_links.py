"""Human-review links of automated rejections in one workspace (ADR-015, SCREEN-003)."""

import uuid

from app.models import ReviewLink
from app.repositories.base import WorkspaceRepository


class ReviewLinkRepository(WorkspaceRepository[ReviewLink]):
    model = ReviewLink

    async def link_of(self, application_id: uuid.UUID, decision_type: str) -> ReviewLink | None:
        row: ReviewLink | None = await self.session.scalar(
            self._scoped().where(
                ReviewLink.application_id == application_id,
                ReviewLink.decision_type == decision_type,
            )
        )
        return row

    def add(self, link: ReviewLink) -> None:
        if link.workspace_id != self.workspace_id:
            raise ValueError("review link belongs to another workspace")
        self.session.add(link)
