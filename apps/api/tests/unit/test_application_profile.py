"""ASMT-004: the profile's comparisons in a pipeline, worked by hand."""

import uuid
from typing import Any

from app.models import Assessment
from app.repositories.application_profile import PipelineScore
from app.services.application_profile import bucket_of, compare, topic_averages


def score(
    overall: int,
    passed: bool,
    technical: int | None = None,
    topics: list[dict[str, Any]] | None = None,
    application_id: uuid.UUID | None = None,
) -> PipelineScore:
    criteria = {"technical": {"score": technical}} if technical is not None else {}
    return PipelineScore(
        application_id or uuid.uuid4(), overall, passed, criteria, topics or [], {}
    )


def assessment(overall: int, application_id: uuid.UUID) -> Assessment:
    return Assessment(
        application_id=application_id,
        overall_score=overall,
        passed=overall >= 70,
        criteria={"technical": {"score": overall}},
        topics=[],
        answer_stats={},
    )


def test_buckets() -> None:
    assert [bucket_of(value) for value in (0, 49, 50, 69, 70, 89, 90, 100)] == [
        0,
        0,
        50,
        60,
        70,
        80,
        90,
        90,
    ]


def test_rank_ties_and_rounding() -> None:
    own = uuid.uuid4()
    scores = [
        score(80, True, 81, application_id=own),
        score(80, True, 80),
        score(91, True, 90),
        score(40, False, 40),
    ]
    result = compare(assessment(80, own), scores)
    # Ties share the better rank.
    assert (result.interviewed, result.rank, result.passed) == (4, 2, 3)
    # (80 + 80 + 91 + 40) / 4 = 72.75
    assert result.average == 73
    # (81 + 80 + 90 + 40) / 4 = 72.75; passed (81 + 80 + 90) / 3 = 83.67
    assert (result.criteria.technical.average, result.criteria.technical.passed_average) == (
        73,
        84,
    )
    assert result.criteria.culture.passed_average is None
    assert {b.start: b.count for b in result.distribution} == {
        0: 1,
        50: 0,
        60: 0,
        70: 0,
        80: 2,
        90: 1,
    }
    assert result.answer_stats is None


def test_half_up_and_the_own_interview_counted_once() -> None:
    own = uuid.uuid4()
    # Not in the list yet (a fresh assessment): it is added, once.
    result = compare(assessment(71, own), [score(70, True, 70)])
    assert (result.interviewed, result.average) == (2, 71)  # 70.5 rounds up


def test_topic_averages_match_by_kind_and_skill() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    plans = {
        a: [
            {"kind": "warm_up", "skills": []},
            {"kind": "skills", "skills": ["Python", "SQL"]},
            {"kind": "candidate_questions", "skills": []},
        ],
        b: [
            {"kind": "warm_up", "skills": []},
            {"kind": "skills", "skills": ["SQL"]},
            {"kind": "skills", "skills": ["Go"]},
        ],
    }
    scores = [
        score(
            80,
            True,
            topics=[{"index": 0, "score": 60}, {"index": 1, "score": 90}],
            application_id=a,
        ),
        score(
            70,
            True,
            topics=[
                {"index": 0, "score": 71},
                {"index": 1, "score": 81},
                {"index": 2, "score": 50},
            ],
            application_id=b,
        ),
    ]
    averages = topic_averages(scores, plans, plans[a])
    # Warm-ups: (60 + 71) / 2 = 65.5; SQL: (90 + 81) / 2 = 85.5; nobody scored a candidate
    # questions topic.
    assert averages == {0: 66, 1: 86, 2: None}
    # Go is only in b's plan.
    assert topic_averages(scores, plans, plans[b])[2] == 50
