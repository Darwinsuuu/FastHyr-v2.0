"""FND-004: /v1/me and /v1/me/workspaces with a real Supabase sign-in."""

from fastapi.testclient import TestClient

from app.core.context import Role
from app.main import create_app
from tests.tenancy.harness import Tenancy


def test_me_needs_a_valid_token() -> None:
    client = TestClient(create_app())

    assert client.get("/v1/me").json()["code"] == "unauthenticated"
    response = client.get("/v1/me", headers={"Authorization": "Bearer nonsense"})
    assert response.status_code == 401


def test_me_returns_the_signed_in_user(tenancy: Tenancy) -> None:
    member = tenancy.member("a", Role.RECRUITER)

    body = tenancy.client("a", Role.RECRUITER).get("/v1/me").json()

    assert body["id"] == str(member.user_id)
    assert body["email"] == member.email
    assert body["email_verified"] is True


def test_my_workspaces_lists_only_my_own(tenancy: Tenancy) -> None:
    workspace = tenancy.workspace("a")

    body = tenancy.client("a", Role.HIRING_MANAGER).get("/v1/me/workspaces").json()

    assert body == [
        {
            "id": str(workspace.id),
            "name": "Tenancy A",
            "slug": f"tenancy-{workspace.id.hex[:12]}",
            "role": "hiring_manager",
            "is_owner": False,
            "member_count": 3,
        }
    ]
