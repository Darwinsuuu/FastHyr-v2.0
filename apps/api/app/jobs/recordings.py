"""Interview recording jobs (INTV-006, MEDIA.md §3).

`finalize_recording` joins a completed interview's chunks into its recording, audio track and
poster, then deletes the chunks (`services/recordings.finalize()`), and queues the transcript
(`transcribe_interview`, INTV-008) once the recording is ready. The registration of an
interview's last chunk queues it at once; `finalize_recordings` runs every minute and queues
every recording that is due, including those whose browser closed before saying it was done and
those whose enqueue Redis lost. A run before the recording is due does nothing.
"""

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.storage import Storage
from app.interview.recording import FFMPEG_TIMEOUT_SECONDS, ffmpeg_path
from app.jobs.framework import NO_RETRY, JobRun, RetryPolicy, job
from app.services import recordings, transcripts

# Room for downloading the chunks, a re-encode in the worst case, and the uploads.
FINALIZE_TIMEOUT = timedelta(seconds=FFMPEG_TIMEOUT_SECONDS + 10 * 60)


async def _mark_failed(session: AsyncSession, error: BaseException, args: tuple[Any, ...]) -> None:
    await recordings.mark_failed(session, args[0], args[1])


@job(retry=RetryPolicy(max_tries=4, base_delay=timedelta(seconds=30)), on_failure=_mark_failed)
async def finalize_recording(run: JobRun, workspace_id: uuid.UUID, interview_id: uuid.UUID) -> str:
    storage: Storage = run.ctx["storage"]
    outcome = await recordings.finalize(
        run.session,
        storage,
        workspace_id,
        interview_id,
        ffmpeg=ffmpeg_path(get_settings().ffmpeg_path),
    )
    if outcome is recordings.Finalized.READY:
        await run.queue.enqueue(
            transcripts.TRANSCRIBE_JOB, workspace_id, interview_id, key=interview_id
        )
    return outcome.value


@job(retry=NO_RETRY)
async def finalize_recordings(run: JobRun) -> int:
    queued = 0
    for workspace_id, interview_id in await recordings.due(run.session):
        if await run.queue.enqueue(
            recordings.FINALIZE_JOB, workspace_id, interview_id, key=interview_id
        ):
            queued += 1
    return queued
