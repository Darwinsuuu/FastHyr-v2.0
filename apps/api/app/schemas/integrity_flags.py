"""Reviewing an integrity flag (ASMT-003, FR-ASMT-06, SCREEN_SPECS.md A-04)."""

import uuid
from typing import Annotated, Literal, Self

from pydantic import BaseModel, StringConstraints, model_validator

from app.schemas.application_profile import IntegrityFlag

ResolutionNote = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class ResolveFlagRequest(BaseModel):
    """No concern, or Concern confirmed with a note saying what the reviewer saw. Confirming a
    concern never rejects anyone: the team still chooses Advance or Reject."""

    status: Literal["no_concern", "concern_confirmed"]
    note: ResolutionNote | None = None

    @model_validator(mode="after")
    def _note_for_a_concern(self) -> Self:
        if not self.note:
            self.note = None
        if self.status == "concern_confirmed" and self.note is None:
            raise ValueError("a confirmed concern needs a note")
        return self


class FlaggedApplication(BaseModel):
    id: uuid.UUID
    # Still under the Flagged filter: open flags left on a ready or did-not-pass application.
    flagged: bool
    open_flags: int


class ResolvedFlag(BaseModel):
    flag: IntegrityFlag
    application: FlaggedApplication
