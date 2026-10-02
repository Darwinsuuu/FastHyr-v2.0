"""Interview plan generation (AI_PIPELINE.md §2, FR-INTV-01).

1. `generate()` asks `interview_plan@v1` for a plan built from the job, the pipeline's interview
   settings, the redacted résumé and the claims the résumé screening flagged. `resolve()` turns
   the answer's skill numbers into names and drops any résumé quote it can't find word for word
   (or that holds a mask): a seed keeps its question without the quote, a claim is dropped. The
   plan must then pass `problems()`: 4-7 topics, warm-up first and the candidate's questions
   last, 1-3 seeds per topic, every skill to probe covered, and no personal detail (no mask
   such as [NAME], and not the candidate's name). A plan that fails is asked for once more, then
   fails like any invalid answer (`AIOutputError`).
2. `fallback()` builds a plain plan in code from the skills to probe, used when the model can't
   give a usable plan, so a candidate who passed screening is never held up by it.

Nothing here logs résumé or plan text.
"""

import logging
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.ai.client import AIClient, AIOutputError
from app.ai.prompts import load_prompt
from app.ai.schemas.interview_plan import InterviewPlan, PlanAnswer
from app.screening.assess import SENIORITY_LABELS, STEP_DOWN, quoted
from app.screening.redact import MASKS

logger = logging.getLogger("app.interview")

PROMPT = ("interview_plan", 1)
PROMPT_VERSION = f"{PROMPT[0]}@v{PROMPT[1]}"
FALLBACK_VERSION = "interview_plan_fallback@v1"
ANSWER_TRIES = 2

MIN_TOPICS = 4
MAX_TOPICS = 7
MAX_SEEDS = 3
# The live interview's cap (ADR-012); the public demo passes its own.
INTERVIEW_MINUTES = 30
# The fallback gives each skill its own topic up to this many, then groups them.
FALLBACK_SKILL_TOPICS = 5

TONES = {
    "warm": "Warm: friendly and encouraging, puts the applicant at ease.",
    "professional": "Professional: courteous, neutral and structured.",
    "direct": "Direct: concise and to the point, with fewer pleasantries.",
}
FORMATS = {
    "video_voice": "Video and voice interview.",
    "voice_only": "Voice-only interview.",
}
# How each "Also open to" rule changes what the interview asks (the screening rules are in
# app/screening/assess.py).
OPEN_TO_RULES = {
    "fresh_grads": (
        "Fresh graduates: internships, school projects and personal projects are good material "
        "for questions; never ask for years of paid experience."
    ),
    "career_changers": (
        "Career changers: ask how skills from other fields transfer to this job; never question "
        "the change of field itself."
    ),
    "returners": "Returning to work: never ask about time away from work.",
    "no_degree": "No degree required: never ask about degrees or studies.",
    "step_up": (
        "Ready for a step up: the expected seniority given with the job is already one level "
        "lower than the role's; ask how they would grow into the role."
    ),
    "relocating": "Relocating or remote-first: never ask about location or moving.",
}

_MASK = re.compile("|".join(re.escape(mask) for mask in MASKS.values()))
_NOT_WORD = re.compile(r"[^\w]+")
# Name parts shorter than this aren't checked: they match too many ordinary words.
MIN_NAME_PART = 3


@dataclass(frozen=True)
class Context:
    """Everything the plan is built from. `resume_text` is the redacted text ("" when there is
    none, for a manually invited candidate whose résumé couldn't be read)."""

    job_title: str
    job_description: str
    seniority: str | None
    tone: str | None
    interview_format: str | None
    skills_to_probe: Sequence[str]
    must_haves: Sequence[str]
    open_to: Sequence[str]
    company_about: str
    resume_text: str
    screening_claims: Sequence[dict[str, Any]] = field(default_factory=list)
    minutes: int = INTERVIEW_MINUTES

    def skills(self) -> list[str]:
        """What the plan must cover: the skills to probe (publishing requires 3), else the
        must-haves for an older pipeline without them."""
        return list(self.skills_to_probe or self.must_haves)


def _numbered(items: Sequence[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1)) or "None"


def variables(context: Context) -> dict[str, str]:
    seniority = context.seniority
    if seniority and "step_up" in context.open_to:
        seniority = STEP_DOWN[seniority]
    rules = [OPEN_TO_RULES[key] for key in OPEN_TO_RULES if key in context.open_to]
    claims = [
        f"- {claim.get('requirement', '')}: {claim.get('found', '')}"
        for claim in context.screening_claims
    ]
    return {
        "minutes": str(context.minutes),
        "tone": TONES.get(context.tone or "", TONES["professional"]),
        "interview_format": FORMATS.get(context.interview_format or "", FORMATS["video_voice"]),
        "open_to_rules": (
            "This pipeline is also open to the following applicants; apply these rules:\n"
            + "\n".join(f"- {rule}" for rule in rules)
            if rules
            else ""
        ),
        "job_title": context.job_title,
        "seniority": SENIORITY_LABELS[seniority] if seniority else "Not stated",
        "job_description": context.job_description.strip() or "Not provided",
        "company_about": context.company_about.strip() or "Not provided",
        "skills_to_probe": _numbered(context.skills()),
        "must_haves": _numbered(context.must_haves),
        "screening_claims": "\n".join(claims) or "None",
        "resume_text": context.resume_text.strip() or "Not available",
    }


# --- Checking the answer ---------------------------------------------------------------------


def _normal(text: str) -> str:
    return " ".join(_NOT_WORD.sub(" ", text.casefold()).split())


def _texts(plan: InterviewPlan) -> list[str]:
    texts: list[str] = []
    for topic in plan.topics:
        texts += [topic.title, topic.goal]
        for seed in topic.seeds:
            texts += [seed.question, seed.resume_quote]
    for claim in plan.claims_to_verify:
        texts += [claim.claim, claim.resume_quote]
    return texts


def _name_parts(candidate_name: str | None) -> list[re.Pattern[str]]:
    """The candidate's name parts as whole, case-sensitive words. The model never sees the
    name, so this only catches one guessed back from the résumé."""
    parts = [part for part in re.split(r"[^\w'-]+", candidate_name or "") if part]
    return [
        re.compile(rf"(?<!\w){re.escape(part)}(?!\w)")
        for part in parts
        if len(part) >= MIN_NAME_PART
    ]


def personal_details(plan: InterviewPlan, candidate_name: str | None) -> bool:
    """True when any plan text holds a mask or the candidate's name."""
    names = _name_parts(candidate_name)
    return any(
        _MASK.search(text) or any(name.search(text) for name in names) for text in _texts(plan)
    )


def _covered(skill: str, plan: InterviewPlan) -> bool:
    wanted = _normal(skill)
    return any(
        _normal(listed) == wanted
        for topic in plan.topics
        if topic.kind == "skills"
        for listed in topic.skills
    )


def _usable_quote(quote: str, resume_text: str) -> bool:
    return bool(quote) and not _MASK.search(quote) and quoted(quote, resume_text)


def resolve(answer: PlanAnswer, context: Context) -> tuple[InterviewPlan, list[str]]:
    """The stored form of the model's answer: skill numbers become the skills' names, and quotes
    the résumé doesn't contain are dropped (an unquoted question is still a good question; an
    invented quote must never be shown). Returns the plan and its problems: skill numbers outside
    the list. Labels only."""
    skills = context.skills()
    found: list[str] = []
    dropped = 0
    topics = []
    for index, topic in enumerate(answer.topics, 1):
        names = []
        for number in topic.skills:
            if 1 <= number <= len(skills):
                if skills[number - 1] not in names:
                    names.append(skills[number - 1])
            else:
                found.append(f"topic_{index}_skill_number")
        seeds = []
        for seed in topic.seeds:
            keep = _usable_quote(seed.resume_quote, context.resume_text)
            dropped += bool(seed.resume_quote) and not keep
            seeds.append(
                {"question": seed.question, "resume_quote": seed.resume_quote if keep else ""}
            )
        topics.append({**topic.model_dump(), "skills": names, "seeds": seeds})
    claims = [
        claim.model_dump()
        for claim in answer.claims_to_verify
        if _usable_quote(claim.resume_quote, context.resume_text)
    ]
    dropped += len(answer.claims_to_verify) - len(claims)
    if dropped:
        logger.info("interview plan: %d résumé quotes not found and dropped", dropped)
    plan = InterviewPlan.model_validate({"topics": topics, "claims_to_verify": claims})
    return plan, found


def problems(plan: InterviewPlan, context: Context, candidate_name: str | None) -> list[str]:
    """What makes a plan unusable. Labels only, never plan or résumé text, so they can be
    logged."""
    found: list[str] = []
    topics = plan.topics
    if not MIN_TOPICS <= len(topics) <= MAX_TOPICS:
        found.append("topic_count")
    kinds = [topic.kind for topic in topics]
    if not kinds or kinds[0] != "warm_up" or kinds.count("warm_up") != 1:
        found.append("warm_up_first")
    if not kinds or kinds[-1] != "candidate_questions" or kinds.count("candidate_questions") != 1:
        found.append("candidate_questions_last")
    for index, topic in enumerate(topics, 1):
        if not 1 <= len(topic.seeds) <= MAX_SEEDS:
            found.append(f"topic_{index}_seeds")
        for number, seed in enumerate(topic.seeds, 1):
            if seed.resume_quote and not quoted(seed.resume_quote, context.resume_text):
                found.append(f"topic_{index}_seed_{number}_quote")
    for index, skill in enumerate(context.skills(), 1):
        if not _covered(skill, plan):
            found.append(f"skill_{index}_not_covered")
    for index, claim in enumerate(plan.claims_to_verify, 1):
        if not claim.resume_quote or not quoted(claim.resume_quote, context.resume_text):
            found.append(f"claim_{index}_quote")
    if personal_details(plan, candidate_name):
        found.append("personal_detail")
    return found


async def generate(
    ai: AIClient,
    context: Context,
    *,
    candidate_name: str | None = None,
    workspace_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
) -> InterviewPlan:
    prompt = load_prompt(*PROMPT)
    for attempt in range(1, ANSWER_TRIES + 1):
        answer = await ai.structured(
            purpose="interview_plan",
            prompt=prompt,
            variables=variables(context),
            schema=PlanAnswer,
            workspace_id=workspace_id,
            entity_id=entity_id,
        )
        plan, issues = resolve(answer, context)
        issues += problems(plan, context, candidate_name)
        if not issues:
            return plan
        logger.warning("interview plan unusable on try %d: %s", attempt, ", ".join(issues))
    raise AIOutputError()


# --- Fallback --------------------------------------------------------------------------------


def _groups(skills: list[str]) -> list[list[str]]:
    """One topic per skill, or the skills spread evenly over FALLBACK_SKILL_TOPICS topics."""
    if len(skills) <= FALLBACK_SKILL_TOPICS:
        return [[skill] for skill in skills]
    return [skills[index::FALLBACK_SKILL_TOPICS] for index in range(FALLBACK_SKILL_TOPICS)]


def fallback(context: Context) -> InterviewPlan:
    """A plain plan from the skills to probe, with no résumé quotes and no claims, so it holds
    nothing about the candidate. The live interviewer still adapts with follow-ups."""
    skills = context.skills()
    topics: list[dict[str, Any]] = [
        {
            "kind": "warm_up",
            "title": "Getting started",
            "goal": "Hear how the candidate describes their recent work.",
            "skills": [],
            "seeds": [
                {
                    "question": (
                        "To start, could you walk me through your current or most recent work "
                        "and what you do day to day?"
                    ),
                    "resume_quote": "",
                }
            ],
        }
    ]
    for group in _groups(skills):
        listed = " and ".join(group)
        topics.append(
            {
                "kind": "skills",
                "title": group[0][:60] if len(group) == 1 else f"{group[0][:40]} and more",
                "goal": f"Understand the depth of the candidate's experience with {listed}.",
                "skills": group,
                "seeds": [
                    {
                        "question": (
                            f"Tell me about a time you worked with {listed}. What was the "
                            "situation, what did you do, and how did it turn out?"
                        ),
                        "resume_quote": "",
                    }
                ],
            }
        )
    topics.append(
        {
            "kind": "candidate_questions",
            "title": "Your questions",
            "goal": "Answer the candidate's questions about the role and the team.",
            "skills": [],
            "seeds": [
                {
                    "question": "What would you like to know about the role or the team?",
                    "resume_quote": "",
                }
            ],
        }
    )
    return InterviewPlan.model_validate({"topics": topics, "claims_to_verify": []})
