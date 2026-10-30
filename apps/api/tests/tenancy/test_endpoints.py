"""WS-005: every workspace endpoint in `endpoints.CASES`, against one world in workspace A.

- Another workspace: every role of B gets 404 for A's resources (403 where its role may not take
  the action at all, which says nothing about the resource), and A's data never changes what B's
  lists and aggregates return.
- Departments: the Engineering Recruiter and Hiring manager get 404 for the Sales and
  "No department" pipelines, applications, flags and review requests, and those pipelines change
  nothing they see.
- Shortlist: the Hiring manager gets 404 for an Engineering application that isn't ready for
  review, flagged or advanced, and those applications change nothing on the shortlist views.
- IDs of another workspace or department sent in a body are refused.

Each check also calls the in-scope resource first, so a 404 means "out of reach", not "wrong ID".
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.core.context import Role
from app.core.permissions import MATRIX, Action
from app.main import create_app
from tests.integration.test_analytics import DAY, HOUR, Applicant, apply
from tests.integration.test_pipelines import CONFIRM, SETUP, admin, draft, grant, ok, sql
from tests.tenancy.endpoints import CASES, Case, fill, routes
from tests.tenancy.harness import Tenancy

ACTIONS = {info.route: info.action for info in routes(create_app())}

READY = Applicant(
    3 * DAY, "ready_for_review", "linkedin", True, "completed",
    finished_after=DAY, score=85, assessed_after=DAY + HOUR,
)  # fmt: skip
ADVANCED = Applicant(
    5 * DAY, "advanced", "jobstreet", True, "completed",
    finished_after=DAY, score=80, assessed_after=2 * DAY,
)  # fmt: skip
FLAGGED = Applicant(
    4 * DAY, "did_not_pass", "careers", True, "completed",
    finished_after=DAY, score=50, assessed_after=2 * DAY, flagged=True,
)  # fmt: skip
INVITED = Applicant(2 * DAY, "invited", "jobstreet", True, "not_started")
NOT_A_MATCH = Applicant(2 * DAY, "resume_not_match", screened=False)
PROCESSING = Applicant(HOUR, "processing_resume")


@dataclass
class World:
    """Workspace A's resources by kind: what the Engineering members may reach, what lives in
    other departments, and what is outside the Hiring manager's shortlist."""

    inside: dict[str, uuid.UUID] = field(default_factory=dict)
    other_departments: dict[str, list[uuid.UUID]] = field(default_factory=dict)
    not_shortlisted: dict[str, uuid.UUID] = field(default_factory=dict)


def application(tenancy: Tenancy, pipeline_id: uuid.UUID, who: Applicant) -> uuid.UUID:
    candidate_id = apply(tenancy, str(pipeline_id), who)
    [row] = sql(
        tenancy,
        "select id from applications where candidate_id = $1 and pipeline_id = $2",
        candidate_id,
        pipeline_id,
    )
    return uuid.UUID(str(row["id"]))


def flag(tenancy: Tenancy, application_id: uuid.UUID) -> uuid.UUID:
    [row] = sql(
        tenancy,
        "insert into integrity_flags (workspace_id, interview_id, application_id, type, "
        "start_ms, end_ms, confidence) select workspace_id, id, application_id, 'second_voice', "
        "1000, 6000, 0.8 from interviews where application_id = $1 returning id",
        application_id,
    )
    sql(tenancy, "update applications set has_open_flags = true where id = $1", application_id)
    return uuid.UUID(str(row["id"]))


def review_request(tenancy: Tenancy, application_id: uuid.UUID) -> uuid.UUID:
    workspace_id = tenancy.workspace("a").id
    [link] = sql(
        tenancy,
        "insert into review_links (workspace_id, application_id, decision_type, token_hash, "
        "expires_at, requested_at) values ($1, $2, 'resume', $3, now() + interval '30 days', "
        "now()) returning id",
        workspace_id,
        application_id,
        uuid.uuid4().hex,
    )
    [row] = sql(
        tenancy,
        "insert into human_review_requests (workspace_id, application_id, decision_type, "
        "review_link_id) values ($1, $2, 'resume', $3) returning id",
        workspace_id,
        application_id,
        link["id"],
    )
    sql(tenancy, "update applications set review_requested = true where id = $1", application_id)
    return uuid.UUID(str(row["id"]))


def pipeline(tenancy: Tenancy, title: str, department_id: uuid.UUID | None) -> uuid.UUID:
    created = draft(
        tenancy,
        title=title,
        department_id=None if department_id is None else str(department_id),
        credits_to_reserve=10,
    )
    ok(admin(tenancy).post(f"/v1/pipelines/{created['id']}/publish", json=CONFIRM))
    return uuid.UUID(created["id"])


def build_shortlist(tenancy: Tenancy, world: World) -> None:
    """Step 1: the Engineering pipeline with shortlisted applications only, plus the
    workspace-wide resources (department, member, invite, report job)."""
    workspace = tenancy.workspace("a")
    grant(tenancy)
    engineering = pipeline(tenancy, "Backend Engineer", workspace.department_id)
    ready = application(tenancy, engineering, READY)
    application(tenancy, engineering, ADVANCED)
    flagged = application(tenancy, engineering, FLAGGED)
    invite = ok(
        admin(tenancy).post(
            "/v1/invites",
            json={
                "email": "new-recruiter@example.com",
                "role": "recruiter",
                "department_ids": [str(workspace.department_id)],
            },
        ),
        201,
    )
    [job] = sql(
        tenancy,
        "insert into report_jobs (workspace_id, requested_by, kind) values ($1, $2, 'sample') "
        "returning id",
        workspace.id,
        tenancy.member("a", Role.ADMIN).user_id,
    )
    world.inside |= {
        "pipeline": engineering,
        "application": ready,
        "flag": flag(tenancy, flagged),
        "department": workspace.department_id,
        "member": tenancy.member("a", Role.RECRUITER).member_id,
        "invite": uuid.UUID(invite["id"]),
        "job": uuid.UUID(str(job["id"])),
    }


def build_rest_of_engineering(tenancy: Tenancy, world: World) -> None:
    """Step 2: Engineering applications the Hiring manager may not see."""
    engineering = world.inside["pipeline"]
    world.not_shortlisted["application"] = application(tenancy, engineering, INVITED)
    application(tenancy, engineering, PROCESSING)
    rejected = application(tenancy, engineering, NOT_A_MATCH)
    world.inside["review_request"] = review_request(tenancy, rejected)


def build_other_departments(tenancy: Tenancy, world: World) -> None:
    """Step 3: the same again in Sales and in No department, which the Engineering members are
    not assigned to."""
    sales = ok(admin(tenancy).post("/v1/departments", json={"name": "Sales"}), 201)
    for title, department_id in (
        ("Account Executive", uuid.UUID(sales["id"])),
        ("Office Manager", None),
    ):
        other = pipeline(tenancy, title, department_id)
        ready = application(tenancy, other, READY)
        found = {
            "pipeline": other,
            "application": ready,
            "flag": flag(tenancy, ready),
            "review_request": review_request(tenancy, application(tenancy, other, NOT_A_MATCH)),
        }
        for kind, value in found.items():
            world.other_departments.setdefault(kind, []).append(value)


def allowed(role: Role, case: Case) -> bool:
    action: Action | None = ACTIONS[case.route]
    return action is None or role in MATRIX[action]


def call(
    tenancy: Tenancy, workspace: str, role: Role, case: Case, ids: dict[str, uuid.UUID]
) -> Any:
    return tenancy.client(workspace, role).request(
        case.method, fill(case.path, ids), params=case.query, json=case.json
    )


def ids_for(case: Case, values: dict[str, uuid.UUID]) -> dict[str, uuid.UUID]:
    return {name: values[kind] for name, kind in case.params.items()}


def assert_out_of_reach(response: Any, role: Role, case: Case) -> None:
    """404 `not_found`, or 403 `forbidden` when the role may not take the action anywhere."""
    expected = (404, "not_found") if allowed(role, case) else (403, "forbidden")
    assert (response.status_code, response.json().get("code")) == expected, (
        role,
        response.text,
    )


# Change with the clock or per request, not with the data.
VOLATILE = {"period", "request_id"}


def stable(body: Any) -> Any:
    if isinstance(body, dict):
        return {key: stable(value) for key, value in body.items() if key not in VOLATILE}
    if isinstance(body, list):
        return [stable(item) for item in body]
    return body


def snapshot(
    tenancy: Tenancy, workspace: str, role: Role, case: Case, world: World, *, drop: bool = False
) -> tuple[int, Any]:
    response = call(tenancy, workspace, role, case, ids_for(case, world.inside))
    body = stable(response.json())
    if drop and isinstance(body, dict):
        body = {key: value for key, value in body.items() if key not in case.workspace_wide_keys}
    return response.status_code, body


RESOURCES = [case for case in CASES if case.params]
LISTINGS = [case for case in CASES if case.listing]
SCOPED_ROLES = (Role.RECRUITER, Role.HIRING_MANAGER)


def test_resources_are_out_of_reach_across_workspaces_departments_and_the_shortlist(
    tenancy: Tenancy, subtests: pytest.Subtests
) -> None:
    world = World()
    build_shortlist(tenancy, world)
    build_rest_of_engineering(tenancy, world)
    build_other_departments(tenancy, world)

    for case in RESOURCES:
        with subtests.test(msg=str(case)):
            inside = ids_for(case, world.inside)
            if case.method == "GET":
                # The in-scope resource is there for everyone allowed to read it.
                roles = [Role.ADMIN] if not case.departments else list(Role)
                for role in filter(lambda r: allowed(r, case), roles):
                    response = call(tenancy, "a", role, case, inside)
                    assert response.json().get("code") != "not_found", (role, response.text)

            for role in Role:
                assert_out_of_reach(call(tenancy, "b", role, case, inside), role, case)

            if case.departments:
                for kind, others in world.other_departments.items():
                    if kind not in case.params.values():
                        continue
                    for other in others:
                        ids = ids_for(case, world.inside | {kind: other})
                        for role in SCOPED_ROLES:
                            assert_out_of_reach(call(tenancy, "a", role, case, ids), role, case)

            if case.shortlist and "application" in case.params.values():
                ids = ids_for(case, world.inside | world.not_shortlisted)
                response = call(tenancy, "a", Role.HIRING_MANAGER, case, ids)
                assert_out_of_reach(response, Role.HIRING_MANAGER, case)


def test_lists_and_aggregates_never_count_what_the_caller_cannot_see(
    tenancy: Tenancy, subtests: pytest.Subtests
) -> None:
    world = World()
    other_workspace = [
        (case, role, snapshot(tenancy, "b", role, case, world))
        for case in LISTINGS
        if not case.params
        for role in Role
    ]

    build_shortlist(tenancy, world)
    shortlist = [
        (case, snapshot(tenancy, "a", Role.HIRING_MANAGER, case, world))
        for case in LISTINGS
        if case.shortlist
    ]

    build_rest_of_engineering(tenancy, world)
    departments = [
        (case, role, snapshot(tenancy, "a", role, case, world, drop=True))
        for case in LISTINGS
        if case.departments
        for role in SCOPED_ROLES
        if not (role is Role.HIRING_MANAGER and case.shortlist)
    ]

    build_other_departments(tenancy, world)

    for case, role, before in other_workspace:
        with subtests.test(msg=f"{case} as workspace B's {role}"):
            assert snapshot(tenancy, "b", role, case, world) == before
    for case, before in shortlist:
        with subtests.test(msg=f"{case}: the Hiring manager's shortlist"):
            assert before[0] == 200
            assert snapshot(tenancy, "a", Role.HIRING_MANAGER, case, world) == before
    for case, role, before in departments:
        with subtests.test(msg=f"{case} as the Engineering {role}"):
            assert snapshot(tenancy, "a", role, case, world, drop=True) == before


def test_ids_from_another_workspace_in_bodies_are_refused(tenancy: Tenancy) -> None:
    a = tenancy.workspace("a")
    other_admin = tenancy.client("b", Role.ADMIN)

    def refused(response: Any) -> None:
        assert (response.status_code, response.json()["code"]) == (422, "unknown_department")

    # Filing a pipeline under another workspace's department, or moving one there.
    refused(
        other_admin.post("/v1/pipelines", json={**SETUP, "department_id": str(a.department_id)})
    )
    mine = ok(other_admin.post("/v1/pipelines", json=SETUP), 201)
    refused(
        other_admin.patch(
            f"/v1/pipelines/{mine['id']}", json={**SETUP, "department_id": str(a.department_id)}
        )
    )
    # Inviting or assigning someone to it.
    refused(
        other_admin.post(
            "/v1/invites",
            json={
                "email": "someone@example.com",
                "role": "recruiter",
                "department_ids": [str(a.department_id)],
            },
        )
    )
    member = tenancy.member("b", Role.RECRUITER).member_id
    refused(
        other_admin.patch(f"/v1/members/{member}", json={"department_ids": [str(a.department_id)]})
    )

    # A Recruiter files pipelines under their own departments only.
    sales = ok(admin(tenancy).post("/v1/departments", json={"name": "Sales"}), 201)
    recruiter = tenancy.client("a", Role.RECRUITER)
    refused(recruiter.post("/v1/pipelines", json={**SETUP, "department_id": sales["id"]}))
    refused(recruiter.post("/v1/pipelines", json={**SETUP, "department_id": None}))
    ok(
        recruiter.post("/v1/pipelines", json={**SETUP, "department_id": str(a.department_id)}),
        201,
    )
