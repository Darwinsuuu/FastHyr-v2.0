"""Integrity checks (ADR-016, AI_PIPELINE.md §5): `check_integrity` is queued by
`transcribe_interview` once the transcript is ready, next to `score_interview`, and again by the
requeue_stuck_work sweeper for transcripts still unchecked after 10 minutes
(`services/integrity.check()`). Storage and model errors are retried; after the last try the
interview's `integrity_status` is `failed`. Nothing ever waits on these checks.
"""

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIClient
from app.core.config import get_settings
from app.integrations.storage import Storage
from app.interview.recording import ffmpeg_path
from app.jobs.framework import JobRun, RetryPolicy, job
from app.services import integrity

# Downloading a 30-minute recording, decoding a frame every 2 s and the model's judgement.
INTEGRITY_TIMEOUT = timedelta(minutes=20)


async def _mark_failed(session: AsyncSession, error: BaseException, args: tuple[Any, ...]) -> None:
    await integrity.mark_failed(session, args[0], args[1])


@job(retry=RetryPolicy(max_tries=3, base_delay=timedelta(seconds=30)), on_failure=_mark_failed)
async def check_integrity(run: JobRun, workspace_id: uuid.UUID, interview_id: uuid.UUID) -> str:
    storage: Storage = run.ctx["storage"]
    ai: AIClient = run.ctx["ai"]
    outcome = await integrity.check(
        run.session,
        storage,
        ai,
        run.ctx["faces"],
        workspace_id,
        interview_id,
        ffmpeg=ffmpeg_path(get_settings().ffmpeg_path),
    )
    return outcome.value
