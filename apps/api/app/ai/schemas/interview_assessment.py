"""`interview_assessment@v1`: what an interview transcript shows against the job's rubric
(AI_PIPELINE.md §4). The model judges each criterion with evidence; the overall score, pass/fail,
fit and answer patterns are computed in code (`app/interview/assessment.py`, ADR-011)."""

from typing import Literal

from pydantic import BaseModel, Field

ClaimStatus = Literal["confirmed", "partly_confirmed", "not_covered", "probe_next_round"]


class Evidence(BaseModel):
    source: Literal["interview", "resume"]
    turn: int | None = Field(
        description="The transcript turn number the quote is from; null for a résumé quote."
    )
    quote: str = Field(
        description=(
            "A short passage copied character for character from that candidate turn, or from "
            "the résumé."
        )
    )
    label: str = Field(
        description=(
            "What it shows or answers, in a few words, e.g. 'System design question' or "
            "'Most recent role'."
        )
    )


class Signal(BaseModel):
    name: str = Field(description="A sub-skill, 1 to 4 words, e.g. 'Trade-off reasoning'.")
    score: int = Field(ge=0, le=100)


class CriterionAnswer(BaseModel):
    score: int = Field(ge=0, le=100)
    signals: list[Signal] = Field(description="3 to 5 sub-skills with scores.")
    evidence: list[Evidence] = Field(
        description="2 to 4 pieces of evidence, at least one quoted from the interview."
    )
    held_back: str = Field(description="What held the score back, in one sentence.")


class Criteria(BaseModel):
    technical: CriterionAnswer
    communication: CriterionAnswer
    culture: CriterionAnswer


class TopicScore(BaseModel):
    topic: int = Field(description="The topic number from the numbered topic list.")
    score: int = Field(ge=0, le=100)


class Summary(BaseModel):
    text: str = Field(
        description="3 to 5 sentences; each claim cites a reference as [1], [2]… in order."
    )
    refs: list[Evidence] = Field(description="The references the text cites, in order.")


class Point(BaseModel):
    title: str = Field(description="A few words.")
    reason: str = Field(description="Why, in a few words, e.g. 'incident topic scored lowest'.")


class ClaimCheck(BaseModel):
    claim: int = Field(description="The claim number from the numbered claim list.")
    status: ClaimStatus
    turn: int | None = Field(
        description="The candidate turn that settles it; null when not covered."
    )


class TurnLabels(BaseModel):
    questions: list[int] = Field(
        description="Interviewer turn numbers that ask a new main question."
    )
    follow_ups: list[int] = Field(
        description="Interviewer turn numbers that follow up on the candidate's last answer."
    )
    candidate_questions: list[int] = Field(
        description="Candidate turn numbers where the candidate asks a question of their own."
    )


class InterviewAssessment(BaseModel):
    criteria: Criteria
    topics: list[TopicScore]
    summary: Summary
    strengths: list[Point] = Field(description="1 to 4 strengths.")
    probes: list[Point] = Field(description="1 to 4 things worth probing in the next round.")
    claims_checked: list[ClaimCheck]
    turns: TurnLabels
