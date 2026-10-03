"""Email templates of one workspace and their saved versions (MSG-001). Only
services/email_templates.py calls this."""

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.emails.defaults import DefaultTemplate
from app.models import EmailTemplate, EmailTemplateVersion
from app.repositories.base import WorkspaceRepository


class EmailTemplateRepository(WorkspaceRepository[EmailTemplate]):
    model = EmailTemplate

    async def list_all(self) -> Sequence[EmailTemplate]:
        rows = await self.session.scalars(self._scoped().order_by(EmailTemplate.key))
        return rows.all()

    async def get_by_key(self, key: str, *, lock: bool = False) -> EmailTemplate | None:
        statement = self._scoped().where(EmailTemplate.key == key)
        if lock:
            statement = statement.with_for_update()
        row: EmailTemplate | None = await self.session.scalar(statement)
        return row

    async def add_missing(self, defaults: Iterable[DefaultTemplate]) -> None:
        """Adds the default for every key the workspace doesn't have yet; keeps the rest as
        they are, so it is safe to run again or alongside another request."""
        rows = [
            {
                "workspace_id": self.workspace_id,
                "key": template.key.value,
                "subject": template.subject,
                "body_html": template.body_html,
            }
            for template in defaults
        ]
        if rows:
            await self.session.execute(
                insert(EmailTemplate)
                .values(rows)
                .on_conflict_do_nothing(constraint="email_templates_workspace_id_key_key")
            )

    def add_version(self, version: EmailTemplateVersion) -> EmailTemplateVersion:
        if version.workspace_id != self.workspace_id:
            raise ValueError("version belongs to another workspace")
        self.session.add(version)
        return version

    async def versions(self, template: EmailTemplate) -> Sequence[EmailTemplateVersion]:
        rows = await self.session.scalars(
            select(EmailTemplateVersion)
            .where(
                EmailTemplateVersion.workspace_id == self.workspace_id,
                EmailTemplateVersion.template_id == template.id,
            )
            .order_by(EmailTemplateVersion.created_at, EmailTemplateVersion.id)
        )
        return rows.all()
