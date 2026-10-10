"""Integrity checks for one completed interview (ADR-016, FR-ASMT-06, MEDIA.md §5,
AI_PIPELINE.md §5), run by the `check_integrity` job once its transcript is ready (INTV-008),
alongside scoring.

`check()` runs nothing when the pipeline's "Flag possible impersonation" is off
(`integrity_status = off`). Otherwise it runs:
- the same-face check (`app/integrity/faces.py`), only on video interviews whose candidate gave
  biometric consent; frames and embeddings stay in memory and are gone with the job;
- second voice, unusual timing and read-aloud windows from the transcript
  (`app/integrity/speech.py`), the read-aloud windows judged by the model
  (`app/integrity/read_aloud.py`);
and writes, in one transaction, each flag with its `ai_decisions` entry, which checks ran
(`integrity_checks`, so the profile can say "Face check not run") and `integrity_status =
ready`. Flags carry times and a confidence and stay `open` for a person to resolve (ASMT-003):
they never move the application or reject anyone. A model that can't judge the read-aloud
windows leaves that one check `failed`; the job giving up leaves `integrity_status = failed`.
"""

import asyncio
import logging
import tempfile
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient, AIOutputError
from app.core.ids import new_id
from app.integrations.storage import Bucket, Storage
from app.integrity import faces, read_aloud, speech
from app.integrity.config import DEFAULT, RULES_VERSION, Thresholds
from app.integrity.flags import Found
from app.interview import recording
from app.interview.assessment import Line
from app.models import AIDecision, IntegrityFlag
from app.repositories import screening as screening_repo
from app.repositories.integrity import IntegrityFlagRepository, integrity_pending_before
from app.repositories.interviews import InterviewAttemptRepository
from app.repositories.screening import ScreeningRepository
from app.repositories.transcripts import TranscriptSegmentRepository
from app.screening.redact import redact_rules

logger = logging.getLogger("app.integrity")

INTEGRITY_JOB = "check_integrity"
FACE_FLAGS = ("different_face", "no_face")

FaceModelFactory = Callable[[], faces.FaceModel]


class Checked(StrEnum):
    SKIPPED = "skipped"  # not ready, already checked, or superseded
    OFF = "off"
    READY = "ready"


def _face_check(format_: str, consent: str | None, recording_path: str | None) -> str:
    if format_ == "voice_only":
        return "voice_only"
    if consent is None:
        # ADR-016: no biometric consent, no face check.
        return "no_consent"
    if recording_path is None:
        return "no_video"
    return "pending"


async def check(
    session: AsyncSession,
    storage: Storage,
    ai: AIClient,
    face_model: FaceModelFactory,
    workspace_id: uuid.UUID,
    interview_id: uuid.UUID,
    *,
    ffmpeg: str,
    thresholds: Thresholds = DEFAULT,
    now: datetime | None = None,
) -> Checked:
    """Checks the interview, once. Storage and model errors propagate for the job to retry;
    the transaction is closed while the checks run."""
    attempts = InterviewAttemptRepository(session, workspace_id)
    interview = await attempts.get_interview(interview_id)
    if (
        interview is None
        or interview.superseded_by is not None
        or interview.status != "completed"
        or interview.transcript_status != "ready"
        or interview.integrity_status != "none"
    ):
        await session.rollback()
        return Checked.SKIPPED
    application = await screening_repo.application_by_id(session, interview.application_id)
    if application is None:
        await session.rollback()
        return Checked.SKIPPED
    screening = ScreeningRepository(session, workspace_id)
    pipeline = await screening.pipeline(application.pipeline_id)
    if not pipeline.integrity_enabled:
        interview = await attempts.lock_interview(interview_id)
        if interview.integrity_status == "none":
            interview.integrity_status = "off"
            interview.integrity_checked_at = now or datetime.now(UTC)
        await session.commit()
        return Checked.OFF

    application_id = application.id
    lines = [
        Line(
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            speaker=segment.speaker,
            text=segment.text,
            topic_index=segment.topic_index,
        )
        for segment in await TranscriptSegmentRepository(session, workspace_id).of_interview(
            interview_id
        )
    ]
    attempt_starts = sorted(
        attempt.recording_offset_ms
        for attempt in await attempts.of_interview(interview_id)
        if attempt.recording_offset_ms is not None
    )
    name = await screening.candidate_name(application.candidate_id)
    face_check = _face_check(
        interview.format, interview.biometric_consent_version, interview.recording_path
    )
    recording_path = interview.recording_path
    length_ms = interview.duration_seconds * 1000 if interview.duration_seconds else None
    await session.commit()

    found: list[Found] = []
    checks: dict[str, str] = {}
    if face_check == "pending" and recording_path is not None:
        face_flags = await _faces(
            storage, recording_path, face_model, ffmpeg, thresholds, length_ms
        )
        if face_flags is None:
            face_check = "no_video"
        else:
            face_check = "ran"
            found += face_flags
    checks["face"] = face_check

    found += speech.second_voice(lines, thresholds)
    checks["second_voice"] = "ran"

    answers = speech.answers(lines, attempt_starts)
    if timing := speech.unusual_timing(answers, thresholds):
        found.append(timing)
    checks["timing"] = "ran" if speech.timing_ran(answers, thresholds) else "too_short"

    windows = speech.read_aloud_windows(answers, thresholds)
    base = speech.baseline([answer for answer in answers if answer.words >= 5])
    if windows is None or base is None:
        checks["read_aloud"] = "too_short"
    else:
        known = [name] if name else []
        try:
            found += await read_aloud.judge(
                ai,
                windows,
                base,
                mask=lambda text: redact_rules(text, known).text,
                thresholds=thresholds,
                workspace_id=workspace_id,
                entity_id=interview_id,
            )
            checks["read_aloud"] = "ran"
        except AIOutputError:
            # The other checks still count; this one is shown as not run.
            checks["read_aloud"] = "failed"
            logger.warning("read-aloud judgement failed; the other integrity checks stand")

    interview = await attempts.lock_interview(interview_id)
    if interview.integrity_status != "none" or interview.superseded_by is not None:
        await session.rollback()
        return Checked.SKIPPED
    flags: list[IntegrityFlag] = []
    decisions: list[AIDecision] = []
    for item in sorted(found, key=lambda flag: (flag.start_ms, flag.type)):
        flag = IntegrityFlag(
            id=new_id(),
            workspace_id=workspace_id,
            interview_id=interview_id,
            application_id=application_id,
            type=item.type,
            start_ms=max(0, item.start_ms),
            end_ms=max(item.start_ms, item.end_ms),
            detail=item.detail,
            confidence=Decimal(str(item.confidence)),
        )
        flags.append(flag)
        decisions.append(_decision(flag, item, ai.model))
    IntegrityFlagRepository(session, workspace_id).add(flags, decisions)
    interview.integrity_status = "ready"
    interview.integrity_checks = checks
    interview.integrity_checked_at = now or datetime.now(UTC)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return Checked.SKIPPED
    logger.info(
        "integrity checks ready: %d flags (%s)",
        len(flags),
        ", ".join(f"{key} {value}" for key, value in checks.items()),
    )
    return Checked.READY


async def _faces(
    storage: Storage,
    recording_path: str,
    face_model: FaceModelFactory,
    ffmpeg: str,
    thresholds: Thresholds,
    length_ms: int | None,
) -> list[Found] | None:
    """The face flags, or None when the recording has no video. The recording is downloaded to
    a temporary folder that is deleted with everything in it when this returns."""
    with tempfile.TemporaryDirectory(prefix="integrity-") as folder:
        video = Path(folder) / Path(recording_path).name
        await storage.download_file(Bucket.RECORDINGS, recording_path, video)
        found = await recording.probe(ffmpeg, video)
        if not found.video or found.size is None:
            return None
        if length_ms is None and found.duration:
            length_ms = round(found.duration * 1000)
        samples = await asyncio.to_thread(
            faces.scan, ffmpeg, video, found.size, face_model(), thresholds
        )
    flags = faces.analyse(samples, thresholds, end_ms=length_ms)
    del samples  # the embeddings go with the job
    return flags


def _decision(flag: IntegrityFlag, item: Found, ai_model: str) -> AIDecision:
    """The flag's `ai_decisions` entry: numbers only, never the rationale or any text."""
    if item.type == "read_aloud":
        model, version, source = ai_model, read_aloud.PROMPT_VERSION, "transcript_segments"
    elif item.type in FACE_FLAGS:
        model, version, source = faces.FACE_MODEL, RULES_VERSION, "recording"
    else:
        model, version, source = "rules", RULES_VERSION, "transcript_segments"
    output: dict[str, Any] = {
        "flag_id": str(flag.id),
        "start_ms": flag.start_ms,
        "end_ms": flag.end_ms,
        "confidence": item.confidence,
        **{key: value for key, value in item.detail.items() if key != "rationale"},
    }
    return AIDecision(
        workspace_id=flag.workspace_id,
        application_id=flag.application_id,
        type="integrity_flag",
        outcome=item.type,
        score=round(item.confidence * 100),
        threshold=None,
        model=model,
        prompt_version=version,
        input_ref=f"{source}:{flag.interview_id}",
        output=output,
    )


async def mark_failed(
    session: AsyncSession, workspace_id: uuid.UUID, interview_id: uuid.UUID
) -> None:
    """For the job's failure hook: the checks couldn't run. Nothing is flagged and nothing waits
    on them."""
    interview = await InterviewAttemptRepository(session, workspace_id).lock_interview(interview_id)
    if interview.integrity_status == "none":
        interview.integrity_status = "failed"
    await session.commit()


async def pending_before(
    session: AsyncSession, before: datetime
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """For requeue_stuck_work: transcribed interviews still waiting for their checks."""
    return await integrity_pending_before(session, before)
