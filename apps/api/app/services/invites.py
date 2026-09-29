"""Member invites (FR-WS-03): Admins invite teammates by email with a role and departments, and
can resend or revoke pending invites. Joining with an invite is `workspaces.accept_invite`.

An invite lasts 7 days from its latest send. Resending gives it a new code and token on the same
row, so the old link and code stop working. There is one pending invite per email: inviting the
same email again replaces it.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, Role
from app.core.errors import AlreadyAMemberError, UnknownDepartmentError
from app.core.ids import new_id
from app.models import Invite
from app.repositories.audit import AuditRepository
from app.repositories.invites import InviteRepository, InviteRow, expire_overdue_invites
from app.repositories.members import MemberRepository
from app.schemas.invites import CreateInviteRequest, InviteList
from app.schemas.invites import Invite as InviteOut
from app.schemas.members import MemberDepartment

INVITE_TTL = timedelta(days=7)
# No look-alike characters (0/O, 1/I/L), so a code read aloud or retyped still works.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
# Codes are unique; a clash is astronomically rare, so try a few times rather than lock.
SAVE_ATTEMPTS = 3


def new_code() -> str:
    """`XXXX-XXXX`, the format `normalize_invite_code` accepts."""
    chars = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    return f"{chars[:4]}-{chars[4:]}"


def new_token_hash() -> tuple[str, str]:
    """A random link token and its SHA-256, the only form stored (SECURITY.md). The token goes
    in the invite email's link once FND-010 sends it; AUTH-004 accepts it."""
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


async def send_invite_email(invite: Invite, token: str) -> None:
    """FND-010 sends the member invite email (link + code, NOTIFICATIONS.md §4) from here. Until
    then the Admin copies the code from the invite dialog."""


async def list_invites(session: AsyncSession, ctx: RequestContext) -> InviteList:
    repo = InviteRepository(session, ctx.workspace_id)
    names = await repo.department_names()
    return InviteList(
        invites=[_invite(row, names) for row in await repo.list_pending(datetime.now(UTC))]
    )


async def create_invite(
    session: AsyncSession, ctx: RequestContext, body: CreateInviteRequest
) -> InviteOut:
    repo = InviteRepository(session, ctx.workspace_id)
    if await repo.is_active_member(body.email):
        raise AlreadyAMemberError()
    department_ids = await _checked_departments(session, ctx, body.role, body.department_ids)

    for attempt in range(SAVE_ATTEMPTS):
        try:
            existing = await repo.find_pending_for_email(body.email)
            invite = existing or Invite(
                id=new_id(), workspace_id=ctx.workspace_id, email=body.email
            )
            if existing is None:
                repo.add(invite)
            invite.role = body.role.value
            invite.department_ids = department_ids
            token = _issue(invite, ctx)
            await session.flush()
            break
        except IntegrityError:
            # Another request invited the same email, or the code clashed: start again.
            await session.rollback()
            if attempt == SAVE_ATTEMPTS - 1:
                raise
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action="member.invited",
        entity_type="invite",
        entity_id=invite.id,
        data={
            "role": invite.role,
            "department_ids": sorted(str(d) for d in department_ids),
            "replaced": existing is not None,
        },
    )
    await session.commit()
    await send_invite_email(invite, token)
    return await _get(repo, invite.id)


async def resend_invite(
    session: AsyncSession, ctx: RequestContext, invite_id: uuid.UUID
) -> InviteOut:
    """A new code, token and 7-day expiry; the old link and code stop working."""
    repo = InviteRepository(session, ctx.workspace_id)
    for attempt in range(SAVE_ATTEMPTS):
        try:
            invite = await repo.get_pending(invite_id, datetime.now(UTC))
            token = _issue(invite, ctx)
            await session.flush()
            break
        except IntegrityError:
            await session.rollback()
            if attempt == SAVE_ATTEMPTS - 1:
                raise
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action="member.invite_resent",
        entity_type="invite",
        entity_id=invite.id,
    )
    await session.commit()
    await send_invite_email(invite, token)
    return await _get(repo, invite.id)


async def revoke_invite(session: AsyncSession, ctx: RequestContext, invite_id: uuid.UUID) -> None:
    repo = InviteRepository(session, ctx.workspace_id)
    invite = await repo.get_pending(invite_id, datetime.now(UTC))
    invite.status = "revoked"
    AuditRepository(session, ctx.workspace_id).record(
        actor_id=ctx.user_id,
        action="member.invite_revoked",
        entity_type="invite",
        entity_id=invite.id,
    )
    await session.commit()


async def expire_invites(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Marks pending invites past their expiry as expired, in every workspace. FND-008 registers
    this as the `expire_invites` cron and commits. Accepting already refuses an invite past its
    expiry, so this keeps the table tidy and frees the email for the unique pending index.
    Returns how many invites expired."""
    return await expire_overdue_invites(session, now or datetime.now(UTC))


def _issue(invite: Invite, ctx: RequestContext) -> str:
    """Fresh code, token and expiry, sent by the caller. Returns the token for the email."""
    token, token_hash = new_token_hash()
    invite.code = new_code()
    invite.token_hash = token_hash
    invite.invited_by = ctx.user_id
    invite.expires_at = datetime.now(UTC) + INVITE_TTL
    return token


async def _checked_departments(
    session: AsyncSession, ctx: RequestContext, role: Role, department_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    if role is Role.ADMIN:
        return []  # Admins see every department
    wanted = list(dict.fromkeys(department_ids))
    existing = await MemberRepository(session, ctx.workspace_id).existing_department_ids(wanted)
    if existing != set(wanted):
        raise UnknownDepartmentError()
    return wanted


async def _get(repo: InviteRepository, invite_id: uuid.UUID) -> InviteOut:
    return _invite(await repo.get_row(invite_id), await repo.department_names())


def _invite(row: InviteRow, names: dict[uuid.UUID, str]) -> InviteOut:
    invite = row.invite
    departments = sorted(
        (MemberDepartment(id=d, name=names[d]) for d in invite.department_ids if d in names),
        key=lambda d: (d.name.lower(), d.id),
    )
    return InviteOut(
        id=invite.id,
        email=invite.email,
        role=Role(invite.role),
        departments=departments,
        code=invite.code,
        invited_by_name=row.invited_by_name,
        sent_at=invite.expires_at - INVITE_TTL,
        expires_at=invite.expires_at,
    )
