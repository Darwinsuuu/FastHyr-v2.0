"""PIPE-001: the pipeline state machine (WORKFLOW.md §2), the setup lock, credit reserves and the
schedule cron. Driven through the API with the tenancy harness, like a TA team would."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.context import Role
from app.models import Pipeline as PipelineRow
from app.services import credits, pipelines
from tests.tenancy.harness import Tenancy

CONFIRM = {"confirm": "I understand"}

SETUP: dict[str, Any] = {
    "title": "Backend Engineer",
    "employment_type": "full_time",
    "work_setup": "hybrid",
    "location": "Makati City",
    "jd_text": "Build and run our APIs.",
    "must_haves": ["Python", "SQL", "REST APIs"],
    "interview_format": "video_voice",
    "tone": "professional",
    "seniority": "mid",
    "skills_to_probe": ["API design", "Debugging", "Testing"],
    "weight_technical": 50,
    "weight_communication": 30,
    "weight_culture": 20,
    "open_mode": "now",
    "duration_days": 30,
    "credits_to_reserve": 10,
}

# Action → (endpoint, body, statuses it starts from, status it ends in; None = unchanged).
ACTIONS: dict[str, tuple[str, dict[str, Any] | None, set[str], str | None]] = {
    "publish": ("publish", CONFIRM, {"draft"}, "live"),
    "start_now": ("start-now", None, {"scheduled"}, "live"),
    "pause": ("pause", None, {"live"}, "paused"),
    "resume": ("resume", None, {"paused"}, "live"),
    "close": ("close", None, {"live", "paused", "paused_no_credits"}, "closed"),
    "cancel": ("cancel", None, {"scheduled"}, "cancelled"),
    "archive": ("archive", None, {"closed", "cancelled"}, None),
    "top_up": (
        "top-up",
        {"credits": 25},
        {"scheduled", "live", "paused", "paused_no_credits"},
        None,
    ),
}
# A top-up puts a pipeline paused for credits back live ("credits added").
TOP_UP_RESULT = {"paused_no_credits": "live"}

STATUSES = ("draft", "scheduled", "live", "paused", "paused_no_credits", "closed", "cancelled")


def db_run[T](tenancy: Tenancy, work: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Runs `work` in a session for the API role, which commits what it keeps."""

    async def main() -> T:
        url = tenancy.supabase.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                return await work(session)
        finally:
            await engine.dispose()

    return asyncio.run(main())


def sql(tenancy: Tenancy, query: str, *args: object) -> list[asyncpg.Record]:
    async def main() -> list[asyncpg.Record]:
        connection = await asyncpg.connect(tenancy.supabase.database_url)
        try:
            return list(await connection.fetch(query, *args))
        finally:
            await connection.close()

    return asyncio.run(main())


def grant(tenancy: Tenancy, credits_to_add: int = 1000, key: str = "a") -> None:
    async def work(session: AsyncSession) -> None:
        await credits.grant_extra(session, tenancy.workspace(key).id, credits=credits_to_add)
        await session.commit()

    db_run(tenancy, work)


def free_credits(tenancy: Tenancy, key: str = "a") -> int:
    async def work(session: AsyncSession) -> int:
        return (await credits.summary(session, tenancy.workspace(key).id)).free

    return db_run(tenancy, work)


def admin(tenancy: Tenancy) -> Any:
    return tenancy.client("a", Role.ADMIN)


def ok(response: Any, status: int = 200) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    return body


def draft(tenancy: Tenancy, **setup: Any) -> dict[str, Any]:
    return ok(admin(tenancy).post("/v1/pipelines", json={**SETUP, **setup}), 201)


def pipeline_in(tenancy: Tenancy, status: str) -> dict[str, Any]:
    """A pipeline brought to `status` the way the product gets there."""
    client = admin(tenancy)
    if status in {"scheduled", "cancelled"}:
        opens_at = (datetime.now(UTC) + timedelta(days=3)).isoformat()
        pipeline = draft(tenancy, open_mode="scheduled", opens_at=opens_at)
    else:
        pipeline = draft(tenancy)
    if status == "draft":
        return pipeline
    url = f"/v1/pipelines/{pipeline['id']}"
    pipeline = ok(client.post(f"{url}/publish", json=CONFIRM))
    if status == "paused":
        pipeline = ok(client.post(f"{url}/pause"))
    elif status == "closed":
        pipeline = ok(client.post(f"{url}/close"))
    elif status == "cancelled":
        pipeline = ok(client.post(f"{url}/cancel"))
    elif status == "paused_no_credits":
        use_whole_reserve(tenancy, uuid.UUID(pipeline["id"]))
        pipeline = ok(client.get(url))
    assert pipeline["status"] == status
    return pipeline


def use_whole_reserve(tenancy: Tenancy, pipeline_id: uuid.UUID) -> None:
    """Applicants use every reserved credit, which pauses the pipeline for credits."""

    async def work(session: AsyncSession) -> None:
        pipeline = await session.get(PipelineRow, pipeline_id)
        assert pipeline is not None
        for _ in range(pipeline.credits_reserved - pipeline.credits_used):
            await credits.consume(session, tenancy.workspace("a").id, pipeline_id)
        await session.commit()

    db_run(tenancy, work)


@pytest.mark.parametrize("status", STATUSES)
def test_every_action_follows_the_state_machine(tenancy: Tenancy, status: str) -> None:
    grant(tenancy)
    client = admin(tenancy)
    for action, (endpoint, body, allowed, result) in ACTIONS.items():
        pipeline = pipeline_in(tenancy, status)
        response = client.post(f"/v1/pipelines/{pipeline['id']}/{endpoint}", json=body)
        if status in allowed:
            moved = ok(response)
            expected = result or (
                TOP_UP_RESULT.get(status, status) if action == "top_up" else status
            )
            assert moved["status"] == expected, action
        else:
            assert response.status_code == 409, (action, response.text)
            assert response.json()["code"] == "invalid_transition", action


def test_setup_can_change_until_the_pipeline_opens(tenancy: Tenancy) -> None:
    grant(tenancy)
    client = admin(tenancy)
    for status in STATUSES:
        pipeline = pipeline_in(tenancy, status)
        response = client.patch(f"/v1/pipelines/{pipeline['id']}", json={"title": "Renamed"})
        if status in {"draft", "scheduled"}:
            assert ok(response)["title"] == "Renamed"
        elif status == "cancelled":
            assert response.json()["code"] == "invalid_transition"
        else:
            assert response.status_code == 409
            assert response.json()["code"] == "pipeline_locked", status


def test_locked_setup_and_published_slug_cannot_change_in_the_database(tenancy: Tenancy) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "live")
    for statement in (
        "update pipelines set title = 'Changed' where id = $1",
        "update pipelines set weight_technical = 40, weight_culture = 30 where id = $1",
        "update pipelines set closes_at = closes_at + interval '1 day' where id = $1",
        "update pipelines set slug = 'other' where id = $1",
    ):
        with pytest.raises(asyncpg.RaiseError, match="pipeline"):
            sql(tenancy, statement, uuid.UUID(pipeline["id"]))
    # Deleting a department still moves locked pipelines to No department (WS-002).
    sql(
        tenancy,
        "update pipelines set department_id = null where id = $1",
        uuid.UUID(pipeline["id"]),
    )


def test_publishing_reserves_credits_and_closing_returns_the_unused_reserve(
    tenancy: Tenancy,
) -> None:
    grant(tenancy, 100)
    client = admin(tenancy)
    pipeline = draft(tenancy, credits_to_reserve=40)
    url = f"/v1/pipelines/{pipeline['id']}"

    published = ok(client.post(f"{url}/publish", json=CONFIRM))
    assert (published["credits_reserved"], free_credits(tenancy)) == (40, 60)
    assert ok(client.post(f"{url}/top-up", json={"credits": 25}))["credits_reserved"] == 65
    assert free_credits(tenancy) == 35

    closed = ok(client.post(f"{url}/close"))
    assert (closed["status"], closed["closed_reason"], closed["credits_reserved"]) == (
        "closed",
        "manual",
        0,
    )
    assert free_credits(tenancy) == 100


def test_publish_refuses_a_reserve_bigger_than_the_free_credits(tenancy: Tenancy) -> None:
    grant(tenancy, 20)
    pipeline = draft(tenancy, credits_to_reserve=30)
    response = admin(tenancy).post(f"/v1/pipelines/{pipeline['id']}/publish", json=CONFIRM)
    assert response.status_code == 409
    assert response.json()["code"] == "insufficient_free_credits"
    assert ok(admin(tenancy).get(f"/v1/pipelines/{pipeline['id']}"))["status"] == "draft"


def test_publish_lists_what_the_setup_is_missing(tenancy: Tenancy) -> None:
    grant(tenancy)
    pipeline = ok(admin(tenancy).post("/v1/pipelines", json={"title": "Designer"}), 201)
    response = admin(tenancy).post(f"/v1/pipelines/{pipeline['id']}/publish", json=CONFIRM)
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "pipeline_incomplete"
    missing = {error["loc"][0] for error in body["errors"]}
    assert {"jd_text", "must_haves", "skills_to_probe", "credits_to_reserve"} <= missing
    assert "title" not in missing


def test_slugs_are_unique_per_workspace_and_set_on_publish(tenancy: Tenancy) -> None:
    grant(tenancy)
    client = admin(tenancy)
    slugs = []
    for _ in range(2):
        pipeline = draft(tenancy, title="Frontend Engineer (React)")
        assert pipeline["slug"] is None
        slugs.append(
            ok(client.post(f"/v1/pipelines/{pipeline['id']}/publish", json=CONFIRM))["slug"]
        )
    assert slugs == ["frontend-engineer-react", "frontend-engineer-react-2"]


def test_scheduled_pipeline_opens_and_closes_on_its_dates(tenancy: Tenancy) -> None:
    grant(tenancy)
    pipeline = pipeline_in(tenancy, "scheduled")
    pipeline_id = uuid.UUID(pipeline["id"])
    opens_at = datetime.fromisoformat(pipeline["opens_at"])
    closes_at = datetime.fromisoformat(pipeline["closes_at"])
    assert closes_at == opens_at + timedelta(days=30)

    def run_cron(now: datetime) -> PipelineRow:
        async def work(session: AsyncSession) -> PipelineRow:
            await pipelines.open_due(session, now=now)
            await pipelines.close_due(session, now=now)
            row = await session.get(PipelineRow, pipeline_id)
            assert row is not None
            return row

        return db_run(tenancy, work)

    assert run_cron(opens_at - timedelta(minutes=1)).status == "scheduled"
    opened = run_cron(opens_at + timedelta(seconds=30))
    assert (opened.status, opened.locked_at) == ("live", opens_at + timedelta(seconds=30))
    # Pausing never extends the closing date.
    ok(admin(tenancy).post(f"/v1/pipelines/{pipeline_id}/pause"))
    closed = run_cron(closes_at)
    assert (closed.status, closed.closed_reason, closed.credits_reserved) == (
        "closed",
        "schedule",
        0,
    )


def test_duplicate_copies_the_setup_into_a_new_draft(tenancy: Tenancy) -> None:
    grant(tenancy)
    source = pipeline_in(tenancy, "closed")
    copy = ok(admin(tenancy).post(f"/v1/pipelines/{source['id']}/duplicate"), 201)
    assert copy["status"] == "draft"
    assert copy["duplicated_from_id"] == source["id"]
    assert copy["slug"] is None and copy["opens_at"] is None
    assert {key: copy[key] for key in SETUP} == {key: source[key] for key in SETUP}


def test_department_scoping_and_roles(tenancy: Tenancy) -> None:
    grant(tenancy)
    engineering = str(tenancy.workspace("a").department_id)
    recruiter = tenancy.client("a", Role.RECRUITER)
    hiring_manager = tenancy.client("a", Role.HIRING_MANAGER)

    # Recruiters create pipelines in their own departments only.
    assert recruiter.post("/v1/pipelines", json={"title": "x"}).json()["code"] == (
        "unknown_department"
    )
    own = ok(recruiter.post("/v1/pipelines", json={**SETUP, "department_id": engineering}), 201)
    ok(recruiter.post(f"/v1/pipelines/{own['id']}/publish", json=CONFIRM))

    # Hiring managers see their departments' pipelines but can't change them.
    assert ok(hiring_manager.get(f"/v1/pipelines/{own['id']}"))["status"] == "live"
    assert hiring_manager.post(f"/v1/pipelines/{own['id']}/pause").status_code == 403

    # No department is for Admins only; other workspaces see nothing.
    no_department = draft(tenancy)
    for client in (recruiter, hiring_manager):
        assert client.get(f"/v1/pipelines/{no_department['id']}").status_code == 404
    tenancy.assert_hidden_from_other_workspace("GET", f"/v1/pipelines/{own['id']}")


def test_out_of_credit_pipelines_resume_when_credits_are_added(tenancy: Tenancy) -> None:
    grant(tenancy, 10)
    pipeline = pipeline_in(tenancy, "paused_no_credits")
    pipeline_id = uuid.UUID(pipeline["id"])
    workspace_id = tenancy.workspace("a").id

    async def top_up_workspace(session: AsyncSession) -> int:
        # The reserve has room again only after a top-up, so nothing resumes on a grant alone.
        await credits.grant_extra(session, workspace_id, credits=50)
        resumed = await pipelines.resume_after_credits_added(session, workspace_id)
        await session.commit()
        return resumed

    assert db_run(tenancy, top_up_workspace) == 0
    topped = ok(admin(tenancy).post(f"/v1/pipelines/{pipeline_id}/top-up", json={"credits": 25}))
    assert topped["status"] == "live"
