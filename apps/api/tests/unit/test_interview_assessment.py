"""ASMT-001 (ADR-011, FR-ASMT-02..05, G2, G4): the transcript reaches the model as numbered turns
with the candidate's name masked and other voices left out; evidence must quote a candidate turn
or the résumé word for word, and an answer left without enough of it is never used; the overall
score, pass/fail, fit, topics and answer patterns are computed in code."""

import asyncio
from typing import Any

import pytest
from pydantic import BaseModel

from app.ai import fakes
from app.ai.client import AIOutputError
from app.ai.prompts import Prompt
from app.ai.schemas.interview_assessment import InterviewAssessment
from app.interview import assessment
from app.interview.assessment import Context, Line, Rubric
from app.screening.redact import redact_rules

RESUME = (
    "Senior Backend Engineer, PayLane, 2022 - present\n"
    "Sharded, multi-region PostgreSQL handling 4M transactions a day."
)
LINES = [
    Line(0, 6_000, "interviewer", "Hi, thanks for joining. Walk me through your role.", 0),
    Line(7_000, 15_000, "candidate", "I'm Bea Garcia. I lead the payments ledger team.", 0),
    Line(15_500, 20_000, "candidate", "Most of my time goes into the storage layer.", 0),
    Line(21_000, 26_000, "interviewer", "How did you pick a shard key?", 1),
    Line(29_000, 41_000, "candidate", "We shard by merchant ID so reads stay on one shard.", 1),
    Line(41_500, 43_000, "other", "Dinner is ready.", 1),
    Line(44_000, 47_000, "interviewer", "What about the hot shards?", 1),
    Line(48_000, 60_000, "candidate", "We split the top merchants into sub-shards.", 1),
    Line(61_000, 64_000, "interviewer", "What would you like to ask me?", 2),
    Line(66_000, 70_000, "candidate", "What does on-call look like for this team?", 2),
]
CLAIMS = [
    {"requirement": "PostgreSQL at scale", "type": "must_have", "found": "Sharded", "strength": 3},
    {"requirement": "Kubernetes", "type": "nice_to_have", "found": "Listed", "strength": 1},
]
RUBRIC = Rubric(weight_technical=50, weight_communication=30, weight_culture=20, pass_mark=70)


def context(**changes: Any) -> Context:
    values: dict[str, Any] = {
        "job_title": "Senior Backend Engineer",
        "job_description": "Build and run payment APIs.",
        "seniority": "senior",
        "open_to": [],
        "skills_to_probe": ["System design", "Go", "PostgreSQL"],
        "topics": ["Getting started", "Sharding", "Your questions"],
        "resume_text": RESUME,
        "claims": CLAIMS,
        "must_haves_met": True,
        **changes,
    }
    return Context(**values)


def masked(text: str) -> str:
    return redact_rules(text, ["Bea Garcia"]).text


TURNS = assessment.turns(LINES, masked)


def fake(**criteria: int) -> dict[str, Any]:
    """The AI_FAKE answer for this transcript, with criterion scores changed."""
    answer = fakes.interview_assessment(assessment.variables(context(), TURNS))
    for name, score in criteria.items():
        answer["criteria"][name]["score"] = score
    return answer


def parsed(answer: dict[str, Any]) -> InterviewAssessment:
    return InterviewAssessment.model_validate(answer)


def test_turns_join_one_speaker_per_topic_and_leave_out_other_voices() -> None:
    assert [(t.number, t.speaker, t.topic_index) for t in TURNS] == [
        (1, "interviewer", 0),
        (2, "candidate", 0),
        (3, "interviewer", 1),
        (4, "candidate", 1),
        (5, "interviewer", 1),
        (6, "candidate", 1),
        (7, "interviewer", 2),
        (8, "candidate", 2),
    ]
    joined = TURNS[1]
    assert (joined.start_ms, joined.end_ms, joined.speech_ms) == (7_000, 20_000, 12_500)
    found = assessment.variables(context(), TURNS)
    transcript = found["transcript"]
    assert found["topics_to_score"] == "1, 2, 3"
    assert "Bea" not in transcript and "Garcia" not in transcript
    assert "#2 [00:07] Candidate: I'm [NAME]. I lead the payments ledger team." in transcript
    assert "--- Topic 2: Sharding ---" in transcript
    assert "Dinner" not in transcript


def test_the_fake_answer_passes_the_checks() -> None:
    assert assessment.problems(parsed(fake()), context(), TURNS) == []


def test_overall_score_is_the_weighted_sum_rounded_half_up() -> None:
    decision = assessment.decide(
        parsed(fake(technical=94, communication=88, culture=86)), context(), TURNS, RUBRIC
    )
    # 94 x 0.5 + 88 x 0.3 + 86 x 0.2 = 47 + 26.4 + 17.2 = 90.6
    assert decision.overall_score == 91
    assert [decision.criteria[name]["points"] for name in assessment.CRITERIA] == [
        47.0,
        26.4,
        17.2,
    ]
    assert decision.passed and decision.fit == "strong_fit"
    assert decision.rubric_snapshot == {
        "weight_technical": 50,
        "weight_communication": 30,
        "weight_culture": 20,
        "pass_mark": 70,
    }


@pytest.mark.parametrize(
    ("scores", "must_haves_met", "passed", "fit"),
    [
        ({"technical": 70, "communication": 70, "culture": 70}, True, True, "good_fit"),
        ({"technical": 69, "communication": 70, "culture": 70}, True, True, "good_fit"),
        ({"technical": 68, "communication": 70, "culture": 70}, True, False, None),
        ({"technical": 90, "communication": 90, "culture": 90}, False, True, "good_fit"),
    ],
)
def test_pass_mark_and_fit(
    scores: dict[str, int], must_haves_met: bool, passed: bool, fit: str | None
) -> None:
    # 69 x 0.5 + 70 x 0.5 = 69.5 → 70 (at the pass mark passes); 68 → 69 fails.
    decision = assessment.decide(
        parsed(fake(**scores)), context(must_haves_met=must_haves_met), TURNS, RUBRIC
    )
    assert (decision.passed, decision.fit) == (passed, fit)


def test_evidence_must_quote_the_candidate_word_for_word() -> None:
    answer = fake()
    evidence = answer["criteria"]["technical"]["evidence"]
    evidence[0]["quote"] = "I designed the whole platform alone"  # never said
    evidence[1]["turn"] = 3  # the interviewer's question, not the candidate
    issues = assessment.problems(parsed(answer), context(), TURNS)
    assert issues == ["technical_evidence"]

    # A résumé quote counts, but a criterion still needs one from the interview.
    evidence[0] = {
        "source": "resume",
        "turn": None,
        "quote": "PostgreSQL handling 4M",
        "label": "r",
    }
    evidence[1] = {
        "source": "resume",
        "turn": None,
        "quote": "Senior Backend Engineer, PayLane",
        "label": "r",
    }
    assert assessment.problems(parsed(answer), context(), TURNS) == ["technical_evidence"]
    evidence.append(
        {"source": "interview", "turn": 4, "quote": "shard by merchant ID", "label": "Shard key"}
    )
    assert assessment.problems(parsed(answer), context(), TURNS) == []
    row = assessment.decide(parsed(answer), context(), TURNS, RUBRIC).criteria["technical"]
    assert [item["source"] for item in row["evidence"]] == ["resume", "resume", "interview"]
    assert row["evidence"][2]["start_ms"] == 29_000


def test_summary_is_checked_and_unscored_topics_are_kept() -> None:
    answer = fake()
    answer["summary"]["refs"][1]["quote"] = "invented"
    assert assessment.problems(parsed(answer), context(), TURNS) == ["summary_ref_2"]
    answer = fake()
    answer["summary"]["text"] = "Gave concrete examples [3]. Explained choices clearly [4]."
    assert assessment.problems(parsed(answer), context(), TURNS) == ["summary_uncited"]

    # A citation of a reference the summary doesn't list is taken out; the answer is kept.
    answer = fake()
    answer["summary"]["text"] += " Asked about on-call [3]."
    # A topic left unscored doesn't discard the answer either; it is kept without a score.
    answer["topics"] = [topic for topic in answer["topics"] if topic["topic"] != 2]
    assert assessment.problems(parsed(answer), context(), TURNS) == []
    assert assessment.unscored_topics(parsed(answer), TURNS) == [1]
    decision = assessment.decide(parsed(answer), context(), TURNS, RUBRIC)
    assert decision.summary["text"] == (
        "Gave concrete examples from recent work [1]. Explained choices clearly [2]."
        " Asked about on-call."
    )
    assert [topic["score"] for topic in decision.topics] == [80, None, 80]


def test_an_unusable_answer_is_asked_for_once_more_then_fails() -> None:
    class Answers:
        model = "stub"

        def __init__(self, answers: list[dict[str, Any]]) -> None:
            self.answers = answers
            self.calls = 0

        async def structured[T: BaseModel](
            self, *, prompt: Prompt, schema: type[T], **kwargs: Any
        ) -> T:
            self.calls += 1
            return schema.model_validate(self.answers.pop(0))

    bad = fake()
    bad["criteria"]["culture"]["evidence"] = []
    ai = Answers([bad, fake()])
    asyncio.run(assessment.assess(ai, context(), TURNS))
    assert ai.calls == 2

    ai = Answers([bad, bad])
    with pytest.raises(AIOutputError):
        asyncio.run(assessment.assess(ai, context(), TURNS))


def test_topics_claims_and_answer_patterns_come_from_the_transcript() -> None:
    answer = fake()
    answer["claims_checked"] = [{"claim": 1, "status": "confirmed", "turn": 4}]
    answer["turns"] = {"questions": [1, 3, 7, 4], "follow_ups": [5, 3], "candidate_questions": [8]}
    decision = assessment.decide(parsed(answer), context(), TURNS, RUBRIC)

    assert [
        (t["index"], t["title"], t["start_ms"], t["questions"], t["follow_ups"])
        for t in decision.topics
    ] == [
        (0, "Getting started", 0, 1, 0),
        (1, "Sharding", 21_000, 1, 1),
        (2, "Your questions", 61_000, 1, 0),
    ]
    assert [(c["requirement"], c["status"], c["start_ms"]) for c in decision.claims_checked] == [
        ("PostgreSQL at scale", "confirmed", 29_000),
        ("Kubernetes", "not_covered", None),
    ]
    stats = decision.answer_stats
    # Answers: 7-20 s, 29-41 s, 48-60 s, 66-70 s. Delays: 1, 3, 1, 2 s. Turn 4 is the
    # candidate's, so it isn't a question; turn 3 is a question, not also a follow-up.
    assert stats == {
        "answers": 4,
        "avg_answer_ms": 10_250,
        "avg_response_delay_ms": 1_750,
        "questions": 3,
        "follow_ups": 1,
        "candidate_questions": 1,
        "candidate_talk_ms": 40_500,
        "interviewer_talk_ms": 17_000,
        "talk_time_pct": 70,
    }
