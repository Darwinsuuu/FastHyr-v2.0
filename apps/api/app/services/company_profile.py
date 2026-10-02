"""Company profile (FR-WS-01): the employer brand candidates see on apply pages, interview screens
and emails. Admins edit it; the logo and banner go through signed uploads and the image checks
in services/images.py.

Emails can't use expiring Storage URLs, so they link the images through the public branding
route (`/v1/public/branding/{workspace_id}/{kind}`), whose URLs change whenever the profile is
saved.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.core.errors import NotFoundError
from app.emails.render import Branding
from app.integrations.storage import Bucket, Storage, StorageObjectMissingError
from app.models import CompanyProfile as CompanyProfileRow
from app.repositories.audit import AuditRepository
from app.repositories.company_profiles import BrandingRow, CompanyProfileRepository, branding_of
from app.schemas.company_profile import (
    BrandingUpload,
    CompanyProfile,
    UpdateCompanyProfileRequest,
)
from app.services import files
from app.services.images import MAX_BYTES, BrandingKind

# Fields the form edits, in the order the audit row lists them.
FIELDS = (
    "company_name",
    "website",
    "industry",
    "company_size",
    "hq_country",
    "timezone",
    "about",
    "careers_url",
)


async def get_profile(
    session: AsyncSession, ctx: RequestContext, storage: Storage
) -> CompanyProfile:
    row = await CompanyProfileRepository(session, ctx.workspace_id).get()
    return await _profile(row, storage)


async def create_branding_upload(
    ctx: RequestContext, storage: Storage, kind: BrandingKind
) -> BrandingUpload:
    pending = await files.create_upload(storage, Bucket.BRANDING, ctx.workspace_id)
    return BrandingUpload(
        upload_id=pending.upload_id,
        url=pending.upload.url,
        path=pending.upload.path,
        token=pending.upload.token,
        max_bytes=MAX_BYTES,
    )


async def update_profile(
    session: AsyncSession,
    ctx: RequestContext,
    storage: Storage,
    body: UpdateCompanyProfileRequest,
) -> CompanyProfile:
    repo = CompanyProfileRepository(session, ctx.workspace_id)
    row = await repo.get()

    changed = [field for field in FIELDS if getattr(row, field) != getattr(body, field)]
    for field in changed:
        setattr(row, field, getattr(body, field))
    if "timezone" in changed and body.timezone:
        await repo.set_workspace_timezone(body.timezone)

    stale: list[str] = []
    for kind, upload_id, remove in (
        (BrandingKind.LOGO, body.logo_upload_id, body.remove_logo),
        (BrandingKind.BANNER, body.banner_upload_id, body.remove_banner),
    ):
        attribute = f"{kind}_path"
        current: str | None = getattr(row, attribute)
        if upload_id is not None:
            path = await files.promote_branding_image(
                storage, workspace_id=ctx.workspace_id, upload_id=upload_id, kind=kind
            )
            if current and current != path:
                stale.append(current)
            setattr(row, attribute, path)
            changed.append(kind.value)
        elif remove and current:
            stale.append(current)
            setattr(row, attribute, None)
            changed.append(kind.value)

    if changed:
        row.updated_by = ctx.user_id
        # A replaced image keeps its path, so set this to force the write: email image links
        # carry `updated_at` and must change with the image.
        row.updated_at = datetime.now(UTC)
        AuditRepository(session, ctx.workspace_id).record(
            actor_id=ctx.user_id,
            action="company_profile.updated",
            entity_type="workspace",
            entity_id=ctx.workspace_id,
            data={"fields": changed},
        )
    await session.commit()
    if stale:
        await storage.delete(Bucket.BRANDING, stale)
    await session.refresh(row)
    return await _profile(row, storage)


async def _profile(row: CompanyProfileRow, storage: Storage) -> CompanyProfile:
    async def signed(path: str | None) -> str | None:
        return await storage.signed_download_url(Bucket.BRANDING, path) if path else None

    return CompanyProfile(
        company_name=row.company_name,
        website=row.website,
        industry=row.industry,
        company_size=row.company_size,
        hq_country=row.hq_country,
        timezone=row.timezone,
        about=row.about,
        careers_url=row.careers_url,
        logo_url=await signed(row.logo_path),
        banner_url=await signed(row.banner_path),
        updated_at=row.updated_at,
    )


# Branding outside the app: emails and the public image route.


def branding_url(api_url: str, workspace_id: uuid.UUID, row: BrandingRow, kind: str) -> str:
    version = int(row.updated_at.timestamp())
    return f"{api_url.rstrip('/')}/v1/public/branding/{workspace_id}/{kind}?v={version}"


async def branding(session: AsyncSession, workspace_id: uuid.UUID, *, api_url: str) -> Branding:
    """The company name and long-lived image links for a workspace's emails."""
    row = await branding_of(session, workspace_id)
    if row is None:
        raise NotFoundError()
    return Branding(
        company_name=row.company_name,
        logo_url=branding_url(api_url, workspace_id, row, "logo") if row.logo_path else None,
        banner_url=branding_url(api_url, workspace_id, row, "banner") if row.banner_path else None,
    )


@dataclass(frozen=True)
class BrandingImage:
    data: bytes
    content_type: str


async def branding_image(
    session: AsyncSession, storage: Storage, workspace_id: uuid.UUID, kind: BrandingKind
) -> BrandingImage:
    """The stored logo or banner, for the public route; 404 when there is none."""
    row = await branding_of(session, workspace_id)
    path = getattr(row, f"{kind}_path") if row else None
    if not path:
        raise NotFoundError()
    try:
        data = await storage.download(Bucket.BRANDING, path)
    except StorageObjectMissingError as error:
        raise NotFoundError() from error
    return BrandingImage(data, "image/jpeg" if path.endswith(".jpg") else "image/png")
