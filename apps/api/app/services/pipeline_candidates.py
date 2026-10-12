"""The Candidates tab of a pipeline (PIPE-008, FR-PIPE-12): stage filters with counts, search
and one page of applications with what the fit explanation needs. Recruiters see their
departments' pipelines, Hiring managers the shortlist only (SECURITY.md §2)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.permissions import Access, Action, can
from app.repositories.company_profiles import workspace_timezone
from app.repositories.pipeline_candidates import (
    CandidateRow,
    PipelineCandidatesRepository,
    RowDetails,
)
from app.repositories.pipelines import PipelineRepository
from app.schemas.pipeline_candidates import (
    CandidateFilter,
    CandidateFilterCounts,
    ListedCandidate,
    MustHaves,
    PipelineCandidate,
    PipelineCandidates,
)

CRITERIA = ("technical", "communication", "culture")


async def list_candidates(
    session: AsyncSession,
    ctx: RequestContext,
    pipeline_id: uuid.UUID,
    *,
    filter_name: CandidateFilter,
    query: str,
    page: int,
    page_size: int,
) -> PipelineCandidates:
    """One page of the pipeline's applications in the filter, matching `query` on the
    candidate's name or email, with every filter's count. 404 outside the caller's
    departments."""
    departments = None if ctx.sees_all_departments else ctx.department_ids
    pipeline = await PipelineRepository(session, ctx.workspace_id, department_ids=departments).get(
        pipeline_id
    )
    shortlist = can(ctx, Action.VIEW_CANDIDATES) is Access.SHORTLIST
    repo = PipelineCandidatesRepository(session, ctx.workspace_id, shortlist=shortlist)
    counts = await repo.counts(pipeline_id)
    rows, total = await repo.page(
        pipeline_id,
        filter_name=filter_name,
        query=query.strip(),
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    details = await repo.details([row.application.id for row in rows])
    return PipelineCandidates(
        items=[_item(row, details) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        counts=CandidateFilterCounts(**counts),
        shortlist_only=shortlist,
        pass_mark=pipeline.pass_mark,
        timezone=await workspace_timezone(session, ctx.workspace_id) or "UTC",
    )


def strongest(criteria: dict[str, Any]) -> str | None:
    """The criterion with the highest score; the rubric's order breaks a tie."""
    scored = [
        (row["score"], -index, name)
        for index, name in enumerate(CRITERIA)
        if isinstance(row := criteria.get(name), dict) and isinstance(row.get("score"), int)
    ]
    return max(scored)[2] if scored else None


def _item(row: CandidateRow, details: RowDetails) -> PipelineCandidate:
    application = row.application
    must_haves = details.must_haves.get(application.id)
    flagged = application.has_open_flags and application.stage in (
        "ready_for_review",
        "did_not_pass",
    )
    return PipelineCandidate(
        id=application.id,
        candidate=ListedCandidate(id=row.candidate_id, name=row.name, email=row.email),
        stage=application.stage,
        flagged=flagged,
        review_requested=application.review_requested,
        fit=application.fit,
        overall_score=application.overall_score,
        must_haves=MustHaves(met=must_haves[0], total=must_haves[1]) if must_haves else None,
        strongest=strongest(details.criteria.get(application.id, {})),
        flag_types=details.flag_types.get(application.id, []) if flagged else [],
        source=application.source,
        applied_at=application.applied_at,
    )
