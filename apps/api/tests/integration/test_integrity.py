"""ASMT-002: a transcribed interview's integrity checks run in the real worker. Flags carry
times and confidence and leave the application where scoring put it; the pipeline's toggle off
runs nothing; no biometric consent skips the face check; nothing but flag rows is stored; the
sweeper picks up a lost job.

The recording is synthetic: solid-colour scenes stand in for faces, and a colour face model
plays the part of the local face model (whose real behaviour `tests/unit/test_integrity_faces.py`
covers)."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pytest
from pydantic import BaseModel

from app.ai import fakes
from app.ai.prompts import Prompt
from app.ai.schemas.integrity_read_aloud import ReadAloudJudgement
from app.integrations.storage import Bucket, SupabaseStorage, recording_file_path
from app.integrity.faces import Embedding, Frame
from app.jobs.queue import JobQueue
from app.services import integrity
from tests.integration.test_applications import CandidateUser, candidates, clean_resumes, queue
from tests.integration.test_emails import FakeSender
from tests.integration.test_interview_sessions import interview, ready, realtime, tenancy_app
from tests.integration.test_pipelines import sql
from tests.integration.test_post_screen import owner_sql, sweep
from tests.integration.test_recordings import clean_recordings
from tests.integration.worker import drain
from tests.media_fixtures import scenes
from tests.tenancy.harness import Tenancy

__all__ = [
    "candidates",
    "clean_recordings",
    "clean_resumes",
    "queue",
    "realtime",
    "tenancy_app",
]

# The candidate (red) for 40 s, nobody for 24 s, someone else (blue) for 8 s, the candidate.
VIDEO = (("red", 40), ("black", 24), ("blue", 8), ("red", 18))
LONG_ANSWER = (
    "Firstly, a distributed cache improves read latency by keeping frequently accessed data "
    "close to the application. Secondly, it reduces load on the primary database, which "
    "improves overall throughput. Thirdly, cache invalidation must be handled with care, "
    "using time to live values and explicit eviction on writes. In conclusion, caching is a "
    "trade-off between freshness and speed."
)
# start s, end s, speaker, text: five quick answers, then two after long pauses (one long and
# even, the read-aloud pattern), and a second voice for 4 s.
LINES = [
    (0, 3, "interviewer", "Hi, thanks for joining. Tell me about your current role."),
    (4, 9, "candidate", "I'm Paolo Reyes and I build payment systems at a fintech."),
    (10, 13, "interviewer", "What does your team own?"),
    (14, 18, "candidate", "We own the ledger and the payouts service for merchants."),
    (19, 22, "interviewer", "How do you deploy?"),
    (23, 27, "candidate", "Small changes behind flags, rolled out over a day."),
    (28, 30, "interviewer", "How do you test?"),
    (31, 35, "candidate", "Unit tests, contract tests and a staging soak."),
    (36, 39, "interviewer", "Who reviews your code?"),
    (40, 44, "candidate", "Two teammates, one from the owning team."),
    (45, 48, "interviewer", "How would you speed up reads with a cache?"),
    (58, 72, "candidate", LONG_ANSWER[:190]),
    (72, 86, "candidate", LONG_ANSWER[190:]),
    (87, 89, "other", "Say the part about invalidation."),
    (90, 92, "other", "And the trade-off."),
    (93, 96, "interviewer", "What is the hardest bug you fixed?"),
    (106, 112, "candidate", "A race in the ledger writes that we fixed with row locks."),
]


class ColourFaces:
    """Red is the candidate, blue someone else, dark frames have no face."""

    name = "colour"
    made = 0

    def __init__(self) -> None:
        ColourFaces.made += 1

    def embed(self, frame: Frame) -> Embedding | None:
        blue, _, red = (float(channel) for channel in frame.reshape(-1, 3).mean(axis=0))
        if max(blue, red) < 60:
            return None
        vector = np.zeros(128, dtype=np.float32)
        vector[0 if red > blue else 1] = 1.0
        return vector


class ReadAloudAI:
    """Judges the first read-aloud window read aloud with `confidence`."""

    model = "stub"

    def __init__(self, confidence: float = 0.8) -> None:
        self.confidence = confidence
        self.seen: list[dict[str, str]] = []

    async def structured[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt: Prompt,
        variables: dict[str, str],
        schema: type[T],
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        temperature: float | None = None,
    ) -> T:
        assert schema is ReadAloudJudgement
        self.seen.append(variables)
        answer = fakes.integrity_read_aloud(variables)
        answer["windows"][0].update(
            read_aloud=True, confidence=self.confidence, rationale="Even, essay-like delivery."
        )
        return schema.model_validate(answer)


@pytest.fixture
def queue_name() -> str:
    return f"arq:test:{uuid.uuid4().hex[:12]}"


def transcribed(
    tenancy: Tenancy,
    storage: SupabaseStorage,
    candidate: CandidateUser,
    *,
    biometric: bool = True,
    ago: timedelta = timedelta(0),
) -> uuid.UUID:
    """A completed video interview with its recording and transcript ready, scored ready for
    review."""
    _, interview_id = ready(tenancy, candidate)
    workspace_id = tenancy.workspace("a").id
    path = recording_file_path(workspace_id, interview_id, "recording.webm")
    asyncio.run(storage.upload(Bucket.RECORDINGS, path, scenes(VIDEO), content_type="video/webm"))
    completed = datetime.now(UTC) - ago
    sql(
        tenancy,
        "update interviews set status = 'completed', started_at = $2, completed_at = $3, "
        "recording_status = 'ready', recording_path = $4, duration_seconds = 90, "
        "transcript_status = 'ready', transcribed_at = $3, assessment_status = 'ready', "
        "biometric_consent_version = $5 where id = $1",
        interview_id,
        completed - timedelta(minutes=20),
        completed,
        path,
        "biometric@v1" if biometric else None,
    )
    sql(
        tenancy,
        "update applications set stage = 'ready_for_review' "
        "where id = (select application_id from interviews where id = $1)",
        interview_id,
    )
    for seq, (start, end, speaker, text) in enumerate(LINES):
        sql(
            tenancy,
            "insert into transcript_segments (workspace_id, interview_id, seq, start_ms, end_ms, "
            "speaker, text, topic_index) values ($1, $2, $3, $4, $5, $6, $7, 1)",
            workspace_id,
            interview_id,
            seq,
            start * 1000,
            end * 1000,
            speaker,
            text,
        )
    return interview_id


def check(
    tenancy: Tenancy,
    storage: SupabaseStorage,
    interview_id: uuid.UUID,
    redis_url: str,
    queue_name: str,
    ai: Any,
) -> None:
    async def main() -> None:
        queue = JobQueue(redis_url, queue_name=queue_name)
        try:
            await queue.enqueue(
                integrity.INTEGRITY_JOB, tenancy.workspace("a").id, interview_id, key=interview_id
            )
        finally:
            await queue.close()

    asyncio.run(main())
    run_worker(redis_url, queue_name, storage, ai)


def run_worker(redis_url: str, queue_name: str, storage: SupabaseStorage, ai: Any) -> None:
    drain(
        redis_url, queue_name, storage=storage, ai=ai, faces=ColourFaces, email_sender=FakeSender()
    )


def flags(tenancy: Tenancy, interview_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = sql(
        tenancy,
        "select * from integrity_flags where interview_id = $1 order by start_ms, type",
        interview_id,
    )
    return [{**row, "detail": json.loads(row["detail"])} for row in rows]


def decisions(tenancy: Tenancy, interview_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = sql(
        tenancy,
        "select * from ai_decisions where type = 'integrity_flag' and application_id = "
        "(select application_id from interviews where id = $1) order by created_at",
        interview_id,
    )
    return [{**row, "output": json.loads(row["output"])} for row in rows]


def test_flags_mark_the_moments_with_times_and_confidence(
    tenancy: Tenancy,
    storage: SupabaseStorage,
    candidates: list[CandidateUser],
    redis_url: str,
    queue_name: str,
) -> None:
    interview_id = transcribed(tenancy, storage, candidates[0])
    ai = ReadAloudAI()
    check(tenancy, storage, interview_id, redis_url, queue_name, ai)

    found = flags(tenancy, interview_id)
    assert [(row["type"], row["start_ms"], row["end_ms"]) for row in found] == [
        ("no_face", 40_000, 64_000),
        ("unusual_timing", 48_000, 106_000),
        ("read_aloud", 58_000, 86_000),
        ("different_face", 64_000, 72_000),
        ("second_voice", 87_000, 92_000),
    ]
    for row in found:
        assert 0 < row["confidence"] < 1
        assert (row["status"], row["resolved_at"]) == ("open", None)
    by_type = {row["type"]: row for row in found}
    assert by_type["no_face"]["detail"] == {"seconds": 24, "samples": 12}
    assert by_type["different_face"]["detail"]["samples"] == 4
    assert by_type["second_voice"]["detail"] == {"seconds": 4.0, "segments": 2}
    assert [late["delay_ms"] for late in by_type["unusual_timing"]["detail"]["late"]] == [
        10_000,
        10_000,
    ]
    assert by_type["read_aloud"]["detail"]["rationale"] == "Even, essay-like delivery."
    # The model saw the long answer, masked, and never the name.
    [seen] = ai.seen
    assert "Window 1" in seen["windows"] and "Window 2" not in seen["windows"]
    assert "Paolo" not in json.dumps(ai.seen)

    row = interview(tenancy, interview_id)
    assert row["integrity_status"] == "ready"
    assert json.loads(row["integrity_checks"]) == {
        "face": "ran",
        "second_voice": "ran",
        "timing": "ran",
        "read_aloud": "ran",
    }
    # Flags never move the application: a person resolves them.
    assert row["stage"] == "ready_for_review"

    logged = decisions(tenancy, interview_id)
    assert sorted(entry["outcome"] for entry in logged) == sorted(by_type)
    for entry in logged:
        assert entry["output"]["flag_id"] in {str(flag["id"]) for flag in found}
        assert "rationale" not in entry["output"]
    models = {entry["outcome"]: (entry["model"], entry["prompt_version"]) for entry in logged}
    assert models["read_aloud"] == ("stub", "integrity_read_aloud@v1")
    assert models["no_face"][1] == "integrity_rules@v1"

    # A repeat changes nothing.
    check(tenancy, storage, interview_id, redis_url, queue_name, ReadAloudAI())
    assert len(flags(tenancy, interview_id)) == len(found)


def test_the_toggle_off_runs_no_checks(
    tenancy: Tenancy,
    storage: SupabaseStorage,
    candidates: list[CandidateUser],
    redis_url: str,
    queue_name: str,
) -> None:
    interview_id = transcribed(tenancy, storage, candidates[0])
    owner_sql(
        tenancy,
        "update pipelines set integrity_enabled = false where id = "
        "(select pipeline_id from applications a join interviews i on i.application_id = a.id "
        "where i.id = $1)",
        interview_id,
    )
    made = ColourFaces.made
    ai = ReadAloudAI()
    check(tenancy, storage, interview_id, redis_url, queue_name, ai)

    assert flags(tenancy, interview_id) == []
    assert decisions(tenancy, interview_id) == []
    row = interview(tenancy, interview_id)
    assert (row["integrity_status"], row["integrity_checks"]) == ("off", None)
    assert row["integrity_checked_at"] is not None
    assert ColourFaces.made == made and ai.seen == []


def test_no_biometric_consent_skips_the_face_check_only(
    tenancy: Tenancy,
    storage: SupabaseStorage,
    candidates: list[CandidateUser],
    redis_url: str,
    queue_name: str,
) -> None:
    interview_id = transcribed(tenancy, storage, candidates[0], biometric=False)
    made = ColourFaces.made
    check(tenancy, storage, interview_id, redis_url, queue_name, ReadAloudAI(confidence=0.5))

    types = [row["type"] for row in flags(tenancy, interview_id)]
    # The model wasn't sure enough to flag the read-aloud window.
    assert types == ["unusual_timing", "second_voice"]
    checks = json.loads(interview(tenancy, interview_id)["integrity_checks"])
    assert checks["face"] == "no_consent"
    assert ColourFaces.made == made


def test_the_sweeper_requeues_unchecked_interviews(
    tenancy: Tenancy,
    storage: SupabaseStorage,
    candidates: list[CandidateUser],
    redis_url: str,
    queue_name: str,
) -> None:
    lost = transcribed(tenancy, storage, candidates[0], ago=timedelta(minutes=30))
    assert sweep(redis_url, queue_name) >= 1
    run_worker(redis_url, queue_name, storage, ReadAloudAI())
    assert interview(tenancy, lost)["integrity_status"] == "ready"
