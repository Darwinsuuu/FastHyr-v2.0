"""PIPE-008: the Candidates tab's list against DASH-003's hand-counted applications: filter
counts, order, search, the Hiring manager's shortlist and each caller's reach."""

from typing import Any

from app.core.context import Role
from tests.integration.test_analytics import get, world  # noqa: F401 (fixture)
from tests.integration.test_pipelines import admin
from tests.tenancy.harness import Tenancy


def candidates(client: Any, pipeline_id: str, **params: Any) -> dict[str, Any]:
    return get(client, f"/v1/pipelines/{pipeline_id}/applications", **params)


def test_filters_count_each_stage(tenancy: Tenancy, world: dict[str, Any]) -> None:  # noqa: F811
    page = candidates(admin(tenancy), world["engineering"])
    assert page["counts"] == {
        "all": 7,
        "processing": 1,
        "not_a_match": 1,
        "invited": 2,
        "in_progress": 0,
        "ready": 1,
        # The flagged did-not-pass application waits under Flagged instead.
        "did_not_pass": 0,
        "flagged": 1,
        "review_requested": 0,
        "advanced": 1,
        "rejected": 0,
    }
    assert (page["total"], page["shortlist_only"], page["pass_mark"]) == (7, False, 70)
    # Needing attention first: ready, flagged, invited (newest first), processing, advanced, …
    assert [(row["stage"], row["flagged"]) for row in page["items"]] == [
        ("ready_for_review", False),
        ("did_not_pass", True),
        ("invited", False),
        ("invited", False),
        ("processing_resume", False),
        ("advanced", False),
        ("resume_not_match", False),
    ]
    invited = [row for row in page["items"] if row["stage"] == "invited"]
    assert invited[0]["applied_at"] > invited[1]["applied_at"]

    flagged = candidates(admin(tenancy), world["engineering"], stage="flagged")
    [row] = flagged["items"]
    assert (row["overall_score"], row["flagged"], row["source"]) == (50, True, "careers")
    assert flagged["counts"] == page["counts"]

    paged = candidates(admin(tenancy), world["engineering"], page=2, page_size=5)
    assert (paged["total"], len(paged["items"])) == (7, 2)


def test_search_matches_name_or_email(tenancy: Tenancy, world: dict[str, Any]) -> None:  # noqa: F811
    by_name = candidates(admin(tenancy), world["engineering"], q="candidate 85")
    assert [row["overall_score"] for row in by_name["items"]] == [85]
    assert by_name["total"] == 1
    # The counts ignore the search.
    assert by_name["counts"]["all"] == 7
    by_email = candidates(admin(tenancy), world["engineering"], q="C@X.TEST", stage="invited")
    assert by_email["total"] == 2
    # Literal text: % is not a wildcard.
    assert candidates(admin(tenancy), world["engineering"], q="%")["total"] == 0


def test_hiring_managers_see_the_shortlist_only(
    tenancy: Tenancy,
    world: dict[str, Any],  # noqa: F811
) -> None:
    page = candidates(tenancy.client("a", Role.HIRING_MANAGER), world["engineering"])
    assert page["shortlist_only"] is True
    assert sorted(row["stage"] for row in page["items"]) == [
        "advanced",
        "did_not_pass",
        "ready_for_review",
    ]
    assert page["counts"]["all"] == 3
    assert page["counts"]["not_a_match"] == page["counts"]["invited"] == 0
    # A filter outside the shortlist holds nobody.
    hidden = candidates(
        tenancy.client("a", Role.HIRING_MANAGER), world["engineering"], stage="processing"
    )
    assert hidden["items"] == []


def test_scope_and_other_workspaces(tenancy: Tenancy, world: dict[str, Any]) -> None:  # noqa: F811
    # No department: Admins only.
    assert candidates(admin(tenancy), world["other"])["counts"]["all"] == 1
    for role in (Role.RECRUITER, Role.HIRING_MANAGER):
        response = tenancy.client("a", role).get(f"/v1/pipelines/{world['other']}/applications")
        assert response.status_code == 404
    assert candidates(tenancy.client("a", Role.RECRUITER), world["engineering"])["total"] == 7
    tenancy.assert_hidden_from_other_workspace(
        "GET", f"/v1/pipelines/{world['engineering']}/applications"
    )
    assert (
        tenancy.anonymous().get(f"/v1/pipelines/{world['engineering']}/applications").status_code
        == 401
    )
