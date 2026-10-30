"""Every API route and how its access rule is tested (WS-005, MULTI_TENANCY.md §4).

Each route of `create_app()` is in exactly one group:

- `CASES`: workspace endpoints that read or change a workspace's resources or lists. The tenancy
  suite (`tests/tenancy/test_endpoints.py`) runs every case: another workspace gets 404, the
  Engineering Recruiter and Hiring manager can't reach other departments or "No department", and
  the Hiring manager can't reach applications outside the shortlist.
- `CALLER_ONLY`: workspace endpoints with nothing of another workspace to reach: they act on the
  caller's own workspace or account. The reason says so, and names the test for any ID they take
  in the body.
- `OUTSIDE_WORKSPACE`: routes without `X-Workspace-Id` (account, candidate, public, webhook), with
  the rule that limits them and where it is tested.

`tests/unit/test_tenancy_coverage.py` fails when a route is in none of them (a new endpoint),
in the wrong one, or when an entry names a route that is gone. Adding an endpoint: add a `Case`
(or, if it truly has nothing to scope, a `CALLER_ONLY` line) next to its neighbours.

No database here: the unit check imports this module.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI

from app.core.permissions import Action

Route = tuple[str, str]  # (method, path as registered)

# Path parameters → the world resource they name (see `test_endpoints.World`).
PIPELINE = {"pipeline_id": "pipeline"}
APPLICATION = {"application_id": "application"}
# The template the world edits (`test_endpoints.build_shortlist`).
TEMPLATE = {"key": "interview_invitation"}


@dataclass(frozen=True)
class Case:
    method: str
    path: str
    # Path parameter → world resource ("pipeline", "application", "flag", …).
    params: dict[str, str] = field(default_factory=dict)
    json: Any = None
    query: dict[str, str] = field(default_factory=dict)
    # Path parameters that aren't resources, such as an email template's key.
    fixed: dict[str, str] = field(default_factory=dict)
    # A list or aggregate: data the caller can't see must not change the response.
    listing: bool = False
    # Limited to the caller's departments (SECURITY.md §2). False for workspace-wide settings.
    departments: bool = True
    # Hiring managers reach shortlisted applications only (ready for review, flagged, advanced).
    shortlist: bool = False
    # Response keys a department-scoped caller legitimately sees change with other departments'
    # data, with the reason in a comment where the case is listed.
    workspace_wide_keys: tuple[str, ...] = ()

    @property
    def route(self) -> Route:
        return (self.method, self.path)

    def __str__(self) -> str:
        return f"{self.method} {self.path}"


CASES: list[Case] = [
    # Lists and aggregates.
    # The Overview's credits card is workspace-wide: credits aren't held by department.
    Case(
        "GET", "/v1/analytics/overview", listing=True, shortlist=True,
        workspace_wide_keys=("credits",),
    ),
    Case("GET", "/v1/analytics/pipelines-flow", listing=True),
    Case("GET", "/v1/candidates/dashboard", listing=True, shortlist=True),
    Case("GET", "/v1/credits/summary", listing=True, departments=False),
    Case("GET", "/v1/departments", listing=True, departments=False),
    Case("GET", "/v1/email-templates", listing=True, departments=False),
    Case("GET", "/v1/email-templates/{key}/versions", fixed=TEMPLATE, listing=True,
         departments=False),
    Case("GET", "/v1/invites", listing=True, departments=False),
    Case("GET", "/v1/members", listing=True, departments=False),
    Case("GET", "/v1/pipelines", listing=True, query={"tab": "all"}),
    Case("GET", "/v1/review-requests", listing=True),
    Case("GET", "/v1/workspace/company-profile", listing=True, departments=False),
    # Pipelines.
    Case("GET", "/v1/pipelines/{pipeline_id}", PIPELINE),
    Case("PATCH", "/v1/pipelines/{pipeline_id}", PIPELINE, json={"title": "Renamed"}),
    Case("GET", "/v1/pipelines/{pipeline_id}/applications", PIPELINE, listing=True,
         shortlist=True),
    Case("GET", "/v1/pipelines/{pipeline_id}/dashboard", PIPELINE),
    Case("GET", "/v1/pipelines/{pipeline_id}/share-links", PIPELINE),
    Case("POST", "/v1/pipelines/{pipeline_id}/publish", PIPELINE,
         json={"confirm": "I understand"}),
    Case("POST", "/v1/pipelines/{pipeline_id}/start-now", PIPELINE),
    Case("POST", "/v1/pipelines/{pipeline_id}/pause", PIPELINE),
    Case("POST", "/v1/pipelines/{pipeline_id}/resume", PIPELINE),
    Case("POST", "/v1/pipelines/{pipeline_id}/close", PIPELINE, json={"notify": False}),
    Case("POST", "/v1/pipelines/{pipeline_id}/cancel", PIPELINE),
    Case("POST", "/v1/pipelines/{pipeline_id}/archive", PIPELINE),
    Case("POST", "/v1/pipelines/{pipeline_id}/duplicate", PIPELINE),
    Case("POST", "/v1/pipelines/{pipeline_id}/top-up", PIPELINE, json={"credits": 25}),
    Case("POST", "/v1/pipelines/{pipeline_id}/reinvite", PIPELINE,
         json={"scope": "all_unfinished"}),
    # Applications and reviews.
    Case("GET", "/v1/applications/{application_id}", APPLICATION, shortlist=True),
    Case("GET", "/v1/applications/{application_id}/recording-url", APPLICATION, shortlist=True),
    Case("POST", "/v1/applications/{application_id}/advance", APPLICATION,
         json={"send_email": False}),
    Case("POST", "/v1/applications/{application_id}/reject", APPLICATION,
         json={"reason": "Not the right fit", "send_email": False}),
    Case("POST", "/v1/applications/{application_id}/reinvite", APPLICATION),
    Case("PATCH", "/v1/integrity-flags/{flag_id}", {"flag_id": "flag"},
         json={"status": "no_concern"}),
    Case("POST", "/v1/review-requests/{request_id}/resolve", {"request_id": "review_request"},
         json={"outcome": "uphold", "note": "Looked again"}),
    # Workspace settings: one workspace, no departments.
    Case("PATCH", "/v1/departments/{department_id}", {"department_id": "department"},
         json={"name": "Renamed"}, departments=False),
    Case("DELETE", "/v1/departments/{department_id}", {"department_id": "department"},
         departments=False),
    Case("PATCH", "/v1/members/{member_id}", {"member_id": "member"},
         json={"role": "hiring_manager"}, departments=False),
    Case("DELETE", "/v1/members/{member_id}", {"member_id": "member"}, departments=False),
    Case("POST", "/v1/invites/{invite_id}/resend", {"invite_id": "invite"}, departments=False),
    Case("DELETE", "/v1/invites/{invite_id}", {"invite_id": "invite"}, departments=False),
    Case("POST", "/v1/email-templates/{key}/versions/{version_id}/restore",
         {"version_id": "template_version"}, fixed=TEMPLATE, departments=False),
    # Report jobs: the member who asked for one, only.
    Case("GET", "/v1/jobs/{job_id}", {"job_id": "job"}, departments=False),
    Case("DELETE", "/v1/jobs/{job_id}", {"job_id": "job"}, departments=False),
]  # fmt: skip

BODY_IDS = "IDs in the body: test_ids_from_another_workspace_in_bodies_are_refused"

TEMPLATE_ONLY = "the caller's workspace's own template of that key; test_email_templates.py"

CALLER_ONLY: dict[Route, str] = {
    ("POST", "/v1/pipelines"): f"creates a draft in the caller's workspace; {BODY_IDS}",
    ("POST", "/v1/invites"): f"invites into the caller's workspace; {BODY_IDS}",
    ("POST", "/v1/departments"): "creates a department in the caller's workspace",
    ("PUT", "/v1/workspace/company-profile"): "the caller's workspace's own profile",
    ("GET", "/v1/email-templates/{key}"): TEMPLATE_ONLY,
    ("PUT", "/v1/email-templates/{key}"): TEMPLATE_ONLY,
    ("POST", "/v1/email-templates/{key}/reset"): TEMPLATE_ONLY,
    ("POST", "/v1/email-templates/{key}/test"): f"{TEMPLATE_ONLY}; sent to the caller only",
    ("POST", "/v1/workspace/company-profile/branding-upload"): (
        "an upload URL under the caller's workspace's branding folder"
    ),
    ("POST", "/v1/dev/error"): "local only: raises a test error",
    ("POST", "/v1/dev/sample-job"): "local only: a sample job for the caller",
    ("POST", "/v1/dev/test-email"): "local only: a test email to the caller",
}

CANDIDATE = "the signed-in candidate's own applications and links only"
INTERVIEW_LINK = f"{CANDIDATE}; test_interview_links.py, test_interview_sessions.py"

OUTSIDE_WORKSPACE: dict[Route, str] = {
    ("GET", "/v1/me"): "the signed-in user's own account; test_me.py",
    ("GET", "/v1/me/workspaces"): "workspaces the user is a member of; test_me.py",
    ("PUT", "/v1/me/last-workspace"): "only a workspace the user is a member of; test_me.py",
    ("POST", "/v1/workspaces"): "creates a workspace the user owns; test_workspaces.py",
    ("GET", "/v1/invites/{key}"): "the invite's own code or token; test_invites.py",
    ("POST", "/v1/invites/accept"): "the invite's own code or token and email; test_invites.py",
    ("POST", "/v1/candidate/applications"): f"{CANDIDATE}; test_applications.py",
    ("GET", "/v1/candidate/pipelines/{pipeline_id}/my-application"): (
        f"{CANDIDATE}; test_applications.py"
    ),
    ("POST", "/v1/candidate/pipelines/{pipeline_id}/resume-upload"): (
        f"{CANDIDATE}; test_applications.py"
    ),
    ("GET", "/v1/candidate/interviews/{token}"): INTERVIEW_LINK,
    ("POST", "/v1/candidate/interviews/{token}/consent"): INTERVIEW_LINK,
    ("POST", "/v1/candidate/interviews/{token}/session"): INTERVIEW_LINK,
    ("POST", "/v1/candidate/interviews/{token}/heartbeat"): INTERVIEW_LINK,
    ("POST", "/v1/candidate/interviews/{token}/complete"): INTERVIEW_LINK,
    ("POST", "/v1/candidate/interviews/{token}/chunk-urls"): f"{CANDIDATE}; test_recordings.py",
    ("POST", "/v1/candidate/interviews/{token}/chunks"): f"{CANDIDATE}; test_recordings.py",
    ("GET", "/v1/public/pipelines/{workspace_slug}/{pipeline_slug}"): (
        "published pipelines' candidate-safe fields; test_public_pipelines.py"
    ),
    ("GET", "/v1/public/branding/{workspace_id}/{kind}"): (
        "a workspace's logo or banner, shown in its emails; test_company_profile.py"
    ),
    ("GET", "/v1/public/notices"): "versioned notice texts, no workspace data",
    ("GET", "/v1/public/notices/{kind}"): "versioned notice texts, no workspace data",
    ("GET", "/v1/public/notices/{kind}/{version}"): "versioned notice texts, no workspace data",
    ("GET", "/v1/public/review-requests/{token}"): (
        "the review link's own company and job title; test_review_requests.py"
    ),
    ("POST", "/v1/public/review-requests/{token}"): (
        "the review link's own application; test_review_requests.py"
    ),
    ("POST", "/v1/webhooks/resend"): "Svix-signed delivery events by message ID; test_emails.py",
}


@dataclass(frozen=True)
class RouteInfo:
    method: str
    path: str
    # Takes a `RequestContext`: a TA member acting in the workspace in `X-Workspace-Id`.
    workspace: bool
    # The `require(action)` on the route, if any.
    action: Action | None

    @property
    def route(self) -> Route:
        return (self.method, self.path)


def _dependency_calls(dependant: Any) -> Iterator[Any]:
    for sub in dependant.dependencies:
        yield sub.call
        yield from _dependency_calls(sub)


def _required_action(call: Any) -> Action | None:
    """The action a `require(action)` dependency closes over."""
    for cell in getattr(call, "__closure__", None) or ():
        if isinstance(cell.cell_contents, Action):
            return cell.cell_contents
    return None


def routes(app: FastAPI) -> list[RouteInfo]:
    """Every `/v1` route of `app`, one per method."""
    found: list[RouteInfo] = []
    for router in app.routes:
        contexts = getattr(router, "effective_route_contexts", None)
        if contexts is None:
            continue
        for context in contexts():
            calls = list(_dependency_calls(context.dependant))
            names = {getattr(call, "__name__", "") for call in calls}
            actions = {a for a in map(_required_action, calls) if a is not None}
            assert len(actions) <= 1, (context.path, actions)
            for method in sorted(context.methods):
                found.append(
                    RouteInfo(
                        method=method,
                        path=context.path,
                        workspace="get_request_context" in names,
                        action=next(iter(actions), None),
                    )
                )
    return found


def fill(path: str, values: Mapping[str, object]) -> str:
    return path.format(**{name: str(value) for name, value in values.items()})
