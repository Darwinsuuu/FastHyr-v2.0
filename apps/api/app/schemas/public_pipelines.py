import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.company_profile import CompanySize, Industry
from app.schemas.pipelines import EmploymentType, InterviewFormat, OpenTo, WorkSetup

# What the apply page tells candidates (WORKFLOW.md §2): live → accepting, scheduled →
# opens_later, paused or out of credits → not_accepting, closed → closed.
Availability = Literal["accepting", "opens_later", "not_accepting", "closed"]


class PublicCompany(BaseModel):
    name: str
    logo_url: str | None
    website: str | None
    industry: Industry | None
    company_size: CompanySize | None
    hq_country: str | None
    about: str | None
    careers_url: str | None


class PublicPipeline(BaseModel):
    """The apply page (FR-APPLY-01): candidate-safe fields only. Must-haves, nice-to-haves,
    skills to probe and the rubric are never part of it."""

    id: uuid.UUID
    workspace_slug: str
    slug: str
    availability: Availability
    title: str
    department: str | None
    employment_type: EmploymentType | None
    work_setup: WorkSetup | None
    location: str | None
    jd_text: str
    open_to: list[OpenTo]
    interview_format: InterviewFormat | None
    opens_at: datetime | None
    closes_at: datetime | None
    # IANA zone the employer works in; dates on the page are shown in it.
    timezone: str
    company: PublicCompany
