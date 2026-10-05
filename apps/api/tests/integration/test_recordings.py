"""INTV-006: recording uploads and finalising. Chunks go to local Supabase Storage through the
signed URLs the API hands out, are registered, and the finalize job joins them with ffmpeg into
the recording, audio track and poster, then deletes them."""

import asyncio
import uuid
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.realtime import FakeRealtime
from app.integrations.storage import (
    Bucket,
    SupabaseStorage,
    recording_chunks_folder,
    recording_folder,
)
from app.main import create_app
from app.services import recordings
from tests.integration.test_applications import (
    CandidateUser,
    RecordingQueue,
    candidates,
    clean_resumes,
    queue,
)
from tests.integration.test_interview_sessions import (
    interview,
    post,
    ready,
    refused,
    start,
)
from tests.integration.test_pipelines import db_run, ok, sql
from tests.media_fixtures import chunks, ffmpeg, fragmented_mp4, webm
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_resumes", "queue"]


@pytest.fixture
def tenancy_app(storage: SupabaseStorage, queue: RecordingQueue) -> FastAPI:
    return create_app(storage=storage, job_queue=queue, realtime=FakeRealtime())


@pytest.fixture(autouse=True)
def clean_recordings(tenancy: Tenancy, storage: SupabaseStorage) -> Any:
    yield
    for workspace in ("a", "b"):
        prefix = str(tenancy.workspace(workspace).id)
        paths = [stored.path for stored in asyncio.run(storage.list(Bucket.RECORDINGS, prefix))]
        if paths:
            asyncio.run(storage.delete(Bucket.RECORDINGS, paths))


def chunk_urls(
    tenancy: Tenancy, token: str, who: CandidateUser, attempt_id: str, **body: Any
) -> Any:
    return post(
        tenancy,
        token,
        "chunk-urls",
        who,
        {"attempt_id": attempt_id, "type": "webm", "from_seq": 0, "count": 3, **body},
    )


def register(
    tenancy: Tenancy, token: str, who: CandidateUser, attempt_id: str, seq: int, last: bool = False
) -> Any:
    return post(tenancy, token, "chunks", who, {"attempt_id": attempt_id, "seq": seq, "last": last})


def upload(url: str, data: bytes, content_type: str = "video/webm") -> int:
    return httpx2.put(url, content=data, headers={"Content-Type": content_type}).status_code


def finalize(tenancy: Tenancy, storage: SupabaseStorage, interview_id: uuid.UUID) -> str:
    workspace_id = tenancy.workspace("a").id

    async def work(session: AsyncSession) -> str:
        outcome = await recordings.finalize(
            session, storage, workspace_id, interview_id, ffmpeg=ffmpeg()
        )
        return outcome.value

    return db_run(tenancy, work)


def due(tenancy: Tenancy) -> list[uuid.UUID]:
    async def work(session: AsyncSession) -> list[uuid.UUID]:
        return [interview_id for _, interview_id in await recordings.due(session)]

    return db_run(tenancy, work)


def files(storage: SupabaseStorage, prefix: str) -> dict[str, int]:
    return {
        stored.path.removeprefix(f"{prefix}/"): stored.size
        for stored in asyncio.run(storage.list(Bucket.RECORDINGS, prefix))
    }


def test_chunks_upload_register_and_become_the_recording(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    queue: RecordingQueue,
) -> None:
    paolo = candidates[0]
    token, interview_id = ready(tenancy, paolo)
    attempt_id = ok(start(tenancy, token, paolo))["attempt_id"]

    urls = ok(chunk_urls(tenancy, token, paolo, attempt_id))["urls"]
    assert [url["seq"] for url in urls] == [0, 1, 2]
    pieces = chunks(webm(3), 3)
    for url, piece in zip(urls, pieces, strict=True):
        assert upload(url["url"], piece) == 200
        registered = ok(register(tenancy, token, paolo, attempt_id, url["seq"]))
        assert registered == {"seq": url["seq"], "bytes": len(piece)}
    # A retry after a lost answer changes nothing; a second upload to the same URL is refused.
    ok(register(tenancy, token, paolo, attempt_id, 1))
    assert upload(urls[1]["url"], pieces[1]) != 200
    assert interview(tenancy, interview_id)["recording_status"] == "uploading"
    [count] = sql(tenancy, "select count(*) from recording_chunks where interview_id = $1",
                  interview_id)  # fmt: skip
    assert count["count"] == 3

    ok(post(tenancy, token, "complete", paolo, {"attempt_id": attempt_id}))
    assert due(tenancy) == []  # The browser hasn't said it stopped, and chunks are recent.
    ok(register(tenancy, token, paolo, attempt_id, 2, last=True))
    assert ("finalize_recording", (tenancy.workspace("a").id, interview_id)) in queue.enqueued
    assert due(tenancy) == [interview_id]

    assert finalize(tenancy, storage, interview_id) == "ready"
    row = interview(tenancy, interview_id)
    folder = recording_folder(tenancy.workspace("a").id, interview_id)
    assert row["recording_status"] == "ready"
    assert row["recording_path"] == f"{folder}/recording.webm"
    assert row["duration_seconds"] == 3
    stored = files(storage, folder)
    assert set(stored) == {"recording.webm", "audio.m4a", "poster.jpg"}
    assert all(size > 0 for size in stored.values())
    # The chunks are gone, from Storage and the table.
    assert files(storage, recording_chunks_folder(tenancy.workspace("a").id, interview_id)) == {}
    assert (
        sql(tenancy, "select * from recording_chunks where interview_id = $1", interview_id) == []
    )

    # Running again changes nothing; late chunks are refused.
    assert finalize(tenancy, storage, interview_id) == "skipped"
    refused(register(tenancy, token, paolo, attempt_id, 3), 409, "recording_finalized")
    refused(chunk_urls(tenancy, token, paolo, attempt_id, from_seq=3), 409, "recording_finalized")


def test_only_the_applying_account_uploads_to_its_own_attempts(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    paolo, maria = candidates[0], candidates[1]
    token, _ = ready(tenancy, paolo)
    attempt_id = ok(start(tenancy, token, paolo))["attempt_id"]
    other_token, _ = ready(tenancy, maria)
    other_attempt = ok(start(tenancy, other_token, maria))["attempt_id"]

    refused(chunk_urls(tenancy, token, maria, attempt_id), 404, "interview_not_found")
    refused(register(tenancy, token, maria, attempt_id, 0), 404, "interview_not_found")
    # An attempt of another interview is unknown here.
    refused(chunk_urls(tenancy, token, paolo, other_attempt), 404, "interview_attempt_not_found")
    refused(register(tenancy, token, paolo, other_attempt, 0), 404, "interview_attempt_not_found")

    # Registering before uploading, or switching type mid-attempt, is refused.
    ok(chunk_urls(tenancy, token, paolo, attempt_id))
    refused(register(tenancy, token, paolo, attempt_id, 0), 422, "recording_chunk_missing")
    refused(chunk_urls(tenancy, token, paolo, attempt_id, type="mp4"), 409,
            "recording_type_mismatch")  # fmt: skip
    over = post(tenancy, token, "chunk-urls", paolo,
                {"attempt_id": attempt_id, "type": "webm", "from_seq": 0, "count": 31})  # fmt: skip
    assert over.status_code == 422


def test_a_closed_tab_settles_after_a_quiet_spell_and_safari_attempts_join(
    tenancy: Tenancy, candidates: list[CandidateUser], storage: SupabaseStorage
) -> None:
    """A tab closed mid-interview (no `last`), then a resume in the same Safari: both attempts'
    chunks, one of them never registered, make one MP4."""
    paolo = candidates[0]
    token, interview_id = ready(tenancy, paolo)
    workspace_id = tenancy.workspace("a").id
    first = ok(start(tenancy, token, paolo))["attempt_id"]
    pieces = chunks(fragmented_mp4(3), 3)
    urls = ok(chunk_urls(tenancy, token, paolo, first, type="mp4"))["urls"]
    for url, piece in zip(urls, pieces, strict=True):
        assert upload(url["url"], piece, "video/mp4") == 200
    for seq in (0, 1):  # The tab closed before registering the last one.
        ok(register(tenancy, token, paolo, first, seq))

    second = ok(start(tenancy, token, paolo))["attempt_id"]
    urls = ok(chunk_urls(tenancy, token, paolo, second, type="mp4"))["urls"]
    for url, piece in zip(urls, chunks(fragmented_mp4(2), 3), strict=True):
        assert upload(url["url"], piece, "video/mp4") == 200
        ok(register(tenancy, token, paolo, second, url["seq"]))
    ok(post(tenancy, token, "complete", paolo, {"attempt_id": second}))

    # Neither attempt said it stopped: wait until nothing arrived for 2 minutes.
    assert due(tenancy) == []
    assert finalize(tenancy, storage, interview_id) == "waiting"
    sql(tenancy, "update recording_chunks set uploaded_at = uploaded_at - interval '3 minutes' "
                 "where interview_id = $1", interview_id)  # fmt: skip
    sql(tenancy, "update interview_attempts set ended_at = ended_at - interval '3 minutes' "
                 "where interview_id = $1", interview_id)  # fmt: skip
    assert due(tenancy) == [interview_id]

    assert finalize(tenancy, storage, interview_id) == "ready"
    row = interview(tenancy, interview_id)
    assert row["recording_path"].endswith("/recording.mp4")
    assert row["duration_seconds"] == 5
    assert set(files(storage, recording_folder(workspace_id, interview_id))) == {
        "recording.mp4",
        "audio.m4a",
        "poster.jpg",
    }


def test_a_recording_with_no_chunks_fails_once_settled(
    tenancy: Tenancy, candidates: list[CandidateUser], storage: SupabaseStorage
) -> None:
    paolo = candidates[0]
    token, interview_id = ready(tenancy, paolo)
    attempt_id = ok(start(tenancy, token, paolo))["attempt_id"]
    ok(post(tenancy, token, "complete", paolo, {"attempt_id": attempt_id}))
    sql(tenancy, "update interviews set completed_at = completed_at - interval '31 minutes' "
                 "where id = $1", interview_id)  # fmt: skip

    assert due(tenancy) == [interview_id]
    assert finalize(tenancy, storage, interview_id) == "failed"
    assert interview(tenancy, interview_id)["recording_status"] == "failed"
    assert due(tenancy) == []
