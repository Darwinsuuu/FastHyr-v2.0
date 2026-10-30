"""Candidate email templates (API.md "Email templates", MSG-002): Admins and Recruiters read and
edit their workspace's ten templates. Keys are the template keys of NOTIFICATIONS.md §1; an
unknown key is 404."""

import uuid
from typing import Annotated

from fastapi import APIRouter, status

from app.api.deps import JobQueueDep, Session, SettingsDep, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_RESPONSES
from app.core.permissions import Action
from app.schemas.email_templates import (
    EmailTemplate,
    EmailTemplateList,
    EmailTemplateVersionList,
    SaveEmailTemplate,
    TestEmailSent,
    TestEmailTemplate,
)
from app.services import email_templates

router = APIRouter(prefix="/email-templates", tags=["email templates"], responses=PROBLEM_RESPONSES)

Editor = Annotated[RequestContext, require(Action.MANAGE_EMAIL_TEMPLATES)]


@router.get("", response_model=EmailTemplateList)
async def list_email_templates(ctx: Editor, session: Session) -> EmailTemplateList:
    """All ten, in the order of NOTIFICATIONS.md §1, with who changed each last."""
    return await email_templates.list_for_editor(session, ctx)


@router.get("/{key}", response_model=EmailTemplate)
async def get_email_template(key: str, ctx: Editor, session: Session) -> EmailTemplate:
    return await email_templates.detail(session, ctx, email_templates.template_key(key))


@router.put("/{key}", response_model=EmailTemplate)
async def save_email_template(
    key: str, body: SaveEmailTemplate, ctx: Editor, session: Session
) -> EmailTemplate:
    """Saves the subject and message as a new version. The message is cleaned with the email
    allow-list; `422 email_template_invalid` names every problem (empty or long subject or
    message, a parameter this template can't fill)."""
    return await email_templates.update(session, ctx, email_templates.template_key(key), body)


@router.post("/{key}/reset", response_model=EmailTemplate)
async def reset_email_template(key: str, ctx: Editor, session: Session) -> EmailTemplate:
    """FastHyr's default wording, as a new version; the old one stays in the history."""
    return await email_templates.reset(session, ctx, email_templates.template_key(key))


@router.get("/{key}/versions", response_model=EmailTemplateVersionList)
async def list_email_template_versions(
    key: str, ctx: Editor, session: Session
) -> EmailTemplateVersionList:
    """The change history, newest (the wording in use) first."""
    return await email_templates.history(session, ctx, email_templates.template_key(key))


@router.post("/{key}/versions/{version_id}/restore", response_model=EmailTemplate)
async def restore_email_template_version(
    key: str, version_id: uuid.UUID, ctx: Editor, session: Session
) -> EmailTemplate:
    """Brings an earlier version back as a new version."""
    return await email_templates.restore(
        session, ctx, email_templates.template_key(key), version_id
    )


@router.post("/{key}/test", response_model=TestEmailSent, status_code=status.HTTP_202_ACCEPTED)
async def send_test_email_template(
    key: str,
    body: TestEmailTemplate,
    ctx: Editor,
    session: Session,
    queue: JobQueueDep,
    settings: SettingsDep,
) -> TestEmailSent:
    """Sends the given wording (saved or not) to the caller, filled with sample details."""
    return await email_templates.send_test(
        session, ctx, queue, settings, email_templates.template_key(key), body
    )
