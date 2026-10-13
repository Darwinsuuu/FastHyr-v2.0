"""Human review requests (ASMT-008, ADR-015, FR-COMP-03)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.schemas.interviews import InterviewCompany

DecisionType = Literal["resume", "interview"]
ReviewStatus = Literal["open", "upheld", "overridden"]
# open: the candidate can ask; requested: they already did (or the decision was looked at
# again); expired: past the link's 30 days; unavailable: the application moved on or is gone.
ReviewLinkState = Literal["open", "requested", "expired", "unavailable"]

# S-03: "Anything you'd like them to know?", 1,000 characters.
CandidateMessage = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
ResolutionNote = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class ReviewLink(BaseModel):
    """What the review request page shows: never a score, stage or reason."""

    state: ReviewLinkState
    company: InterviewCompany
    job_title: str


class ReviewRequestCreate(BaseModel):
    message: CandidateMessage | None = None


class ResolveReviewRequest(BaseModel):
    """Uphold or override, with a note only the team sees."""

    outcome: Literal["uphold", "override"]
    note: ResolutionNote


class ReviewRequestItem(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    pipeline_id: uuid.UUID
    pipeline_title: str
    decision_type: DecisionType
    # A person's own rejection (ASMT-007) rather than an automated one.
    by_person: bool
    status: ReviewStatus
    created_at: datetime


class ReviewRequestList(BaseModel):
    items: list[ReviewRequestItem]
    total: int


class ResolvedReviewRequest(BaseModel):
    id: uuid.UUID
    status: Literal["upheld", "overridden"]
    application_id: uuid.UUID
    # The application's stage afterwards.
    stage: str
    # Whether an email to the candidate went out (the invitation after a résumé override).
    emailed: bool
