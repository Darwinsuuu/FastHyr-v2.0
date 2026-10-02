"""Résumé assessment and decision (AI_PIPELINE.md §1 steps 3-5, ADR-013, FR-SCREEN-03..05).

1. `assess()` asks `resume_assessment@v1` to judge the redacted résumé against the pipeline's
   criteria, with the pipeline's "Also open to" rules in the prompt. The answer must cover every
   criterion and quote the résumé word for word; an answer that doesn't is asked for once more,
   then fails like any invalid answer (`AIOutputError`).
2. `score()` computes the fit score in code: must-haves 40, nice-to-haves 20, relevant
   experience 25, skill depth 15, with the weight of a part that has no criteria redistributed
   proportionally. Pass = score ≥ the pipeline's pass bar and every must-have met.

Nothing here logs résumé text.
"""

import logging
import re
import unicodedata
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.ai.client import AIClient, AIOutputError
from app.ai.prompts import load_prompt
from app.ai.schemas.resume_assessment import MustHaveResult, NiceToHaveResult, ResumeAssessment

logger = logging.getLogger("app.screening")

PROMPT = ("resume_assessment", 1)
PROMPT_VERSION = f"{PROMPT[0]}@v{PROMPT[1]}"
# Answers that cover every criterion and quote the résumé exactly; one retry (AI_PIPELINE.md §0).
ANSWER_TRIES = 2

WEIGHTS: dict[str, Decimal] = {
    "must_haves": Decimal(40),
    "nice_to_haves": Decimal(20),
    "experience": Decimal(25),
    "skill_depth": Decimal(15),
}
SENIORITY_LABELS = {
    "entry": "Entry level",
    "mid": "Mid level",
    "senior": "Senior",
    "lead": "Lead or principal",
}
# "Ready for a step up" drops the expectation one level (AI_PIPELINE.md §1 step 5).
STEP_DOWN = {"entry": "entry", "mid": "entry", "senior": "mid", "lead": "senior"}
# "Fresh graduates": the experience score never drops below this for entry and mid roles.
FRESH_GRAD_EXPERIENCE_FLOOR = 50
FRESH_GRAD_SENIORITIES = ("entry", "mid")

OPEN_TO_RULES = {
    "fresh_grads": (
        "Fresh graduates: internships, school projects and personal projects count as "
        "experience and as evidence for must-haves."
    ),
    "career_changers": (
        "Career changers: transferable skills from other fields can meet must-haves; judge "
        "what the work shows, not the job title or industry."
    ),
    "returners": (
        "Returning to work: never mention, count or penalise gaps between roles; judge the "
        "experience the résumé shows."
    ),
    "no_degree": (
        "No degree required: ignore degree requirements in the job description; a must-have "
        "that only asks for a degree is marked degree_requirement true."
    ),
    "step_up": (
        "Ready for a step up: the expected seniority given with the job is already one level lower "
        "than the role's; judge experience against it."
    ),
    "relocating": (
        "Relocating or remote-first: location, time zone and willingness to move are never a gap."
    ),
}


@dataclass(frozen=True)
class Criteria:
    """The locked pipeline setup the résumé is assessed against."""

    job_title: str
    job_description: str
    must_haves: Sequence[str]
    nice_to_haves: Sequence[str]
    seniority: str | None
    open_to: Sequence[str]
    pass_bar: int


@dataclass(frozen=True)
class Decision:
    score: int
    passed: bool
    breakdown: dict[str, dict[str, Any]]
    must_haves: list[dict[str, Any]]
    nice_to_haves: list[dict[str, Any]]


def expected_seniority(criteria: Criteria) -> str | None:
    if criteria.seniority is None:
        return None
    if "step_up" in criteria.open_to:
        return STEP_DOWN[criteria.seniority]
    return criteria.seniority


def _numbered(items: Sequence[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1)) or "None"


def variables(criteria: Criteria, resume_text: str) -> dict[str, str]:
    rules = [OPEN_TO_RULES[key] for key in OPEN_TO_RULES if key in criteria.open_to]
    seniority = expected_seniority(criteria)
    return {
        "job_title": criteria.job_title,
        "seniority": SENIORITY_LABELS[seniority] if seniority else "Not stated",
        "job_description": criteria.job_description.strip() or "Not provided",
        "must_haves": _numbered(criteria.must_haves),
        "nice_to_haves": _numbered(criteria.nice_to_haves),
        "open_to_rules": (
            "This pipeline is also open to the following applicants; apply these rules:\n"
            + "\n".join(f"- {rule}" for rule in rules)
            if rules
            else ""
        ),
        "resume_text": resume_text,
    }


# --- Checking the answer ---------------------------------------------------------------------

_NOT_WORD = re.compile(r"[^\w]+")
_ELLIPSIS = re.compile(r"\.\.\.+|\u2026")


def _normal(text: str) -> str:
    """Words only: case, spacing, punctuation, bullets, quote and dash styles are ignored."""
    words = _NOT_WORD.sub(" ", unicodedata.normalize("NFKC", text).casefold())
    return " ".join(words.split())


def quoted(quote: str, resume_text: str) -> bool:
    """True when `quote` appears in the résumé as whole words in order, ignoring case,
    punctuation and line breaks. A quote the model shortened with "..." passes when every part
    appears, in order."""
    haystack = f" {_normal(resume_text)} "
    parts = [_normal(part) for part in _ELLIPSIS.split(quote)]
    parts = [part for part in parts if part]
    position = 0
    for part in parts:
        found = haystack.find(f" {part} ", position)
        if found < 0:
            return False
        position = found + len(part)
    return bool(parts)


def _aligned[T: (MustHaveResult, NiceToHaveResult)](
    expected: Sequence[str], results: list[T]
) -> list[T] | None:
    """The model's results in the pipeline's order: matched by criterion text, or by position
    when the model returned one per criterion but reworded them. None when any is missing."""
    by_text = {_normal(result.criterion): result for result in results}
    matched = [by_text.get(_normal(criterion)) for criterion in expected]
    if all(result is not None for result in matched):
        return [result for result in matched if result is not None]
    if len(results) == len(expected):
        return results
    return None


def problems(answer: ResumeAssessment, criteria: Criteria, resume_text: str) -> list[str]:
    """What makes an answer unusable: missing criteria or evidence the résumé doesn't contain.
    Labels only, never résumé text, so they can be logged."""
    found: list[str] = []
    musts = _aligned(criteria.must_haves, answer.must_haves)
    nices = _aligned(criteria.nice_to_haves, answer.nice_to_haves)
    if musts is None:
        found.append("must_haves_missing")
    if nices is None:
        found.append("nice_to_haves_missing")
    for index, must in enumerate(musts or [], 1):
        waived = must.degree_requirement and "no_degree" in criteria.open_to
        if must.met and not waived and not quoted(must.evidence_quote, resume_text):
            found.append(f"must_have_{index}_quote")
    for index, nice in enumerate(nices or [], 1):
        if nice.found and not quoted(nice.evidence_quote, resume_text):
            found.append(f"nice_to_have_{index}_quote")
    return found


async def assess(
    ai: AIClient,
    criteria: Criteria,
    resume_text: str,
    *,
    workspace_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
) -> ResumeAssessment:
    prompt = load_prompt(*PROMPT)
    for attempt in range(1, ANSWER_TRIES + 1):
        answer = await ai.structured(
            purpose="resume_assessment",
            prompt=prompt,
            variables=variables(criteria, resume_text),
            schema=ResumeAssessment,
            workspace_id=workspace_id,
            entity_id=entity_id,
            temperature=0,
        )
        issues = problems(answer, criteria, resume_text)
        if not issues:
            return answer
        logger.warning("resume assessment unusable on try %d: %s", attempt, ", ".join(issues))
    raise AIOutputError()


# --- Computing the score ---------------------------------------------------------------------


def _round(value: Decimal, places: str = "0.1") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def weights(criteria: Criteria) -> dict[str, Decimal]:
    """ADR-013 weights as fractions; a part with no criteria is left out and the rest scaled up
    proportionally to total 1."""
    present = {
        part: weight
        for part, weight in WEIGHTS.items()
        if (part != "must_haves" or criteria.must_haves)
        and (part != "nice_to_haves" or criteria.nice_to_haves)
    }
    total = sum(present.values())
    return {part: weight / total for part, weight in present.items()}


def score(answer: ResumeAssessment, criteria: Criteria) -> Decision:
    """The fit score and decision, from an answer `problems()` accepted."""
    musts = _aligned(criteria.must_haves, answer.must_haves) or []
    nices = _aligned(criteria.nice_to_haves, answer.nice_to_haves) or []

    must_rows = []
    for criterion, result in zip(criteria.must_haves, musts, strict=True):
        waived = result.degree_requirement and "no_degree" in criteria.open_to
        must_rows.append(
            {
                "criterion": criterion,
                "met": result.met or waived,
                "evidence_quote": result.evidence_quote if result.met else "",
                "strength": result.strength if result.met else 0,
                "waived": waived,
                "note": "No degree required for this role." if waived else result.note,
            }
        )
    nice_rows = [
        {
            "criterion": criterion,
            "found": result.found,
            "where": result.where if result.found else "Not found",
            "evidence_quote": result.evidence_quote if result.found else "",
        }
        for criterion, result in zip(criteria.nice_to_haves, nices, strict=True)
    ]
    met = sum(1 for row in must_rows if row["met"])
    found = sum(1 for row in nice_rows if row["found"])

    experience = answer.experience.score
    floored = (
        "fresh_grads" in criteria.open_to
        and criteria.seniority in FRESH_GRAD_SENIORITIES
        and experience < FRESH_GRAD_EXPERIENCE_FLOOR
    )
    if floored:
        experience = FRESH_GRAD_EXPERIENCE_FLOOR
    experience_detail = f"{answer.experience.relevant_years:g} yrs relevant vs " + (
        answer.experience.required_hint or "the role's seniority"
    )
    if floored:
        experience_detail += " (fresh graduate floor applied)"

    parts: dict[str, tuple[Decimal, str]] = {
        "must_haves": (
            Decimal(100 * met) / len(must_rows) if must_rows else Decimal(0),
            f"{met} of {len(must_rows)} met",
        ),
        "nice_to_haves": (
            Decimal(100 * found) / len(nice_rows) if nice_rows else Decimal(0),
            f"{found} of {len(nice_rows)} found",
        ),
        "experience": (Decimal(experience), experience_detail),
        "skill_depth": (Decimal(answer.skill_depth.score), "Evidence strength across skills"),
    }
    breakdown: dict[str, dict[str, Any]] = {}
    total = Decimal(0)
    for part, weight in weights(criteria).items():
        part_score, detail = parts[part]
        points = part_score * weight
        total += points
        breakdown[part] = {
            "score": float(_round(part_score)),
            "weight": float(_round(weight, "0.0001")),
            "points": float(_round(points)),
            "detail": detail,
        }
    fit = int(_round(total, "1"))
    passed = fit >= criteria.pass_bar and met == len(must_rows)
    return Decision(
        score=fit,
        passed=passed,
        breakdown=breakdown,
        must_haves=must_rows,
        nice_to_haves=nice_rows,
    )
