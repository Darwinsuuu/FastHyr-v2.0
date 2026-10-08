"""Interview scoring (AI_PIPELINE.md §4, ADR-011, FR-ASMT-02..05).

1. `turns()` joins the transcript's consecutive lines of one speaker in one topic into numbered
   turns, leaves out other voices (ASMT-002 looks at those) and masks the candidate's name and
   contact details.
2. `assess()` asks `interview_assessment@v1` to score technical fit, communication and culture
   alignment with signals and evidence, score the topics, summarise with references, and label
   the turns. Evidence must quote a candidate turn or the résumé word for word; evidence that
   doesn't is dropped, and an answer left with a criterion under 2 pieces of evidence (or none
   from the interview), a reached topic without a score, or a summary reference that doesn't
   check out is asked for once more, then fails (`AIOutputError`): no score without evidence.
3. `decide()` computes everything that isn't judgement in code: points and the overall score
   from the pipeline's weights, pass/fail against the pass mark, the fit badge, topic start
   times and question counts, and answer patterns from the transcript's timings.

Nothing here logs transcript or résumé text.
"""

import logging
import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise
from typing import Any

from app.ai.client import AIClient, AIOutputError
from app.ai.prompts import load_prompt
from app.ai.schemas.interview_assessment import (
    CriterionAnswer,
    Evidence,
    InterviewAssessment,
)
from app.screening.assess import SENIORITY_LABELS, STEP_DOWN, quoted

logger = logging.getLogger("app.interview")

PROMPT = ("interview_assessment", 1)
PROMPT_VERSION = f"{PROMPT[0]}@v{PROMPT[1]}"
# Answers whose evidence checks out; one retry (AI_PIPELINE.md §0).
ANSWER_TRIES = 2

CRITERIA = ("technical", "communication", "culture")
MIN_EVIDENCE = 2
MAX_EVIDENCE = 4
MAX_SIGNALS = 5
MAX_POINTS = 4
# ADR-011: Strong fit = passed, overall at least this, and every must-have met.
STRONG_FIT_SCORE = 80

SPEAKERS = {"interviewer": "Interviewer", "candidate": "Candidate"}
_REFERENCE = re.compile(r"\[(\d+)\]")

OPEN_TO_RULES = {
    "fresh_grads": (
        "Fresh graduates: internships, school projects and personal projects are good evidence; "
        "never mark anyone down for fewer years of paid work."
    ),
    "career_changers": (
        "Career changers: experience from other fields counts when it transfers to this job."
    ),
    "returners": "Returning to work: never consider time away from work.",
    "no_degree": "No degree required: never consider degrees or studies.",
    "step_up": (
        "Ready for a step up: the expected seniority given with the job is already one level "
        "lower than the role's; judge the answers against it."
    ),
    "relocating": "Relocating or remote-first: location and moving are never relevant.",
}


@dataclass(frozen=True)
class Line:
    """One transcript segment (INTV-008)."""

    start_ms: int
    end_ms: int
    speaker: str  # interviewer | candidate | other
    text: str
    topic_index: int | None


@dataclass(frozen=True)
class Turn:
    """Consecutive lines of one speaker in one topic, numbered from 1."""

    number: int
    speaker: str  # interviewer | candidate
    start_ms: int
    end_ms: int
    speech_ms: int  # the lines' own durations, without the pauses between them
    text: str
    topic_index: int | None


def turns(lines: Sequence[Line], mask: Callable[[str], str] = lambda text: text) -> list[Turn]:
    found: list[Turn] = []
    for line in lines:
        if line.speaker not in SPEAKERS or not line.text.strip():
            continue
        text = mask(line.text.strip())
        last = found[-1] if found else None
        if last and last.speaker == line.speaker and last.topic_index == line.topic_index:
            found[-1] = Turn(
                number=last.number,
                speaker=last.speaker,
                start_ms=last.start_ms,
                end_ms=max(last.end_ms, line.end_ms),
                speech_ms=last.speech_ms + line.end_ms - line.start_ms,
                text=f"{last.text} {text}",
                topic_index=last.topic_index,
            )
        else:
            found.append(
                Turn(
                    number=len(found) + 1,
                    speaker=line.speaker,
                    start_ms=line.start_ms,
                    end_ms=line.end_ms,
                    speech_ms=line.end_ms - line.start_ms,
                    text=text,
                    topic_index=line.topic_index,
                )
            )
    return found


@dataclass(frozen=True)
class Rubric:
    """The pipeline's scoring settings when scored (they total 100, PIPE-003)."""

    weight_technical: int
    weight_communication: int
    weight_culture: int
    pass_mark: int

    def weight(self, criterion: str) -> int:
        weight: int = getattr(self, f"weight_{criterion}")
        return weight

    def snapshot(self) -> dict[str, int]:
        return {
            "weight_technical": self.weight_technical,
            "weight_communication": self.weight_communication,
            "weight_culture": self.weight_culture,
            "pass_mark": self.pass_mark,
        }


@dataclass(frozen=True)
class Context:
    """Everything the interview is judged against. `resume_text` is the redacted text ("" when
    there is none); `claims` are the résumé screen's claims ({requirement, type, found,
    strength}); `must_haves_met` is whether the résumé screen met every must-have (False when
    there was no screen)."""

    job_title: str
    job_description: str
    seniority: str | None
    open_to: Sequence[str]
    skills_to_probe: Sequence[str]
    topics: Sequence[str]  # the plan's topic titles, in order
    resume_text: str
    claims: Sequence[dict[str, Any]] = field(default_factory=list)
    must_haves_met: bool = False


def clock(ms: int) -> str:
    seconds = ms // 1000
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _numbered(items: Sequence[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1)) or "None"


def topic_title(context: Context, index: int) -> str:
    return context.topics[index] if 0 <= index < len(context.topics) else f"Topic {index + 1}"


def transcript_text(context: Context, found: Sequence[Turn]) -> str:
    """Numbered turns with a heading wherever the topic changes."""
    lines: list[str] = []
    topic: int | None = None
    for turn in found:
        if turn.topic_index is not None and turn.topic_index != topic:
            topic = turn.topic_index
            lines.append(f"--- Topic {topic + 1}: {topic_title(context, topic)} ---")
        lines.append(
            f"#{turn.number} [{clock(turn.start_ms)}] {SPEAKERS[turn.speaker]}: {turn.text}"
        )
    return "\n".join(lines)


def variables(context: Context, found: Sequence[Turn]) -> dict[str, str]:
    seniority = context.seniority
    if seniority and "step_up" in context.open_to:
        seniority = STEP_DOWN[seniority]
    rules = [OPEN_TO_RULES[key] for key in OPEN_TO_RULES if key in context.open_to]
    claims = [
        f"{claim.get('requirement', '')}: {claim.get('found', '')}" for claim in context.claims
    ]
    return {
        "job_title": context.job_title,
        "seniority": SENIORITY_LABELS[seniority] if seniority else "Not stated",
        "job_description": context.job_description.strip() or "Not provided",
        "skills_to_probe": _numbered(context.skills_to_probe),
        "topics": _numbered(context.topics),
        "claims": _numbered(claims),
        "resume_text": context.resume_text.strip() or "Not available",
        "transcript": transcript_text(context, found),
        "open_to_rules": (
            "This pipeline is also open to the following applicants; apply these rules:\n"
            + "\n".join(f"- {rule}" for rule in rules)
            if rules
            else ""
        ),
    }


# --- Checking the answer ---------------------------------------------------------------------


def _candidate_turn(found: Sequence[Turn], number: int | None) -> Turn | None:
    if number is None or not 1 <= number <= len(found):
        return None
    turn = found[number - 1]
    return turn if turn.speaker == "candidate" else None


def evidence_row(item: Evidence, found: Sequence[Turn], resume_text: str) -> dict[str, Any] | None:
    """The stored evidence for `item`, or None when it doesn't quote its source word for word."""
    quote = item.quote.strip()
    if not quote:
        return None
    if item.source == "interview":
        turn = _candidate_turn(found, item.turn)
        if turn is None or not quoted(quote, turn.text):
            return None
        return {
            "source": "interview",
            "quote": quote,
            "start_ms": turn.start_ms,
            "source_label": item.label,
        }
    if not resume_text.strip() or not quoted(quote, resume_text):
        return None
    return {"source": "resume", "quote": quote, "source_label": item.label}


def _evidence(
    answer: CriterionAnswer, found: Sequence[Turn], resume_text: str
) -> list[dict[str, Any]]:
    rows = [evidence_row(item, found, resume_text) for item in answer.evidence]
    return [row for row in rows if row is not None][:MAX_EVIDENCE]


def reached_topics(found: Sequence[Turn]) -> list[int]:
    """The plan topics the interview reached, in order."""
    return sorted({turn.topic_index for turn in found if turn.topic_index is not None})


def _answered_topics(found: Sequence[Turn]) -> set[int]:
    return {
        turn.topic_index
        for turn in found
        if turn.speaker == "candidate" and turn.topic_index is not None
    }


def problems(answer: InterviewAssessment, context: Context, found: Sequence[Turn]) -> list[str]:
    """What makes an answer unusable. Labels only, never transcript text, so they can be
    logged."""
    issues: list[str] = []
    for name in CRITERIA:
        criterion: CriterionAnswer = getattr(answer.criteria, name)
        rows = _evidence(criterion, found, context.resume_text)
        if len(rows) < MIN_EVIDENCE or not any(row["source"] == "interview" for row in rows):
            issues.append(f"{name}_evidence")
        if not criterion.signals:
            issues.append(f"{name}_signals")
        if not criterion.held_back.strip():
            issues.append(f"{name}_held_back")
    scored = {topic.topic - 1 for topic in answer.topics}
    for index in sorted(_answered_topics(found) - scored):
        issues.append(f"topic_{index + 1}_score")
    refs = answer.summary.refs
    if not answer.summary.text.strip() or not refs:
        issues.append("summary_missing")
    for number, ref in enumerate(refs, 1):
        if evidence_row(ref, found, context.resume_text) is None:
            issues.append(f"summary_ref_{number}")
    cited = {int(number) for number in _REFERENCE.findall(answer.summary.text)}
    if any(not 1 <= number <= len(refs) for number in cited):
        issues.append("summary_cites_missing_ref")
    return issues


async def assess(
    ai: AIClient,
    context: Context,
    found: Sequence[Turn],
    *,
    workspace_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
) -> InterviewAssessment:
    prompt = load_prompt(*PROMPT)
    for attempt in range(1, ANSWER_TRIES + 1):
        answer = await ai.structured(
            purpose="interview_assessment",
            prompt=prompt,
            variables=variables(context, found),
            schema=InterviewAssessment,
            workspace_id=workspace_id,
            entity_id=entity_id,
            temperature=0,
        )
        issues = problems(answer, context, found)
        if not issues:
            return answer
        logger.warning("interview assessment unusable on try %d: %s", attempt, ", ".join(issues))
    raise AIOutputError()


# --- Computing the result --------------------------------------------------------------------


def _round(value: Decimal, places: str = "0.1") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Decision:
    overall_score: int
    passed: bool
    fit: str | None
    criteria: dict[str, dict[str, Any]]
    topics: list[dict[str, Any]]
    summary: dict[str, Any]
    strengths: list[dict[str, str]]
    probes: list[dict[str, str]]
    claims_checked: list[dict[str, Any]]
    answer_stats: dict[str, Any]
    rubric_snapshot: dict[str, int]


@dataclass(frozen=True)
class Labels:
    questions: frozenset[int]
    follow_ups: frozenset[int]
    candidate_questions: frozenset[int]


def labels(answer: InterviewAssessment, found: Sequence[Turn]) -> Labels:
    """The model's turn labels that name a turn of the right speaker; a turn labelled both a
    question and a follow-up counts as a question."""

    def of(numbers: list[int], speaker: str) -> frozenset[int]:
        return frozenset(
            number
            for number in numbers
            if 1 <= number <= len(found) and found[number - 1].speaker == speaker
        )

    questions = of(answer.turns.questions, "interviewer")
    return Labels(
        questions=questions,
        follow_ups=of(answer.turns.follow_ups, "interviewer") - questions,
        candidate_questions=of(answer.turns.candidate_questions, "candidate"),
    )


def answer_stats(found: Sequence[Turn], marked: Labels) -> dict[str, Any]:
    """Answer patterns from the transcript's timings (FR-ASMT-04); only the question counts
    come from the turn labels."""
    answers = [turn for turn in found if turn.speaker == "candidate"]
    delays = [
        max(0, after.start_ms - before.end_ms)
        for before, after in pairwise(found)
        if before.speaker == "interviewer" and after.speaker == "candidate"
    ]
    candidate_ms = sum(turn.speech_ms for turn in answers)
    interviewer_ms = sum(turn.speech_ms for turn in found if turn.speaker == "interviewer")
    talk = candidate_ms + interviewer_ms
    return {
        "answers": len(answers),
        "avg_answer_ms": round(sum(t.end_ms - t.start_ms for t in answers) / len(answers))
        if answers
        else 0,
        "avg_response_delay_ms": round(sum(delays) / len(delays)) if delays else 0,
        "questions": len(marked.questions),
        "follow_ups": len(marked.follow_ups),
        "candidate_questions": len(marked.candidate_questions),
        "candidate_talk_ms": candidate_ms,
        "interviewer_talk_ms": interviewer_ms,
        "talk_time_pct": round(100 * candidate_ms / talk) if talk else 0,
    }


def fit_of(passed: bool, overall: int, must_haves_met: bool) -> str | None:
    """ADR-011's fit badge."""
    if not passed:
        return None
    if overall >= STRONG_FIT_SCORE and must_haves_met:
        return "strong_fit"
    return "good_fit"


def decide(
    answer: InterviewAssessment, context: Context, found: Sequence[Turn], rubric: Rubric
) -> Decision:
    """The assessment to store, from an answer `problems()` accepted."""
    criteria: dict[str, dict[str, Any]] = {}
    total = Decimal(0)
    for name in CRITERIA:
        criterion: CriterionAnswer = getattr(answer.criteria, name)
        weight = rubric.weight(name)
        points = Decimal(criterion.score * weight) / 100
        total += points
        criteria[name] = {
            "score": criterion.score,
            "weight": weight,
            "points": float(_round(points)),
            "signals": [
                {"name": signal.name, "score": signal.score}
                for signal in criterion.signals[:MAX_SIGNALS]
            ],
            "evidence": _evidence(criterion, found, context.resume_text),
            "held_back": criterion.held_back,
        }
    overall = int(_round(total, "1"))
    passed = overall >= rubric.pass_mark

    marked = labels(answer, found)
    scores = {topic.topic - 1: topic.score for topic in answer.topics}
    answered = _answered_topics(found)
    topics = []
    for index in reached_topics(found):
        in_topic = [turn for turn in found if turn.topic_index == index]
        topics.append(
            {
                "index": index,
                "title": topic_title(context, index),
                "start_ms": min(turn.start_ms for turn in in_topic),
                "questions": sum(1 for turn in in_topic if turn.number in marked.questions),
                "follow_ups": sum(1 for turn in in_topic if turn.number in marked.follow_ups),
                "score": scores.get(index) if index in answered else None,
            }
        )

    checks = {check.claim: check for check in reversed(answer.claims_checked)}
    claims_checked = []
    for number, claim in enumerate(context.claims, 1):
        check = checks.get(number)
        turn = _candidate_turn(found, check.turn) if check else None
        claims_checked.append(
            {
                "requirement": claim.get("requirement", ""),
                "type": claim.get("type", ""),
                "found": claim.get("found", ""),
                "strength": claim.get("strength"),
                "status": check.status if check else "not_covered",
                "start_ms": turn.start_ms if turn else None,
            }
        )

    refs = [evidence_row(ref, found, context.resume_text) for ref in answer.summary.refs]
    return Decision(
        overall_score=overall,
        passed=passed,
        fit=fit_of(passed, overall, context.must_haves_met),
        criteria=criteria,
        topics=topics,
        summary={"text": answer.summary.text, "refs": [ref for ref in refs if ref is not None]},
        strengths=[point.model_dump() for point in answer.strengths[:MAX_POINTS]],
        probes=[point.model_dump() for point in answer.probes[:MAX_POINTS]],
        claims_checked=claims_checked,
        answer_stats=answer_stats(found, marked),
        rubric_snapshot=rubric.snapshot(),
    )
