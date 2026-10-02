"""INTV-001 (FR-INTV-01, G2, G3): a plan is used only when it has 4-7 topics with the warm-up
first and the candidate's questions last, 1-3 seeds per topic, every skill to probe covered (by
number, so a reworded skill can't miss), and no personal detail; otherwise it is asked for once
more and then fails. Résumé quotes the résumé doesn't contain are dropped, never shown. The
fallback plan covers every skill and holds nothing about the candidate, and the pipeline's
settings shape the prompt."""

import asyncio
import uuid
from typing import Any

import pytest
from pydantic import BaseModel

from app.ai import fakes
from app.ai.client import AIOutputError
from app.ai.prompts import Prompt, load_prompt
from app.ai.schemas.interview_plan import InterviewPlan, PlanAnswer
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


def resolved(plan: dict[str, Any], **changes: Any) -> tuple[InterviewPlan, list[str]]:
    return planning.resolve(PlanAnswer.model_validate(plan), context(**changes))


def problems(plan: dict[str, Any], name: str | None = NAME, **changes: Any) -> list[str]:
    stored, found = resolved(plan, **changes)
    return found + planning.problems(stored, context(**changes), name)


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
    all_skills = {**topics[1], "skills": [1, 2, 3]}
    assert problems(answer(topics=[topics[0], all_skills, topics[-1]])) == ["topic_count"]
    too_many = [topics[0], *([topics[1]] * 6), topics[-1]]
    assert "topic_count" in problems(answer(topics=too_many))
    swapped = [topics[0], topics[-1], *topics[1:-1]]
    assert "candidate_questions_last" in problems(answer(topics=swapped))

    no_seeds = [*topics[:2], {**topics[2], "seeds": []}, *topics[3:]]
    assert problems(answer(topics=no_seeds)) == ["topic_3_seeds"]
    four = [{**topics[1], "seeds": topics[1]["seeds"] * 4}]
    assert problems(answer(topics=[topics[0], *four, *topics[2:]])) == ["topic_2_seeds"]


def test_every_skill_to_probe_is_covered() -> None:
    topics = answer()["topics"]
    # Skills come back by number and are stored by name; one topic may cover several.
    merged = [topics[0], {**topics[1], "skills": [1, 2, 2]}, *topics[3:]]
    stored, found = resolved(answer(topics=merged))
    assert (stored.topics[1].skills, found) == (["API design", "PostgreSQL"], [])
    # A number outside the list is a problem.
    wrong = [*topics[:2], {**topics[2], "skills": [2, 9]}, *topics[3:]]
    assert problems(answer(topics=wrong)) == ["topic_3_skill_number"]


def test_a_skill_the_model_left_out_is_added_by_code() -> None:
    topics = answer()["topics"]
    # Joins the skills topic that talks about it...
    about_it = {**topics[1], "title": "Running PostgreSQL", "skills": [1]}
    stored, _ = resolved(answer(topics=[topics[0], about_it, topics[3], topics[4]]))
    assert stored.topics[1].skills == ["API design", "PostgreSQL"]
    assert problems(answer(topics=[topics[0], about_it, topics[3], topics[4]])) == []
    # ...else gets its own plain topic before the candidate's questions...
    without = [topic for topic in topics if topic["skills"] != [2]]
    stored, _ = resolved(answer(topics=without))
    assert [topic.skills for topic in stored.topics][-2:] == [["PostgreSQL"], []]
    assert stored.topics[-2].seeds[0].resume_quote == ""
    # ...else, with 7 topics already, joins the last skills topic. Warm-up skills don't count.
    full = [{**topics[0], "skills": [2]}, *([topics[1]] * 5), topics[-1]]
    stored, _ = resolved(answer(topics=full))
    assert stored.topics[0].skills == []
    assert stored.topics[5].skills == ["API design", "PostgreSQL", "Incident response"]
    assert problems(answer(topics=full)) == []


def test_quotes_the_resume_does_not_contain_are_dropped() -> None:
    topics = answer()["topics"]
    seed = {"question": "How did you shard it?", "resume_quote": "Sharded, multi-region PostgreSQL"}
    invented = {"question": "How did you lead them?", "resume_quote": "Led a team of 40 engineers"}
    masked = {
        "question": "What did you learn there?",
        "resume_quote": "BS Computer Science, [YEAR]",
    }
    mixed = [*topics[:2], {**topics[2], "seeds": [seed, invented, masked]}, *topics[3:]]
    stored, found = resolved(answer(topics=mixed))
    assert found == []
    assert [s.resume_quote for s in stored.topics[2].seeds] == [seed["resume_quote"], "", ""]
    assert [s.question for s in stored.topics[2].seeds][1] == invented["question"]
    assert problems(answer(topics=mixed)) == []

    good = {
        "claim": "Big tables",
        "resume_quote": "handling 4M transactions",
        "skill": "PostgreSQL",
    }
    bad = {"claim": "Led 40 engineers", "resume_quote": "Led a team of 40", "skill": "API design"}
    stored, _ = resolved(answer(claims_to_verify=[bad, good, {**good, "resume_quote": ""}]))
    assert [claim.claim for claim in stored.claims_to_verify] == ["Big tables"]


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
    assert planning.problems(plan, context(), NAME) == []
    assert all(seed.resume_quote == "" for topic in plan.topics for seed in topic.seeds)
    assert plan.claims_to_verify == []

    many = [f"Skill {index}" for index in range(1, 9)]
    grouped = planning.fallback(context(skills_to_probe=many))
    assert len(grouped.topics) == 7
    assert sorted(skill for topic in grouped.topics for skill in topic.skills) == sorted(many)
    assert planning.problems(grouped, context(skills_to_probe=many), NAME) == []


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
