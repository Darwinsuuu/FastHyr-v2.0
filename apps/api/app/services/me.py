"""The signed-in user's own profile and workspaces."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.repositories.users import MembershipRow, UserRepository
from app.schemas.me import MeResponse, MyWorkspace


async def get_me(session: AsyncSession, user: CurrentUser) -> MeResponse:
    profile = await UserRepository(session, user.user_id).get_profile()
    return MeResponse(
        id=user.user_id,
        email=user.email,
        email_verified=user.email_verified,
        full_name=profile.full_name if profile else None,
        avatar_url=profile.avatar_url if profile else None,
        last_workspace_id=profile.last_workspace_id if profile else None,
    )


async def list_my_workspaces(session: AsyncSession, user: CurrentUser) -> list[MyWorkspace]:
    rows = await UserRepository(session, user.user_id).list_memberships()
    return [_to_workspace(row) for row in rows]


def _to_workspace(row: MembershipRow) -> MyWorkspace:
    return MyWorkspace(
        id=row.workspace_id,
        name=row.workspace_name,
        slug=row.workspace_slug,
        role=row.role,
        is_owner=row.is_owner,
        member_count=row.member_count,
    )
