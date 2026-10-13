"""Reviewing integrity flags (ASMT-003, FR-ASMT-06, FRAUD_INTEGRITY.md §3).

A person listens to the flagged moments and marks each flag No concern or Concern confirmed with
a note. Neither changes the stage: confirming a concern never rejects anyone, the team still
chooses Advance or Reject. Once an application has no open flags it leaves the Flagged filter
for Ready for review or Didn't pass. Every review goes to `audit_log` (never the note, which may
describe the person).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext
from app.models import IntegrityFlag
from app.repositories.audit import AuditRepository
from app.repositories.integrity import IntegrityFlagRepository, reviewer_names
from app.repositories.pipeline_candidates import FLAGGABLE_STAGES
from app.schemas.application_profile import IntegrityFlag as FlagResult
from app.schemas.integrity_flags import FlaggedApplication, ResolvedFlag, ResolveFlagRequest


def flag_result(flag: IntegrityFlag, reviewers: dict[uuid.UUID, str]) -> FlagResult:
    return FlagResult(
        id=flag.id,
        type=flag.type,
        start_ms=flag.start_ms,
        end_ms=flag.end_ms,
        confidence=float(flag.confidence),
        status=flag.status,
        resolved_at=flag.resolved_at,
        resolved_by=reviewers.get(flag.resolved_by) if flag.resolved_by else None,
        note=flag.resolution_note,
    )


async def resolve(
    session: AsyncSession, ctx: RequestContext, flag_id: uuid.UUID, body: ResolveFlagRequest
) -> ResolvedFlag:
    """Records the review. A reviewed flag can be reviewed again; it never reopens. A flag in
    another workspace, outside the caller's departments, or on deleted candidate data is 404."""
    repo = IntegrityFlagRepository(session, ctx.workspace_id)
    flag = await repo.get(flag_id)
    application = await repo.lock_application(
        flag.application_id,
        department_ids=None if ctx.sees_all_departments else ctx.department_ids,
    )
    # Re-read under the application's lock: another review may have just landed.
    await session.refresh(flag)
    previous = flag.status
    flag.status = body.status
    flag.resolution_note = body.note
    flag.resolved_by = ctx.user_id
    flag.resolved_at = datetime.now(UTC)
    await session.flush()

    open_flags = await repo.open_count(application.id)
    if open_flags == 0 and application.has_open_flags:
        await repo.clear_flagged(application.id)
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action="integrity_flag.resolved",
        entity_type="integrity_flag",
        entity_id=flag.id,
        data={
            "application_id": str(application.id),
            "type": flag.type,
            "from": previous,
            "to": flag.status,
        },
    )
    result = ResolvedFlag(
        flag=flag_result(flag, await reviewer_names(session, [flag])),
        application=FlaggedApplication(
            id=application.id,
            flagged=open_flags > 0 and application.stage in FLAGGABLE_STAGES,
            open_flags=open_flags,
        ),
    )
    await session.commit()
    return result
