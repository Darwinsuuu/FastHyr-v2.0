"""Supabase Storage (STORAGE.md, ADR-006): private buckets, short-lived signed URLs, and the file
operations services need. Only the API holds the service key; the browser gets signed URLs.

Paths carry IDs only, never names or emails. Nothing here logs paths' owners or file contents.
"""

import logging
import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlencode

import httpx2

from app.core.config import Settings

logger = logging.getLogger("app.storage")

# NFR-02: signed URLs live at most 15 minutes. Callers may ask for less, never more.
MAX_SIGNED_URL_TTL = timedelta(minutes=15)
# Uploads must land within this window after their URL is issued (see `claim_upload` in
# services/files.py): Supabase's own upload tokens last 2 hours and can't be shortened per call.
UPLOAD_WINDOW = timedelta(minutes=10)
# Folder for uploads that haven't been checked yet. The orphan cron empties what's left behind.
TEMP_PREFIX = "tmp"
# Read size for streamed uploads.
UPLOAD_BLOCK = 1024 * 1024


class Bucket(StrEnum):
    RESUMES = "resumes"
    RECORDINGS = "recordings"
    BRANDING = "branding"
    REPORTS = "reports"
    DEMO = "demo"


# Path builders for the patterns in STORAGE.md.


def temp_upload_path(workspace_id: uuid.UUID, upload_id: uuid.UUID) -> str:
    """Where a browser uploads before the API checks the file. `upload_id` is a UUID v7, so the
    path records when its upload URL was issued."""
    return f"{TEMP_PREFIX}/{workspace_id}/{upload_id}"


def resume_path(workspace_id: uuid.UUID, application_id: uuid.UUID) -> str:
    return f"{workspace_id}/{application_id}/resume.pdf"


def recording_folder(workspace_id: uuid.UUID, interview_id: uuid.UUID) -> str:
    return f"{workspace_id}/{interview_id}"


def recording_chunks_folder(workspace_id: uuid.UUID, interview_id: uuid.UUID) -> str:
    return f"{recording_folder(workspace_id, interview_id)}/chunks"


def recording_chunk_path(
    workspace_id: uuid.UUID, interview_id: uuid.UUID, attempt_id: uuid.UUID, seq: int, kind: str
) -> str:
    """One piece of an attempt's recording; `kind` is "webm" or "mp4". The zero-padded `seq`
    keeps a folder listing in recording order."""
    return f"{recording_chunks_folder(workspace_id, interview_id)}/{attempt_id}/{seq:05d}.{kind}"


def recording_file_path(workspace_id: uuid.UUID, interview_id: uuid.UUID, name: str) -> str:
    """The finished files: `recording.webm|mp4`, `audio.m4a`, `poster.jpg`."""
    return f"{recording_folder(workspace_id, interview_id)}/{name}"


def demo_resume_path(demo_session_id: uuid.UUID) -> str:
    return f"{demo_session_id}/resume.pdf"


def branding_path(workspace_id: uuid.UUID, kind: str, extension: str) -> str:
    """`kind` is "logo" or "banner"; `extension` is "png" or "jpg"."""
    return f"{workspace_id}/{kind}.{extension}"


def report_path(workspace_id: uuid.UUID, report_job_id: uuid.UUID) -> str:
    return f"{workspace_id}/{report_job_id}.pdf"


@dataclass(frozen=True)
class SignedUpload:
    path: str
    url: str
    # Also accepted by supabase-js `uploadToSignedUrl(path, token, file)`.
    token: str


@dataclass(frozen=True)
class StoredObject:
    path: str
    size: int
    content_type: str | None
    created_at: datetime


class StorageUnavailableError(Exception):
    """Storage couldn't be reached or failed. Worth retrying."""

    code = "storage_unavailable"


class StorageObjectMissingError(Exception):
    """The object isn't there (never uploaded, or already moved or deleted)."""

    code = "storage_object_missing"


class StorageRejectedError(Exception):
    """Storage refused the request: a type the bucket doesn't allow, a file over its limit, or
    a bad request. Retrying won't help."""

    code = "storage_rejected"


class StorageConflictError(Exception):
    """An object already exists at the destination."""

    code = "storage_conflict"


class Storage(Protocol):
    async def signed_upload_url(self, bucket: Bucket, path: str) -> SignedUpload: ...

    async def signed_download_url(
        self,
        bucket: Bucket,
        path: str,
        *,
        ttl: timedelta = MAX_SIGNED_URL_TTL,
        download_as: str | None = None,
    ) -> str: ...

    async def info(self, bucket: Bucket, path: str) -> StoredObject | None: ...

    async def download(self, bucket: Bucket, path: str) -> bytes: ...

    async def upload(
        self, bucket: Bucket, path: str, data: bytes, *, content_type: str, upsert: bool = False
    ) -> None: ...

    async def upload_file(
        self, bucket: Bucket, path: str, file: Path, *, content_type: str, upsert: bool = False
    ) -> None: ...

    async def move(self, bucket: Bucket, source: str, destination: str) -> None: ...

    async def delete(self, bucket: Bucket, paths: Sequence[str]) -> None: ...

    async def list(self, bucket: Bucket, prefix: str) -> list[StoredObject]: ...


def _ttl_seconds(ttl: timedelta) -> int:
    seconds = int(ttl.total_seconds())
    if seconds <= 0 or ttl > MAX_SIGNED_URL_TTL:
        raise ValueError("signed URL lifetime must be between 1 second and 15 minutes")
    return seconds


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class SupabaseStorage:
    """The Storage REST API, called with the service key."""

    LIST_PAGE = 1000

    def __init__(self, supabase_url: str, service_key: str, *, timeout: float = 30) -> None:
        self.public_url = f"{supabase_url.rstrip('/')}/storage/v1"
        self.service_key = service_key
        self.timeout = timeout

    async def _request(
        self, method: str, path: str, *, ok_missing: bool = False, **kwargs: Any
    ) -> httpx2.Response:
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            **kwargs.pop("headers", {}),
        }
        try:
            async with httpx2.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method, f"{self.public_url}{path}", headers=headers, **kwargs
                )
        except httpx2.HTTPError as error:
            raise StorageUnavailableError() from error
        status = _status_of(response)
        if status >= 500 or status == 429:
            raise StorageUnavailableError()
        if status == 404:
            if ok_missing:
                return response
            raise StorageObjectMissingError()
        if status == 409:
            raise StorageConflictError()
        if status >= 400:
            # Bodies can echo the path; keep to the status.
            logger.warning("storage %s refused (%d)", method, status)
            raise StorageRejectedError()
        return response

    async def signed_upload_url(self, bucket: Bucket, path: str) -> SignedUpload:
        # No `x-upsert`: the token can create the object once and never overwrite it.
        response = await self._request("POST", f"/object/upload/sign/{bucket}/{_quote(path)}")
        body = response.json()
        return SignedUpload(path=path, url=f"{self.public_url}{body['url']}", token=body["token"])

    async def signed_download_url(
        self,
        bucket: Bucket,
        path: str,
        *,
        ttl: timedelta = MAX_SIGNED_URL_TTL,
        download_as: str | None = None,
    ) -> str:
        response = await self._request(
            "POST",
            f"/object/sign/{bucket}/{_quote(path)}",
            json={"expiresIn": _ttl_seconds(ttl)},
        )
        url = f"{self.public_url}{response.json()['signedURL']}"
        if download_as is not None:
            # Storage then answers with `Content-Disposition: attachment; filename=...`.
            url = f"{url}&{urlencode({'download': download_as})}"
        return url

    async def info(self, bucket: Bucket, path: str) -> StoredObject | None:
        response = await self._request(
            "GET", f"/object/info/{bucket}/{_quote(path)}", ok_missing=True
        )
        if _status_of(response) == 404:
            return None
        body = response.json()
        return StoredObject(
            path=path,
            size=int(body.get("size") or 0),
            content_type=body.get("content_type"),
            created_at=_parse_time(body["created_at"]),
        )

    async def download(self, bucket: Bucket, path: str) -> bytes:
        response = await self._request("GET", f"/object/{bucket}/{_quote(path)}")
        return response.content

    async def upload(
        self, bucket: Bucket, path: str, data: bytes, *, content_type: str, upsert: bool = False
    ) -> None:
        await self._request(
            "POST",
            f"/object/{bucket}/{_quote(path)}",
            content=data,
            headers={"Content-Type": content_type, "x-upsert": "true" if upsert else "false"},
        )

    async def upload_file(
        self, bucket: Bucket, path: str, file: Path, *, content_type: str, upsert: bool = False
    ) -> None:
        """Uploads a file from disk without reading it all into memory (a recording can be
        hundreds of megabytes)."""

        async def body() -> AsyncIterator[bytes]:
            with file.open("rb") as handle:
                while block := handle.read(UPLOAD_BLOCK):
                    yield block

        await self._request(
            "POST",
            f"/object/{bucket}/{_quote(path)}",
            content=body(),
            headers={
                "Content-Type": content_type,
                "Content-Length": str(file.stat().st_size),
                "x-upsert": "true" if upsert else "false",
            },
        )

    async def move(self, bucket: Bucket, source: str, destination: str) -> None:
        await self._request(
            "POST",
            "/object/move",
            json={"bucketId": str(bucket), "sourceKey": source, "destinationKey": destination},
        )

    async def delete(self, bucket: Bucket, paths: Sequence[str]) -> None:
        """Deletes the objects; paths that are already gone are fine."""
        for start in range(0, len(paths), self.LIST_PAGE):
            await self._request(
                "DELETE",
                f"/object/{bucket}",
                json={"prefixes": list(paths[start : start + self.LIST_PAGE])},
            )

    async def list(self, bucket: Bucket, prefix: str) -> list[StoredObject]:
        """Every object under `prefix` (a folder path, no trailing slash), walking subfolders."""
        found: list[StoredObject] = []
        folders = [prefix.strip("/")]
        while folders:
            folder = folders.pop()
            offset = 0
            while True:
                response = await self._request(
                    "POST",
                    f"/object/list/{bucket}",
                    json={
                        "prefix": folder,
                        "limit": self.LIST_PAGE,
                        "offset": offset,
                        "sortBy": {"column": "name", "order": "asc"},
                    },
                )
                entries: list[dict[str, Any]] = response.json()
                for entry in entries:
                    path = f"{folder}/{entry['name']}" if folder else entry["name"]
                    if entry.get("id") is None:
                        folders.append(path)
                        continue
                    metadata = entry.get("metadata") or {}
                    found.append(
                        StoredObject(
                            path=path,
                            size=int(metadata.get("size") or 0),
                            content_type=metadata.get("mimetype"),
                            created_at=_parse_time(entry["created_at"]),
                        )
                    )
                if len(entries) < self.LIST_PAGE:
                    break
                offset += self.LIST_PAGE
        return found


def _quote(path: str) -> str:
    return quote(path, safe="/")


def _status_of(response: httpx2.Response) -> int:
    """Storage answers most errors with HTTP 400 and the real status in the body's
    `statusCode` (e.g. "404" for a missing object, "409" for a duplicate)."""
    if response.status_code != 400:
        return response.status_code
    try:
        body = response.json()
        return int(body["statusCode"])
    except (ValueError, KeyError, TypeError):
        return response.status_code


def storage_from_settings(settings: Settings) -> SupabaseStorage:
    return SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key)
