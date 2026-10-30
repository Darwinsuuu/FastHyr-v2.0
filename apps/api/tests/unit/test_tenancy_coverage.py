"""WS-005: every API route has an entry in the tenancy registry (`tests/tenancy/endpoints.py`).

A new endpoint fails here until it is listed: as a tenancy case (another workspace gets 404,
departments and the shortlist hold), as caller-only, or as outside any workspace, with the rule
that limits it. No database: this runs in the pull request CI job.
"""

from collections import Counter

from app.core.config import Settings
from app.main import create_app
from tests.tenancy.endpoints import CALLER_ONLY, CASES, OUTSIDE_WORKSPACE, routes

# The dev routes exist locally only; build the app the way local runs see it.
APP_ROUTES = {info.route: info for info in routes(create_app(Settings(app_env="local")))}


def test_every_route_is_listed_once() -> None:
    listed = [case.route for case in CASES] + list(CALLER_ONLY) + list(OUTSIDE_WORKSPACE)
    twice = [route for route, count in Counter(listed).items() if count > 1]
    assert twice == [], "listed more than once"

    missing = sorted(set(APP_ROUTES) - set(listed))
    assert missing == [], (
        "routes with no tenancy entry: add a Case (or a CALLER_ONLY / OUTSIDE_WORKSPACE line "
        "with its reason) in tests/tenancy/endpoints.py"
    )
    gone = sorted(set(listed) - set(APP_ROUTES))
    assert gone == [], "entries for routes that no longer exist"


def test_workspace_routes_are_tenancy_cases_or_caller_only() -> None:
    workspace = {route for route, info in APP_ROUTES.items() if info.workspace}
    assert sorted(workspace & set(OUTSIDE_WORKSPACE)) == [], (
        "these take X-Workspace-Id, so they need a tenancy Case"
    )
    outside = {route for route, info in APP_ROUTES.items() if not info.workspace}
    in_workspace = {case.route for case in CASES} | set(CALLER_ONLY)
    assert sorted(outside & in_workspace) == [], "these don't run in a workspace"


def test_cases_name_the_parameters_their_paths_take() -> None:
    for case in CASES:
        names = {part[1:-1] for part in case.path.split("/") if part.startswith("{")}
        assert names == set(case.params), case
