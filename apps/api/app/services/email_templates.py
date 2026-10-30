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
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.context import RequestContext
from app.core.errors import EmailTemplateInvalidError, NotFoundError
from app.emails.candidate import render_template
from app.emails.defaults import DEFAULTS, REJECTION_KEYS, TemplateKey, parameters_for
from app.emails.render import html_to_text, sanitize
from app.jobs.queue import JobQueue
from app.models import EmailTemplate, EmailTemplateVersion
from app.repositories.audit import AuditRepository
from app.repositories.email_templates import EmailTemplateRepository
from app.repositories.integrity import member_names
from app.repositories.users import UserRepository
from app.schemas.email_templates import EmailTemplate as EmailTemplateOut
from app.schemas.email_templates import (
    EmailTemplateList,
    EmailTemplateSummary,
    EmailTemplateVersionList,
    SaveEmailTemplate,
    TemplateEditor,
    TestEmailSent,
    TestEmailTemplate,
)
from app.schemas.email_templates import EmailTemplateVersion as EmailTemplateVersionOut
from app.services import candidate_emails, company_profile, emails

SUBJECT_MAX = 200
BODY_MAX = 20_000

# What a saved version was (`email_template_versions.note`).
EDIT = "edit"
RESET = "reset"
RESTORE = "restore"

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
    note: str | None = EDIT,
) -> EmailTemplate:
    """Stores the workspace's wording and adds it to the change history as `note` (`edit`,
    `reset` or `restore`). Wording that matches FastHyr's default counts as the default again.
    The caller commits."""
    subject, body = validate(key, subject, body_html)
    template = await get_template(session, workspace_id, key, lock=True)
    default = DEFAULTS[key]
    template.subject = subject
    template.body_html = body
    template.is_default = (subject, body) == (default.subject, sanitize(default.body_html))
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


# The editor (MSG-002, FR-MSG-02): Admins and Recruiters read and change their workspace's
# templates. Every change is a new version and an audit row (SECURITY.md §5); the audit keeps
# the key and version, never the wording.


def template_key(value: str) -> TemplateKey:
    """The key in a path, or 404 for anything that isn't one of the ten."""
    try:
        return TemplateKey(value)
    except ValueError:
        raise NotFoundError() from None


async def list_for_editor(session: AsyncSession, ctx: RequestContext) -> EmailTemplateList:
    rows = await list_templates(session, ctx.workspace_id)
    await session.commit()  # the defaults a workspace from before MSG-001 just got
    names = await member_names(session, {row.updated_by for row in rows if row.updated_by})
    return EmailTemplateList(templates=[_summary(row, names) for row in rows])


async def detail(session: AsyncSession, ctx: RequestContext, key: TemplateKey) -> EmailTemplateOut:
    row = await get_template(session, ctx.workspace_id, key)
    await session.commit()
    return await _detail(session, row)


async def update(
    session: AsyncSession, ctx: RequestContext, key: TemplateKey, body: SaveEmailTemplate
) -> EmailTemplateOut:
    row = await save(
        session, ctx.workspace_id, ctx.user_id, key, subject=body.subject, body_html=body.body_html
    )
    return await _changed(session, ctx, row, "email_template.edited")


async def reset(session: AsyncSession, ctx: RequestContext, key: TemplateKey) -> EmailTemplateOut:
    """FastHyr's default wording again, as a new version; the old wording stays in history."""
    default = DEFAULTS[key]
    row = await save(
        session,
        ctx.workspace_id,
        ctx.user_id,
        key,
        subject=default.subject,
        body_html=default.body_html,
        note=RESET,
    )
    return await _changed(session, ctx, row, "email_template.reset")


async def restore(
    session: AsyncSession, ctx: RequestContext, key: TemplateKey, version_id: uuid.UUID
) -> EmailTemplateOut:
    """An earlier version's wording, saved as a new version (history is never rewritten)."""
    repo = EmailTemplateRepository(session, ctx.workspace_id)
    template = await get_template(session, ctx.workspace_id, key)
    version = await repo.get_version(template, version_id)
    if version is None:
        raise NotFoundError()
    row = await save(
        session,
        ctx.workspace_id,
        ctx.user_id,
        key,
        subject=version.subject,
        body_html=version.body_html,
        note=RESTORE,
    )
    return await _changed(
        session, ctx, row, "email_template.restored", restored_from=str(version.id)
    )


async def history(
    session: AsyncSession, ctx: RequestContext, key: TemplateKey
) -> EmailTemplateVersionList:
    rows = list(reversed(await versions(session, ctx.workspace_id, key)))
    await session.commit()
    names = await member_names(session, {row.created_by for row in rows if row.created_by})
    return EmailTemplateVersionList(
        versions=[
            EmailTemplateVersionOut(
                id=row.id,
                kind=row.note if row.note in (RESET, RESTORE) else EDIT,
                subject=row.subject,
                body_html=row.body_html,
                created_at=row.created_at,
                created_by=_editor(row.created_by, names),
            )
            for row in rows
        ]
    )


# "Send test to me": the sample candidate of the editor's test dialog (NOTIFICATIONS.md §4).
SAMPLE_FIRST_NAME = "Bea"
SAMPLE_LAST_NAME = "Garcia"
SAMPLE_JOB_TITLE = "Senior Backend Engineer"
SAMPLE_LINK_DAYS = 7
TEST_KEY = "test"  # email_messages.template_key of test emails


async def send_test(
    session: AsyncSession,
    ctx: RequestContext,
    queue: JobQueue,
    settings: Settings,
    key: TemplateKey,
    body: TestEmailTemplate,
) -> TestEmailSent:
    """Sends the wording in the editor, saved or not, to the caller's own address, filled with
    sample details, exactly as a candidate would get it (review line included)."""
    subject, body_html = validate(key, body.subject, body.body_html)
    profile = await UserRepository(session, ctx.user_id).get_profile()
    if profile is None or not profile.email:
        raise NotFoundError()
    brand = await company_profile.branding(session, ctx.workspace_id, api_url=settings.api_url)
    site = settings.site_url.rstrip("/")
    expiry = datetime.now(UTC) + timedelta(days=SAMPLE_LINK_DAYS)
    values = {
        "Candidate.firstname": SAMPLE_FIRST_NAME,
        "Candidate.lastname": SAMPLE_LAST_NAME,
        "Job.title": SAMPLE_JOB_TITLE,
        "Company.name": brand.company_name,
        "Interview.link": f"{site}/interview/sample",
        "Interview.expiry": await candidate_emails.local_time(session, ctx.workspace_id, expiry),
        "Review.link": f"{site}/review-request/sample",
    }
    email = render_template(
        key=key,
        subject=subject,
        body_html=body_html,
        values=values,
        site_url=settings.site_url,
        branding=brand,
    )
    message = emails.queue_email(
        session,
        workspace_id=ctx.workspace_id,
        template_key=TEST_KEY,
        to_email=profile.email,
        from_name=emails.via_fasthyr(brand.company_name),
        email=email,
    )
    await session.commit()
    await emails.enqueue(queue, message)
    return TestEmailSent(message_id=message.id, to_email=profile.email, subject=email.subject)


async def _changed(
    session: AsyncSession,
    ctx: RequestContext,
    row: EmailTemplate,
    action: str,
    **data: str,
) -> EmailTemplateOut:
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action=action,
        entity_type="email_template",
        entity_id=row.id,
        data={"key": row.key, **data},
    )
    await session.commit()
    await session.refresh(row)  # updated_at comes from the trigger
    return await _detail(session, row)


async def _detail(session: AsyncSession, row: EmailTemplate) -> EmailTemplateOut:
    key = TemplateKey(row.key)
    names = await member_names(session, {row.updated_by} if row.updated_by else set())
    return EmailTemplateOut(
        **_summary(row, names).model_dump(),
        body_html=row.body_html,
        parameters=list(parameters_for(key)),
        review_line=key in REJECTION_KEYS,
    )


def _summary(row: EmailTemplate, names: dict[uuid.UUID, str]) -> EmailTemplateSummary:
    return EmailTemplateSummary(
        key=TemplateKey(row.key),
        subject=row.subject,
        is_default=row.is_default,
        updated_at=row.updated_at,
        updated_by=_editor(row.updated_by, names),
    )


def _editor(user_id: uuid.UUID | None, names: dict[uuid.UUID, str]) -> TemplateEditor | None:
    if user_id is None:
        return None
    return TemplateEditor(id=user_id, name=names.get(user_id) or "")
