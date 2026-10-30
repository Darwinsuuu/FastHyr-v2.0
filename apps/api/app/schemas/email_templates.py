"""Candidate email templates (MSG-002, FR-MSG-02, API.md "Email templates")."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.emails.defaults import TemplateKey

# edit: someone saved their own wording; reset: back to FastHyr's default; restore: an earlier
# version brought back. Older rows without a kind were edits.
VersionKind = Literal["edit", "reset", "restore"]


class TemplateEditor(BaseModel):
    """Who last changed a template or saved a version. `name` is their name, or their email
    without one; members only see it inside their own workspace."""

    id: uuid.UUID
    name: str


class EmailTemplateSummary(BaseModel):
    key: TemplateKey
    subject: str
    # True while the wording is FastHyr's default (never edited, or reset).
    is_default: bool
    updated_at: datetime
    updated_by: TemplateEditor | None


class EmailTemplateList(BaseModel):
    templates: list[EmailTemplateSummary]


class EmailTemplate(EmailTemplateSummary):
    body_html: str
    # The parameters this template can fill, without brackets (NOTIFICATIONS.md §2).
    parameters: list[str]
    # Rejections always end with the review line (ADR-015): the editor shows it locked.
    review_line: bool


class EmailTemplateVersion(BaseModel):
    id: uuid.UUID
    kind: VersionKind
    subject: str
    body_html: str
    created_at: datetime
    created_by: TemplateEditor | None


class EmailTemplateVersionList(BaseModel):
    """Newest first: the first one is the wording in use. Empty while the template has never
    been changed (it is FastHyr's default)."""

    versions: list[EmailTemplateVersion]


class SaveEmailTemplate(BaseModel):
    # Checked by `services/email_templates.validate()`, which names every problem at once.
    subject: str = Field(max_length=1000)
    body_html: str = Field(max_length=100_000)


class TestEmailTemplate(BaseModel):
    """The wording to try, saved or not. Filled with sample details (NOTIFICATIONS.md §4)."""

    __test__ = False  # not a pytest class

    subject: str = Field(max_length=1000)
    body_html: str = Field(max_length=100_000)


class TestEmailSent(BaseModel):
    __test__ = False

    message_id: uuid.UUID
    # The caller's own address, which the dialog shows as "To".
    to_email: str
    subject: str
