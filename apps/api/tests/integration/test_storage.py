"""Storage against local Supabase (FND-011): signed URLs expire within 15 minutes, a browser
upload is checked and promoted, and the public key can't reach the private buckets."""

import asyncio
import base64
import json
from datetime import timedelta
from typing import Any

import httpx2
import pytest

from app.core.ids import new_id
from app.integrations.storage import Bucket, SupabaseStorage, resume_path
from app.services import files
from app.services.pdfs import active_content
from tests.conftest import Supabase
from tests.pdf_fixtures import hostile_pdf


def token_claims(url: str) -> dict[str, Any]:
    token = url.split("token=")[1].split("&")[0]
    payload = token.split(".")[1]
    claims: dict[str, Any] = json.loads(
        base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    )
    return claims


def test_upload_promote_and_download(storage: SupabaseStorage, supabase: Supabase) -> None:
    workspace_id = new_id()
    destination = resume_path(workspace_id, new_id())

    async def run() -> None:
        pending = await files.create_upload(storage, Bucket.RESUMES, workspace_id)
        async with httpx2.AsyncClient() as browser:
            # What supabase-js `uploadToSignedUrl` does.
            headers = {"Content-Type": "application/pdf"}
            uploaded = await browser.put(pending.upload.url, content=hostile_pdf(), headers=headers)
            assert uploaded.status_code == 200
            # The URL can't be used to overwrite the file.
            again = await browser.put(pending.upload.url, content=b"%PDF-1.7", headers=headers)
            assert again.status_code >= 400

        clean = await files.promote_pdf(
            storage,
            Bucket.RESUMES,
            workspace_id=workspace_id,
            upload_id=pending.upload_id,
            destination=destination,
        )
        assert await storage.info(Bucket.RESUMES, pending.upload.path) is None

        url = await storage.signed_download_url(
            Bucket.RESUMES, destination, download_as="resume.pdf"
        )
        claims = token_claims(url)
        assert claims["exp"] - claims["iat"] <= 15 * 60
        with pytest.raises(ValueError):
            await storage.signed_download_url(
                Bucket.RESUMES, destination, ttl=timedelta(minutes=16)
            )

        async with httpx2.AsyncClient() as browser:
            downloaded = await browser.get(url)
            assert downloaded.status_code == 200
            assert downloaded.headers["content-disposition"].startswith("attachment")
            assert downloaded.content == clean
            assert active_content(downloaded.content) == []

            # The public key reads and writes nothing (no storage policies, ADR-006).
            public = {"apikey": supabase.anon_key}
            base = f"{supabase.url}/storage/v1/object"
            read = await browser.get(f"{base}/{Bucket.RESUMES}/{destination}", headers=public)
            assert read.status_code >= 400
            write = await browser.post(
                f"{base}/{Bucket.RESUMES}/{workspace_id}/x.pdf",
                content=b"%PDF-1.7",
                headers={**public, "Content-Type": "application/pdf"},
            )
            assert write.status_code >= 400

        await storage.delete(Bucket.RESUMES, [destination])
        assert await storage.info(Bucket.RESUMES, destination) is None

    asyncio.run(run())


def test_buckets_refuse_other_file_types(storage: SupabaseStorage) -> None:
    async def run() -> None:
        pending = await files.create_upload(storage, Bucket.RESUMES, new_id())
        async with httpx2.AsyncClient() as browser:
            response = await browser.put(
                pending.upload.url, content=b"hello", headers={"Content-Type": "text/plain"}
            )
        assert response.status_code >= 400

    asyncio.run(run())
