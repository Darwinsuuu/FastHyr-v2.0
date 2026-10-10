"""The candidate pool (API.md "Applications & candidates"), read only. The list and profile come
with CAND-001; the dashboard numbers with DASH-003."""

from typing import Annotated

from fastapi import APIRouter

from app.api.deps import Session, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_RESPONSES
from app.core.permissions import Action
from app.schemas.analytics import CandidatesDashboard
from app.services import analytics

router = APIRouter(prefix="/candidates", tags=["candidates"], responses=PROBLEM_RESPONSES)

PoolViewer = Annotated[RequestContext, require(Action.VIEW_CANDIDATE_POOL)]


@router.get("/dashboard", response_model=CandidatesDashboard)
async def candidates_dashboard(ctx: PoolViewer, session: Session) -> CandidatesDashboard:
    """KPIs, new candidates per month, applications per candidate, where applications ended
    up and the best sources (FR-CAND-03). Hiring managers count shortlisted applications only."""
    return await analytics.candidates_dashboard(session, ctx)
