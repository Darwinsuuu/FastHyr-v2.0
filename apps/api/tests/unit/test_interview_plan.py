"""INTV-001 (FR-INTV-01, G2, G3): a plan is used only when it has 4-7 topics with the warm-up
first and the candidate's questions last, 1-3 seeds per topic, every skill to probe covered,
résumé quotes copied from the redacted résumé, and no personal detail; otherwise it is asked for
once more and then fails. The fallback plan covers every skill and holds nothing about the
candidate, and the pipeline's settings shape the prompt."""

import asyncio
import uuid
from typing import Any

import pytest
from pydantic import BaseModel

from app.ai import fakes
from app.ai.client import AIOutputError
from app.ai.prompts import Prompt, load_prompt
from app.ai.schemas.interview_plan import InterviewPlan
from app.interview import plan as planning
from app.interview.plan import Context

RESUME = (
    "Senior Backend Engineer, PayLane, 2022 - present\n"
    "Sharded, multi-region PostgreSQL handling 4M transactions a day.\n"
    "Built gRPC services in Go; cut p99 latency by 40%.\n"
    "Education\n[SCHOOL]\nBS Computer Science, [YEAR]"
)
SKILLS = ["API design", "PostgreSQL", "Incident response"]
NAME = "Maria Santos"


def context(**changes: Any) -> Context:
    values: dict[str, Any] = {
        "job_title": "Senior Backend Engineer",
        "job_description": "Design and run payment APIs.",
        "seniority": "senior",
        "tone": "warm",
        "interview_format": "video_voice",
        "skills_to_probe": SKILLS,
        "must_haves": ["Go in production"],
        "open_to": [],
        "company_about": "Payments for 2,000 merchants.",
        "resume_text": RESUME,
        "screening_claims": [{"requirement": "PostgreSQL at scale", "found": "4M a day"}],
    }
    return Context(**{**values, **changes})


def answer(**changes: Any) -> dict[str, Any]:
    """A plan that passes every check (the fake builder's), with `changes` applied."""
    plan = fakes.interview_plan(planning.variables(context()))
    plan.update(changes)
    return plan


def problems(plan: dict[str, Any], name: str | None = NAME, **changes: Any) -> list[str]:
    return planning.problems(InterviewPlan.model_validate(plan), context(**changes), name)


def test_the_fake_plan_passes_every_check() -> None:
    plan = answer()
    assert problems(plan) == []
    assert [topic["kind"] for topic in plan["topics"]] == [
        "warm_up",
        "skills",
        "skills",
        "skills",
        "candidate_questions",
    ]


def test_order_and_counts_are_checked() -> None:
    topics = answer()["topics"]
    assert problems(answer(topics=topics[1:])) == ["warm_up_first"]
    assert problems(answer(topics=topics[:-1])) == ["candidate_questions_last"]
    assert "topic_count" in problems(answer(topics=[topics[0], topics[1], topics[-1]]))
    too_many = [topics[0], *([topics[1]] * 6), topics[-1]]
    assert "topic_count" in problems(answer(topics=too_many))
    swapped = [topics[0], topics[-1], *topics[1:-1]]
    assert "candidate_questions_last" in problems(answer(topics=swapped))

    no_seeds = [*topics[:2], {**topics[2], "seeds": []}, *topics[3:]]
    assert problems(answer(topics=no_seeds)) == ["topic_3_seeds"]
    four = [{**topics[1], "seeds": topics[1]["seeds"] * 4}]
    assert problems(answer(topics=[topics[0], *four, *topics[2:]])) == ["topic_2_seeds"]


def test_every_skill_to_probe_must_be_covered() -> None:
    topics = answer()["topics"]
    dropped = [topic for topic in topics if topic["skills"] != ["PostgreSQL"]]
    dropped.insert(2, {**topics[1], "skills": ["API design"]})
    assert problems(answer(topics=dropped)) == ["skill_2_not_covered"]
    # Matched ignoring case and punctuation, but only in skills topics.
    renamed = [*topics[:2], {**topics[2], "skills": ["postgresql"]}, *topics[3:]]
    assert problems(answer(topics=renamed)) == []
    in_warm_up = [{**topics[0], "skills": ["PostgreSQL"]}, topics[1], *topics[3:]]
    assert problems(answer(topics=in_warm_up)) == ["skill_2_not_covered"]


def test_resume_quotes_must_come_from_the_resume() -> None:
    topics = answer()["topics"]
    seed = {"question": "How did you shard it?", "resume_quote": "Sharded, multi-region PostgreSQL"}
    good = [*topics[:2], {**topics[2], "seeds": [seed]}, *topics[3:]]
    assert problems(answer(topics=good)) == []

    invented = {**seed, "resume_quote": "Led a team of 40 engineers"}
    bad = [*topics[:2], {**topics[2], "seeds": [invented]}, *topics[3:]]
    assert problems(answer(topics=bad)) == ["topic_3_seed_1_quote"]

    claim = {"claim": "Led 40 engineers", "resume_quote": "Led a team of 40", "skill": "API design"}
    assert problems(answer(claims_to_verify=[claim])) == ["claim_1_quote"]
    assert problems(answer(claims_to_verify=[{**claim, "resume_quote": ""}])) == ["claim_1_quote"]


@pytest.mark.parametrize(
    "question",
    [
        "What did you study at [SCHOOL]?",
        "Tell me about your work in [ADDRESS].",
        "Maria, tell me about PayLane.",
        "How did Santos approach the migration?",
    ],
)
def test_no_personal_detail_reaches_the_plan(question: str) -> None:
    topics = answer()["topics"]
    seed = {"question": question, "resume_quote": ""}
    leaked = [*topics[:2], {**topics[2], "seeds": [seed]}, *topics[3:]]
    assert problems(answer(topics=leaked)) == ["personal_detail"]


def test_a_quote_holding_a_mask_is_a_personal_detail() -> None:
    topics = answer()["topics"]
    seed = {"question": "Tell me about your studies.", "resume_quote": "[SCHOOL]"}
    leaked = [*topics[:2], {**topics[2], "seeds": [seed]}, *topics[3:]]
    assert "personal_detail" in problems(answer(topics=leaked))


def test_short_name_parts_and_other_words_are_not_flagged() -> None:
    topics = answer()["topics"]
    seed = {"question": "How will you benchmark the API?", "resume_quote": ""}
    plan = answer(topics=[*topics[:2], {**topics[2], "seeds": [seed]}, *topics[3:]])
    assert problems(plan, name="Will Ng") == []
    assert problems(plan, name="Mark Li") == []


def test_settings_shape_the_prompt() -> None:
    variables = planning.variables(context())
    prompt = load_prompt(*planning.PROMPT).render(variables)
    assert "Warm: friendly" in prompt.system
    assert "about 30 minutes" in prompt.system
    assert "Expected seniority: Senior" in prompt.user
    assert "1. API design\n2. PostgreSQL\n3. Incident response" in prompt.user
    assert "- PostgreSQL at scale: 4M a day" in prompt.user
    assert "Payments for 2,000 merchants." in prompt.user
    assert "also open to" not in prompt.system

    stepped = planning.variables(context(open_to=["step_up", "returners"]))
    assert stepped["seniority"] == "Mid level"
    assert "never ask about time away from work" in stepped["open_to_rules"]

    plain = planning.variables(
        context(tone=None, skills_to_probe=[], resume_text="", company_about="")
    )
    assert plain["tone"].startswith("Professional")
    assert plain["skills_to_probe"] == "1. Go in production"
    assert (plain["resume_text"], plain["company_about"]) == ("Not available", "Not provided")


def test_fallback_covers_every_skill_with_nothing_about_the_candidate() -> None:
    plan = planning.fallback(context())
    assert problems(plan.model_dump()) == []
    assert all(seed.resume_quote == "" for topic in plan.topics for seed in topic.seeds)
    assert plan.claims_to_verify == []

    many = [f"Skill {index}" for index in range(1, 9)]
    grouped = planning.fallback(context(skills_to_probe=many))
    assert len(grouped.topics) == 7
    assert sorted(skill for topic in grouped.topics for skill in topic.skills) == sorted(many)
    assert problems(grouped.model_dump(), skills_to_probe=many) == []


class StubAI:
    model = "stub"

    def __init__(self, answers: list[dict[str, Any]]) -> None:
        self.answers = answers
        self.calls = 0

    async def structured[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt: Prompt,
        variables: dict[str, str],
        schema: type[T],
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        temperature: float | None = None,
    ) -> T:
        self.calls += 1
        return schema.model_validate(self.answers[min(self.calls, len(self.answers)) - 1])


def test_an_unusable_plan_is_asked_for_once_more() -> None:
    topics = answer()["topics"]
    bad = answer(topics=topics[1:])
    ai = StubAI([bad, answer()])
    plan = asyncio.run(planning.generate(ai, context(), candidate_name=NAME))
    assert ai.calls == 2
    assert plan.topics[0].kind == "warm_up"

    ai = StubAI([bad])
    with pytest.raises(AIOutputError):
        asyncio.run(planning.generate(ai, context(), candidate_name=NAME))
    assert ai.calls == 2
