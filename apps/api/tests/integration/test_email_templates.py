"""MSG-001: every workspace has the ten candidate email templates, including workspaces made
before them; a save keeps the change history; one workspace never reads another's templates."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import Role
from app.emails.defaults import DEFAULTS, TemplateKey
from app.services import email_templates
from tests.integration.test_pipelines import db_run, sql
from tests.tenancy.harness import Tenancy


def test_workspaces_made_before_templates_get_the_defaults_when_read(tenancy: Tenancy) -> None:
    # The harness inserts workspaces directly, as they were before MSG-001.
    workspace_id = tenancy.workspace("a").id
    assert sql(tenancy, "select 1 from email_templates where workspace_id = $1", workspace_id) == []

    async def read(session: AsyncSession) -> list[str]:
        rows = await email_templates.list_templates(session, workspace_id)
        await session.commit()
        return [row.key for row in rows]

    assert db_run(tenancy, read) == [key.value for key in TemplateKey]
    # Reading again adds nothing.
    db_run(tenancy, read)
    rows = sql(
        tenancy,
        "select key, subject, body_html, is_default from email_templates where workspace_id = $1",
        workspace_id,
    )
    assert len(rows) == 10
    for row in rows:
        default = DEFAULTS[TemplateKey(row["key"])]
        assert (row["subject"], row["body_html"], row["is_default"]) == (
            default.subject,
            default.body_html,
            True,
        )


def test_a_save_replaces_the_wording_and_adds_a_version(tenancy: Tenancy) -> None:
    workspace_id = tenancy.workspace("a").id
    other_id = tenancy.workspace("b").id
    editor = tenancy.member("a", Role.RECRUITER).user_id

    async def save(session: AsyncSession) -> uuid.UUID:
        for subject in ("First wording", "Second wording"):
            template = await email_templates.save(
                session,
                workspace_id,
                editor,
                TemplateKey.NEXT_STAGE,
                subject=subject,
                body_html="<p>Hi [Candidate.firstname], see you soon.</p>",
            )
        await session.commit()
        return template.id

    template_id = db_run(tenancy, save)

    [row] = sql(
        tenancy,
        "select subject, is_default, updated_by from email_templates where id = $1",
        template_id,
    )
    assert (row["subject"], row["is_default"], row["updated_by"]) == (
        "Second wording",
        False,
        editor,
    )

    async def history(session: AsyncSession) -> tuple[list[str], list[str]]:
        mine = await email_templates.versions(session, workspace_id, TemplateKey.NEXT_STAGE)
        theirs = await email_templates.versions(session, other_id, TemplateKey.NEXT_STAGE)
        other = await email_templates.get_template(session, other_id, TemplateKey.NEXT_STAGE)
        await session.commit()
        return [v.subject for v in mine], [v.subject for v in theirs] + [other.subject]

    mine, theirs = db_run(tenancy, history)
    assert mine == ["First wording", "Second wording"]
    # The other workspace still has the default and no history.
    assert theirs == [DEFAULTS[TemplateKey.NEXT_STAGE].subject]
