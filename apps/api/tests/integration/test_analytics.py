"""DASH-003: the dashboards' numbers against a small, hand-counted set of applications, each
caller's reach (departments, Hiring-manager shortlist, other workspaces) and the response time on
the Acme Talent seed."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import Role
from app.services import credits
from tests.integration.test_pipelines import CONFIRM, admin, db_run, draft, grant, ok
from tests.tenancy.harness import Tenancy

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


@dataclass(frozen=True)
class Applicant:
    """One application and what happened to it. Times are offsets back from now."""

    applied: timedelta
    stage: str
    source: str = "linkedin"
    screened: bool | None = None  # None: not screened yet
    interview: str | None = None  # interview status
    drop_reason: str | None = None
    expires_in: timedelta = 3 * DAY  # from now; negative = expired
    finished_after: timedelta | None = None  # from applying
    score: int | None = None
    assessed_after: timedelta | None = None  # from applying
    flagged: bool = False
    candidate: uuid.UUID | None = None  # reuse a person (a returning candidate)


def apply(tenancy: Tenancy, pipeline_id: str, who: Applicant) -> uuid.UUID:
    """Writes an application the way the product leaves it, using one of the pipeline's
    credits. Returns the candidate's ID."""
    workspace_id = tenancy.workspace("a").id
    now = datetime.now(UTC)
    applied_at = now - who.applied

    async def work(session: AsyncSession) -> uuid.UUID:
        application_id = uuid.uuid4()
        entry = await credits.consume(
            session, workspace_id, uuid.UUID(pipeline_id), application_id=application_id
        )
        candidate_id = who.candidate or uuid.uuid4()
        if who.candidate is None:
            await session.execute(
                text(
                    "insert into candidates (id, workspace_id, auth_user_id, email, full_name, "
                    "phone_country_code, phone) values (:id, :ws, :user, 'c@x.test', :name, "
                    "'+63', '9171234567')"
                ),
                {
                    "id": candidate_id,
                    "ws": workspace_id,
                    "user": uuid.uuid4(),
                    "name": f"Candidate {who.score or 0}",
                },
            )
        values = {"ws": workspace_id, "app": application_id}
        await session.execute(
            text(
                "insert into applications (id, workspace_id, pipeline_id, candidate_id, source, "
                "resume_path, resume_filename, resume_pages, resume_bytes, consent_version, "
                "consent_at, stage, has_open_flags, overall_score, credit_ledger_id, applied_at, "
                "stage_changed_at, resume_status) values (:app, :ws, :pipeline, :candidate, "
                ":source, 'r.pdf', 'r.pdf', 1, 100, 'apply@v1', :at, :stage, :flagged, :score, "
                ":entry, :at, :at, :resume_status)"
            ),
            values
            | {
                "pipeline": uuid.UUID(pipeline_id),
                "candidate": candidate_id,
                "source": who.source,
                "at": applied_at,
                "stage": who.stage,
                "flagged": who.flagged,
                "score": who.score,
                "entry": entry.id,
                "resume_status": "pending" if who.screened is None else "done",
            },
        )
        if who.screened is not None:
            await session.execute(
                text(
                    "insert into resume_assessments (application_id, workspace_id, score, "
                    "breakdown, pass_bar, passed, model, prompt_version, duration_ms) values "
                    "(:app, :ws, 70, '{}', 60, :passed, 'test', 'test', 1000)"
                ),
                values | {"passed": who.screened},
            )
        if who.interview is not None:
            interview_id = uuid.uuid4()
            finished = applied_at + who.finished_after if who.finished_after else None
            await session.execute(
                text(
                    "insert into interviews (id, workspace_id, application_id, token_hash, "
                    "format, status, drop_reason, invited_at, expires_at, completed_at) values "
                    "(:id, :ws, :app, :hash, 'voice_only', :status, :reason, :invited, "
                    ":expires, :finished)"
                ),
                values
                | {
                    "id": interview_id,
                    "hash": uuid.uuid4().hex,
                    "status": who.interview,
                    "reason": who.drop_reason,
                    "invited": applied_at + HOUR / 6,
                    "expires": now + who.expires_in,
                    "finished": finished,
                },
            )
            if who.score is not None and who.assessed_after is not None:
                await session.execute(
                    text(
                        "insert into assessments (workspace_id, application_id, interview_id, "
                        "overall_score, criteria, summary, answer_stats, rubric_snapshot, "
                        "passed, model, prompt_version, created_at) values (:ws, :app, :id, "
                        ":score, '{}', '{}', '{}', '{}', :passed, 'test', 'test', :at)"
                    ),
                    values
                    | {
                        "id": interview_id,
                        "score": who.score,
                        "passed": who.score >= 70,
                        "at": applied_at + who.assessed_after,
                    },
                )
        await session.commit()
        return candidate_id

    return db_run(tenancy, work)


# The hand-counted set. Engineering pipeline:
A = {
    "processing": Applicant(HOUR, "processing_resume"),
    "not_a_match": Applicant(2 * DAY, "resume_not_match", screened=False),
    "not_started": Applicant(2 * DAY, "invited", "jobstreet", True, "not_started"),
    "ready": Applicant(
        3 * DAY, "ready_for_review", "linkedin", True, "completed",
        finished_after=DAY, score=85, assessed_after=DAY + HOUR,
    ),
    "flagged": Applicant(
        4 * DAY, "did_not_pass", "careers", True, "completed",
        finished_after=2 * DAY, score=50, assessed_after=2 * DAY + HOUR, flagged=True,
    ),
    # Applied last week: in the 30 days but not this week.
    "expired": Applicant(
        10 * DAY, "invited", "linkedin", True, "expired", "link_expired", expires_in=-4 * DAY
    ),
    "advanced": Applicant(
        20 * DAY, "advanced", "jobstreet", True, "completed",
        finished_after=2 * DAY, score=75, assessed_after=3 * DAY,
    ),
}  # fmt: skip
# No department (Admins only), from the person who wasn't a match in Engineering.
B_READY = Applicant(
    DAY, "ready_for_review", "linkedin", True, "completed",
    finished_after=12 * HOUR, score=90, assessed_after=13 * HOUR,
)  # fmt: skip


@pytest.fixture
def world(tenancy: Tenancy) -> dict[str, Any]:
    grant(tenancy)
    engineering = draft(
        tenancy,
        title="Backend Engineer",
        department_id=str(tenancy.workspace("a").department_id),
        credits_to_reserve=20,
    )
    ok(admin(tenancy).post(f"/v1/pipelines/{engineering['id']}/publish", json=CONFIRM))
    other = draft(tenancy, title="Office Manager", credits_to_reserve=10)
    ok(admin(tenancy).post(f"/v1/pipelines/{other['id']}/publish", json=CONFIRM))
    people = {name: apply(tenancy, engineering["id"], who) for name, who in A.items()}
    returning = Applicant(**{**B_READY.__dict__, "candidate": people["not_a_match"]})
    apply(tenancy, other["id"], returning)
    return {"engineering": engineering["id"], "other": other["id"]}


def get(client: Any, path: str, **params: Any) -> dict[str, Any]:
    return ok(client.get(path, params=params))


def test_pipelines_flow_counts_this_weeks_applicants(
    tenancy: Tenancy, world: dict[str, Any]
) -> None:
    flow = get(admin(tenancy), "/v1/analytics/pipelines-flow", range="week")
    counts = {key: flow[key] for key in flow if key not in {"period", "median_hours_to_assessment"}}
    assert counts == {
        "applied": 6,
        "applied_change_pct": 500,  # 1 the week before
        "processing": 1,
        "invited": 4,
        "not_a_match": 1,
        "interviewed": 3,
        "in_progress": 0,
        "not_started": 1,
        "scoring": 0,
        "ready_for_review": 2,
        "flagged": 1,
        "did_not_pass": 0,
    }
    # Assessed this week after 13, 25 and 49 hours.
    assert flow["median_hours_to_assessment"] == 25.0

    month = get(admin(tenancy), "/v1/analytics/pipelines-flow", range="30d")
    assert (month["applied"], month["applied_change_pct"]) == (8, None)

    # A Recruiter in Engineering sees the Engineering pipeline only.
    mine = get(tenancy.client("a", Role.RECRUITER), "/v1/analytics/pipelines-flow")
    assert (mine["applied"], mine["applied_change_pct"], mine["ready_for_review"]) == (5, 400, 1)
    assert mine["median_hours_to_assessment"] == 37.0

    # Closed pipelines leave the band.
    ok(admin(tenancy).post(f"/v1/pipelines/{world['other']}/close"))
    assert get(admin(tenancy), "/v1/analytics/pipelines-flow")["applied"] == 5


def test_overview_numbers_and_the_shortlist(tenancy: Tenancy, world: dict[str, Any]) -> None:
    overview = get(admin(tenancy), "/v1/analytics/overview", range="week")
    kpis = overview["kpis"]
    assert (kpis["applicants"], kpis["applicants_change_pct"], kpis["applicants_processing"]) == (
        6,
        500,
        1,
    )
    assert (kpis["ready_for_review"], kpis["flagged"], kpis["advanced"]) == (2, 1, 1)
    assert (kpis["live_pipelines"], kpis["paused_pipelines"], kpis["scheduled_pipelines"]) == (
        2,
        0,
        0,
    )
    # Interviews finished this week took 12, 24 and 48 hours from applying.
    assert kpis["median_days_to_screen"] == 1.0
    assert overview["funnel"] == {
        "applied": 6,
        "resume_matched": 4,
        "finished_interview": 3,
        "passed_interview": 2,
        "interview_completion_pct": 75,
    }
    assert [(c["score"], c["pipeline_title"]) for c in overview["top_candidates"]] == [
        (90, "Office Manager"),
        (85, "Backend Engineer"),
    ]
    assert [(s["source"], s["applicants"], s["pass_rate"]) for s in overview["sources"]] == [
        ("linkedin", 5, 40),
        ("jobstreet", 2, 50),
        ("careers", 1, 0),
    ]
    assert overview["dropoffs"] == {"link_expired": 1, "left_unfinished": 0, "technical_issue": 0}
    assert sum(week["applied"] for week in overview["weekly"]) == 8
    attention = overview["attention"]
    assert (attention["ready_for_review"]["count"], attention["ready_for_review"]["pipelines"]) == (
        2,
        2,
    )
    assert attention["flagged"]["count"] == 1
    assert overview["credits"] is not None

    # A Hiring manager in Engineering sees shortlist numbers only.
    shortlist = get(tenancy.client("a", Role.HIRING_MANAGER), "/v1/analytics/overview")
    assert shortlist["shortlist_only"] is True
    assert (shortlist["kpis"]["ready_for_review"], shortlist["kpis"]["flagged"]) == (1, 1)
    assert shortlist["kpis"]["applicants"] is None
    assert shortlist["funnel"] is None and shortlist["sources"] is None
    assert shortlist["credits"] is None and shortlist["weekly"] is None
    assert [c["score"] for c in shortlist["top_candidates"]] == [85]
    # Its pipelines count shortlisted people only.
    assert [(p["title"], p["applicants"]) for p in shortlist["closing_soon"]] == [
        ("Backend Engineer", 3)
    ]


def test_pipeline_dashboard(tenancy: Tenancy, world: dict[str, Any]) -> None:
    path = f"/v1/pipelines/{world['engineering']}/dashboard"
    dashboard = get(admin(tenancy), path)
    assert dashboard["kpis"] | {"closes_at": None} == {
        "candidates": 7,
        "new_this_week": 5,
        "ready_for_review": 1,
        "median_days_to_assessment": 2.0,  # 25, 49 and 72 hours
        "credits_used": 7,
        "credits_reserved": 20,
        "days_remaining": 30,
        "closes_at": None,
    }
    assert dashboard["funnel"] == {
        "applied": 7,
        "invited": 5,
        "interviewed": 3,
        "ready_for_review": 1,
        "flagged": 1,
    }
    scores = {b["start"]: b["count"] for b in dashboard["scores"] if b["count"]}
    assert scores == {50: 1, 70: 1, 80: 1}
    assert (dashboard["interviewed"], dashboard["passed"], dashboard["pass_mark"]) == (3, 2, 70)
    assert [
        (s["source"], s["applicants"], s["resume_pass_rate"]) for s in dashboard["sources"]
    ] == [
        ("linkedin", 4, 67),  # one of 3 screened wasn't a match; one is still being screened
        ("jobstreet", 2, 100),
        ("careers", 1, 100),
    ]
    assert dashboard["dropoffs"] == {
        "link_expired": 1,
        "left_unfinished": 0,
        "technical_issue": 0,
        "invited": 5,
        "reinvitable": 1,
    }
    assert len(dashboard["daily"]) == 14
    assert sum(day["applicants"] for day in dashboard["daily"]) == 6

    # A Hiring manager sees the whole pipeline they can open (not just the shortlist)...
    assert get(tenancy.client("a", Role.HIRING_MANAGER), path)["kpis"]["candidates"] == 7
    # ...but pipelines outside their departments, or another workspace's, are missing.
    other = f"/v1/pipelines/{world['other']}/dashboard"
    assert tenancy.client("a", Role.RECRUITER).get(other).status_code == 404
    assert tenancy.client("b", Role.ADMIN).get(path).status_code == 404


def test_candidates_dashboard(tenancy: Tenancy, world: dict[str, Any]) -> None:
    pool = get(admin(tenancy), "/v1/candidates/dashboard")
    assert pool["kpis"] | {"new_this_month": 0} == {
        "candidates": 7,
        "new_this_month": 0,
        "applied_more_than_once": 1,
        "interviewed": 4,
        "interviewed_pipelines": 2,
        "passed_interview": 3,
        "median_days_to_assessment": 1.5,  # 13, 25, 49 and 72 hours: 37
    }
    assert pool["repeats"] == {
        "once": 6,
        "twice": 1,
        "three_times": 0,
        "four_or_more": 0,
        "returning_pass_rate": 100,
        "first_time_pass_rate": 33,
    }
    assert pool["stages"]["ready_for_review"] == 2 and pool["stages"]["advanced"] == 1
    assert sum(pool["stages"].values()) == 8
    assert sum(month["candidates"] for month in pool["new_per_month"]) == 7
    # Best pass rate first; the returning person counts once on LinkedIn.
    assert [(s["source"], s["people"], s["pass_rate"]) for s in pool["sources"]] == [
        ("linkedin", 4, 50),
        ("jobstreet", 2, 50),
        ("careers", 1, 0),
    ]

    shortlist = get(tenancy.client("a", Role.HIRING_MANAGER), "/v1/candidates/dashboard")
    assert (shortlist["shortlist_only"], shortlist["kpis"]["candidates"]) == (True, 3)
    recruiter = get(tenancy.client("a", Role.RECRUITER), "/v1/candidates/dashboard")
    assert recruiter["kpis"]["candidates"] == 7  # Engineering's applicants only


def test_other_workspaces_are_refused(tenancy: Tenancy, world: dict[str, Any]) -> None:
    for path in (
        "/v1/analytics/overview",
        "/v1/analytics/pipelines-flow",
        "/v1/candidates/dashboard",
        f"/v1/pipelines/{world['engineering']}/dashboard",
    ):
        for role in Role:
            response = tenancy.anonymous().get(
                path, headers=tenancy.headers("b", role, as_workspace="a")
            )
            assert response.status_code in {403, 404}, (path, role, response.status_code)
    # Workspace b's own numbers leave a's out.
    assert get(tenancy.client("b", Role.ADMIN), "/v1/analytics/pipelines-flow")["applied"] == 0
    assert (
        get(tenancy.client("b", Role.ADMIN), "/v1/candidates/dashboard")["kpis"]["candidates"] == 0
    )
    assert tenancy.anonymous().get("/v1/analytics/overview").status_code == 401
