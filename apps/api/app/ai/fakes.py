"""Fake answers that depend on the prompt's input, for `AI_FAKE=1` (FakeAIClient). Most prompts
answer from a fixed `fixtures/<name>@v<N>.json`; a prompt whose answer must mirror its input
(one result per pipeline criterion, quotes taken from the résumé) registers a builder here."""

import re
from collections.abc import Callable
from typing import Any

_NUMBERED = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)


def _items(numbered: str) -> list[str]:
    return _NUMBERED.findall(numbered)


def _quote(resume_text: str) -> str:
    """The résumé's longest line without a mask, so it is a verbatim quote."""
    lines = [line.strip() for line in resume_text.splitlines() if "[" not in line]
    return max(lines, key=len, default="")[:120]


def resume_assessment(variables: dict[str, str]) -> dict[str, Any]:
    """Every must-have met and every other nice-to-have found, quoting the résumé, so local runs
    and e2e reach a passing screen for any pipeline."""
    quote = _quote(variables["resume_text"])
    nice = _items(variables["nice_to_haves"])
    return {
        "must_haves": [
            {
                "criterion": criterion,
                "met": True,
                "evidence_quote": quote,
                "strength": 2,
                "degree_requirement": False,
                "note": "Shown in a recent role.",
            }
            for criterion in _items(variables["must_haves"])
        ],
        "nice_to_haves": [
            {
                "criterion": criterion,
                "found": index % 2 == 0,
                "where": "Most recent role" if index % 2 == 0 else "Not found",
                "evidence_quote": quote if index % 2 == 0 else "",
            }
            for index, criterion in enumerate(nice)
        ],
        "experience": {
            "relevant_years": 5,
            "required_hint": "the role's seniority",
            "score": 80,
            "note": "Relevant experience close to what the role asks for.",
        },
        "skill_depth": {"score": 75, "note": "Specific systems and results in most roles."},
        "impact": [{"value": "40%", "statement": "faster response times"}],
        "claims": [
            {
                "requirement": criterion,
                "type": "must_have",
                "found": "Described in a recent role",
                "strength": 2,
            }
            for criterion in _items(variables["must_haves"])[:3]
        ],
        "timeline": [
            {
                "employer": "Recent employer",
                "title": variables["job_title"],
                "start_year": 2021,
                "end_year": None,
                "current": True,
                "relevant": True,
            }
        ],
        "career_snapshot": {
            "total_years": 5,
            "companies": 2,
            "average_years_per_role": 2.5,
            "title_promotions": 1,
        },
    }


BUILDERS: dict[str, Callable[[dict[str, str]], dict[str, Any]]] = {
    "resume_assessment@v1": resume_assessment,
}
