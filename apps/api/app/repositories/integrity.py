"""Integrity flags in one workspace (ASMT-002)."""

import uuid
from collections.abc import Collection, Sequence
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import (
    AIDecision,
    Application,
    Candidate,
    IntegrityFlag,
    Interview,
    Pipeline,
    Profile,
    WorkspaceMember,
)
from app.repositories.base import WorkspaceRepository


class IntegrityFlagRepository(WorkspaceRepository[IntegrityFlag]):
    model = IntegrityFlag

    async def of_interview(self, interview_id: uuid.UUID) -> list[IntegrityFlag]:
        rows = await self.session.scalars(
            self._scoped()
            .where(IntegrityFlag.interview_id == interview_id)
            .order_by(IntegrityFlag.start_ms, IntegrityFlag.type)
        )
        return list(rows)

    def add(self, flags: Sequence[IntegrityFlag], decisions: Sequence[AIDecision]) -> None:
        """The flags and their `ai_decisions` entries, written together (FRAUD_INTEGRITY.md
        §3)."""
        scopes = [flag.workspace_id for flag in flags] + [row.workspace_id for row in decisions]
        if any(scope != self.workspace_id for scope in scopes):
            raise ValueError("integrity flag belongs to another workspace")
        self.session.add_all([*flags, *decisions])

    async def mark_flagged(self, application_id: uuid.UUID) -> None:
        """Sets the application's Flagged overlay (WORKFLOW.md §3) until a person resolves
        its flags (ASMT-003); the Candidates tab and dashboards read it."""
        await self._set_flagged(application_id, True)

    async def clear_flagged(self, application_id: uuid.UUID) -> None:
        """Clears the overlay once every flag is resolved: the application goes back under
        Ready for review or Didn't pass (ASMT-003)."""
        await self._set_flagged(application_id, False)

    async def _set_flagged(self, application_id: uuid.UUID, value: bool) -> None:
        await self.session.execute(
            update(Application)
            .where(Application.workspace_id == self.workspace_id, Application.id == application_id)
            .values(has_open_flags=value)
        )

    async def get(self, flag_id: uuid.UUID) -> IntegrityFlag:
        return await self._get_or_404(flag_id)

    async def lock_application(
        self, application_id: uuid.UUID, *, department_ids: Collection[uuid.UUID] | None
    ) -> Application:
        """The flag's application, locked so reviews of its flags run one after another; 404
        when its pipeline is outside `department_ids` (None: every department) or the
        candidate's data was deleted."""
        statement = (
            select(Application)
            .join(
                Pipeline,
                (Pipeline.workspace_id == Application.workspace_id)
                & (Pipeline.id == Application.pipeline_id),
            )
            .join(
                Candidate,
                (Candidate.workspace_id == Application.workspace_id)
                & (Candidate.id == Application.candidate_id),
            )
            .where(
                Application.workspace_id == self.workspace_id,
                Application.id == application_id,
                Candidate.deleted_at.is_(None),
            )
            .with_for_update(of=Application)
        )
        if department_ids is not None:
            # No department is Admins only (null is never in the list).
            statement = statement.where(Pipeline.department_id.in_(list(department_ids)))
        application = await self.session.scalar(statement)
        if application is None:
            raise NotFoundError()
        return application

    async def open_count(self, application_id: uuid.UUID) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(IntegrityFlag)
            .where(
                IntegrityFlag.workspace_id == self.workspace_id,
                IntegrityFlag.application_id == application_id,
                IntegrityFlag.status == "open",
            )
        )
        return count or 0


async def reviewer_names(
    session: AsyncSession, flags: Sequence[IntegrityFlag]
) -> dict[uuid.UUID, str]:
    """Who reviewed these flags: each reviewer's name, or their email without one."""
    return await member_names(
        session, {flag.resolved_by for flag in flags if flag.resolved_by is not None}
    )


async def member_names(session: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Each user's name, or their email without one."""
    if not ids:
        return {}
    rows = await session.execute(
        select(Profile.id, Profile.full_name, Profile.email).where(Profile.id.in_(ids))
    )
    return {row.id: (row.full_name or "").strip() or row.email or "" for row in rows}


async def integrity_pending_before(
    session: AsyncSession, before: datetime
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """For requeue_stuck_work: (workspace_id, interview_id) of live interviews transcribed
    before `before` and not checked yet."""
    rows = await session.execute(
        select(Interview.workspace_id, Interview.id)
        .where(
            Interview.transcript_status == "ready",
            Interview.integrity_status == "none",
            Interview.superseded_by.is_(None),
            Interview.transcribed_at < before,
        )
        .order_by(Interview.transcribed_at)
        .limit(200)
    )
    return [(row.workspace_id, row.id) for row in rows]


async def member_names_by_member(
    session: AsyncSession, member_ids: set[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """Each workspace member's name, or their email without one, by member ID."""
    if not member_ids:
        return {}
    rows = await session.execute(
        select(WorkspaceMember.id, Profile.full_name, Profile.email)
        .join(Profile, Profile.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.id.in_(member_ids))
    )
    return {row.id: (row.full_name or "").strip() or row.email or "" for row in rows}
