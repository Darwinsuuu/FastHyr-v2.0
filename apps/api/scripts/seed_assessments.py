"""Full interview assessments for the Acme Talent sample applicants (ASMT-004), so the candidate
profile has signals, evidence, topics, a summary and answer patterns to show.

Everything here is synthetic and made in the shape `app/interview/assessment.py` stores. Bea
Garcia (the frames' sample candidate) gets the frame's assessment; everyone else gets one built
from a small bank of answers around their score. Scores stay as `seed_applications.py` chose
them; only the content around them is added.
"""

# Sample answers read best on one line each.
# ruff: noqa: E501

import random
from dataclasses import dataclass
from typing import Any

CRITERIA = ("technical", "communication", "culture")
SIGNALS = {
    "technical": ("Problem solving", "Depth of knowledge", "Trade-off reasoning", "Practical examples"),
    "communication": ("Structure and clarity", "Answers the question asked", "Concise", "Listening"),
    "culture": ("Ownership", "Collaboration", "Curiosity", "Learning from mistakes"),
}  # fmt: skip
ANSWERS = {
    "technical": (
        ("I broke the problem into smaller pieces and tested each one before joining them.", "Problem-solving question"),
        ("We measured first, then fixed the slowest step instead of guessing.", "Performance question"),
        ("I picked the simpler option because the team could support it on their own.", "Trade-off follow-up"),
    ),
    "communication": (
        ("Let me give you the short version first, then the details.", "Opening answer"),
        ("I wrote a one-page summary so everyone could agree before we started.", "Working with others"),
        ("I checked I understood the question before answering it.", "Clarifying question"),
    ),
    "culture": (
        ("I owned the mistake, fixed it, and we changed the checklist so it wouldn't happen again.", "Learning from a mistake"),
        ("I asked the newer people on the team what slowed them down.", "Teamwork question"),
        ("What does a good first three months look like in this role?", "Candidate's questions"),
    ),
}  # fmt: skip
HELD_BACK = {
    "technical": "Examples stayed general and didn't show how results were measured.",
    "communication": "A few answers ran long before reaching the main point.",
    "culture": "Few examples of helping other people grow.",
}
STRENGTHS = (
    ("Clear, structured answers", "communication"),
    ("Practical problem solving", "technical"),
    ("Takes ownership", "culture"),
)
PROBES = (
    ("Depth on measuring results", "technical"),
    ("Mentoring and feedback", "culture"),
    ("Keeping answers short", "communication"),
)


@dataclass(frozen=True)
class SampleInterview:
    plan_topics: list[dict[str, Any]]
    criteria: dict[str, Any]
    topics: list[dict[str, Any]]
    summary: dict[str, Any]
    strengths: list[dict[str, str]]
    probes: list[dict[str, str]]
    answer_stats: dict[str, Any]
    integrity_checks: dict[str, str]


def _plan(skills: list[str]) -> list[dict[str, Any]]:
    seed = [{"question": "Could you walk me through your current work?", "resume_quote": ""}]
    topics = [
        {
            "kind": "warm_up",
            "title": "Warm-up and background",
            "goal": "",
            "skills": [],
            "seeds": seed,
        }
    ]
    for skill in skills or ["Problem solving"]:
        topics.append(
            {
                "kind": "skills",
                "title": f"{skill} in practice",
                "goal": "",
                "skills": [skill],
                "seeds": seed,
            }
        )
    topics.append(
        {
            "kind": "candidate_questions",
            "title": "Candidate's questions",
            "goal": "",
            "skills": [],
            "seeds": seed,
        }
    )
    return topics


def _points(score: int, weight: int) -> float:
    return round(score * weight / 100, 1)


def sample_interview(
    rng: random.Random,
    *,
    score: int,
    scores: dict[str, int],
    weights: dict[str, int],
    skills: list[str],
    seconds: int,
    video: bool,
    consent: bool,
    integrity: bool,
) -> SampleInterview:
    """An assessment around `score`, with `scores` per criterion (seed_applications.py)."""
    plan = _plan(skills)
    span = max(seconds * 1000, 60_000)
    starts = [round(span * index / len(plan)) for index in range(len(plan))]
    criteria: dict[str, Any] = {}
    for name in CRITERIA:
        value = scores[name]
        answers = rng.sample(ANSWERS[name], 2)
        criteria[name] = {
            "score": value,
            "weight": weights[name],
            "points": _points(value, weights[name]),
            "signals": [
                {"name": signal, "score": max(0, min(100, value + rng.randint(-8, 8)))}
                for signal in SIGNALS[name]
            ],
            "evidence": [
                {
                    "source": "interview",
                    "quote": quote,
                    "start_ms": starts[rng.randrange(1, len(plan))] + rng.randint(5, 50) * 1000,
                    "source_label": label,
                }
                for quote, label in answers
            ],
            "held_back": HELD_BACK[name],
        }
    topics = [
        {
            "index": index,
            "title": topic["title"],
            "start_ms": starts[index],
            "questions": 1 if topic["kind"] != "skills" else rng.randint(1, 3),
            "follow_ups": 0 if topic["kind"] != "skills" else rng.randint(0, 2),
            "score": max(0, min(100, score + rng.randint(-10, 10))),
        }
        for index, topic in enumerate(plan)
    ]
    first = criteria["technical"]["evidence"][0]
    second = criteria["communication"]["evidence"][0]
    best = max(CRITERIA, key=lambda name: scores[name])
    worst = min(CRITERIA, key=lambda name: scores[name])
    words = {
        "technical": "technical fit",
        "communication": "communication",
        "culture": "culture alignment",
    }
    return SampleInterview(
        plan_topics=plan,
        criteria=criteria,
        topics=topics,
        summary={
            "text": (
                f"The strongest area was {words[best]} [1]. Answers were easy to follow [2]. "
                f"{words[worst].capitalize()} is worth a closer look in the next round."
            ),
            "refs": [
                {k: first[k] for k in ("source", "quote", "start_ms", "source_label")},
                {k: second[k] for k in ("source", "quote", "start_ms", "source_label")},
            ],
        },
        strengths=[
            {"title": title, "reason": f"{words[area]} {scores[area]}"}
            for title, area in STRENGTHS
            if scores[area] >= score - 3
        ][:3]
        or [{"title": STRENGTHS[0][0], "reason": f"communication {scores['communication']}"}],
        probes=[
            {"title": title, "reason": f"{words[area]} {scores[area]}"}
            for title, area in PROBES
            if scores[area] <= score + 3
        ][:3]
        or [{"title": PROBES[0][0], "reason": f"technical fit {scores['technical']}"}],
        answer_stats=_answer_stats(rng, len(plan)),
        integrity_checks=_checks(video, consent) if integrity else {},
    )


def _answer_stats(rng: random.Random, topics: int) -> dict[str, Any]:
    answers = topics + rng.randint(2, 6)
    candidate_ms = rng.randint(600, 1200) * 1000
    interviewer_ms = rng.randint(300, 600) * 1000
    return {
        "answers": answers,
        "avg_answer_ms": rng.randint(50, 130) * 1000,
        "avg_response_delay_ms": rng.randint(1500, 3800),
        "questions": topics + rng.randint(1, 4),
        "follow_ups": rng.randint(2, 10),
        "candidate_questions": rng.randint(0, 3),
        "candidate_talk_ms": candidate_ms,
        "interviewer_talk_ms": interviewer_ms,
        "talk_time_pct": round(100 * candidate_ms / (candidate_ms + interviewer_ms)),
    }


def _checks(video: bool, consent: bool) -> dict[str, str]:
    face = "ran" if video and consent else ("voice_only" if not video else "no_consent")
    return {"face": face, "second_voice": "ran", "timing": "ran", "read_aloud": "ran"}


def _at(minutes: int, seconds: int) -> int:
    return (minutes * 60 + seconds) * 1000


def bea_garcia(weights: dict[str, int], skills: list[str]) -> SampleInterview:
    """The frame CandidateProfile's assessment, on this pipeline's skills to probe."""
    problem, communication, ownership = (skills + ["Problem solving"] * 3)[:3]
    seed = [{"question": "Could you walk me through what you work on?", "resume_quote": ""}]
    plan = [
        {"kind": "warm_up", "title": "Warm-up and background", "skills": [], "seeds": seed},
        {"kind": "skills", "title": "System design: payments sharding", "skills": [problem], "seeds": seed},
        {"kind": "skills", "title": "Go concurrency and gRPC", "skills": [problem], "seeds": seed},
        {"kind": "skills", "title": "Handling a production incident", "skills": [ownership], "seeds": seed},
        {"kind": "skills", "title": "Teamwork and ways of working", "skills": [communication], "seeds": seed},
        {"kind": "candidate_questions", "title": "Candidate's questions", "skills": [], "seeds": seed},
    ]  # fmt: skip
    plan = [{**topic, "goal": ""} for topic in plan]

    def interview(quote: str, at: int, label: str) -> dict[str, Any]:
        return {"source": "interview", "quote": quote, "start_ms": at, "source_label": label}

    def resume(quote: str, label: str) -> dict[str, Any]:
        return {"source": "resume", "quote": quote, "source_label": label}

    scores = {"technical": 94, "communication": 88, "culture": 86}
    criteria = {
        "technical": {
            "signals": [("System design", 96), ("Databases at scale", 95), ("Go and concurrency", 93), ("Trade-off reasoning", 92)],
            "evidence": [
                interview("We shard by merchant ID. Most queries are per-merchant, so it keeps reads on one shard.", _at(3, 21), "System design question"),
                interview("I pass the context all the way down and set deadlines at the edge.", _at(12, 11), "Go and gRPC question"),
                resume("Sharded, multi-region PostgreSQL handling 4M transactions a day.", "Most recent role"),
            ],
            "held_back": "The incident answer stayed high-level on monitoring and alerting (84 on that topic).",
        },
        "communication": {
            "signals": [("Structure and clarity", 92), ("Answers the question asked", 90), ("Explains to non-experts", 85), ("Concise", 85)],
            "evidence": [
                interview("Looking back, I would have planned for that from day one instead of retrofitting it.", _at(4, 30), "Follow-up on hot shards"),
                interview("Early and often. I'd rather push back on scope in week one than in week six.", _at(26, 11), "Working with product"),
            ],
            "held_back": "Two answers ran past 3 minutes before reaching the main point.",
        },
        "culture": {
            "signals": [("Ownership", 90), ("Collaboration", 88), ("Curiosity", 86), ("Mentoring", 80)],
            "evidence": [
                interview("I rolled it back, then we added a rule that big migrations run online in batches.", _at(19, 12), "Production incident"),
                interview("What does on-call look like for this team?", _at(28, 20), "Candidate's questions"),
            ],
            "held_back": "Few examples of mentoring or growing other engineers.",
        },
    }  # fmt: skip
    stored = {
        name: {
            "score": scores[name],
            "weight": weights[name],
            "points": _points(scores[name], weights[name]),
            "signals": [{"name": n, "score": v} for n, v in row["signals"]],
            "evidence": row["evidence"],
            "held_back": row["held_back"],
        }
        for name, row in criteria.items()
    }
    starts = (0, 185, 720, 1140, 1560, 1690)
    counts = ((1, 0), (3, 2), (2, 1), (2, 2), (2, 1), (1, 0))
    topic_scores = (90, 96, 93, 84, 88, 86)
    return SampleInterview(
        plan_topics=plan,
        criteria=stored,
        topics=[
            {
                "index": index,
                "title": topic["title"],
                "start_ms": starts[index] * 1000,
                "questions": counts[index][0],
                "follow_ups": counts[index][1],
                "score": topic_scores[index],
            }
            for index, topic in enumerate(plan)
        ],
        summary={
            "text": (
                "6 years of backend work in Go and Java, including a sharded, multi-region "
                "PostgreSQL setup [1]. Gave the most complete system design answer in this "
                "pipeline and named a trade-off worth making differently now [2]. Answers were "
                "structured and easy to follow [3]. The incident answer was solid but stayed "
                "high-level on monitoring [4]."
            ),
            "refs": [
                resume(
                    "Sharded, multi-region PostgreSQL handling 4M transactions a day.",
                    "Most recent role",
                ),
                interview(
                    "Looking back, I would have planned for that from day one instead of retrofitting it.",
                    _at(4, 30),
                    "Follow-up on hot shards",
                ),
                interview(
                    "Early and often. I'd rather push back on scope in week one than in week six.",
                    _at(26, 11),
                    "Working with product",
                ),
                interview(
                    "I rolled it back, then we added a rule that big migrations run online in batches.",
                    _at(19, 12),
                    "Production incident",
                ),
            ],
        },
        strengths=[
            {"title": "System design at scale", "reason": "top score in pipeline (96)"},
            {"title": "Clear, structured answers", "reason": "communication 88"},
            {"title": "Owns mistakes and fixes the process", "reason": "incident answer"},
        ],
        probes=[
            {"title": "On-call and monitoring", "reason": "incident topic scored lowest (84)"},
            {"title": "Mentoring junior engineers", "reason": "mentoring signal 80"},
            {"title": "Kubernetes depth", "reason": "on the résumé, not covered in the interview"},
        ],
        answer_stats={
            "answers": 14,
            "avg_answer_ms": 112_000,
            "avg_response_delay_ms": 2100,
            "questions": 11,
            "follow_ups": 6,
            "candidate_questions": 2,
            "candidate_talk_ms": 1_315_000,
            "interviewer_talk_ms": 619_000,
            "talk_time_pct": 68,
        },
        integrity_checks=_checks(True, True),
    )
