"""The Candidates tab of a pipeline (PIPE-008, FR-PIPE-12): one page of applications with the
stage filters' counts. Scores and flags are for TA users only; nothing here reaches candidates."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.integrity.flags import FlagType
from app.schemas.applications import SourceTag

# WORKFLOW.md §3.
ApplicationStage = Literal[
    "processing_resume",
    "resume_not_match",
    "invited",
    "interview_in_progress",
    "scoring",
    "ready_for_review",
    "did_not_pass",
    "advanced",
    "rejected",
]

# The stage filters. `in_progress` holds interviews in progress and being scored; `ready` and
# `did_not_pass` leave out applications with open flags, which wait under `flagged` instead;
# `review_requested` is an overlay on any stage.
CandidateFilter = Literal[
    "all",
    "processing",
    "not_a_match",
    "invited",
    "in_progress",
    "ready",
    "did_not_pass",
    "flagged",
    "review_requested",
    "advanced",
    "rejected",
]

Criterion = Literal["technical", "communication", "culture"]


class CandidateFilterCounts(BaseModel):
    all: int
    processing: int
    not_a_match: int
    invited: int
    in_progress: int
    ready: int
    did_not_pass: int
    flagged: int
    review_requested: int
    advanced: int
    rejected: int


class ListedCandidate(BaseModel):
    id: uuid.UUID
    name: str
    email: str


class MustHaves(BaseModel):
    """Must-haves the résumé screen found met, of all the pipeline's must-haves."""

    met: int
    total: int


class PipelineCandidate(BaseModel):
    # The application's ID (the row), with the person who applied.
    id: uuid.UUID
    candidate: ListedCandidate
    stage: ApplicationStage
    # Open integrity flags on a ready or did-not-pass application: the Flagged filter.
    flagged: bool
    review_requested: bool
    # ADR-011's badge and the interview score, once an interview has been assessed.
    fit: Literal["strong", "good"] | None
    overall_score: int | None
    must_haves: MustHaves | None
    # The interview criterion with the highest score, for the fit explanation.
    strongest: Criterion | None
    # Types of the open flags, earliest first, for the fit explanation.
    flag_types: list[FlagType]
    source: SourceTag
    applied_at: datetime


class PipelineCandidates(BaseModel):
    items: list[PipelineCandidate]
    # Applications matching the filter and search; `counts` ignore the search.
    total: int
    page: int
    page_size: int
    counts: CandidateFilterCounts
    # Hiring managers see shortlisted applications only: ready for review, flagged, advanced.
    shortlist_only: bool
    # The pipeline's interview pass mark, for the "Good fit" explanation.
    pass_mark: int | None
    # The workspace's time zone, for the applied date and time.
    timezone: str
