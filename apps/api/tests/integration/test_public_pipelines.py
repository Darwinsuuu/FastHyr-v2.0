"""APPLY-001: the public apply page endpoint. Anyone with the link reads candidate-safe fields
only; drafts, cancelled pipelines and unknown links are 404."""

from typing import Any

import pytest

from tests.integration.test_pipelines import grant, ok, pipeline_in, sql
from tests.tenancy.harness import Tenancy

# Everything the apply page may show. A new field must be added here on purpose.
PUBLIC_KEYS = {
    "id",
    "workspace_slug",
    "slug",
    "availability",
    "title",
    "department",
    "employment_type",
    "work_setup",
    "location",
    "jd_text",
    "open_to",
    "interview_format",
    "opens_at",
    "closes_at",
    "timezone",
    "company",
}
COMPANY_KEYS = {
    "name",
    "logo_url",
    "website",
    "industry",
    "company_size",
    "hq_country",
    "about",
    "careers_url",
}
HIDDEN = (
    "must_haves",
    "nice_to_haves",
    "skills_to_probe",
    "resume_pass_bar",
    "tone",
    "seniority",
    "weight_technical",
    "weight_communication",
    "weight_culture",
    "pass_mark",
    "credits_reserved",
    "credits_used",
    "status",
)


def workspace_slug(tenancy: Tenancy, key: str = "a") -> str:
    rows = sql(tenancy, "select slug from workspaces where id = $1", tenancy.workspace(key).id)
    slug: str = rows[0]["slug"]
    return slug


def public_url(tenancy: Tenancy, pipeline: dict[str, Any], key: str = "a") -> str:
    return f"/v1/public/pipelines/{workspace_slug(tenancy, key)}/{pipeline['slug']}"


def test_returns_only_candidate_safe_fields(tenancy: Tenancy) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    response = tenancy.anonymous().get(public_url(tenancy, pipeline))
    body = ok(response)
    assert set(body) == PUBLIC_KEYS
    assert set(body["company"]) == COMPANY_KEYS
    text = response.text
    for key in HIDDEN:
        assert f'"{key}"' not in text
    # The values behind the hidden keys never appear either.
    for value in ("Python", "REST APIs", "API design", "Debugging"):
        assert value not in text
    assert body["availability"] == "accepting"
    assert body["title"] == "Backend Engineer"
    assert body["company"]["name"] == "Tenancy A"


@pytest.mark.parametrize(
    ("status", "availability"),
    [
        ("scheduled", "opens_later"),
        ("paused", "not_accepting"),
        ("paused_no_credits", "not_accepting"),
        ("closed", "closed"),
    ],
)
def test_availability_follows_the_status(tenancy: Tenancy, status: str, availability: str) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, status)
    if status == "scheduled":
        # The slug is set on publish, so a scheduled pipeline already has its link.
        assert pipeline["slug"]
    body = ok(tenancy.anonymous().get(public_url(tenancy, pipeline)))
    assert body["availability"] == availability


def test_drafts_cancelled_and_unknown_links_are_not_found(tenancy: Tenancy) -> None:
    grant(tenancy)
    public = tenancy.anonymous()
    cancelled = pipeline_in(tenancy, "cancelled")
    assert public.get(public_url(tenancy, cancelled)).status_code == 404

    pipeline_in(tenancy, "draft")
    drafts = sql(
        tenancy,
        "select count(*) as n from pipelines where workspace_id = $1 and status = 'draft'"
        " and slug is not null",
        tenancy.workspace("a").id,
    )
    assert drafts[0]["n"] == 0  # drafts have no link at all

    slug = workspace_slug(tenancy)
    for path in (f"{slug}/no-such-role", "no-such-workspace/backend-engineer"):
        response = public.get(f"/v1/public/pipelines/{path}")
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"


def test_a_pipeline_is_only_found_under_its_own_workspace(tenancy: Tenancy) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    other = f"/v1/public/pipelines/{workspace_slug(tenancy, 'b')}/{pipeline['slug']}"
    assert tenancy.anonymous().get(other).status_code == 404
