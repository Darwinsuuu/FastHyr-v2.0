"""FND-004: TA requests are bound to one workspace, role and departments; nothing crosses over.

Test-only routes stand in for real endpoints until business endpoints exist.
"""

import asyncio
import uuid
from typing import Annotated

import asyncpg
import pytest
from fastapi import APIRouter, FastAPI

from app.api.deps import RequestContextDep, Session, require
from app.core.context import RequestContext, Role
from app.core.permissions import Action
from app.main import create_app
from app.models import Department
from app.repositories.base import WorkspaceRepository
from tests.tenancy.harness import Tenancy


class DepartmentRepository(WorkspaceRepository[Department]):
    model = Department

    async def get(self, department_id: uuid.UUID) -> Department:
        return await self._get_or_404(department_id)


@pytest.fixture
def tenancy_app() -> FastAPI:
    app = create_app()
    router = APIRouter(prefix="/v1/test")

    @router.get("/context")
    async def context(ctx: RequestContextDep) -> dict[str, object]:
        return {
            "workspace_id": str(ctx.workspace_id),
            "role": ctx.role.value,
            "is_owner": ctx.is_owner,
            "department_ids": sorted(str(d) for d in ctx.department_ids),
            "sees_all_departments": ctx.sees_all_departments,
        }

    @router.get("/billing")
    async def billing(ctx: Annotated[RequestContext, require(Action.MANAGE_BILLING)]) -> None:
        return None

    @router.get("/departments/{department_id}")
    async def department(
        department_id: uuid.UUID,
        ctx: Annotated[RequestContext, require(Action.VIEW_DEPARTMENTS)],
        session: Session,
    ) -> dict[str, str]:
        row = await DepartmentRepository(session, ctx.workspace_id).get(department_id)
        return {"name": row.name}

    app.include_router(router)
    return app


def test_context_carries_role_owner_and_departments(tenancy: Tenancy) -> None:
    workspace = tenancy.workspace("a")

    admin = tenancy.client("a", Role.ADMIN).get("/v1/test/context").json()
    recruiter = tenancy.client("a", Role.RECRUITER).get("/v1/test/context").json()

    assert admin == {
        "workspace_id": str(workspace.id),
        "role": "admin",
        "is_owner": True,
        "department_ids": [],
        "sees_all_departments": True,
    }
    assert recruiter["role"] == "recruiter"
    assert recruiter["is_owner"] is False
    assert recruiter["department_ids"] == [str(workspace.department_id)]
    assert recruiter["sees_all_departments"] is False


@pytest.mark.parametrize("role", list(Role))
def test_other_workspace_is_not_a_member(tenancy: Tenancy, role: Role) -> None:
    headers = tenancy.headers("b", role, as_workspace="a")

    response = tenancy.client("b", role).get("/v1/test/context", headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "not_a_member"


@pytest.mark.parametrize("value", ["", "not-a-uuid", str(uuid.uuid4())])
def test_missing_or_unknown_workspace_header(tenancy: Tenancy, value: str) -> None:
    response = tenancy.client("a", Role.ADMIN).get(
        "/v1/test/context", headers={"X-Workspace-Id": value}
    )

    expected = "workspace_required" if value == "" else "not_a_member"
    assert response.json()["code"] == expected


def test_removed_member_is_not_a_member(tenancy: Tenancy) -> None:
    member = tenancy.member("a", Role.RECRUITER)

    async def remove() -> None:
        connection = await asyncpg.connect(tenancy.supabase.database_url)
        await connection.execute(
            "update workspace_members set status = 'removed' where id = $1", member.member_id
        )
        await connection.close()

    asyncio.run(remove())

    response = tenancy.client("a", Role.RECRUITER).get("/v1/test/context")
    assert response.json()["code"] == "not_a_member"


def test_require_refuses_roles_outside_the_matrix(tenancy: Tenancy) -> None:
    assert tenancy.client("a", Role.ADMIN).get("/v1/test/billing").status_code == 200
    for role in (Role.RECRUITER, Role.HIRING_MANAGER):
        response = tenancy.client("a", role).get("/v1/test/billing")
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"


def test_workspace_rows_are_hidden_from_other_workspace(tenancy: Tenancy) -> None:
    department_id = tenancy.workspace("a").department_id
    url = f"/v1/test/departments/{department_id}"

    assert tenancy.client("a", Role.HIRING_MANAGER).get(url).json() == {"name": "Engineering"}
    tenancy.assert_hidden_from_other_workspace("GET", url)
