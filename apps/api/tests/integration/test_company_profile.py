"""WS-001: Admins read and save the company profile, upload a logo and banner through signed URLs,
and emails load the images from the public branding route. Other roles get 403 and other
workspaces never see the profile."""

import asyncio
import io
import uuid
from typing import Any

import asyncpg
import httpx2
import pytest
from fastapi import FastAPI
from PIL import Image

from app.core.context import Role
from app.core.ids import new_id
from app.integrations.storage import Bucket, SupabaseStorage
from app.main import create_app
from tests.conftest import Supabase
from tests.tenancy.harness import Tenancy

URL = "/v1/workspace/company-profile"


@pytest.fixture
def tenancy_app(storage: SupabaseStorage) -> FastAPI:
    return create_app(storage=storage)


@pytest.fixture(autouse=True)
def clean_branding(tenancy: Tenancy, storage: SupabaseStorage) -> Any:
    yield
    for key in tenancy.workspaces:
        prefix = str(tenancy.workspace(key).id)

        async def remove(prefix: str = prefix) -> None:
            for folder in (prefix, f"tmp/{prefix}"):
                paths = [obj.path for obj in await storage.list(Bucket.BRANDING, folder)]
                if paths:
                    await storage.delete(Bucket.BRANDING, paths)

        asyncio.run(remove())


def db(supabase: Supabase, query: str, *args: object) -> list[asyncpg.Record]:
    async def run() -> list[asyncpg.Record]:
        connection = await asyncpg.connect(supabase.database_url)
        try:
            return list(await connection.fetch(query, *args))
        finally:
            await connection.close()

    return asyncio.run(run())


def image(width: int, height: int, fmt: str = "PNG") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (232, 131, 95)).save(out, format=fmt)
    return out.getvalue()


def upload(tenancy: Tenancy, kind: str, data: bytes, content_type: str) -> str:
    """What the page does: ask for a signed URL, then PUT the file to it."""
    response = tenancy.client("a", Role.ADMIN).post(f"{URL}/branding-upload", json={"kind": kind})
    assert response.status_code == 200, response.text
    target = response.json()
    put = httpx2.put(target["url"], content=data, headers={"Content-Type": content_type})
    assert put.status_code == 200, put.text
    upload_id: str = target["upload_id"]
    return upload_id


def save(tenancy: Tenancy, **body: Any) -> httpx2.Response:
    return tenancy.client("a", Role.ADMIN).put(URL, json={"company_name": "Acme Talent", **body})


def test_admin_saves_the_profile(tenancy: Tenancy) -> None:
    admin = tenancy.client("a", Role.ADMIN)
    assert admin.get(URL).json()["company_name"] == "Tenancy A"

    response = save(
        tenancy,
        website="acme.com",
        industry="technology",
        company_size="51-200",
        hq_country="PH",
        timezone="Asia/Manila",
        about="We build hiring software.",
        careers_url="https://acme.com/careers",
    )

    assert response.status_code == 200, response.text
    body = admin.get(URL).json()
    assert body | {"updated_at": None} == {
        "company_name": "Acme Talent",
        "website": "https://acme.com",
        "industry": "technology",
        "company_size": "51-200",
        "hq_country": "PH",
        "timezone": "Asia/Manila",
        "about": "We build hiring software.",
        "careers_url": "https://acme.com/careers",
        "logo_url": None,
        "banner_url": None,
        "updated_at": None,
    }
    workspace_id = tenancy.workspace("a").id
    [workspace] = db(
        tenancy.supabase, "select timezone from workspaces where id = $1", workspace_id
    )
    assert workspace["timezone"] == "Asia/Manila"
    [audit] = db(
        tenancy.supabase,
        "select action, data from audit_log where workspace_id = $1",
        workspace_id,
    )
    assert audit["action"] == "company_profile.updated"
    assert "We build" not in audit["data"]  # field names only

    # Clearing optional fields.
    assert save(tenancy, website="", about=None).json()["website"] is None
    assert save(tenancy, company_name=" ").status_code == 422


def test_logo_and_banner_upload_and_public_route(tenancy: Tenancy) -> None:
    workspace_id = tenancy.workspace("a").id
    logo_id = upload(tenancy, "logo", image(512, 512), "image/png")
    banner_id = upload(tenancy, "banner", image(1200, 400), "image/png")

    body = save(tenancy, logo_upload_id=logo_id, banner_upload_id=banner_id).json()

    assert httpx2.get(body["logo_url"]).status_code == 200  # signed, short-lived
    paths = db(
        tenancy.supabase,
        "select logo_path, banner_path from company_profiles where workspace_id = $1",
        workspace_id,
    )[0]
    assert (paths["logo_path"], paths["banner_path"]) == (
        f"{workspace_id}/logo.png",
        f"{workspace_id}/banner.png",
    )

    # The public route needs no sign-in and caches for a long time.
    public = tenancy.anonymous()
    logo = public.get(f"/v1/public/branding/{workspace_id}/logo")
    assert logo.status_code == 200
    assert logo.headers["content-type"] == "image/png"
    assert "immutable" in logo.headers["cache-control"]
    assert Image.open(io.BytesIO(logo.content)).size == (512, 512)

    # A JPEG banner replaces the PNG one; removing the logo removes the file.
    jpeg_id = upload(tenancy, "banner", image(1200, 400, "JPEG"), "image/jpeg")
    save(tenancy, banner_upload_id=jpeg_id, remove_logo=True)
    banner = public.get(f"/v1/public/branding/{workspace_id}/banner")
    assert banner.headers["content-type"] == "image/jpeg"
    assert public.get(f"/v1/public/branding/{workspace_id}/logo").status_code == 404
    assert public.get(f"/v1/public/branding/{new_id()}/logo").status_code == 404

    async def stored() -> list[str]:
        storage = SupabaseStorage(tenancy.supabase.url, tenancy.supabase.secret_key)
        return sorted(obj.path for obj in await storage.list(Bucket.BRANDING, str(workspace_id)))

    assert asyncio.run(stored()) == [f"{workspace_id}/banner.jpg"]


def test_bad_images_are_refused(tenancy: Tenancy) -> None:
    not_square = upload(tenancy, "logo", image(600, 300), "image/png")
    response = save(tenancy, logo_upload_id=not_square)
    assert response.status_code == 422
    assert response.json()["code"] == "logo_not_square"

    # The upload is gone, so the same ID can't be retried.
    assert save(tenancy, logo_upload_id=not_square).json()["code"] == "upload_missing"
    assert save(tenancy, logo_upload_id=str(uuid.uuid4())).json()["code"] == "upload_missing"


def test_admin_only_and_scoped_to_the_workspace(tenancy: Tenancy) -> None:
    for role in (Role.RECRUITER, Role.HIRING_MANAGER):
        client = tenancy.client("a", role)
        assert client.get(URL).status_code == 403
        assert client.put(URL, json={"company_name": "Mine"}).status_code == 403
        assert client.post(f"{URL}/branding-upload", json={"kind": "logo"}).status_code == 403

    save(tenancy, about="Only for workspace A")
    other = tenancy.client("b", Role.ADMIN).get(URL).json()
    assert other["company_name"] == "Tenancy B"
    assert other["about"] is None
