"""Pipeline setup and lifecycle (API.md "Pipelines", FR-PIPE-01..07, FR-PIPE-15)."""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

EmploymentType = Literal["full_time", "part_time", "contract", "internship"]
WorkSetup = Literal["on_site", "hybrid", "remote"]
OpenTo = Literal[
    "fresh_grads", "career_changers", "returners", "no_degree", "step_up", "relocating"
]
InterviewFormat = Literal["video_voice", "voice_only"]
Tone = Literal["warm", "professional", "direct"]
Seniority = Literal["entry", "mid", "senior", "lead"]
OpenMode = Literal["now", "scheduled"]
PipelineStatus = Literal[
    "draft", "scheduled", "live", "paused", "paused_no_credits", "closed", "cancelled"
]
ClosedReason = Literal["schedule", "manual"]

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Location = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]
JobDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20_000)]
ListItem = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Percent = Annotated[int, Field(ge=0, le=100)]


def _unique[T](items: list[T]) -> list[T]:
    return list(dict.fromkeys(items))


ItemList = Annotated[list[ListItem], Field(max_length=20), AfterValidator(_unique)]


def _multiple_of_ten(credits: int) -> int:
    if credits % 10:
        raise ValueError("reserve credits in steps of 10")
    return credits


ReserveCredits = Annotated[int, Field(ge=10, le=100_000), AfterValidator(_multiple_of_ten)]


class PipelineSetup(BaseModel):
    """The wizard's fields (FR-PIPE-01..04). Every field is optional so a draft can be saved at
    any step; publishing checks the setup is complete. On PATCH only the fields sent change."""

    model_config = ConfigDict(extra="forbid")

    # Role
    department_id: uuid.UUID | None = None
    title: Title | None = None
    employment_type: EmploymentType | None = None
    work_setup: WorkSetup | None = None
    location: Location | None = None
    jd_text: JobDescription | None = None
    must_haves: ItemList | None = None
    nice_to_haves: ItemList | None = None
    open_to: Annotated[list[OpenTo], AfterValidator(_unique)] | None = None
    resume_pass_bar: Percent | None = None
    # AI interview
    interview_format: InterviewFormat | None = None
    tone: Tone | None = None
    seniority: Seniority | None = None
    skills_to_probe: ItemList | None = None
    link_expiry_days: Literal[3, 5, 7, 14] | None = None
    reminder_enabled: bool | None = None
    integrity_enabled: bool | None = None
    # Scoring
    weight_technical: Percent | None = None
    weight_communication: Percent | None = None
    weight_culture: Percent | None = None
    pass_mark: Percent | None = None
    email_resume_reject: bool | None = None
    email_post_interview: bool | None = None
    # Schedule & credits
    open_mode: OpenMode | None = None
    opens_at: datetime | None = None
    duration_days: Literal[30, 60, 90, 120] | None = None
    credits_to_reserve: ReserveCredits | None = None

    @model_validator(mode="after")
    def _no_null_for_fields_with_defaults(self) -> Self:
        """Lists, toggles and scores always have a value; null can only clear the others."""
        for name in NOT_NULLABLE:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} can't be empty")
        return self

    @model_validator(mode="after")
    def _opens_at_has_time_zone(self) -> Self:
        if self.opens_at is not None and self.opens_at.tzinfo is None:
            raise ValueError("opens_at needs a time zone")
        return self

    def changes(self) -> dict[str, Any]:
        """The fields the caller sent, as column values."""
        return {name: getattr(self, name) for name in self.model_fields_set}


NOT_NULLABLE = (
    "must_haves",
    "nice_to_haves",
    "open_to",
    "resume_pass_bar",
    "skills_to_probe",
    "link_expiry_days",
    "reminder_enabled",
    "integrity_enabled",
    "pass_mark",
    "email_resume_reject",
    "email_post_interview",
)


class PublishRequest(BaseModel):
    """Publishing or scheduling needs the words typed in the confirm box (FR-PIPE-05)."""

    confirm: Literal["I understand"]


class TopUpRequest(BaseModel):
    """Top-up amounts the pipeline menus offer (FR-BILL-04)."""

    credits: Literal[25, 50, 100, 200]


class Pipeline(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: PipelineStatus
    department_id: uuid.UUID | None
    owner_id: uuid.UUID | None
    slug: str | None
    # Role
    title: str | None
    employment_type: EmploymentType | None
    work_setup: WorkSetup | None
    location: str | None
    jd_text: str | None
    must_haves: list[str]
    nice_to_haves: list[str]
    open_to: list[OpenTo]
    resume_pass_bar: int
    # AI interview
    interview_format: InterviewFormat | None
    tone: Tone | None
    seniority: Seniority | None
    skills_to_probe: list[str]
    link_expiry_days: int
    reminder_enabled: bool
    integrity_enabled: bool
    # Scoring
    weight_technical: int | None
    weight_communication: int | None
    weight_culture: int | None
    pass_mark: int
    email_resume_reject: bool
    email_post_interview: bool
    # Schedule & credits
    open_mode: OpenMode | None
    opens_at: datetime | None
    duration_days: int | None
    closes_at: datetime | None
    credits_to_reserve: int | None
    credits_reserved: int
    credits_used: int
    # Lifecycle
    closed_reason: ClosedReason | None
    archived_at: datetime | None
    ended_at: datetime | None
    published_at: datetime | None
    published_by: uuid.UUID | None
    locked_at: datetime | None
    duplicated_from_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


# -- The Pipelines list (PIPE-004, FR-PIPE-08) ------------------------------------------------
PipelineTab = Literal["live", "scheduled", "closed", "drafts", "all"]


class PipelineOwner(BaseModel):
    """Who owns the pipeline, for the avatar. Null when the owner has left the workspace."""

    user_id: uuid.UUID
    name: str | None
    email: str | None
    avatar_url: str | None


class PipelineListDepartment(BaseModel):
    id: uuid.UUID
    name: str


class PipelineListItem(BaseModel):
    id: uuid.UUID
    status: PipelineStatus
    closed_reason: ClosedReason | None
    title: str | None
    slug: str | None
    department: PipelineListDepartment | None
    owner: PipelineOwner | None
    candidates: int
    # Ready for review and not flagged.
    to_review: int
    credits_used: int
    # Reserved credits; a draft shows the reserve it will ask for.
    credits_reserved: int
    opens_at: datetime | None
    closes_at: datetime | None
    ended_at: datetime | None
    updated_at: datetime


class PipelineTabCounts(BaseModel):
    live: int
    scheduled: int
    closed: int
    drafts: int
    all: int


class PipelineList(BaseModel):
    items: list[PipelineListItem]
    # Pipelines matching the tab and search; `counts` ignore the search.
    total: int
    page: int
    page_size: int
    counts: PipelineTabCounts
    # Candidates ready for review across the caller's open pipelines.
    to_review: int
    # The workspace's time zone, for "Closes today", "Opens tomorrow" and "Closed 2 Sep".
    timezone: str
