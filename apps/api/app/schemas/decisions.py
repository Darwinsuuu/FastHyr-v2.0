"""Advancing and rejecting a candidate (ASMT-007, ADR-017, FR-PIPE-13)."""

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

# Frame PipelineView's reject dialog allows 500 characters.
RejectReason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
AdvanceNote = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class AdvanceRequest(BaseModel):
    """ "Advance to next round": an optional note for the team, and whether the candidate gets
    the workspace's "Moving to the next stage" email (ticked by default)."""

    note: AdvanceNote | None = None
    send_email: bool = True


class RejectRequest(BaseModel):
    """ "Reject candidate": the reason (only the team sees it) and whether the candidate gets the
    rejection email (ticked by default)."""

    reason: RejectReason
    send_email: bool = True


class ApplicationDecision(BaseModel):
    id: uuid.UUID
    stage: Literal["advanced", "rejected"]
    # Whether an email to the candidate went out with the decision.
    emailed: bool
