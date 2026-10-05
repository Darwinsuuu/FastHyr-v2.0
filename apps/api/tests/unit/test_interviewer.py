"""INTV-004: the live interviewer's instructions (AI_PIPELINE.md §3) and Realtime session."""

from typing import Any

from app.ai import interviewer

TOPICS: list[dict[str, Any]] = [
    {"kind": "warm_up", "title": "Getting started", "goal": "Ease in.", "skills": [],
     "seeds": [{"question": "Tell me about your current role.", "resume_quote": ""}]},
    {"kind": "skills", "title": "API design", "goal": "Depth on APIs.", "skills": ["API design"],
     "seeds": [{"question": "How was it built?", "resume_quote": "Designed the payments API"}]},
    {"kind": "skills", "title": "Debugging", "goal": "How they debug.", "skills": ["Debugging"],
     "seeds": [{"question": "Walk me through a hard bug.", "resume_quote": ""}]},
    {"kind": "candidate_questions", "title": "Your questions", "goal": "Their questions.",
     "skills": [], "seeds": [{"question": "What would you like to know?", "resume_quote": ""}]},
]  # fmt: skip


def context(**changes: Any) -> interviewer.Context:
    values: dict[str, Any] = {
        "company_name": "Acme Talent",
        "job_title": "Senior Backend Engineer",
        "job_description": "Build and run our APIs.",
        "company_about": "We build hiring tools.",
        "tone": "warm",
        "seniority": "senior",
        "interview_format": "video_voice",
        "open_to": [],
        "topics": TOPICS,
        "claims": [{"claim": "Led a team", "resume_quote": "Led a team of 5", "skill": "Lead"}],
        **changes,
    }
    return interviewer.Context(**values)


def test_instructions_carry_the_fairness_rules_and_never_claim_to_be_human() -> None:
    built = interviewer.build(context())
    assert built.version == "interviewer@v1"
    fairness = built.text.split("# Fairness rules")[1].split("# Time")[0]
    for attribute in (
        "age",
        "family",
        "health",
        "religion",
        "immigration status",
        "ethnicity",
        "sexual orientation",
        "pregnancy",
        "disability",
        "salary history",
        "unrelated to the job",
    ):
        assert attribute in fairness
    assert "don't follow up on it" in fairness
    assert "Never claim or imply that you are human" in built.text
    assert "English only" in built.text
    assert "never give a score" in built.text
    # "Also open to" rules join the fairness rules.
    returners = interviewer.build(context(open_to=["returners"]))
    assert "never ask about time away from work" in returners.text


def test_instructions_follow_the_plan_and_answer_only_from_the_job_and_company() -> None:
    built = interviewer.build(context())
    topics = built.text.split("# Topics")[1]
    assert topics.index("1. Getting started (warm-up)") < topics.index("2. API design")
    assert '(from the résumé: "Designed the payments API")' in topics
    assert "4. Your questions (their questions)" in topics
    assert 'Led a team (résumé: "Led a team of 5"; skill: Lead)' in built.text
    assert "Build and run our APIs." in built.text and "We build hiring tools." in built.text
    assert "The hiring team can share more about that in the next round." in built.text
    assert "Resuming" not in built.text
    assert built.opening.startswith("Begin the interview now")
    # A very long job description is cut so the instructions stay a manageable size.
    long = interviewer.build(context(job_description="word " * 5000))
    assert len(long.text) < len(built.text) + interviewer.MAX_JOB_DESCRIPTION + 10


def test_a_resumed_interview_continues_from_the_next_topic() -> None:
    assert interviewer.resume_point(None, 4) == 0
    assert interviewer.resume_point(0, 4) == 1
    assert interviewer.resume_point(1, 4) == 2
    # Already at the candidate's questions: carry on there.
    assert interviewer.resume_point(3, 4) == 3

    built = interviewer.build(context(resume_from=2, minutes_left=12))
    assert "Topics already covered: 1. Getting started, 2. API design." in built.text
    assert "Continue from topic 3 (Debugging)." in built.text
    assert "About 12 minutes of the interview remain." in built.text
    assert "call set_topic with 3" in built.opening
    assert "without introducing yourself again" in built.opening


def test_the_session_has_the_tools_turn_taking_and_optional_captions() -> None:
    config = interviewer.session_config("Be fair.", model="rt", voice="marin")
    assert config["instructions"] == "Be fair."
    assert {tool["name"] for tool in config["tools"]} == interviewer.TOOL_NAMES
    assert config["audio"]["input"]["turn_detection"]["silence_duration_ms"] == 1000
    assert "transcription" not in config["audio"]["input"]
    captioned = interviewer.session_config("x", model="rt", voice="marin", caption_model="cap")
    assert captioned["audio"]["input"]["transcription"]["model"] == "cap"
    assert "about 1 minute of" in interviewer.wrap_up_message(1)
    assert "about 4 minutes of" in interviewer.wrap_up_message(4)
