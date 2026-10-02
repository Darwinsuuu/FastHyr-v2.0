"""Credits (API.md "Billing"): the workspace's credit totals. Credits change only through
services/credits.py; this router only reads."""

from typing import Annotated

from fastapi import APIRouter

from app.api.deps import Session, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_RESPONSES
from app.core.permissions import Action
from app.schemas.credits import CreditSummary
from app.services import credits as credit_service

router = APIRouter(prefix="/credits", tags=["credits"], responses=PROBLEM_RESPONSES)

Viewer = Annotated[RequestContext, require(Action.VIEW_CREDIT_USAGE)]


@router.get("/summary", response_model=CreditSummary)
async def credit_summary(ctx: Viewer, session: Session) -> CreditSummary:
    """Balance, reserved and free credits, e.g. for the wizard's reserve check (PIPE-003)."""
    summary = await credit_service.summary(session, ctx.workspace_id)
    return CreditSummary(balance=summary.balance, reserved=summary.reserved, free=summary.free)
