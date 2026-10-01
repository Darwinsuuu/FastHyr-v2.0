import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

JobKind = Literal["candidate_report", "pipelines_report", "resume_download", "sample"]
JobState = Literal["queued", "running", "done", "failed", "cancelled"]


class Job(BaseModel):
    """A long job's progress, polled by `JobProgressDialog` (FRONTEND.md) until it finishes."""

    id: uuid.UUID
    kind: JobKind
    status: JobState
    step: int
    steps_total: int
    # Stable error code when status is failed; never a message.
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class SampleJobRequest(BaseModel):
    """Local-only demo of the job framework: `fail_tries` makes the first tries fail."""

    steps: int = Field(default=3, ge=1, le=20)
    step_seconds: float = Field(default=1.0, ge=0, le=10)
    fail_tries: int = Field(default=0, ge=0, le=10)
