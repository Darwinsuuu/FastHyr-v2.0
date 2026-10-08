"""The authoritative interview transcript (INTV-008, FR-ASMT-01, MEDIA.md §4).

Once an interview's recording is ready, the `transcribe_interview` job (`transcribe()`) reads its
`audio.m4a`, cuts audio longer than 10 minutes at silences, sends each piece to the
transcription model with speaker separation, and turns the answer into `transcript_segments`:
timed against the recording, each line `interviewer`, `candidate` or `other`, and placed in a
plan topic (`app/interview/transcript.py`). Scoring (ASMT-001) and integrity checks (ASMT-002)
read it; live captions are never used for either (ADR-007).

`transcript_status`: `none` → `processing` → `ready`, or `failed` after the job's last try.
A rerun replaces the transcript whole.
"""

import logging
import tempfile
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.transcription import Transcriber
from app.core.ids import new_id
from app.integrations.storage import Bucket, Storage, recording_file_path
from app.interview import recording, transcript
from app.models import InterviewAttempt, TranscriptSegment
from app.repositories.interviews import InterviewAttemptRepository
from app.repositories.transcripts import (
    InterviewEventRepository,
    TranscriptSegmentRepository,
    transcripts_pending_before,
)

logger = logging.getLogger("app.transcript")

TRANSCRIBE_JOB = "transcribe_interview"
AUDIO_FILE = "audio.m4a"


class Transcribed(StrEnum):
    READY = "ready"
    SKIPPED = "skipped"


async def transcribe(
    session: AsyncSession,
    storage: Storage,
    transcriber: Transcriber,
    workspace_id: uuid.UUID,
    interview_id: uuid.UUID,
    *,
    ffmpeg: str,
    now: datetime | None = None,
) -> Transcribed:
    """Makes the interview's transcript. Skips an interview whose recording isn't ready or
    whose transcript already is. Model and network errors propagate so the job retries."""
    attempts = InterviewAttemptRepository(session, workspace_id)
    interview = await attempts.get_interview(interview_id)
    if (
        interview is None
        or interview.recording_status != "ready"
        or interview.transcript_status in ("ready", "failed")
    ):
        await session.rollback()
        return Transcribed.SKIPPED
    interview = await attempts.lock_interview(interview_id)
    interview.transcript_status = "processing"
    spans = _spans(await attempts.of_interview(interview_id))
    events = [
        transcript.CallEvent(
            attempt_id=event.attempt_id,
            kind=event.kind,
            at=event.at,
            ended_at=event.ended_at,
            text=event.text,
            topic_index=event.topic_index,
        )
        for event in await InterviewEventRepository(session, workspace_id).of_interview(
            interview_id
        )
    ]
    await session.commit()

    with tempfile.TemporaryDirectory(prefix="transcript-") as folder:
        workdir = Path(folder)
        audio = workdir / AUDIO_FILE
        audio.write_bytes(
            await storage.download(
                Bucket.RECORDINGS, recording_file_path(workspace_id, interview_id, AUDIO_FILE)
            )
        )
        found = await recording.probe(ffmpeg, audio)
        duration = found.duration or 0.0
        pieces = transcript.plan_pieces(
            duration,
            await recording.silences(ffmpeg, audio)
            if duration > transcript.MAX_PIECE_SECONDS
            else [],
        )
        answers = []
        for index, piece in enumerate(pieces):
            path = audio
            if len(pieces) > 1:
                path = await recording.cut(
                    ffmpeg, audio, piece.start, piece.end, workdir / f"piece-{index}.m4a"
                )
            result = await transcriber.transcribe(
                path, duration=piece.length, workspace_id=workspace_id, entity_id=interview_id
            )
            answers.append(result.segments)

    lines = transcript.build(transcript.merge(pieces, answers), spans, events)
    segments = [
        TranscriptSegment(
            id=new_id(),
            workspace_id=workspace_id,
            interview_id=interview_id,
            seq=seq,
            start_ms=line.start_ms,
            end_ms=line.end_ms,
            speaker=line.speaker,
            text=line.text,
            topic_index=line.topic_index,
        )
        for seq, line in enumerate(lines)
    ]
    interview = await attempts.lock_interview(interview_id)
    if interview.recording_status != "ready":
        await session.rollback()
        return Transcribed.SKIPPED
    await TranscriptSegmentRepository(session, workspace_id).replace(interview_id, segments)
    interview.transcript_status = "ready"
    interview.transcribed_at = now or datetime.now(UTC)
    await session.commit()
    logger.info("interview transcript ready (%d segments)", len(segments))
    return Transcribed.READY


def _spans(attempts: list[InterviewAttempt]) -> list[transcript.AttemptSpan]:
    """The attempts that are in the recording, in recording order."""
    spans = [
        transcript.AttemptSpan(
            attempt_id=attempt.id,
            offset_ms=attempt.recording_offset_ms,
            length_ms=attempt.recording_ms or 0,
            origin=attempt.connected_at or attempt.started_at,
            resume_from=attempt.resume_from,
        )
        for attempt in attempts
        if attempt.recording_offset_ms is not None
    ]
    return sorted(spans, key=lambda span: span.offset_ms)


async def mark_failed(
    session: AsyncSession, workspace_id: uuid.UUID, interview_id: uuid.UUID
) -> None:
    """For the job's failure hook: the transcript couldn't be made."""
    attempts = InterviewAttemptRepository(session, workspace_id)
    interview = await attempts.lock_interview(interview_id)
    if interview.transcript_status != "ready":
        interview.transcript_status = "failed"
    await session.commit()


async def pending_before(
    session: AsyncSession, before: datetime
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """For requeue_stuck_work: ready recordings still waiting for their transcript."""
    return await transcripts_pending_before(session, before)
