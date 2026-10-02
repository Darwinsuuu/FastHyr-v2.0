import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

# GLOSSARY.md source tags; "direct" when the link had none.
SourceTag = Literal[
    "linkedin",
    "jobstreet",
    "indeed",
    "kalibrr",
    "glassdoor",
    "facebook",
    "careers",
    "other",
    "direct",
]

_PHONE_SEPARATORS = re.compile(r"[\s().-]")


def _phone_digits(value: str) -> str:
    digits = _PHONE_SEPARATORS.sub("", value)
    if not re.fullmatch(r"[0-9]{7,15}", digits):
        raise ValueError("Enter 7 to 15 digits")
    return digits


def _blank_to_none(value: str | None) -> str | None:
    return value or None


def _web_link(value: str | None) -> str | None:
    if not value:
        return None
    if not re.match(r"^https?://[^\s/$.?#][^\s]*$", value, re.IGNORECASE):
        raise ValueError("Enter a link that starts with http:// or https://")
    return value


Text = Annotated[str, StringConstraints(strip_whitespace=True)]
City = Annotated[Text, StringConstraints(max_length=100), AfterValidator(_blank_to_none)]
WebLink = Annotated[Text, StringConstraints(max_length=500), AfterValidator(_web_link)]


class ResumeUpload(BaseModel):
    """PUT the PDF to `url` (or `uploadToSignedUrl(path, token, file)` in supabase-js) within
    10 minutes, then send `upload_id` with the application."""

    upload_id: uuid.UUID
    url: str
    path: str
    token: str
    max_bytes: int = Field(description="Largest file the API accepts")


class SubmitApplicationRequest(BaseModel):
    """The application form (FR-APPLY-03). The email is the signed-in account's, never sent."""

    pipeline_id: uuid.UUID
    upload_id: uuid.UUID
    resume_filename: Annotated[Text, StringConstraints(min_length=1, max_length=255)]
    full_name: Annotated[Text, StringConstraints(min_length=1, max_length=120)]
    phone_country_code: Annotated[Text, StringConstraints(pattern=r"^\+[0-9]{1,4}$")]
    phone: Annotated[Text, AfterValidator(_phone_digits)]
    city: City | None = None
    profile_url: WebLink | None = None
    # The apply notice the candidate ticked, e.g. "apply@v1" (COMP-002).
    consent_notice_id: Annotated[Text, StringConstraints(min_length=1, max_length=40)]
    source: SourceTag = "direct"


class SubmittedApplication(BaseModel):
    """`created` is false when the candidate had already applied: nothing changed and no credit
    was used (FR-APPLY-05)."""

    application_id: uuid.UUID
    applied_at: datetime
    created: bool


# What the apply page tells a candidate about their application (FR-APPLY-07): a few words for
# where it is, never the stage, a score or a decision. `with_team` covers every stage after the
# interview and the "not moving forward" ones too, so the page never gets ahead of the emails.
CandidateStatus = Literal["received", "interview", "with_team"]


class MyApplication(BaseModel):
    """The apply page's "Applied on {date}" state (FR-APPLY-05, FR-APPLY-07): when the candidate
    applied and a candidate-safe status, never a stage, score or flag. `workspace_member` is true
    when the signed-in account is also a member of the employer's workspace: they may still
    apply, and the form says their teammates will see it (APPLY-004)."""

    applied_at: datetime | None
    status: CandidateStatus | None
    workspace_member: bool
