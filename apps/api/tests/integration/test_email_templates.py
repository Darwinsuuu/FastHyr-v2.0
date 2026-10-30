"""MSG-001: every workspace has the ten candidate email templates, including workspaces made
before them; a save keeps the change history; one workspace never reads another's templates."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import Role
from app.emails.defaults import DEFAULTS, TemplateKey
from app.services import email_templates
from tests.integration.test_pipelines import db_run, ok, sql
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


# MSG-002: the editor's endpoints.

TEMPLATES = "/v1/email-templates"


def test_editing_cleans_the_html_and_keeps_every_version(tenancy: Tenancy) -> None:
    recruiter = tenancy.client("a", Role.RECRUITER)
    admin = tenancy.client("a", Role.ADMIN)
    url = f"{TEMPLATES}/next_stage"

    listed = ok(recruiter.get(TEMPLATES))["templates"]
    assert [row["key"] for row in listed] == [key.value for key in TemplateKey]
    assert all(row["is_default"] and row["updated_by"] is None for row in listed)
    assert ok(recruiter.get(f"{url}/versions"))["versions"] == []

    saved = ok(
        recruiter.put(
            url,
            json={
                "subject": "  Good news,   [Candidate.firstname] ",
                "body_html": '<p onclick="x()">Hi <strong>[Candidate.firstname]</strong>,</p>'
                "<script>alert(1)</script><h1>Big</h1><ul><li><p>One</p></li></ul>"
                '<p><a href="javascript:alert(1)">bad</a> <a href="https://acme.test">ok</a></p>',
            },
        )
    )
    assert saved["subject"] == "Good news, [Candidate.firstname]"
    body = saved["body_html"]
    for gone in ("onclick", "<script", "alert", "<h1", "javascript:"):
        assert gone not in body
    assert "<strong>[Candidate.firstname]</strong>" in body
    assert 'href="https://acme.test"' in body
    assert saved["is_default"] is False
    assert saved["updated_by"]["id"] == str(tenancy.member("a", Role.RECRUITER).user_id)
    assert saved["parameters"] == ["Candidate.firstname", "Candidate.lastname", "Job.title",
                                   "Company.name"]  # fmt: skip
    assert saved["review_line"] is False

    first = ok(admin.get(f"{url}/versions"))["versions"]
    assert [(v["kind"], v["subject"]) for v in first] == [("edit", saved["subject"])]

    # Reset: the default again, as a new version.
    reset = ok(admin.post(f"{url}/reset"))
    assert reset["is_default"] is True
    assert reset["subject"] == DEFAULTS[TemplateKey.NEXT_STAGE].subject

    # Restore the edit: a third version with the edit's wording; nothing is rewritten.
    restored = ok(admin.post(f"{url}/versions/{first[0]['id']}/restore"))
    assert (restored["subject"], restored["body_html"], restored["is_default"]) == (
        saved["subject"],
        saved["body_html"],
        False,
    )
    history = ok(admin.get(f"{url}/versions"))["versions"]
    assert [v["kind"] for v in history] == ["restore", "reset", "edit"]
    assert history[0]["created_by"]["id"] == str(tenancy.member("a", Role.ADMIN).user_id)
    assert history[2]["id"] == first[0]["id"]

    row = next(r for r in ok(admin.get(TEMPLATES))["templates"] if r["key"] == "next_stage")
    assert (row["is_default"], row["updated_by"]["id"]) == (False, history[0]["created_by"]["id"])

    audit = sql(
        tenancy,
        "select action, data->>'key' as key from audit_log where entity_type = 'email_template' "
        "and workspace_id = $1 order by created_at",
        tenancy.workspace("a").id,
    )
    assert [(r["action"], r["key"]) for r in audit] == [
        ("email_template.edited", "next_stage"),
        ("email_template.reset", "next_stage"),
        ("email_template.restored", "next_stage"),
    ]
    # Workspace B's template is untouched.
    theirs = ok(tenancy.client("b", Role.ADMIN).get(url))
    assert theirs["is_default"] is True


def test_editor_refusals(tenancy: Tenancy) -> None:
    recruiter = tenancy.client("a", Role.RECRUITER)
    body = {"subject": "Hello", "body_html": "<p>Hi</p>"}
    # Hiring managers can't read or edit templates.
    manager = tenancy.client("a", Role.HIRING_MANAGER)
    assert manager.get(TEMPLATES).status_code == 403
    assert manager.put(f"{TEMPLATES}/next_stage", json=body).status_code == 403
    # Unknown keys and versions are not found.
    assert recruiter.get(f"{TEMPLATES}/welcome").json()["code"] == "not_found"
    missing = f"{TEMPLATES}/next_stage/versions/{uuid.uuid4()}/restore"
    assert recruiter.post(missing).json()["code"] == "not_found"
    # A parameter the template can't fill, or an empty message.
    response = recruiter.put(
        f"{TEMPLATES}/next_stage",
        json={"subject": "[Interview.link]", "body_html": "<p><br></p>"},
    )
    assert response.status_code == 422
    assert [(e["loc"][-1], e["type"]) for e in response.json()["errors"]] == [
        ("body_html", "missing"),
        ("subject", "unknown_parameter"),
    ]
    # A version of another template can't be restored into this one.
    ok(recruiter.put(f"{TEMPLATES}/role_closed", json=body))
    [other] = ok(recruiter.get(f"{TEMPLATES}/role_closed/versions"))["versions"]
    wrong = recruiter.post(f"{TEMPLATES}/next_stage/versions/{other['id']}/restore")
    assert wrong.json()["code"] == "not_found"


def test_send_test_to_me_uses_the_unsaved_wording_and_sample_details(tenancy: Tenancy) -> None:
    recruiter = tenancy.member("a", Role.RECRUITER)
    sent = ok(
        tenancy.client("a", Role.RECRUITER).post(
            f"{TEMPLATES}/reject_resume/test",
            json={
                "subject": "About [Job.title], [Candidate.firstname]",
                "body_html": "<p>Hi [Candidate.firstname] [Candidate.lastname].</p>",
            },
        ),
        202,
    )
    assert sent["to_email"] == recruiter.email
    assert sent["subject"] == "About Senior Backend Engineer, Bea"
    [message] = sql(
        tenancy,
        "select to_email, template_key, html_rendered, application_id from email_messages "
        "where id = $1",
        uuid.UUID(sent["message_id"]),
    )
    assert (message["to_email"], message["template_key"], message["application_id"]) == (
        recruiter.email,
        "test",
        None,
    )
    assert "Hi Bea Garcia." in message["html_rendered"]
    # Rejections always carry the review line, filled with a sample link.
    assert "Want a person to review this decision?" in message["html_rendered"]
    assert "/review-request/sample" in message["html_rendered"]
    # Nothing was saved.
    template = ok(tenancy.client("a", Role.RECRUITER).get(f"{TEMPLATES}/reject_resume"))
    assert template["is_default"] is True
