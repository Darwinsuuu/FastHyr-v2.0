"""Re-invites (INTV-007, API.md "Pipelines" and "Applications & candidates")."""

from typing import Literal

from pydantic import BaseModel


class ReinviteAllRequest(BaseModel):
    """The pipeline dashboard's "Re-invite all": candidates whose link expired, who left their
    interview unfinished, or who hit a technical issue (FR-PIPE-11)."""

    scope: Literal["all_unfinished"]


class ReinviteResult(BaseModel):
    """How many candidates got a new interview link and invitation."""

    reinvited: int
