"""File flows on top of the storage integration (STORAGE.md): upload URLs for files the API checks
before using, promoting a checked PDF to its final path, and cleaning up what's left behind.

Feature code checks permissions first, then calls these with IDs from its own workspace-scoped
rows, so a path never comes from the browser.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.errors import PdfInvalidError, UploadExpiredError, UploadMissingError
from app.core.ids import new_id
from app.integrations.storage import (
    TEMP_PREFIX,
    UPLOAD_WINDOW,
    Bucket,
    SignedUpload,
    Storage,
    temp_upload_path,
)
from app.services.pdfs import sanitise_pdf, validate_pdf

logger = logging.getLogger("app.storage")

# Temp uploads and demo files older than this are removed by the daily orphan cron.
ORPHAN_AGE = timedelta(hours=24)
# Buckets whose whole contents are short-lived (STORAGE.md: demo files hard-deleted within 24 h).
_SHORT_LIVED_BUCKETS = (Bucket.DEMO,)


@dataclass(frozen=True)
class PendingUpload:
    upload_id: uuid.UUID
    upload: SignedUpload


async def create_upload(storage: Storage, bucket: Bucket, workspace_id: uuid.UUID) -> PendingUpload:
    """A signed URL for one upload to a fresh temp path. The caller returns `upload_id` and the
    URL to the browser, and later passes `upload_id` back to `promote_pdf`."""
    upload_id = new_id()
    upload = await storage.signed_upload_url(bucket, temp_upload_path(workspace_id, upload_id))
    return PendingUpload(upload_id=upload_id, upload=upload)


def issued_at(upload_id: uuid.UUID) -> datetime:
    """When the upload URL was issued: the timestamp inside the UUID v7."""
    if upload_id.version != 7:
        raise UploadMissingError()
    return datetime.fromtimestamp((upload_id.int >> 80) / 1000, UTC)


async def promote_pdf(
    storage: Storage,
    bucket: Bucket,
    *,
    workspace_id: uuid.UUID,
    upload_id: uuid.UUID,
    destination: str,
) -> bytes:
    """Checks the PDF uploaded for `upload_id`, stores a sanitised copy at `destination` and
    deletes the upload. Returns the sanitised bytes (for text extraction).

    Safe to run again after a crash: once the upload is gone and `destination` exists, it
    returns the stored copy. A file that fails a check is deleted and its `PdfInvalidError`
    raised; a file that arrived after the upload window raises `UploadExpiredError`.
    """
    temp_path = temp_upload_path(workspace_id, upload_id)
    uploaded = await storage.info(bucket, temp_path)
    if uploaded is None:
        if await storage.info(bucket, destination) is not None:
            return await storage.download(bucket, destination)
        raise UploadMissingError()
    if uploaded.created_at - issued_at(upload_id) > UPLOAD_WINDOW:
        await storage.delete(bucket, [temp_path])
        raise UploadExpiredError()
    data = await storage.download(bucket, temp_path)
    try:
        validate_pdf(data)
        clean = sanitise_pdf(data)
    except PdfInvalidError as error:
        await storage.delete(bucket, [temp_path])
        logger.info("upload %s rejected (%s)", upload_id, error.code)
        raise
    await storage.upload(bucket, destination, clean, content_type="application/pdf", upsert=True)
    await storage.delete(bucket, [temp_path])
    return clean


async def remove_orphans(storage: Storage, *, now: datetime | None = None) -> int:
    """Deletes temp uploads (every bucket) and demo files older than 24 hours. Returns how many
    files were deleted. Later tasks add files whose rows are gone (STORAGE.md: Deletion)."""
    cutoff = (now or datetime.now(UTC)) - ORPHAN_AGE
    deleted = 0
    for bucket in Bucket:
        prefixes = [""] if bucket in _SHORT_LIVED_BUCKETS else [TEMP_PREFIX]
        for prefix in prefixes:
            objects = await storage.list(bucket, prefix)
            stale = [obj.path for obj in objects if obj.created_at < cutoff]
            if stale:
                await storage.delete(bucket, stale)
                deleted += len(stale)
    return deleted
