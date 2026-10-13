"""Integrity flags (API.md "Applications & candidates", ASMT-003). Admins review any flag,
Recruiters those in their departments' pipelines; anything else is 404. Hiring managers read
flags on the profile but don't review them."""

import uuid
from typing import Annotated

from fastapi import APIRouter

from app.api.deps import Session, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_RESPONSES
from app.core.permissions import Action
from app.schemas.integrity_flags import ResolvedFlag, ResolveFlagRequest
from app.services import integrity_reviews

router = APIRouter(prefix="/integrity-flags", tags=["applications"], responses=PROBLEM_RESPONSES)

Reviewer = Annotated[RequestContext, require(Action.RESOLVE_REVIEWS)]


@router.patch("/{flag_id}", response_model=ResolvedFlag)
async def resolve_flag(
    flag_id: uuid.UUID, body: ResolveFlagRequest, ctx: Reviewer, session: Session
) -> ResolvedFlag:
    """Marks a flag No concern or Concern confirmed (a note is required for a concern). The
    stage never changes; when the application's last open flag is reviewed it leaves the
    Flagged filter. Returns the flag and whether the application is still flagged."""
    return await integrity_reviews.resolve(session, ctx, flag_id, body)
