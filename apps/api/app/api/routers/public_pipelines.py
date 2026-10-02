"""The public apply page (API.md "Public"): no sign-in. Drafts, cancelled pipelines and unknown
links are 404."""

from typing import Annotated

from fastapi import APIRouter, Path

from app.api.deps import Session, SettingsDep
from app.core.errors import PROBLEM_RESPONSES
from app.schemas.public_pipelines import PublicPipeline
from app.services import public_pipelines as public_pipeline_service

router = APIRouter(prefix="/public/pipelines", tags=["public"], responses=PROBLEM_RESPONSES)

Slug = Annotated[str, Path(min_length=1, max_length=120)]


@router.get("/{workspace_slug}/{pipeline_slug}", response_model=PublicPipeline)
async def get_public_pipeline(
    workspace_slug: Slug, pipeline_slug: Slug, session: Session, settings: SettingsDep
) -> PublicPipeline:
    """Apply page data: candidate-safe pipeline fields, availability and the company profile."""
    return await public_pipeline_service.get_public_pipeline(
        session, workspace_slug, pipeline_slug, api_url=settings.api_url
    )
