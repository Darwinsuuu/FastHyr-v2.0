"""The human review request page (API.md "Public", ASMT-008, SCREEN_SPECS.md S-03): no sign-in,
the token from the rejection email is the key. Unknown tokens are 404."""

from typing import Annotated, Any

from fastapi import APIRouter, Path

from app.api.deps import JobQueueDep, Session, SettingsDep
from app.core.errors import PROBLEM_JSON, PROBLEM_RESPONSES, Problem
from app.schemas.review_requests import ReviewLink, ReviewRequestCreate
from app.services import review_requests

router = APIRouter(prefix="/public/review-requests", tags=["public"], responses=PROBLEM_RESPONSES)

Token = Annotated[str, Path(min_length=1, max_length=review_requests.MAX_TOKEN_LENGTH)]
CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": Problem, "content": {PROBLEM_JSON: {}}}}


@router.get("/{token}", response_model=ReviewLink)
async def get_review_link(token: Token, session: Session, settings: SettingsDep) -> ReviewLink:
    """The link's state (`open`, `requested`, `expired`, `unavailable`), the company and the job
    title. Never a stage, score or reason."""
    return await review_requests.review_link(session, token, api_url=settings.api_url)


@router.post("/{token}", response_model=ReviewLink, responses=CONFLICT)
async def request_review(
    token: Token,
    body: ReviewRequestCreate,
    session: Session,
    settings: SettingsDep,
    queue: JobQueueDep,
) -> ReviewLink:
    """Asks a person to review the decision, with an optional message (1,000 characters). The
    pipeline's owner is emailed and the candidate gets the "Human review received" email. A
    repeat returns `requested`; `409 review_link_closed` once the link expired or the decision
    no longer stands."""
    return await review_requests.request_review(session, settings, queue, token, body)
