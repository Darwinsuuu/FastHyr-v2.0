"""Upload promotion and orphan cleanup (FND-011) against an in-memory storage fake."""

import asyncio
import os
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import PdfEncryptedError, UploadExpiredError, UploadMissingError
from app.core.ids import new_id
from app.integrations.storage import (
    Bucket,
    SignedUpload,
    StorageObjectMissingError,
    StoredObject,
    resume_path,
    temp_upload_path,
)
from app.services import files
from app.services.pdfs import active_content
from tests.pdf_fixtures import encrypted_pdf, hostile_pdf


@dataclass
class FakeStorage:
    objects: dict[tuple[Bucket, str], tuple[bytes, datetime]] = field(default_factory=dict)

    def put(self, bucket: Bucket, path: str, data: bytes, created_at: datetime) -> None:
        self.objects[(bucket, path)] = (data, created_at)

    async def signed_upload_url(self, bucket: Bucket, path: str) -> SignedUpload:
        return SignedUpload(path=path, url=f"https://storage.test/{bucket}/{path}", token="t")

    async def info(self, bucket: Bucket, path: str) -> StoredObject | None:
        if (bucket, path) not in self.objects:
            return None
        data, created_at = self.objects[(bucket, path)]
        return StoredObject(path, len(data), "application/pdf", created_at)

    async def download(self, bucket: Bucket, path: str) -> bytes:
        if (bucket, path) not in self.objects:
            raise StorageObjectMissingError()
        return self.objects[(bucket, path)][0]

    async def upload(
        self, bucket: Bucket, path: str, data: bytes, *, content_type: str, upsert: bool = False
    ) -> None:
        self.put(bucket, path, data, datetime.now(UTC))

    async def delete(self, bucket: Bucket, paths: Sequence[str]) -> None:
        for path in paths:
            self.objects.pop((bucket, path), None)

    async def list(self, bucket: Bucket, prefix: str) -> list[StoredObject]:
        return [
            StoredObject(path, len(data), None, created_at)
            for (b, path), (data, created_at) in self.objects.items()
            if b == bucket and path.startswith(prefix)
        ]


def upload_id_issued(ago: timedelta) -> uuid.UUID:
    """A UUID v7 as `new_id()` would have made it `ago` earlier."""
    unix_ms = int((datetime.now(UTC) - ago).timestamp() * 1000)
    value = unix_ms << 80 | int.from_bytes(os.urandom(10))
    value = (value & ~(0xF << 76)) | (0x7 << 76)
    value = (value & ~(0x3 << 62)) | (0x2 << 62)
    return uuid.UUID(int=value)


WORKSPACE = new_id()
DESTINATION = resume_path(WORKSPACE, new_id())


def promote(storage: FakeStorage, upload_id: uuid.UUID) -> bytes:
    return asyncio.run(
        files.promote_pdf(
            storage,  # type: ignore[arg-type]
            Bucket.RESUMES,
            workspace_id=WORKSPACE,
            upload_id=upload_id,
            destination=DESTINATION,
        )
    )


def test_promotes_a_sanitised_copy_and_removes_the_upload() -> None:
    storage = FakeStorage()
    upload_id = new_id()
    temp = temp_upload_path(WORKSPACE, upload_id)
    storage.put(Bucket.RESUMES, temp, hostile_pdf(), datetime.now(UTC))

    clean = promote(storage, upload_id)

    assert active_content(clean) == []
    assert storage.objects[(Bucket.RESUMES, DESTINATION)][0] == clean
    assert (Bucket.RESUMES, temp) not in storage.objects
    # A retried job finds the work done and gets the stored copy back.
    assert promote(storage, upload_id) == clean


def test_refuses_a_file_uploaded_after_the_window() -> None:
    storage = FakeStorage()
    upload_id = upload_id_issued(timedelta(minutes=11))
    temp = temp_upload_path(WORKSPACE, upload_id)
    storage.put(Bucket.RESUMES, temp, hostile_pdf(), datetime.now(UTC))

    with pytest.raises(UploadExpiredError):
        promote(storage, upload_id)
    assert storage.objects == {}


def test_deletes_a_file_that_fails_the_checks() -> None:
    storage = FakeStorage()
    upload_id = new_id()
    storage.put(
        Bucket.RESUMES, temp_upload_path(WORKSPACE, upload_id), encrypted_pdf(), datetime.now(UTC)
    )

    with pytest.raises(PdfEncryptedError):
        promote(storage, upload_id)
    assert storage.objects == {}


def test_missing_upload() -> None:
    with pytest.raises(UploadMissingError):
        promote(FakeStorage(), new_id())
    # Not a UUID v7 from `create_upload`.
    with pytest.raises(UploadMissingError):
        files.issued_at(uuid.uuid4())


def test_removes_only_stale_temp_uploads_and_demo_files() -> None:
    storage = FakeStorage()
    now = datetime.now(UTC)
    old, fresh = now - timedelta(hours=25), now - timedelta(hours=1)
    storage.put(Bucket.RESUMES, "tmp/w/old", b"", old)
    storage.put(Bucket.RESUMES, "tmp/w/fresh", b"", fresh)
    storage.put(Bucket.RESUMES, "w/a/resume.pdf", b"", old)  # a used résumé stays
    storage.put(Bucket.DEMO, "d/resume.pdf", b"", old)
    storage.put(Bucket.DEMO, "e/resume.pdf", b"", fresh)

    deleted = asyncio.run(files.remove_orphans(storage, now=now))  # type: ignore[arg-type]

    assert deleted == 2
    assert sorted(path for _, path in storage.objects) == [
        "e/resume.pdf",
        "tmp/w/fresh",
        "w/a/resume.pdf",
    ]
