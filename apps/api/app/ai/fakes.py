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


def interview_plan(variables: dict[str, str]) -> dict[str, Any]:
    """Warm-up, one topic per skill to probe anchored in the résumé, then the candidate's
    questions, so local runs and e2e get a plan that passes every check."""
    resume = variables["resume_text"]
    quote = _quote(resume) if resume != "Not available" else ""
    skills = _items(variables["skills_to_probe"])
    topics: list[dict[str, Any]] = [
        {
            "kind": "warm_up",
            "title": "Getting started",
            "goal": "Hear how the candidate describes their recent work.",
            "skills": [],
            "seeds": [
                {
                    "question": "Could you walk me through your most recent role?",
                    "resume_quote": quote,
                }
            ],
        }
    ]
    topics += [
        {
            "kind": "skills",
            "title": skill[:60],
            "goal": f"Understand the depth of the candidate's experience with {skill}.",
            "skills": [skill],
            "seeds": [
                {
                    "question": f"Tell me about a project where you used {skill}.",
                    "resume_quote": quote,
                }
            ],
        }
        for skill in skills[:5]
    ]
    if len(skills) > 5:
        topics[-1]["skills"] += skills[5:]
    topics.append(
        {
            "kind": "candidate_questions",
            "title": "Your questions",
            "goal": "Answer the candidate's questions about the role and the team.",
            "skills": [],
            "seeds": [
                {"question": "What would you like to know about the role?", "resume_quote": ""}
            ],
        }
    )
    claim = {"claim": "Recent work described in the résumé", "resume_quote": quote}
    claims = [{**claim, "skill": skills[0]}] if quote and skills else []
    return {"topics": topics, "claims_to_verify": claims}


BUILDERS: dict[str, Callable[[dict[str, str]], dict[str, Any]]] = {
    "resume_assessment@v1": resume_assessment,
    "interview_plan@v1": interview_plan,
}
