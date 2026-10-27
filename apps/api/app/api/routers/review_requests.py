"""Human review requests (API.md "Applications & candidates", ASMT-008, ADR-015). Admins resolve
any request, Recruiters those in their departments' pipelines; anything else is 404. Hiring
managers don't resolve them."""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from app.api.deps import JobQueueDep, Session, SettingsDep, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.core.permissions import Action
from app.schemas.review_requests import (
    ResolvedReviewRequest,
    ResolveReviewRequest,
    ReviewRequestList,
)
from app.services import review_requests

router = APIRouter(prefix="/review-requests", tags=["applications"], responses=PROBLEM_RESPONSES)

Reviewer = Annotated[RequestContext, require(Action.RESOLVE_REVIEWS)]
CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": Problem, "content": {PROBLEM_JSON: {}}}}


@router.get("", response_model=ReviewRequestList)
async def list_review_requests(
    ctx: Reviewer,
    session: Session,
    status: Annotated[Literal["open", "upheld", "overridden", "all"], Query()] = "open",
) -> ReviewRequestList:
    """Review requests in the caller's departments, oldest first (up to 100), and the total."""
    return await review_requests.list_requests(
        session, ctx, status=None if status == "all" else status
    )


@router.post("/{request_id}/resolve", response_model=ResolvedReviewRequest, responses=CONFLICT)
async def resolve_review_request(
    request_id: uuid.UUID,
    body: ResolveReviewRequest,
    ctx: Reviewer,
    session: Session,
    settings: SettingsDep,
    queue: JobQueueDep,
) -> ResolvedReviewRequest:
    """Upholds the decision (no email) or overrides it: a résumé that didn't pass goes to
    Invited and gets the interview invitation, an interview below the pass mark goes to Ready
    for review. The note is required and only the team sees it. A person's own rejection can
    only be upheld (`409 override_not_allowed`); `409 review_request_resolved` once resolved."""
    return await review_requests.resolve(session, settings, queue, ctx, request_id, body)
