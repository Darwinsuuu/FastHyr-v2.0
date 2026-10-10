"""Dashboards (API.md "Dashboard & analytics", DASH-003): the Overview and the Pipelines page
flow. A pipeline's dashboard lives under /pipelines and the candidate pool's under /candidates.
Every number is limited to the caller's departments."""

from typing import Annotated

from fastapi import APIRouter

from app.api.deps import Session, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_RESPONSES
from app.core.permissions import Action
from app.schemas.analytics import FlowSummary, Overview, Range
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"], responses=PROBLEM_RESPONSES)

OverviewViewer = Annotated[RequestContext, require(Action.VIEW_OVERVIEW)]
PipelinesViewer = Annotated[RequestContext, require(Action.VIEW_PIPELINES)]


@router.get("/overview", response_model=Overview)
async def overview(ctx: OverviewViewer, session: Session, range: Range = "week") -> Overview:
    """KPIs, needs your attention, funnel, top waiting candidates, pipelines closing soonest,
    applicants per week, sources, drop-offs and credits (FR-DASH-02..04). "week" is the last 7
    days and "30d" the last 30, compared with the period before. Hiring managers get shortlist
    numbers only: the sections about every applicant are null."""
    return await analytics.overview(session, ctx, range)


@router.get("/pipelines-flow", response_model=FlowSummary)
async def pipelines_flow(
    ctx: PipelinesViewer, session: Session, range: Range = "week"
) -> FlowSummary:
    """The Pipelines page's "How candidates are moving": applications to open pipelines that
    applied in the range, and where they are now."""
    return await analytics.pipelines_flow(session, ctx, range)
