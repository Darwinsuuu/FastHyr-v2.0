"""Company profile (API.md "Workspace admin"): Admins read and edit it. The public branding
route serves the logo and banner to email clients, which can't sign in or follow expiring
links."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Response

from app.api.deps import Session, StorageDep, require
from app.core.context import RequestContext
from app.core.errors import PROBLEM_RESPONSES
from app.core.permissions import Action
from app.schemas.company_profile import (
    BrandingUpload,
    BrandingUploadRequest,
    CompanyProfile,
    UpdateCompanyProfileRequest,
)
from app.services import company_profile as profile_service
from app.services.images import BrandingKind

router = APIRouter(
    prefix="/workspace/company-profile", tags=["company profile"], responses=PROBLEM_RESPONSES
)
public_router = APIRouter(prefix="/public/branding", tags=["public"], responses=PROBLEM_RESPONSES)

Admin = Annotated[RequestContext, require(Action.MANAGE_WORKSPACE)]

# The image URL changes whenever the profile is saved, so a stored copy never goes stale.
IMMUTABLE = "public, max-age=31536000, immutable"


@router.get("", response_model=CompanyProfile)
async def get_company_profile(ctx: Admin, session: Session, storage: StorageDep) -> CompanyProfile:
    return await profile_service.get_profile(session, ctx, storage)


@router.put("", response_model=CompanyProfile)
async def update_company_profile(
    body: UpdateCompanyProfileRequest, ctx: Admin, session: Session, storage: StorageDep
) -> CompanyProfile:
    """Saves the whole form. Uploaded images are checked here: `image_invalid`,
    `image_too_large`, `image_too_big`, `logo_not_square`, `logo_too_small`, `upload_missing`
    or `upload_expired`."""
    return await profile_service.update_profile(session, ctx, storage, body)


@router.post("/branding-upload", response_model=BrandingUpload)
async def create_branding_upload(
    body: BrandingUploadRequest, ctx: Admin, storage: StorageDep
) -> BrandingUpload:
    """A signed URL for one logo or banner upload, valid for 10 minutes."""
    return await profile_service.create_branding_upload(ctx, storage, body.kind)


@public_router.get(
    "/{workspace_id}/{kind}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}}}},
)
async def get_branding_image(
    workspace_id: uuid.UUID, kind: BrandingKind, session: Session, storage: StorageDep
) -> Response:
    """The company logo or email banner. No sign-in: emails link to it."""
    image = await profile_service.branding_image(session, storage, workspace_id, kind)
    return Response(
        content=image.data,
        media_type=image.content_type,
        headers={"Cache-Control": IMMUTABLE, "X-Content-Type-Options": "nosniff"},
    )
