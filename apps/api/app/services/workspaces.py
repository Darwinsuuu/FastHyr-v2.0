"""Creating a workspace, joining one with an invite code or link, and remembering the active one
(FR-AUTH-04 to FR-AUTH-06)."""

import hashlib
import re
import unicodedata
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.context import Role
from app.core.errors import (
    InviteExpiredError,
    InviteInvalidError,
    InviteNotFoundError,
    InviteWrongEmailError,
    NotFoundError,
)
from app.models import Invite, Workspace
from app.repositories.users import UserRepository
from app.repositories.workspaces import WorkspaceSetupRepository
from app.schemas.me import MyWorkspace
from app.schemas.workspaces import InvitePreview, InviteState
from app.services import credits, email_templates
from app.services.me import to_my_workspace

SLUG_MAX = 63
# Leaves room for a "-<n>" suffix within SLUG_MAX.
SLUG_BASE_MAX = 56
SLUG_FALLBACK = "workspace"
# Another request can take the same slug between our read and our insert; try again.
CREATE_ATTEMPTS = 3


def slugify(name: str) -> str:
    """A URL-safe slug for apply links: lowercase ASCII letters and digits joined by single
    hyphens (the workspaces.slug check), e.g. "Café Talent, Inc." → "cafe-talent-inc"."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    slug = slug[:SLUG_BASE_MAX].rstrip("-")
    return slug or SLUG_FALLBACK


def next_free_slug(base: str, taken: set[str]) -> str:
    """`base` if free, else `base-2`, `base-3`… (never longer than SLUG_MAX)."""
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"[:SLUG_MAX]


# The format `invites.new_code()` makes. Anything else in a join link is the link token.
INVITE_CODE = re.compile(r"[A-Z0-9]{4}-[A-Z0-9]{4}")


def invite_key(raw: str) -> str:
    """Accepts what people paste: a bare code or token, or a whole `/join/<key>` link."""
    value = raw.strip().rstrip("/")
    return value.rsplit("/", 1)[-1].split("?", 1)[0].strip()


def normalize_invite_code(raw: str) -> str:
    """A code in any case, or a whole `/join/<code>` link, as stored."""
    return invite_key(raw).upper()


def mask_email(email: str) -> str:
    """Enough for the invitee to recognise which account to use: "d•••@acme.com"."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}•••@{domain}"


async def _find_invite(setup: WorkspaceSetupRepository, raw: str, *, lock: bool) -> Invite:
    """The invite for a code (case-insensitive) or the link token from the invite email (exact;
    only its SHA-256 is stored), or `404 invite_not_found`."""
    key = invite_key(raw)
    if INVITE_CODE.fullmatch(key.upper()):
        invite = await setup.get_invite(code=key.upper(), lock=lock)
    else:
        token_hash = hashlib.sha256(key.encode()).hexdigest()
        invite = await setup.get_invite(token_hash=token_hash, lock=lock)
    if invite is None:
        raise InviteNotFoundError()
    return invite


def _usable_or_raise(invite: Invite) -> None:
    if invite.status in ("revoked", "accepted"):
        raise InviteInvalidError()
    if invite.status == "expired" or invite.expires_at <= datetime.now(UTC):
        raise InviteExpiredError()


async def grant_trial(session: AsyncSession, workspace: Workspace) -> None:
    """Trial credits for a new workspace (FR-BILL-02): 20 credits from `trial_granted_at`, which
    the caller sets. Workspaces created before BILL-002 got theirs from its migration."""
    assert workspace.trial_granted_at is not None
    await credits.grant_trial(session, workspace.id, granted_at=workspace.trial_granted_at)


async def create_default_email_templates(session: AsyncSession, workspace: Workspace) -> None:
    """The nine candidate email templates every workspace starts with (FR-MSG-01)."""
    await email_templates.ensure_defaults(session, workspace.id)


async def create_workspace(session: AsyncSession, user: CurrentUser, name: str) -> MyWorkspace:
    """The caller becomes the owner (an Admin) of a new workspace with a company profile stub
    and the trial grant, and it becomes their active workspace (FR-AUTH-05)."""
    setup = WorkspaceSetupRepository(session)
    base = slugify(name)
    for attempt in range(CREATE_ATTEMPTS):
        try:
            slug = next_free_slug(base, await setup.slugs_like(base))
            workspace = await setup.add_workspace(
                name=name, slug=slug, owner_id=user.user_id, trial_granted_at=datetime.now(UTC)
            )
            await setup.add_member(
                workspace_id=workspace.id,
                user_id=user.user_id,
                role=Role.ADMIN.value,
                is_owner=True,
            )
            await grant_trial(session, workspace)
            await create_default_email_templates(session, workspace)
            await setup.set_last_workspace(user.user_id, workspace.id)
            await session.commit()
            break
        except IntegrityError:
            await session.rollback()
            if attempt == CREATE_ATTEMPTS - 1:
                raise
    return await _my_workspace(session, user, workspace.id)


async def preview_invite(session: AsyncSession, user: CurrentUser, raw: str) -> InvitePreview:
    """What the join page shows (S-04), by the same rules and in the same order as accepting: a
    different account only learns the masked address the invite was sent to."""
    setup = WorkspaceSetupRepository(session)
    invite = await _find_invite(setup, raw, lock=False)
    if (user.email or "").lower() != invite.email:
        return InvitePreview(state=InviteState.WRONG_EMAIL, masked_email=mask_email(invite.email))
    member = await setup.get_member(invite.workspace_id, user.user_id)
    if member is not None and member.status == "active":
        return InvitePreview(state=InviteState.ALREADY_MEMBER, workspace_id=invite.workspace_id)
    try:
        _usable_or_raise(invite)
    except InviteInvalidError:
        return InvitePreview(state=InviteState.INVALID)
    except InviteExpiredError:
        return InvitePreview(state=InviteState.EXPIRED)
    workspace_name, inviter, departments = await setup.invite_details(invite)
    role = Role(invite.role)
    return InvitePreview(
        state=InviteState.READY,
        workspace_id=invite.workspace_id,
        workspace_name=workspace_name,
        invited_by_name=inviter,
        role=role,
        departments=[] if role is Role.ADMIN else departments,
    )


async def accept_invite(session: AsyncSession, user: CurrentUser, raw: str) -> MyWorkspace:
    """Joins the invite's workspace with its role and departments (FR-AUTH-06), by code or link
    token. The invite must be addressed to the signed-in email; that is checked before anything
    else about it shows."""
    setup = WorkspaceSetupRepository(session)
    invite = await _find_invite(setup, raw, lock=True)
    if (user.email or "").lower() != invite.email:
        raise InviteWrongEmailError()

    member = await setup.get_member(invite.workspace_id, user.user_id)
    already_member = member is not None and member.status == "active"
    if not already_member:
        _usable_or_raise(invite)
        if member is None:
            member = await setup.add_member(
                workspace_id=invite.workspace_id, user_id=user.user_id, role=invite.role
            )
        else:
            # Removed earlier and invited back: same row, the invite's role.
            member.status = "active"
            member.role = invite.role
        await setup.set_member_departments(
            member, [] if invite.role == Role.ADMIN.value else list(invite.department_ids)
        )
    if invite.status == "pending":
        invite.status = "accepted"
        invite.accepted_by = user.user_id
    await setup.set_last_workspace(user.user_id, invite.workspace_id)
    await session.commit()
    return await _my_workspace(session, user, invite.workspace_id)


async def set_last_workspace(
    session: AsyncSession, user: CurrentUser, workspace_id: uuid.UUID
) -> None:
    """Remembers the workspace the user switched to, so sign-in on any device lands there
    (FR-AUTH-04). Only workspaces the user is an active member of; others read as missing."""
    if await UserRepository(session, user.user_id).get_active_membership(workspace_id) is None:
        raise NotFoundError()
    await WorkspaceSetupRepository(session).set_last_workspace(user.user_id, workspace_id)
    await session.commit()


async def _my_workspace(
    session: AsyncSession, user: CurrentUser, workspace_id: uuid.UUID
) -> MyWorkspace:
    rows = await UserRepository(session, user.user_id).list_memberships(workspace_id)
    return to_my_workspace(rows[0])
