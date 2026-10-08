"""The authoritative interview transcript job (INTV-008, MEDIA.md §4).

`transcribe_interview` is queued by `finalize_recording` once the recording is ready, and again
by `requeue_stuck_work` if Redis lost it (`services/transcripts.transcribe()`). Model and network
errors are retried with backoff; after the last try the interview's `transcript_status` is
`failed`. A ready transcript queues `score_interview` (ASMT-001).
"""

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.transcription import Transcriber
from app.core.config import get_settings
from app.integrations.storage import Storage
from app.interview.recording import ffmpeg_path
from app.jobs.framework import JobRun, RetryPolicy, job
from app.services import scoring, transcripts

# Three 10-minute pieces, each taking up to a few minutes, plus the ffmpeg work.
TRANSCRIBE_TIMEOUT = timedelta(minutes=20)


async def _mark_failed(session: AsyncSession, error: BaseException, args: tuple[Any, ...]) -> None:
    await transcripts.mark_failed(session, args[0], args[1])


@job(retry=RetryPolicy(max_tries=4, base_delay=timedelta(seconds=30)), on_failure=_mark_failed)
async def transcribe_interview(
    run: JobRun, workspace_id: uuid.UUID, interview_id: uuid.UUID
) -> str:
    storage: Storage = run.ctx["storage"]
    transcriber: Transcriber = run.ctx["transcriber"]
    outcome = await transcripts.transcribe(
        run.session,
        storage,
        transcriber,
        workspace_id,
        interview_id,
        ffmpeg=ffmpeg_path(get_settings().ffmpeg_path),
    )
    if outcome is transcripts.Transcribed.READY:
        await run.queue.enqueue(scoring.SCORE_JOB, workspace_id, interview_id, key=interview_id)
    return outcome.value
