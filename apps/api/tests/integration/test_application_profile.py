"""ASMT-004: the candidate profile on DASH-003's hand-counted applications, with three of the
Engineering interviews given full assessments: the payload, the comparisons in the pipeline, the
returning candidate's history, each caller's reach and the recording's signed link."""

import json
import uuid
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import Role
from app.integrations.storage import Bucket
from app.main import create_app
from tests.integration.test_analytics import get, world  # noqa: F401 (fixture)
from tests.integration.test_pipelines import admin, db_run
from tests.tenancy.harness import Tenancy


class SigningStorage:
    """Signs any path; the profile only asks for download links."""

    async def signed_download_url(
        self, bucket: Bucket, path: str, expires_in: timedelta | None = None
    ) -> str:
        return f"https://storage.test/{bucket.value}/{path}?token=t"


@pytest.fixture
def tenancy_app() -> FastAPI:
    return create_app(storage=SigningStorage())  # type: ignore[arg-type]


def evidence(start_ms: int) -> dict[str, Any]:
    return {
        "source": "interview",
        "quote": "I split the service by write path.",
        "start_ms": start_ms,
        "source_label": "Interview 3:21",
    }


RESUME = {"source": "resume", "quote": "Led the API team", "start_ms": None, "source_label": "CV"}


def criterion(score: int, weight: int, *, rich: bool = False) -> dict[str, Any]:
    return {
        "score": score,
        "weight": weight,
        "points": round(score * weight / 100, 1),
        "signals": [{"name": "System design", "score": score + 2}] if rich else [],
        "evidence": [evidence(201_000), RESUME] if rich else [],
        "held_back": "Little on testing." if rich else "",
    }


def stats(avg_answer_ms: int) -> dict[str, Any]:
    return {
        "answers": 5,
        "avg_answer_ms": avg_answer_ms,
        "avg_response_delay_ms": 2_000,
        "questions": 6,
        "follow_ups": 2,
        "candidate_questions": 1,
        "candidate_talk_ms": 600_000,
        "interviewer_talk_ms": 400_000,
        "talk_time_pct": 60,
    }


# Weighted 50/30/20: 85 = 45 + 24 + 16, 75 = 35 + 24 + 16, 50 = 25 + 15 + 10.
FULL: dict[str, dict[str, Any]] = {
    "Candidate 85": {
        "criteria": {
            "technical": criterion(90, 50, rich=True),
            "communication": criterion(80, 30),
            "culture": criterion(80, 20),
        },
        "topics": [
            {"index": 0, "title": "Warm-up", "start_ms": 0, "questions": 1, "follow_ups": 0},
            {
                "index": 1,
                "title": "APIs",
                "start_ms": 60_000,
                "questions": 2,
                "follow_ups": 1,
                "score": 88,
            },
        ],
        "summary": {"text": "Strong on APIs [1].", "refs": [evidence(201_000)]},
        "strengths": [{"title": "API design", "reason": "Clear trade-offs."}],
        "probes": [{"title": "Testing", "reason": "Said little about it."}],
        "answer_stats": stats(90_000),
        "fit": "strong_fit",
    },
    "Candidate 75": {
        "criteria": {
            "technical": criterion(70, 50),
            "communication": criterion(80, 30),
            "culture": criterion(80, 20),
        },
        "answer_stats": stats(70_000),
    },
    "Candidate 50": {
        "criteria": {
            "technical": criterion(50, 50),
            "communication": criterion(50, 30),
            "culture": criterion(50, 20),
        },
    },
}


@pytest.fixture
def people(tenancy: Tenancy, world: dict[str, Any]) -> dict[str, dict[str, str]]:  # noqa: F811
    """Fills three assessments and returns each application's and candidate's IDs by name."""

    async def work(session: AsyncSession) -> dict[str, dict[str, str]]:
        for name, content in FULL.items():
            await session.execute(
                text(
                    "update assessments s set criteria = cast(:criteria as jsonb), "
                    "topics = cast(:topics as jsonb), summary = cast(:summary as jsonb), "
                    "strengths = cast(:strengths as jsonb), probes = cast(:probes as jsonb), "
                    "answer_stats = cast(:stats as jsonb), fit = :fit, "
                    "rubric_snapshot = cast(:rubric as jsonb) "
                    "from applications a join candidates c on c.id = a.candidate_id "
                    "where s.application_id = a.id and c.full_name = :name "
                    "and a.pipeline_id = :pipeline"
                ),
                {
                    "name": name,
                    "pipeline": uuid.UUID(world["engineering"]),
                    "criteria": json.dumps(content["criteria"]),
                    "topics": json.dumps(content.get("topics", [])),
                    "summary": json.dumps(content.get("summary", {})),
                    "strengths": json.dumps(content.get("strengths", [])),
                    "probes": json.dumps(content.get("probes", [])),
                    "stats": json.dumps(content.get("answer_stats", {})),
                    "fit": content.get("fit"),
                    "rubric": json.dumps({"pass_mark": 70}),
                },
            )
        rows = await session.execute(
            text(
                "select c.full_name, a.id, a.candidate_id, a.stage, p.title from applications a "
                "join candidates c on c.id = a.candidate_id "
                "join pipelines p on p.id = a.pipeline_id where a.workspace_id = :ws"
            ),
            {"ws": tenancy.workspace("a").id},
        )
        found = {
            f"{name}/{title}/{stage}": {"application": str(app_id), "candidate": str(candidate)}
            for name, app_id, candidate, stage, title in rows
        }
        await session.commit()
        return found

    found = db_run(tenancy, work)
    return {
        "ready": found["Candidate 85/Backend Engineer/ready_for_review"],
        "advanced": found["Candidate 75/Backend Engineer/advanced"],
        "flagged": found["Candidate 50/Backend Engineer/did_not_pass"],
        "not_a_match": found["Candidate 0/Backend Engineer/resume_not_match"],
        "returning": found["Candidate 0/Office Manager/ready_for_review"],
        "invited": next(value for key, value in found.items() if key.endswith("/invited")),
    }


def profile_of(client: Any, application_id: str) -> dict[str, Any]:
    return get(client, f"/v1/applications/{application_id}")


def test_profile_shows_the_score_its_calculation_and_evidence(
    tenancy: Tenancy, people: dict[str, dict[str, str]]
) -> None:
    profile = profile_of(admin(tenancy), people["ready"]["application"])
    assert profile["candidate"]["id"] == people["ready"]["candidate"]
    assert (profile["stage"], profile["fit"], profile["flagged"], profile["source"]) == (
        "ready_for_review",
        None,  # the list's overlay; the assessment's own fit is below
        False,
        "linkedin",
    )
    assert profile["pipeline"]["title"] == "Backend Engineer"
    assert profile["pipeline"]["rubric_locked_at"] is not None

    assessment = profile["assessment"]
    assert (assessment["overall_score"], assessment["passed"], assessment["fit"]) == (
        85,
        True,
        "strong",
    )
    assert assessment["pass_mark"] == 70
    technical = assessment["criteria"]["technical"]
    assert (technical["score"], technical["weight"], technical["points"]) == (90, 50, 45.0)
    assert technical["signals"] == [{"name": "System design", "score": 92}]
    assert [(e["source"], e["start_ms"]) for e in technical["evidence"]] == [
        ("interview", 201_000),
        ("resume", None),
    ]
    assert technical["held_back"] == "Little on testing."
    assert sum(c["points"] for c in assessment["criteria"].values()) == 85
    assert assessment["evidence_count"] == 2
    assert [(t["title"], t["score"]) for t in assessment["topics"]] == [
        ("Warm-up", None),
        ("APIs", 88),
    ]
    assert assessment["summary"]["refs"][0]["start_ms"] == 201_000
    assert assessment["strengths"] == [{"title": "API design", "reason": "Clear trade-offs."}]
    assert assessment["answer_stats"]["avg_answer_ms"] == 90_000

    assert [step["kind"] for step in profile["journey"]] == [
        "applied",
        "resume_matched",
        "invited",
        "interview_finished",
        "ready_for_review",
    ]
    assert profile["interview"]["recording_ready"] is False


def test_comparisons_in_the_pipeline(tenancy: Tenancy, people: dict[str, dict[str, str]]) -> None:
    comparison = profile_of(admin(tenancy), people["ready"]["application"])["comparison"]
    # Three interviews were assessed in Engineering: 85, 75 and 50.
    assert (comparison["interviewed"], comparison["rank"], comparison["passed"]) == (3, 1, 2)
    assert comparison["average"] == 70
    assert {b["start"]: b["count"] for b in comparison["distribution"] if b["count"]} == {
        50: 1,
        70: 1,
        80: 1,
    }
    assert comparison["criteria"]["technical"] == {"average": 70, "passed_average": 80}
    assert comparison["criteria"]["communication"] == {"average": 70, "passed_average": 80}
    # Only two have answer stats.
    assert comparison["answer_stats"]["avg_answer_ms"] == 80_000

    lowest = profile_of(admin(tenancy), people["flagged"]["application"])
    assert (lowest["comparison"]["rank"], lowest["flagged"]) == (3, True)
    assert lowest["assessment"]["passed"] is False


def test_no_assessment_yet(tenancy: Tenancy, people: dict[str, dict[str, str]]) -> None:
    profile = profile_of(admin(tenancy), people["not_a_match"]["application"])
    assert profile["assessment"] is None and profile["comparison"] is None
    assert profile["interview"] is None and profile["integrity"] is None
    assert profile["resume"]["passed"] is False
    assert [step["kind"] for step in profile["journey"]] == ["applied", "resume_not_matched"]


def test_history_follows_the_callers_reach(
    tenancy: Tenancy, people: dict[str, dict[str, str]]
) -> None:
    # The person who wasn't a match in Engineering applied again to Office Manager.
    history = profile_of(admin(tenancy), people["returning"]["application"])["history"]
    assert [(item["pipeline_title"], item["current"]) for item in history] == [
        ("Backend Engineer", False),
        ("Office Manager", True),
    ]
    # A Recruiter in Engineering can't see the No department pipeline, there or in the history.
    recruiter = tenancy.client("a", Role.RECRUITER)
    mine = profile_of(recruiter, people["not_a_match"]["application"])["history"]
    assert [item["pipeline_title"] for item in mine] == ["Backend Engineer"]
    response = recruiter.get(f"/v1/applications/{people['returning']['application']}")
    assert response.status_code == 404


def test_hiring_managers_read_the_shortlist_only(
    tenancy: Tenancy, people: dict[str, dict[str, str]]
) -> None:
    manager = tenancy.client("a", Role.HIRING_MANAGER)
    for key in ("ready", "flagged", "advanced"):
        assert profile_of(manager, people[key]["application"])["id"] == people[key]["application"]
    for key in ("invited", "not_a_match"):
        response = manager.get(f"/v1/applications/{people[key]['application']}")
        assert response.status_code == 404, key
    # Comparisons are aggregates: the same for every caller.
    assert (
        profile_of(manager, people["ready"]["application"])["comparison"]
        == profile_of(admin(tenancy), people["ready"]["application"])["comparison"]
    )


def test_other_workspaces_and_signed_out(
    tenancy: Tenancy, people: dict[str, dict[str, str]]
) -> None:
    application_id = people["ready"]["application"]
    tenancy.assert_hidden_from_other_workspace("GET", f"/v1/applications/{application_id}")
    tenancy.assert_hidden_from_other_workspace(
        "GET", f"/v1/applications/{application_id}/recording-url"
    )
    assert tenancy.anonymous().get(f"/v1/applications/{application_id}").status_code == 401
    assert tenancy.client("a", Role.ADMIN).get(f"/v1/applications/{uuid.uuid4()}").status_code == (
        404
    )


def test_recording_url(tenancy: Tenancy, people: dict[str, dict[str, str]]) -> None:
    application_id = people["ready"]["application"]
    url = f"/v1/applications/{application_id}/recording-url"
    response = admin(tenancy).get(url)
    assert (response.status_code, response.json()["code"]) == (404, "recording_not_ready")

    async def ready(session: AsyncSession) -> str:
        path = f"{tenancy.workspace('a').id}/{uuid.uuid4()}/recording.m4a"
        await session.execute(
            text(
                "update interviews set recording_status = 'ready', recording_path = :path, "
                "duration_seconds = 1500 where application_id = :app"
            ),
            {"path": path, "app": uuid.UUID(application_id)},
        )
        await session.commit()
        return path

    path = db_run(tenancy, ready)
    assert profile_of(admin(tenancy), application_id)["interview"]["recording_ready"] is True
    recording = get(tenancy.client("a", Role.HIRING_MANAGER), url)
    assert recording["url"] == f"https://storage.test/recordings/{path}?token=t"
    # A voice-only interview plays as audio, with no poster frame.
    assert (recording["kind"], recording["poster_url"], recording["duration_seconds"]) == (
        "audio",
        None,
        1500,
    )
