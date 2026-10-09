"""Fake answers that depend on the prompt's input, for `AI_FAKE=1` (FakeAIClient). Most prompts
answer from a fixed `fixtures/<name>@v<N>.json`; a prompt whose answer must mirror its input
(one result per pipeline criterion, quotes taken from the résumé) registers a builder here."""

import copy
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
    """Warm-up, one topic per skill to probe (by number) anchored in the résumé, then the
    candidate's questions, so local runs and e2e get a plan that passes every check."""
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
            "skills": [number],
            "seeds": [
                {
                    "question": f"Tell me about a project where you used {skill}.",
                    "resume_quote": quote,
                }
            ],
        }
        for number, skill in enumerate(skills[:5], 1)
    ]
    if len(skills) > 5:
        topics[-1]["skills"] += list(range(6, len(skills) + 1))
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


_TURN = re.compile(r"^#(\d+) \[[\d:]+\] (Interviewer|Candidate): (.+)$")
_TOPIC = re.compile(r"^--- Topic (\d+): ")


def interview_assessment(variables: dict[str, str]) -> dict[str, Any]:
    """Good scores (overall 80) quoting the candidate's own turns, a score for every topic,
    every résumé claim confirmed, so local runs and e2e reach Ready for review."""
    turns: list[tuple[int, str, str, int]] = []  # number, speaker, text, topic
    topic = 0
    for line in variables["transcript"].splitlines():
        if heading := _TOPIC.match(line):
            topic = int(heading.group(1))
        elif turn := _TURN.match(line):
            turns.append((int(turn.group(1)), turn.group(2), turn.group(3), topic))
    answers = [turn for turn in turns if turn[1] == "Candidate"] or [(1, "Candidate", "", 0)]

    def quote(text: str, last: bool = False) -> str:
        words = text.split()
        return " ".join(words[-8:] if last else words[:8])

    first, second = answers[0], answers[min(1, len(answers) - 1)]
    evidence = [
        {"source": "interview", "turn": first[0], "quote": quote(first[2]), "label": "Opening"},
        {
            "source": "interview",
            "turn": second[0],
            "quote": quote(second[2], last=second is first),
            "label": "Follow-up",
        },
    ]

    def criterion(score: int, names: list[str]) -> dict[str, Any]:
        return {
            "score": score,
            "signals": [{"name": name, "score": score} for name in names],
            "evidence": copy.deepcopy(evidence),
            "held_back": "Some answers stayed general.",
        }

    asked: set[int] = set()
    questions: list[int] = []
    follow_ups: list[int] = []
    for number, speaker, _text, in_topic in turns:
        if speaker == "Interviewer":
            (follow_ups if in_topic in asked else questions).append(number)
            asked.add(in_topic)
    claims = _items(variables["claims"]) if variables["claims"] != "None" else []
    return {
        "criteria": {
            "technical": criterion(82, ["System design", "Tools of the job", "Trade-offs"]),
            "communication": criterion(78, ["Structure and clarity", "Answers the question"]),
            "culture": criterion(80, ["Ownership", "Collaboration", "Curiosity"]),
        },
        "topics": [
            {"topic": number, "score": 80}
            for number in range(1, len(_items(variables["topics"])) + 1)
        ],
        "summary": {
            "text": "Gave concrete examples from recent work [1]. Explained choices clearly [2].",
            "refs": copy.deepcopy(evidence),
        },
        "strengths": [{"title": "Concrete examples", "reason": "specific answers"}],
        "probes": [{"title": "Depth at scale", "reason": "answers stayed general"}],
        "claims_checked": [
            {"claim": number, "status": "confirmed", "turn": first[0]}
            for number in range(1, len(claims) + 1)
        ],
        "turns": {
            "questions": questions,
            "follow_ups": follow_ups,
            "candidate_questions": [
                number
                for number, speaker, text, _ in turns
                if speaker == "Candidate" and "?" in text
            ],
        },
    }


_WINDOW = re.compile(r"^Window (\d+) ", re.MULTILINE)


def integrity_read_aloud(variables: dict[str, str]) -> dict[str, Any]:
    """Nothing sounded read aloud: local runs and e2e raise no read-aloud flags."""
    return {
        "windows": [
            {
                "window": int(number),
                "read_aloud": False,
                "confidence": 0.3,
                "rationale": "The answer sounds spoken freely, with personal specifics.",
            }
            for number in _WINDOW.findall(variables["windows"])
        ]
    }


BUILDERS: dict[str, Callable[[dict[str, str]], dict[str, Any]]] = {
    "resume_assessment@v1": resume_assessment,
    "interview_plan@v1": interview_plan,
    "interview_assessment@v1": interview_assessment,
    "integrity_read_aloud@v1": integrity_read_aloud,
}
