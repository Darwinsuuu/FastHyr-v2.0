"""Workspace candidate email templates (FR-MSG-01, FR-MSG-03; NOTIFICATIONS.md §1-2).

Every workspace has one template per key, starting from FastHyr's defaults
(`app/emails/defaults.py`). New workspaces get them when they are created; workspaces created
before MSG-001 get them the first time their templates are read here, so callers always find
all ten. A save checks the parameters, cleans the HTML with the email allow-list and records
the new wording in the change history. Rejection templates never need `[Review.link]` in the
text: `app/emails/candidate.py` adds the review line when the email is rendered.
"""

import re
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import EmailTemplateInvalidError
from app.emails.defaults import DEFAULTS, TemplateKey, parameters_for
from app.emails.render import html_to_text, sanitize
from app.models import EmailTemplate, EmailTemplateVersion
from app.repositories.email_templates import EmailTemplateRepository

SUBJECT_MAX = 200
BODY_MAX = 20_000

# Anything written like a parameter: square brackets around text with a dot, such as
# [Candidate.firstname] or a mistyped [Candidate.first_name]. "[sic]" is plain text.
_PARAMETER_LIKE = re.compile(r"\[([^\[\]<>\n]{1,60}\.[^\[\]<>\n]{1,60})\]")


async def ensure_defaults(session: AsyncSession, workspace_id: uuid.UUID) -> None:
    """Adds FastHyr's default for every template the workspace doesn't have yet. Safe to run
    again; templates the workspace already has, edited or not, stay as they are."""
    await EmailTemplateRepository(session, workspace_id).add_missing(DEFAULTS.values())


async def list_templates(session: AsyncSession, workspace_id: uuid.UUID) -> list[EmailTemplate]:
    """All ten templates in the order of NOTIFICATIONS.md §1."""
    await ensure_defaults(session, workspace_id)
    rows = {row.key: row for row in await EmailTemplateRepository(session, workspace_id).list_all()}
    return [rows[key.value] for key in TemplateKey]


async def get_template(
    session: AsyncSession, workspace_id: uuid.UUID, key: TemplateKey, *, lock: bool = False
) -> EmailTemplate:
    repo = EmailTemplateRepository(session, workspace_id)
    row = await repo.get_by_key(key.value, lock=lock)
    if row is None:
        await ensure_defaults(session, workspace_id)
        row = await repo.get_by_key(key.value, lock=lock)
    assert row is not None
    return row


def unknown_parameters(key: TemplateKey, text: str) -> list[str]:
    """Parameters in `text` this template can't fill, as written, in order of appearance."""
    allowed = set(parameters_for(key))
    found: list[str] = []
    for match in _PARAMETER_LIKE.finditer(text):
        if match.group(1) not in allowed and match.group(0) not in found:
            found.append(match.group(0))
    return found


def validate(key: TemplateKey, subject: str, body_html: str) -> tuple[str, str]:
    """The subject and the cleaned body to store, or `422 email_template_invalid` naming every
    problem: an empty or too long subject or message, or a parameter the template can't fill."""
    subject = " ".join(subject.split())
    body = sanitize(body_html).strip()
    errors: list[dict[str, Any]] = []
    if not subject:
        errors.append(_error("subject", "missing", "Add a subject line."))
    elif len(subject) > SUBJECT_MAX:
        message = f"Keep the subject to {SUBJECT_MAX} characters."
        errors.append(_error("subject", "too_long", message))
    if not html_to_text(body):
        errors.append(_error("body_html", "missing", "Add a message."))
    elif len(body) > BODY_MAX:
        errors.append(_error("body_html", "too_long", "Shorten the message."))
    for field, text in (("subject", subject), ("body_html", body)):
        for parameter in unknown_parameters(key, text):
            errors.append(_error(field, "unknown_parameter", parameter))
    if errors:
        raise EmailTemplateInvalidError(errors=errors)
    return subject, body


async def save(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    key: TemplateKey,
    *,
    subject: str,
    body_html: str,
    note: str | None = None,
) -> EmailTemplate:
    """Stores the workspace's own wording and adds it to the change history. The caller
    commits. MSG-002's editor saves through this."""
    subject, body = validate(key, subject, body_html)
    template = await get_template(session, workspace_id, key, lock=True)
    template.subject = subject
    template.body_html = body
    template.is_default = False
    template.updated_by = user_id
    EmailTemplateRepository(session, workspace_id).add_version(
        EmailTemplateVersion(
            workspace_id=workspace_id,
            template_id=template.id,
            subject=subject,
            body_html=body,
            created_by=user_id,
            note=note,
        )
    )
    await session.flush()
    return template


async def versions(
    session: AsyncSession, workspace_id: uuid.UUID, key: TemplateKey
) -> Sequence[EmailTemplateVersion]:
    """The template's change history, oldest first."""
    template = await get_template(session, workspace_id, key)
    return await EmailTemplateRepository(session, workspace_id).versions(template)


def _error(field: str, kind: str, message: str) -> dict[str, Any]:
    return {"loc": ["body", field], "type": kind, "msg": message}
