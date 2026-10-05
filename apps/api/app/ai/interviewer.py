"""The live AI interviewer's instructions (AI_PIPELINE.md §3, FR-INTV-04), built from the
interview plan (INTV-001) and the pipeline's interview settings, and the Realtime session they
go out with.

`build()` renders `prompts/interviewer@v1.md`: role and tone, how to run the interview, the
fairness rules, time, tools, the plan's topics with their starting questions and résumé quotes,
the claims to verify, and the job description and company "About" the candidate's questions are
answered from. On a resumed interview (WORKFLOW.md §4) it adds which topics were covered and the
topic to continue from, and the opening cue welcomes the candidate back instead of greeting
them. The candidate's name is never in the instructions: the model only sees the redacted
résumé's quotes (AGENTS.md rule 4).

Any change to the wording here or in the prompt file is a new `interviewer@vN`.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.ai.prompts import load_prompt
from app.interview.plan import FORMATS, INTERVIEW_MINUTES, OPEN_TO_RULES, TONES
from app.screening.assess import SENIORITY_LABELS, STEP_DOWN

PROMPT = ("interviewer", 1)
INSTRUCTIONS_VERSION = f"{PROMPT[0]}@v{PROMPT[1]}"
# The interviewer starts wrapping up at 25 minutes of talk (ADR-012).
WRAP_UP_MINUTES = 25
# Long texts are cut so the instructions stay a manageable size.
MAX_JOB_DESCRIPTION = 8000
MAX_COMPANY_ABOUT = 3000

OPENING = (
    "Begin the interview now. Greet the applicant, introduce yourself as the AI interviewer "
    "for {company}, say it takes about 20 to 30 minutes, and ask whether they are ready."
)
OPENING_RESUMED = (
    "The applicant has reconnected to continue the interview. Welcome them back in one "
    "sentence, without introducing yourself again, say you will carry on where you left off, "
    "then call set_topic with {number} and ask that topic's first question."
)

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "set_topic",
        "description": (
            "Call each time you move to a topic, before its first question, with the topic's "
            "number as listed under Topics (1 is the first topic)."
        ),
        "parameters": {
            "type": "object",
            "properties": {"number": {"type": "integer", "minimum": 1}},
            "required": ["number"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "show_resume_quote",
        "description": (
            "Call right before a question that builds on the résumé, with the exact quote from "
            "the topic's starting question, so the applicant sees it."
        ),
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "end_interview",
        "description": (
            "Call only after you have thanked the applicant and said goodbye: 'completed' when "
            "the topics are done or time is up, 'candidate_request' when they ask to stop."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "enum": ["completed", "candidate_request"]}
            },
            "required": ["reason"],
            "additionalProperties": False,
        },
    },
]
TOOL_NAMES = frozenset(tool["name"] for tool in TOOLS)


@dataclass(frozen=True)
class Context:
    """What the instructions are built from. `topics` and `claims` are the stored plan's
    (`interview_plans.topics` / `claims_to_verify`)."""

    company_name: str
    job_title: str
    job_description: str
    company_about: str
    tone: str | None
    seniority: str | None
    interview_format: str | None
    open_to: Sequence[str]
    topics: Sequence[dict[str, Any]]
    claims: Sequence[dict[str, Any]] = field(default_factory=list)
    # The topic to start from (0-based): 0 for a new interview, later on a resume.
    resume_from: int = 0
    # What is left of the cap when this attempt starts.
    minutes_left: int = INTERVIEW_MINUTES


@dataclass(frozen=True)
class Instructions:
    version: str
    text: str  # the session's instructions
    opening: str  # the cue that makes the interviewer speak first


def resume_point(topic_reached: int | None, topic_count: int) -> int:
    """The topic a new attempt starts from (0-based): the one after the furthest topic the
    interviewer reached, or the last topic if it was already there; 0 when no topic was set."""
    if topic_reached is None or topic_count == 0:
        return 0
    return min(topic_reached + 1, topic_count - 1)


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " …"


def _topics(topics: Sequence[dict[str, Any]]) -> str:
    lines: list[str] = []
    for number, topic in enumerate(topics, 1):
        kind = topic.get("kind")
        label = {"warm_up": " (warm-up)", "candidate_questions": " (their questions)"}.get(
            str(kind), ""
        )
        lines.append(f"{number}. {topic.get('title', '')}{label}")
        if topic.get("goal"):
            lines.append(f"   Goal: {topic['goal']}")
        skills = topic.get("skills") or []
        if skills:
            lines.append(f"   Skills: {', '.join(skills)}")
        seeds = topic.get("seeds") or []
        if seeds:
            lines.append("   Starting questions:")
        for seed in seeds:
            quote = (seed.get("resume_quote") or "").strip()
            suffix = f' (from the résumé: "{quote}")' if quote else ""
            lines.append(f"   - {seed.get('question', '')}{suffix}")
    return "\n".join(lines) or "None"


def _claims(claims: Sequence[dict[str, Any]]) -> str:
    lines = [
        f'- {claim.get("claim", "")} (résumé: "{claim.get("resume_quote", "")}"; '
        f"skill: {claim.get('skill', '')})"
        for claim in claims
    ]
    return "\n".join(lines) or "None"


def _resumed(context: Context) -> str:
    if context.resume_from == 0:
        return ""
    covered = ", ".join(
        f"{number}. {topic.get('title', '')}"
        for number, topic in enumerate(context.topics[: context.resume_from], 1)
    )
    title = context.topics[context.resume_from].get("title", "")
    return (
        "\n# Resuming\n"
        "This interview was interrupted and the applicant has come back to finish it. "
        f"Topics already covered: {covered}. Don't ask about them again. "
        f"Continue from topic {context.resume_from + 1} ({title}). "
        f"About {context.minutes_left} minutes of the interview remain.\n"
    )


def build(context: Context) -> Instructions:
    seniority = context.seniority
    if seniority and "step_up" in context.open_to:
        seniority = STEP_DOWN[seniority]
    rules = [OPEN_TO_RULES[key] for key in OPEN_TO_RULES if key in context.open_to]
    variables = {
        "company_name": context.company_name.strip() or "the hiring company",
        "job_title": context.job_title.strip() or "this role",
        "tone": TONES.get(context.tone or "", TONES["professional"]),
        "seniority": SENIORITY_LABELS[seniority] if seniority else "Not stated",
        "format": FORMATS.get(context.interview_format or "", FORMATS["video_voice"]),
        "open_to_rules": "\n".join(f"- {rule}" for rule in rules),
        "minutes_total": str(INTERVIEW_MINUTES),
        "topics": _topics(context.topics),
        "claims": _claims(context.claims),
        "resume": _resumed(context),
        "job_description": _clip(context.job_description, MAX_JOB_DESCRIPTION) or "Not provided",
        "company_about": _clip(context.company_about, MAX_COMPANY_ABOUT) or "Not provided",
        "opening": (
            OPENING_RESUMED.format(number=context.resume_from + 1)
            if context.resume_from
            else OPENING.format(company=context.company_name.strip() or "the hiring company")
        ),
    }
    rendered = load_prompt(*PROMPT).render(variables)
    return Instructions(version=rendered.version, text=rendered.system, opening=rendered.user)


def session_config(
    instructions: str, *, model: str, voice: str, caption_model: str = ""
) -> dict[str, Any]:
    """The Realtime session (MEDIA.md §2): audio only, server voice activity detection that
    waits about a second of silence so candidates can pause to think, captions from input
    transcription when a caption model is set (never used for scoring), and the three tools."""
    audio_input: dict[str, Any] = {
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 1000,
            "create_response": True,
            "interrupt_response": True,
        },
        "noise_reduction": {"type": "near_field"},
    }
    if caption_model:
        audio_input["transcription"] = {"model": caption_model, "language": "en"}
    return {
        "type": "realtime",
        "model": model,
        "instructions": instructions,
        "output_modalities": ["audio"],
        "audio": {"input": audio_input, "output": {"voice": voice}},
        "tools": TOOLS,
        "tool_choice": "auto",
    }


def wrap_up_message(minutes_left: int) -> str:
    return (
        f"Time message: about {minutes_left} minute{'' if minutes_left == 1 else 's'} of the "
        "interview left. Finish the current question, skip the remaining topics except the "
        "applicant's questions if there is time, and start wrapping up."
    )


GOODBYE_MESSAGE = (
    "Time message: time is up. In one or two sentences, thank the applicant, tell them the "
    "hiring team will review the interview and be in touch by email, and say goodbye. Then "
    'call end_interview with reason "completed".'
)
