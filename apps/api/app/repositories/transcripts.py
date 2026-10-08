"""The live call's timeline (`interview_events`) and the authoritative transcript
(`transcript_segments`) of interviews in one workspace (INTV-008)."""

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import new_id
from app.models import Interview, InterviewEvent, TranscriptSegment
from app.repositories.base import WorkspaceRepository


class InterviewEventRepository(WorkspaceRepository[InterviewEvent]):
    model = InterviewEvent

    async def save_speech(
        self,
        interview_id: uuid.UUID,
        attempt_id: uuid.UUID,
        ref: str,
        *,
        at: datetime,
        ended_at: datetime | None,
        text: str | None,
    ) -> None:
        """Stores one interviewer response, or fills in what arrived since (its end, its
        words): the sideband writes it when the audio stops and again when the words come."""
        statement = insert(InterviewEvent).values(
            id=new_id(),
            workspace_id=self.workspace_id,
            interview_id=interview_id,
            attempt_id=attempt_id,
            kind="ai_speech",
            at=at,
            ended_at=ended_at,
            ref=ref,
            text=text,
        )
        excluded = statement.excluded
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=["attempt_id", "ref"],
                index_where=InterviewEvent.ref.is_not(None),
                set_={
                    "ended_at": excluded.ended_at,
                    "text": excluded.text,
                },
            )
        )

    def add_topic(
        self, interview_id: uuid.UUID, attempt_id: uuid.UUID, topic_index: int, at: datetime
    ) -> None:
        self.session.add(
            InterviewEvent(
                id=new_id(),
                workspace_id=self.workspace_id,
                interview_id=interview_id,
                attempt_id=attempt_id,
                kind="topic",
                at=at,
                topic_index=topic_index,
            )
        )

    async def of_interview(self, interview_id: uuid.UUID) -> list[InterviewEvent]:
        rows = await self.session.scalars(
            self._scoped()
            .where(InterviewEvent.interview_id == interview_id)
            .order_by(InterviewEvent.at, InterviewEvent.created_at)
        )
        return list(rows)


class TranscriptSegmentRepository(WorkspaceRepository[TranscriptSegment]):
    model = TranscriptSegment

    async def replace(self, interview_id: uuid.UUID, segments: list[TranscriptSegment]) -> None:
        """The interview's transcript becomes `segments` (a rerun replaces it whole)."""
        await self.session.execute(
            delete(TranscriptSegment).where(
                TranscriptSegment.workspace_id == self.workspace_id,
                TranscriptSegment.interview_id == interview_id,
            )
        )
        for segment in segments:
            if segment.workspace_id != self.workspace_id:
                raise ValueError("transcript segment belongs to another workspace")
            self.session.add(segment)

    async def of_interview(self, interview_id: uuid.UUID) -> list[TranscriptSegment]:
        rows = await self.session.scalars(
            self._scoped()
            .where(TranscriptSegment.interview_id == interview_id)
            .order_by(TranscriptSegment.seq)
        )
        return list(rows)


# Transcript statuses that still need the transcribe_interview job.
TRANSCRIPT_PENDING = ("none", "processing")


async def transcripts_pending_before(
    session: AsyncSession, before: datetime
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """For requeue_stuck_work: (workspace_id, interview_id) of ready recordings whose interview
    completed before `before` and still has no transcript."""
    rows = await session.execute(
        select(Interview.workspace_id, Interview.id)
        .where(
            Interview.recording_status == "ready",
            Interview.transcript_status.in_(TRANSCRIPT_PENDING),
            Interview.completed_at < before,
        )
        .order_by(Interview.completed_at)
        .limit(200)
    )
    return [(row.workspace_id, row.id) for row in rows]
