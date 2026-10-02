"""SCREEN-002 (ADR-013, FR-SCREEN-03..05, G2): the fit score is computed in code from the model's
parts with the 40/20/25/15 weights, a résumé passes only at or above the pass bar with every
must-have met, the "Also open to" rules change the prompt and the score as documented, and an
answer that skips a criterion or misquotes the résumé is never used."""

import asyncio
import uuid
from typing import Any

import pytest
from pydantic import BaseModel

from app.ai import fakes
from app.ai.client import AIOutputError
from app.ai.prompts import Prompt, load_prompt
from app.ai.schemas.resume_assessment import ResumeAssessment
from app.screening import assess
from app.screening.assess import Criteria
from tests.unit.test_resume_redaction import cases, run

RESUME = (
    "Senior Backend Engineer, PayLane, 2022 - present\n"
    "Sharded, multi-region PostgreSQL handling 4M transactions a day.\n"
    "Built gRPC services in Go; cut p99 latency by 40%.\n"
    "Backend Engineer, Kinetiq, 2020 - 2022\n"
    "Event-driven order processing with Kafka.\n"
    "Education\n[SCHOOL]\nBS Computer Science, [YEAR]"
)
MUSTS = ["Go or Java in production", "Distributed systems design", "PostgreSQL at scale"]
NICES = ["Kafka or event streaming", "AWS", "Kubernetes", "Terraform", "Mentoring"]
QUOTES = {
    "Go or Java in production": "Built gRPC services in Go",
    "Distributed systems design": "Event-driven order processing with Kafka.",
    "PostgreSQL at scale": "Sharded, multi-region PostgreSQL handling 4M transactions a day.",
    "Kafka or event streaming": "Event-driven order processing with Kafka",
}


def criteria(**changes: Any) -> Criteria:
    values: dict[str, Any] = {
        "job_title": "Senior Backend Engineer",
        "job_description": "Build and run payment APIs.",
        "must_haves": MUSTS,
        "nice_to_haves": NICES,
        "seniority": "senior",
        "open_to": [],
        "pass_bar": 60,
        **changes,
    }
    return Criteria(**values)


def answer(
    *,
    met: set[str] | None = None,
    found: set[str] | None = None,
    experience: int = 92,
    skill_depth: int = 86,
    musts: list[str] = MUSTS,
    nices: list[str] = NICES,
    degree: set[str] | None = None,
    quotes: dict[str, str] | None = None,
) -> ResumeAssessment:
    met = set(musts) if met is None else met
    found = {"Kafka or event streaming"} if found is None else found
    quotes = QUOTES if quotes is None else quotes
    return ResumeAssessment.model_validate(
        {
            "must_haves": [
                {
                    "criterion": criterion,
                    "met": criterion in met,
                    "evidence_quote": quotes.get(criterion, "") if criterion in met else "",
                    "strength": 3 if criterion in met else 0,
                    "degree_requirement": criterion in (degree or set()),
                    "note": "",
                }
                for criterion in musts
            ],
            "nice_to_haves": [
                {
                    "criterion": criterion,
                    "found": criterion in found,
                    "where": "Kinetiq, 2020 - 2022" if criterion in found else "Not found",
                    "evidence_quote": quotes.get(criterion, "") if criterion in found else "",
                }
                for criterion in nices
            ],
            "experience": {
                "relevant_years": 6,
                "required_hint": "4+ years backend",
                "score": experience,
                "note": "",
            },
            "skill_depth": {"score": skill_depth, "note": ""},
            "impact": [{"value": "4M", "statement": "transactions a day"}],
            "claims": [],
            "timeline": [],
            "career_snapshot": {
                "total_years": 6,
                "companies": 2,
                "average_years_per_role": 3,
                "title_promotions": 0,
            },
        }
    )


class QueuedAI:
    """Answers `resume_assessment` with the queued answers in turn, recording the prompts."""

    model = "stub"

    def __init__(self, *answers: ResumeAssessment) -> None:
        self.answers = list(answers)
        self.prompts: list[dict[str, str]] = []

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
        assert schema is ResumeAssessment
        assert temperature == 0
        prompt.render(variables)  # every placeholder filled
        self.prompts.append(variables)
        return schema.model_validate(self.answers.pop(0).model_dump())


def test_the_score_follows_the_design_example() -> None:
    # CandidateProfile: 4 of 4 met, 3 of 5 found, experience 92, skill depth 86 → 87.9 → 88.
    four = [*MUSTS, "4+ years backend"]
    decision = assess.score(
        answer(musts=four, found=set(NICES[:3]), experience=92, skill_depth=86),
        criteria(must_haves=four),
    )

    assert decision.score == 88
    assert decision.passed
    assert decision.breakdown["must_haves"] == {
        "score": 100.0,
        "weight": 0.4,
        "points": 40.0,
        "detail": "4 of 4 met",
    }
    assert decision.breakdown["nice_to_haves"]["points"] == 12.0
    assert decision.breakdown["experience"]["points"] == 23.0
    assert decision.breakdown["skill_depth"]["points"] == 12.9


def test_without_nice_to_haves_their_weight_is_redistributed() -> None:
    weights = assess.weights(criteria(nice_to_haves=[]))

    assert {part: float(weight) for part, weight in weights.items()} == {
        "must_haves": 0.5,
        "experience": 0.3125,
        "skill_depth": 0.1875,
    }
    decision = assess.score(
        answer(nices=[], found=set(), experience=60, skill_depth=40), criteria(nice_to_haves=[])
    )
    # 50 + 18.75 + 7.5 = 76.25
    assert decision.score == 76
    assert "nice_to_haves" not in decision.breakdown


@pytest.mark.parametrize(
    ("met", "experience", "bar", "passed"),
    [
        (set(MUSTS), 92, 60, True),
        # High score, one must-have missing: never passes.
        ({MUSTS[0], MUSTS[1]}, 100, 10, False),
        # Every must-have met, below the bar.
        (set(MUSTS), 0, 80, False),
    ],
)
def test_pass_needs_the_bar_and_every_must_have(
    met: set[str], experience: int, bar: int, passed: bool
) -> None:
    decision = assess.score(answer(met=met, experience=experience), criteria(pass_bar=bar))

    assert decision.passed is passed


def test_a_score_exactly_at_the_bar_passes() -> None:
    decision = assess.score(answer(), criteria())
    exact = assess.score(answer(), criteria(pass_bar=decision.score))
    above = assess.score(answer(), criteria(pass_bar=decision.score + 1))

    assert exact.passed
    assert not above.passed


def test_fresh_graduates_get_an_experience_floor_for_entry_and_mid_roles() -> None:
    low = answer(experience=10)

    mid = assess.score(low, criteria(seniority="mid", open_to=["fresh_grads"]))
    senior = assess.score(low, criteria(seniority="senior", open_to=["fresh_grads"]))
    without = assess.score(low, criteria(seniority="mid"))

    assert mid.breakdown["experience"]["score"] == 50.0
    assert "fresh graduate floor" in mid.breakdown["experience"]["detail"]
    assert senior.breakdown["experience"]["score"] == 10.0
    assert without.breakdown["experience"]["score"] == 10.0


def test_no_degree_required_waives_a_degree_must_have() -> None:
    musts = [*MUSTS, "Bachelor's degree in Computer Science"]
    result = answer(musts=musts, met=set(MUSTS), degree={musts[3]})

    waived = assess.score(result, criteria(must_haves=musts, open_to=["no_degree"]))
    kept = assess.score(result, criteria(must_haves=musts))

    assert waived.passed and waived.must_haves[3]["waived"]
    assert waived.breakdown["must_haves"]["detail"] == "4 of 4 met"
    assert not kept.passed


def test_open_to_rules_and_step_up_change_the_prompt() -> None:
    plain = assess.variables(criteria(), RESUME)
    open_to = assess.variables(
        criteria(open_to=["returners", "step_up", "relocating"], seniority="lead"), RESUME
    )

    assert plain["open_to_rules"] == ""
    assert plain["seniority"] == "Senior"
    assert "never mention, count or penalise gaps" in open_to["open_to_rules"]
    assert "location" in open_to["open_to_rules"]
    # Ready for a step up: a lead role is judged against senior experience.
    assert open_to["seniority"] == "Senior"
    assert plain["must_haves"].splitlines() == [f"{i}. {m}" for i, m in enumerate(MUSTS, 1)]


def test_quotes_must_be_verbatim_but_tolerate_typography() -> None:
    assert assess.quoted("\u201cBuilt gRPC services in GO;\u201d", RESUME)
    assert assess.quoted("Senior Backend Engineer, PayLane, 2022 \u2013 present", RESUME)
    assert not assess.quoted("Built gRPC services in Rust", RESUME)
    assert not assess.quoted("", RESUME)


def test_an_answer_missing_criteria_or_quotes_is_unusable() -> None:
    assert assess.problems(answer(), criteria(), RESUME) == []
    assert "must_haves_missing" in assess.problems(answer(musts=MUSTS[:2]), criteria(), RESUME)
    invented = {**QUOTES, "PostgreSQL at scale": "Ran PostgreSQL for 10 billion rows"}
    assert assess.problems(answer(quotes=invented), criteria(), RESUME) == ["must_have_3_quote"]


def test_reworded_criteria_are_matched_by_position() -> None:
    reworded_quotes = {m.lower() + ".": q for m, q in QUOTES.items()}
    reworded = answer(musts=[m.lower() + "." for m in MUSTS], quotes=reworded_quotes)

    decision = assess.score(reworded, criteria())

    assert [row["criterion"] for row in decision.must_haves] == MUSTS
    assert decision.passed


def test_an_unusable_answer_is_asked_again_once_then_fails() -> None:
    bad = answer(quotes={**QUOTES, "Go or Java in production": "Java at a bank"})

    ai = QueuedAI(bad, answer())
    result = asyncio.run(assess.assess(ai, criteria(), RESUME))
    assert assess.score(result, criteria()).passed
    assert len(ai.prompts) == 2

    with pytest.raises(AIOutputError):
        asyncio.run(assess.assess(QueuedAI(bad, bad), criteria(), RESUME))


def test_the_fake_answer_fits_any_pipeline() -> None:
    variables = assess.variables(criteria(), RESUME)
    fake = ResumeAssessment.model_validate(fakes.resume_assessment(variables))

    assert assess.problems(fake, criteria(), RESUME) == []
    assert assess.score(fake, criteria()).passed


def test_counterfactual_pairs_send_the_same_prompt() -> None:
    """G2: résumés that differ only in name, gender, age, school and address reach the model as
    the same prompt, so their fit scores can't differ for those details."""
    prompts: dict[str, set[str]] = {}
    for case in cases():
        prompt = load_prompt(*assess.PROMPT).render(assess.variables(criteria(), run(case)[0]))
        prompts.setdefault(case["pair"], set()).add(prompt.system + prompt.user)

    assert len(prompts) >= 2
    assert all(len(texts) == 1 for texts in prompts.values())
