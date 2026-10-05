"""Interview recordings (INTV-006, MEDIA.md §3, STORAGE.md).

While an attempt runs, the browser records it in 5-second chunks and uploads each one at once to
a signed URL (`chunk_urls()`), then registers it (`register_chunk()`); a closed or crashed tab
loses only the chunk it was recording. Chunks live at
`{workspace_id}/{interview_id}/chunks/{attempt_id}/{seq}.{webm|mp4}` in the recordings bucket.

Once the interview is complete and every attempt is settled (the browser registered its last
chunk, or nothing arrived for `QUIET` after it ended), `finalize()` joins the chunks into
`recording.webm|mp4`, `audio.m4a` and `poster.jpg`, sets `recording_status = ready` and deletes
the chunks. The last chunk's registration queues it; the every-minute `finalize_recordings` cron
queues the rest (`due()`).

`recording_status`: `none` → `uploading` (first chunk) → `finalizing` → `ready` or `failed`.
"""

import logging
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import CandidateContext
from app.core.errors import (
    InterviewAttemptNotFoundError,
    InterviewNotFoundError,
    InterviewNotOpenError,
    RecordingChunkMissingError,
    RecordingChunkTooLargeError,
    RecordingFinalizedError,
    RecordingTypeMismatchError,
)
from app.core.ids import new_id
from app.integrations.storage import (
    Bucket,
    Storage,
    recording_chunk_path,
    recording_chunks_folder,
    recording_file_path,
)
from app.interview import recording
from app.jobs.queue import JobQueue
from app.models import Interview, InterviewAttempt, RecordingChunk
from app.repositories.interviews import (
    InterviewAttemptRepository,
    RecordingChunkRepository,
    recordings_due,
)
from app.schemas.interviews import (
    RecordingChunkRegistered,
    RecordingChunkRequest,
    RecordingChunkUrl,
    RecordingChunkUrls,
    RecordingChunkUrlsRequest,
)
from app.services import interview_links

logger = logging.getLogger("app.recording")

FINALIZE_JOB = "finalize_recording"
# An attempt whose browser never said it stopped is settled once nothing arrived for this long
# after it ended (a closed tab, or a connection too poor to send the rest).
QUIET = timedelta(minutes=2)
# The latest a completed interview's recording waits for missing chunks.
LATEST = timedelta(minutes=30)
# STORAGE.md: ~50 MB per chunk at most. A 5-second chunk is well under 1 MB.
MAX_CHUNK_BYTES = 50 * 1024 * 1024
DONE = frozenset({"finalizing", "ready", "failed"})
KINDS: dict[str, recording.Kind] = {"webm": "webm", "mp4": "mp4"}


# --- Uploads (the candidate's browser) --------------------------------------------------------


async def chunk_urls(
    session: AsyncSession,
    storage: Storage,
    token: str,
    candidate: CandidateContext,
    body: RecordingChunkUrlsRequest,
    *,
    now: datetime | None = None,
) -> RecordingChunkUrls:
    """Signed upload URLs for chunks `from_seq` … `from_seq + count - 1` of an attempt. The
    first request fixes the attempt's recording type."""
    now = now or datetime.now(UTC)
    interview = await _recording_interview(session, token, candidate, now)
    if interview.recording_status in DONE:
        raise RecordingFinalizedError()
    attempts = InterviewAttemptRepository(session, interview.workspace_id)
    attempt = await _attempt(attempts, interview, body.attempt_id, lock=True)
    if attempt.recording_type is None:
        attempt.recording_type = body.type
    elif attempt.recording_type != body.type:
        raise RecordingTypeMismatchError()
    await session.commit()

    urls = []
    for seq in range(body.from_seq, body.from_seq + body.count):
        path = recording_chunk_path(
            interview.workspace_id, interview.id, attempt.id, seq, body.type
        )
        signed = await storage.signed_upload_url(Bucket.RECORDINGS, path)
        urls.append(RecordingChunkUrl(seq=seq, url=signed.url))
    return RecordingChunkUrls(urls=urls)


async def register_chunk(
    session: AsyncSession,
    storage: Storage,
    queue: JobQueue,
    token: str,
    candidate: CandidateContext,
    body: RecordingChunkRequest,
    *,
    now: datetime | None = None,
) -> RecordingChunkRegistered:
    """Records that a chunk arrived, after checking it in Storage. Registering it again is
    harmless. `last` marks the attempt's recording as complete; when that settles a completed
    interview, the recording is put together at once."""
    now = now or datetime.now(UTC)
    interview = await _recording_interview(session, token, candidate, now)
    workspace_id, interview_id = interview.workspace_id, interview.id
    if interview.recording_status in DONE:
        raise RecordingFinalizedError()
    attempts = InterviewAttemptRepository(session, workspace_id)
    attempt = await _attempt(attempts, interview, body.attempt_id)
    attempt_id, kind = attempt.id, attempt.recording_type
    if kind is None:
        raise RecordingChunkMissingError()
    path = recording_chunk_path(workspace_id, interview_id, attempt_id, body.seq, kind)
    # Storage first, with no transaction open (rolling back expires the rows read so far).
    await session.rollback()
    stored = await storage.info(Bucket.RECORDINGS, path)
    if stored is None:
        raise RecordingChunkMissingError()
    if stored.size > MAX_CHUNK_BYTES:
        await storage.delete(Bucket.RECORDINGS, [path])
        raise RecordingChunkTooLargeError()

    interview = await attempts.lock_interview(interview_id)
    if interview.recording_status in DONE:
        raise RecordingFinalizedError()
    await RecordingChunkRepository(session, workspace_id).add_if_new(
        RecordingChunk(
            id=new_id(),
            workspace_id=workspace_id,
            interview_id=interview_id,
            attempt_id=attempt_id,
            seq=body.seq,
            path=path,
            bytes=stored.size,
            uploaded_at=now,
        )
    )
    interview.recording_status = "uploading"
    if body.last:
        locked = await attempts.get(attempt_id, lock=True)
        if locked is not None and locked.recording_stopped_at is None:
            locked.recording_stopped_at = now
    completed = interview.status == "completed"
    await session.commit()
    if body.last and completed:
        await queue.enqueue(FINALIZE_JOB, workspace_id, interview_id, key=interview_id)
    return RecordingChunkRegistered(seq=body.seq, bytes=stored.size)


async def _recording_interview(
    session: AsyncSession, token: str, candidate: CandidateContext, now: datetime
) -> Interview:
    """The applying account's interview. Uploads go on after the interview finished, or its link
    expired, while the last chunks arrive; only a link that was withdrawn refuses them."""
    row = await interview_links.link_row(session, token)
    if candidate.user_id != row.candidate_auth_user_id:
        raise InterviewNotFoundError()
    if interview_links.resolve(row, candidate, now) == "unavailable":
        raise InterviewNotOpenError()
    return row.interview


async def _attempt(
    attempts: InterviewAttemptRepository,
    interview: Interview,
    attempt_id: uuid.UUID,
    *,
    lock: bool = False,
) -> InterviewAttempt:
    attempt = await attempts.get(attempt_id, lock=lock)
    if attempt is None or attempt.interview_id != interview.id:
        raise InterviewAttemptNotFoundError()
    return attempt


# --- Finalising (the worker) ------------------------------------------------------------------


async def due(
    session: AsyncSession, *, now: datetime | None = None
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """For the finalize_recordings cron: (workspace_id, interview_id) of every recording that
    can be put together now."""
    return await recordings_due(session, now or datetime.now(UTC), quiet=QUIET, latest=LATEST)


class Finalized(StrEnum):
    WAITING = "waiting"
    READY = "ready"
    FAILED = "failed"
    SKIPPED = "skipped"


async def finalize(
    session: AsyncSession,
    storage: Storage,
    workspace_id: uuid.UUID,
    interview_id: uuid.UUID,
    *,
    ffmpeg: str,
    now: datetime | None = None,
) -> Finalized:
    """Puts the interview's recording together once it is due, uploads the files and deletes
    the chunks. Safe to run again: a ready recording only gets its chunk clean-up repeated."""
    now = now or datetime.now(UTC)
    attempts = InterviewAttemptRepository(session, workspace_id)
    interview = await attempts.get_interview(interview_id)
    if interview is None or interview.recording_status == "failed":
        await session.rollback()
        return Finalized.SKIPPED
    if interview.recording_status == "ready":
        await session.rollback()
        await _delete_chunks(storage, workspace_id, interview_id)
        return Finalized.SKIPPED
    if not await recordings_due(
        session, now, quiet=QUIET, latest=LATEST, interview_id=interview_id
    ):
        await session.rollback()
        return Finalized.WAITING

    interview = await attempts.lock_interview(interview_id)
    interview.recording_status = "finalizing"
    history = await attempts.of_interview(interview_id)
    video = interview.format == "video_voice"
    await session.commit()

    order = {attempt.id: index for index, attempt in enumerate(history)}
    with tempfile.TemporaryDirectory(prefix="recording-") as folder:
        workdir = Path(folder)
        parts = await _download_parts(storage, workspace_id, interview_id, order, workdir)
        built = await recording.build(ffmpeg, parts, workdir, video=video) if parts else None
        if built is None:
            await _mark_failed(session, attempts, interview_id)
            logger.warning("interview recording has no usable chunks")
            return Finalized.FAILED
        recording_path = recording_file_path(workspace_id, interview_id, f"recording.{built.kind}")
        await storage.upload_file(
            Bucket.RECORDINGS,
            recording_path,
            built.recording,
            content_type=recording.content_type(built.kind, built.video),
            upsert=True,
        )
        if built.audio is not None:
            await storage.upload_file(
                Bucket.RECORDINGS,
                recording_file_path(workspace_id, interview_id, "audio.m4a"),
                built.audio,
                content_type="audio/mp4",
                upsert=True,
            )
        if built.poster is not None:
            await storage.upload_file(
                Bucket.RECORDINGS,
                recording_file_path(workspace_id, interview_id, "poster.jpg"),
                built.poster,
                content_type="image/jpeg",
                upsert=True,
            )

    interview = await attempts.lock_interview(interview_id)
    interview.recording_path = recording_path
    interview.recording_status = "ready"
    interview.duration_seconds = built.duration_seconds
    await RecordingChunkRepository(session, workspace_id).delete_of_interview(interview_id)
    await session.commit()
    await _delete_chunks(storage, workspace_id, interview_id)
    return Finalized.READY


async def mark_failed(
    session: AsyncSession, workspace_id: uuid.UUID, interview_id: uuid.UUID
) -> None:
    """For the job's failure hook: the recording couldn't be put together. Its chunks stay
    (deleted with the interview's other recording files)."""
    await _mark_failed(session, InterviewAttemptRepository(session, workspace_id), interview_id)


async def _mark_failed(
    session: AsyncSession, attempts: InterviewAttemptRepository, interview_id: uuid.UUID
) -> None:
    interview = await attempts.lock_interview(interview_id)
    if interview.recording_status != "ready":
        interview.recording_status = "failed"
    await session.commit()


async def _download_parts(
    storage: Storage,
    workspace_id: uuid.UUID,
    interview_id: uuid.UUID,
    order: dict[uuid.UUID, int],
    workdir: Path,
) -> list[recording.Part]:
    """Each attempt's chunks from Storage, joined byte for byte in order into one file per
    attempt. Storage is the source, not the registrations: a chunk that uploaded but whose tab
    closed before registering it still counts."""
    folder = recording_chunks_folder(workspace_id, interview_id)
    found: dict[uuid.UUID, list[tuple[int, str, recording.Kind]]] = {}
    for stored in await storage.list(Bucket.RECORDINGS, folder):
        chunk = _parse_chunk(stored.path, folder)
        if chunk is None or chunk[0] not in order:
            continue
        attempt_id, seq, kind = chunk
        found.setdefault(attempt_id, []).append((seq, stored.path, kind))

    parts: list[recording.Part] = []
    for attempt_id in sorted(found, key=order.__getitem__):
        chunks = sorted(found[attempt_id])
        kinds = {kind for _, _, kind in chunks}
        if len(kinds) != 1:
            logger.warning("recording attempt has chunks of two types; left out")
            continue
        target = workdir / f"attempt-{order[attempt_id]}.raw"
        with target.open("wb") as joined:
            for _, path, _ in chunks:
                joined.write(await storage.download(Bucket.RECORDINGS, path))
        parts.append(recording.Part(path=target, kind=kinds.pop()))
    return parts


def _parse_chunk(path: str, folder: str) -> tuple[uuid.UUID, int, recording.Kind] | None:
    """`{folder}/{attempt_id}/{seq}.{kind}` → (attempt_id, seq, kind)."""
    rest = path.removeprefix(f"{folder}/")
    attempt, _, name = rest.partition("/")
    seq, _, extension = name.partition(".")
    kind = KINDS.get(extension)
    if kind is None or not seq.isdigit():
        return None
    try:
        return uuid.UUID(attempt), int(seq), kind
    except ValueError:
        return None


async def _delete_chunks(
    storage: Storage, workspace_id: uuid.UUID, interview_id: uuid.UUID
) -> None:
    folder = recording_chunks_folder(workspace_id, interview_id)
    paths = [stored.path for stored in await storage.list(Bucket.RECORDINGS, folder)]
    if paths:
        await storage.delete(Bucket.RECORDINGS, paths)
