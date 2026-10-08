"""INTV-008: the authoritative transcript. The sideband keeps the call's timeline, finalising the
recording records where each attempt sits in it and queues `transcribe_interview`, which turns
the diarised audio into ordered, speaker-separated, topic-placed `transcript_segments`."""

import asyncio
import json
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx2
import openai
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from websockets.asyncio.server import ServerConnection

from app.ai.transcription import FakeTranscriber, OpenAITranscriber, RawSegment
from app.core.config import Settings
from app.integrations.storage import Bucket, SupabaseStorage, recording_file_path
from app.interview.sideband import Timing
from app.jobs.queue import JobQueue
from app.services import recordings, transcripts
from tests.integration.test_applications import CandidateUser, candidates, clean_resumes, queue
from tests.integration.test_interview_sessions import (
    attempts,
    heartbeat,
    interview,
    post,
    ready,
    receive,
    run_sideband,
    start,
)
from tests.integration.test_pipelines import db_run, ok, sql
from tests.integration.test_recordings import (
    chunk_urls,
    clean_recordings,
    register,
    tenancy_app,
    upload,
)
from tests.integration.worker import drain
from tests.media_fixtures import chunks, ffmpeg, webm
from tests.tenancy.harness import Tenancy

__all__ = ["candidates", "clean_recordings", "clean_resumes", "queue", "tenancy_app"]


@pytest.fixture
def queue_name() -> str:
    return f"arq:test:{uuid.uuid4().hex[:12]}"


def segments(tenancy: Tenancy, interview_id: uuid.UUID) -> list[tuple[Any, ...]]:
    return [
        (row["seq"], row["start_ms"], row["end_ms"], row["speaker"], row["topic_index"])
        for row in sql(
            tenancy,
            "select * from transcript_segments where interview_id = $1 order by seq",
            interview_id,
        )
    ]


def record_attempt(
    tenancy: Tenancy, token: str, who: CandidateUser, seconds: float, tone: int
) -> str:
    """One connected attempt whose recording uploaded in full."""
    attempt_id: str = ok(start(tenancy, token, who))["attempt_id"]
    heartbeat(tenancy, token, who, attempt_id)
    urls = ok(chunk_urls(tenancy, token, who, attempt_id))["urls"]
    for url, piece in zip(urls, chunks(webm(seconds, tone=tone), 3), strict=True):
        assert upload(url["url"], piece) == 200
        ok(register(tenancy, token, who, attempt_id, url["seq"], last=url["seq"] == 2))
    return attempt_id


def event(
    tenancy: Tenancy,
    attempt_id: str,
    kind: str,
    after: float,
    *,
    until: float | None = None,
    text: str | None = None,
    topic: int | None = None,
) -> None:
    """An interview_events row `after` seconds into the attempt's connection."""
    sql(
        tenancy,
        "insert into interview_events (workspace_id, interview_id, attempt_id, kind, at, "
        "ended_at, ref, text, topic_index) select workspace_id, interview_id, id, $2, "
        "connected_at + make_interval(secs => $3), "
        "connected_at + make_interval(secs => $4), $5, $6, $7 "
        "from interview_attempts where id = $1",
        uuid.UUID(attempt_id),
        kind,
        after,
        until,
        f"resp_{uuid.uuid4().hex[:8]}" if kind == "ai_speech" else None,
        text,
        topic,
    )


def test_a_finished_recording_becomes_its_transcript(
    tenancy: Tenancy,
    candidates: list[CandidateUser],
    storage: SupabaseStorage,
    redis_url: str,
    queue_name: str,
) -> None:
    """Two attempts (a resume) recorded 3 s and 2 s; a third voice speaks in the first."""
    paolo = candidates[0]
    token, interview_id = ready(tenancy, paolo)
    workspace_id = tenancy.workspace("a").id
    first = record_attempt(tenancy, token, paolo, 3, 440)
    second = record_attempt(tenancy, token, paolo, 2, 660)
    ok(post(tenancy, token, "complete", paolo, {"attempt_id": second}))

    greeting = "Hi, I'm the AI interviewer. Thanks for making time today."
    question = "Welcome back. Your résumé mentions Kubernetes. How did you choose what to move?"
    event(tenancy, first, "ai_speech", 0.0, until=1.3, text=greeting)
    event(tenancy, second, "topic", 0.05, topic=2)
    event(tenancy, second, "ai_speech", 0.1, until=1.0, text=question)
    heard = [
        RawSegment(0.1, 1.2, "A", greeting),
        RawSegment(1.3, 2.2, "B", "Hello, thanks for having me."),
        RawSegment(2.3, 2.8, "C", "Is that the interviewer?"),
        RawSegment(3.1, 4.0, "A", question),
        RawSegment(4.1, 4.9, "B", "We started with the stateless services."),
    ]
    transcriber = FakeTranscriber(segments=[heard])

    async def enqueue() -> None:
        jobs = JobQueue(redis_url, queue_name=queue_name)
        try:
            await jobs.enqueue(
                recordings.FINALIZE_JOB, workspace_id, interview_id, key=interview_id
            )
        finally:
            await jobs.close()

    asyncio.run(enqueue())
    drain(redis_url, queue_name, storage=storage, transcriber=transcriber)

    row = interview(tenancy, interview_id)
    assert (row["recording_status"], row["transcript_status"]) == ("ready", "ready")
    assert row["transcribed_at"] is not None
    offsets = [a["recording_offset_ms"] for a in attempts(tenancy, interview_id)]
    lengths = [a["recording_ms"] for a in attempts(tenancy, interview_id)]
    assert offsets == [0, lengths[0]]
    assert lengths[0] == pytest.approx(3000, abs=100) and lengths[1] == pytest.approx(2000, abs=100)
    # One call for the whole 5 s.
    assert transcriber.calls == [pytest.approx(5, abs=0.2)]

    assert segments(tenancy, interview_id) == [
        (0, 100, 1200, "interviewer", 0),
        (1, 1300, 2200, "candidate", 0),
        (2, 2300, 2800, "other", 0),
        (3, 3100, 4000, "interviewer", 2),
        (4, 4100, 4900, "candidate", 2),
    ]
    # Full-text search over the transcript.
    [found] = sql(
        tenancy,
        "select seq from transcript_segments where interview_id = $1 and "
        "to_tsvector('english', text) @@ plainto_tsquery('english', 'kubernetes')",
        interview_id,
    )
    assert found["seq"] == 3

    # A rerun changes nothing.
    async def again(session: AsyncSession) -> str:
        outcome = await transcripts.transcribe(
            session, storage, transcriber, workspace_id, interview_id, ffmpeg=ffmpeg()
        )
        return outcome.value

    assert db_run(tenancy, again) == "skipped"
    assert len(segments(tenancy, interview_id)) == 5


def silent_gap_audio(seconds: int, gap: tuple[int, int]) -> bytes:
    """Mono AAC tone with silence between `gap` seconds, as audio.m4a."""
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "audio.m4a"
        subprocess.run(
            [
                ffmpeg(), "-v", "error", "-y",
                "-f", "lavfi", "-i", f"sine=frequency=300:sample_rate=16000:duration={seconds}",
                "-af", f"volume=enable='between(t,{gap[0]},{gap[1]})':volume=0",
                "-ac", "1", "-c:a", "aac", "-b:a", "32k", str(out),
            ],
            check=True,
        )  # fmt: skip
        return out.read_bytes()


def test_long_audio_is_cut_at_a_silence_and_merged_back(
    tenancy: Tenancy, candidates: list[CandidateUser], storage: SupabaseStorage
) -> None:
    paolo = candidates[0]
    token, interview_id = ready(tenancy, paolo)
    workspace_id = tenancy.workspace("a").id
    attempt_id = ok(start(tenancy, token, paolo))["attempt_id"]
    ok(post(tenancy, token, "complete", paolo, {"attempt_id": attempt_id}))
    # A 700 s recording made elsewhere (its attempt left out: no place to put topics in).
    asyncio.run(
        storage.upload(
            Bucket.RECORDINGS,
            recording_file_path(workspace_id, interview_id, "audio.m4a"),
            silent_gap_audio(700, (399, 401)),
            content_type="audio/mp4",
            upsert=True,
        )
    )
    sql(
        tenancy,
        "update interviews set recording_status = 'ready', "
        "completed_at = now() - interval '11 minutes' where id = $1",
        interview_id,
    )

    # Redis lost the job: requeue_stuck_work finds it.
    async def pending(session: AsyncSession) -> list[tuple[uuid.UUID, uuid.UUID]]:
        return await transcripts.pending_before(session, datetime.now(UTC) - timedelta(minutes=10))

    assert (workspace_id, interview_id) in db_run(tenancy, pending)

    transcriber = FakeTranscriber(
        segments=[
            [
                RawSegment(10.0, 12.0, "A", "Tell me about your current role?"),
                RawSegment(13.0, 20.0, "B", "I lead a platform team."),
            ],
            [
                RawSegment(5.0, 7.0, "B", "What would you change next time?"),
                RawSegment(8.0, 15.0, "A", "I would move the databases first."),
            ],
        ]
    )

    async def work(session: AsyncSession) -> str:
        outcome = await transcripts.transcribe(
            session, storage, transcriber, workspace_id, interview_id, ffmpeg=ffmpeg()
        )
        return outcome.value

    assert db_run(tenancy, work) == "ready"
    # Cut in the middle of the silence at 400 s, each piece with 2 s of overlap.
    assert transcriber.calls == [pytest.approx(402, abs=0.5), pytest.approx(302, abs=0.5)]
    found = segments(tenancy, interview_id)
    assert [(seq, speaker, topic) for seq, _, _, speaker, topic in found] == [
        (0, "interviewer", None),
        (1, "candidate", None),
        (2, "interviewer", None),
        (3, "candidate", None),
    ]
    # The second piece's times are on the recording's clock (it was sent from about 398 s).
    starts = [start for _, start, _, _, _ in found]
    assert starts[:2] == [10_000, 13_000]
    assert starts[2:] == [pytest.approx(403_000, abs=100), pytest.approx(406_000, abs=100)]
    assert (workspace_id, interview_id) not in db_run(tenancy, pending)


def test_a_transcript_that_cannot_be_made_is_marked_failed(
    tenancy: Tenancy, candidates: list[CandidateUser], storage: SupabaseStorage
) -> None:
    paolo = candidates[0]
    _, interview_id = ready(tenancy, paolo)
    workspace_id = tenancy.workspace("a").id

    async def fail(session: AsyncSession) -> None:
        await transcripts.mark_failed(session, workspace_id, interview_id)

    db_run(tenancy, fail)
    sql(tenancy, "update interviews set recording_status = 'ready' where id = $1", interview_id)
    assert interview(tenancy, interview_id)["transcript_status"] == "failed"

    async def work(session: AsyncSession) -> str:
        outcome = await transcripts.transcribe(
            session, storage, FakeTranscriber(), workspace_id, interview_id, ffmpeg=ffmpeg()
        )
        return outcome.value

    assert db_run(tenancy, work) == "skipped"


def test_the_sideband_keeps_the_calls_timeline(
    tenancy: Tenancy, candidates: list[CandidateUser]
) -> None:
    paolo = candidates[0]
    token, interview_id = ready(tenancy, paolo)
    session = ok(start(tenancy, token, paolo))
    heartbeat(tenancy, token, paolo, session["attempt_id"])
    workspace_id = interview(tenancy, interview_id)["workspace_id"]

    async def script(ws: ServerConnection, seen: list[dict[str, Any]]) -> None:
        for _ in range(3):  # session.update, opening, response.create
            await receive(ws, seen)
        # The greeting: audio starts, its words arrive, audio stops.
        for kind in (
            "output_audio_buffer.started",
            "response.output_audio_transcript.done",
            "output_audio_buffer.stopped",
        ):
            await ws.send(
                json.dumps(
                    {
                        "type": kind,
                        "response_id": "resp_1",
                        "transcript": " Hi, I'm the AI interviewer. ",
                    }
                )
            )
            await asyncio.sleep(0.05)  # fmt: skip
        await ws.send(json.dumps({"type": "response.function_call_arguments.done",
                                  "name": "set_topic", "call_id": "c1",
                                  "arguments": '{"number": 2}'}))  # fmt: skip
        await receive(ws, seen)
        # A response cut off by the end: its first words only.
        await ws.send(json.dumps({"type": "response.output_audio_transcript.delta",
                                  "response_id": "resp_2", "delta": "Thanks"}))  # fmt: skip
        await ws.send(json.dumps({"type": "response.function_call_arguments.done",
                                  "name": "end_interview", "call_id": "c2",
                                  "arguments": '{"reason": "completed"}'}))  # fmt: skip
        await receive(ws, seen)
        await ws.send(json.dumps({"type": "output_audio_buffer.stopped"}))

    reason, _, _, _ = run_sideband(tenancy, workspace_id, session["attempt_id"], script, Timing())
    assert reason == "wrap_up"
    rows = sql(
        tenancy,
        "select * from interview_events where interview_id = $1 order by at",
        interview_id,
    )
    assert [(r["kind"], r["ref"], r["text"], r["topic_index"]) for r in rows] == [
        ("ai_speech", "resp_1", "Hi, I'm the AI interviewer.", None),
        ("topic", None, None, 1),
        ("ai_speech", "resp_2", None, None),
    ]
    greeting, _, cut_off = rows
    assert greeting["ended_at"] > greeting["at"]
    assert cut_off["ended_at"] is None


def test_the_openai_transcriber_asks_for_speakers_and_logs_the_call(tenancy: Tenancy) -> None:
    requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(
            200,
            json={
                "task": "transcribe",
                "duration": 30.0,
                "text": "Hello. Hi.",
                "segments": [
                    {"type": "transcript.text.segment", "id": "s1", "start": 0.5, "end": 1.5,
                     "speaker": "A", "text": " Hello. "},
                    {"type": "transcript.text.segment", "id": "s2", "start": 2.0, "end": 2.6,
                     "speaker": "B", "text": "Hi."},
                ],
                "usage": {"type": "duration", "seconds": 30.0},
            },
        )  # fmt: skip

    entity_id = uuid.uuid4()

    async def main() -> list[RawSegment]:
        url = tenancy.supabase.database_url.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(url)
        try:
            settings = Settings(
                openai_transcribe_model="tx-test", openai_prices={"tx-test": {"per_minute": 0.006}}
            )
            client = openai.AsyncOpenAI(
                api_key="sk-test",
                http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
            )
            transcriber = OpenAITranscriber(
                settings, async_sessionmaker(engine, expire_on_commit=False), client=client
            )
            with tempfile.TemporaryDirectory() as folder:
                audio = Path(folder) / "audio.m4a"
                audio.write_bytes(b"not really audio")
                result = await transcriber.transcribe(
                    audio, duration=30.0, workspace_id=tenancy.workspace("a").id,
                    entity_id=entity_id,
                )  # fmt: skip
            return result.segments
        finally:
            await engine.dispose()

    assert asyncio.run(main()) == [
        RawSegment(0.5, 1.5, "A", "Hello."),
        RawSegment(2.0, 2.6, "B", "Hi."),
    ]
    [request] = requests
    assert request.url.path == "/v1/audio/transcriptions"
    body = request.content.decode("utf-8", "replace")
    for field, value in (
        ("model", "tx-test"),
        ("response_format", "diarized_json"),
        ("chunking_strategy", "auto"),
    ):
        assert f'name="{field}"\r\n\r\n{value}\r\n' in body
    [call] = sql(tenancy, "select * from ai_calls where entity_id = $1", entity_id)
    assert (call["purpose"], call["prompt_version"], call["status"]) == (
        "interview_transcription",
        "transcription@v1",
        "ok",
    )
    assert float(call["audio_seconds"]) == 30.0
    assert float(call["cost_usd"]) == pytest.approx(0.003)
