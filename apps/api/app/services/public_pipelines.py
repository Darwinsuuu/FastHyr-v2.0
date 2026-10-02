"""The public apply page (FR-APPLY-01, FR-APPLY-06): a published pipeline's candidate-safe
fields, its availability and the employer's company profile. Anyone with the link can read it,
so it is looked up by the two slugs in the link and never by ID."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.repositories.company_profiles import BrandingRow
from app.repositories.pipelines import PublicPipelineRow, public_pipeline_of
from app.schemas.public_pipelines import Availability, PublicCompany, PublicPipeline
from app.services.company_profile import branding_url

AVAILABILITY: dict[str, Availability] = {
    "live": "accepting",
    "scheduled": "opens_later",
    "paused": "not_accepting",
    "paused_no_credits": "not_accepting",
    "closed": "closed",
}


async def get_public_pipeline(
    session: AsyncSession, workspace_slug: str, pipeline_slug: str, *, api_url: str
) -> PublicPipeline:
    row = await public_pipeline_of(session, workspace_slug, pipeline_slug)
    if row is None or row.status not in AVAILABILITY:
        raise NotFoundError()
    return PublicPipeline(
        id=row.id,
        workspace_slug=row.workspace_slug,
        slug=row.slug,
        availability=AVAILABILITY[row.status],
        # Publishing requires both (PIPE-001), so they are only empty on bad data.
        title=row.title or "",
        department=row.department,
        employment_type=row.employment_type,
        work_setup=row.work_setup,
        location=row.location,
        jd_text=row.jd_text or "",
        open_to=row.open_to,
        interview_format=row.interview_format,
        opens_at=row.opens_at,
        closes_at=row.closes_at,
        timezone=row.timezone,
        company=_company(row, api_url),
    )


def _company(row: PublicPipelineRow, api_url: str) -> PublicCompany:
    # The same long-lived link the emails use; it changes whenever the profile is saved.
    branding = BrandingRow(row.company_name, row.logo_path, None, row.profile_updated_at)
    logo_url = branding_url(api_url, row.workspace_id, branding, "logo") if row.logo_path else None
    return PublicCompany(
        name=row.company_name,
        logo_url=logo_url,
        website=row.website,
        industry=row.industry,
        company_size=row.company_size,
        hq_country=row.hq_country,
        about=row.about,
        careers_url=row.careers_url,
    )
