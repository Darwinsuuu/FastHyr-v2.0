"""PIPE-006: the share modal's links. Each source gets
`{SITE_URL}/apply/{workspace-slug}/{pipeline-slug}?source={id}` in tile order, scheduled pipelines
share too, drafts and cancelled pipelines have no link, and the department scope and other
workspaces get 404."""

import pytest

from app.core.config import get_settings
from app.core.context import Role
from tests.integration.test_pipelines import admin, draft, grant, ok, pipeline_in
from tests.tenancy.harness import Tenancy

SOURCES = [
    "linkedin",
    "jobstreet",
    "indeed",
    "kalibrr",
    "glassdoor",
    "facebook",
    "careers",
    "other",
]


@pytest.mark.parametrize("status", ["scheduled", "live", "paused", "closed"])
def test_every_source_gets_a_tagged_apply_link(tenancy: Tenancy, status: str) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, status)
    body = ok(admin(tenancy).get(f"/v1/pipelines/{pipeline['id']}/share-links"))

    workspace_slug = f"tenancy-{tenancy.workspace('a').id.hex[:12]}"
    assert body["workspace_slug"] == workspace_slug
    assert body["pipeline_slug"] == pipeline["slug"]
    base = f"{get_settings().site_url}/apply/{workspace_slug}/{pipeline['slug']}"
    assert body["links"] == [
        {"source": source, "url": f"{base}?source={source}"} for source in SOURCES
    ]


@pytest.mark.parametrize("status", ["draft", "cancelled"])
def test_pipelines_without_an_apply_page_have_no_link(tenancy: Tenancy, status: str) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, status)
    response = admin(tenancy).get(f"/v1/pipelines/{pipeline['id']}/share-links")
    assert response.status_code == 409
    assert response.json()["code"] == "no_apply_link"


def test_share_links_follow_the_department_scope(tenancy: Tenancy) -> None:
    grant(tenancy)
    engineering = str(tenancy.workspace("a").department_id)
    own = ok(
        admin(tenancy).post(
            f"/v1/pipelines/{draft(tenancy, department_id=engineering)['id']}/publish",
            json={"confirm": "I understand"},
        )
    )
    no_department = pipeline_in(tenancy, "live")

    # Everyone who sees the pipeline may copy its link, Hiring managers included.
    for role in Role:
        client = tenancy.client("a", role)
        ok(client.get(f"/v1/pipelines/{own['id']}/share-links"))
        hidden = client.get(f"/v1/pipelines/{no_department['id']}/share-links")
        assert hidden.status_code == (200 if role == Role.ADMIN else 404), role
    tenancy.assert_hidden_from_other_workspace("GET", f"/v1/pipelines/{own['id']}/share-links")
