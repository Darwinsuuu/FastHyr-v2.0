"""`interview_plan@v1`: one candidate's interview plan (AI_PIPELINE.md §2). The model answers
with `PlanAnswer` (skills as numbers from the prompt's list, so they can't be reworded); code
turns it into an `InterviewPlan` with the skills' names, drops résumé quotes it can't find, and
checks the order, coverage and that no personal detail appears (`app/interview/plan.py`)."""

from typing import Literal

from pydantic import BaseModel, Field

TopicKind = Literal["warm_up", "skills", "candidate_questions"]


class Seed(BaseModel):
    question: str = Field(description="A starting question, spoken to the candidate.")
    resume_quote: str = Field(
        description=(
            "Verbatim text from the résumé the question builds on, shown to the candidate as "
            "'From your résumé', or an empty string when the question doesn't use the résumé."
        )
    )


class Topic(BaseModel):
    kind: TopicKind = Field(
        description="warm_up for the first topic, candidate_questions for the last, else skills."
    )
    title: str = Field(description="A short topic name shown to the candidate, 2 to 5 words.")
    goal: str = Field(description="What the interviewer wants to learn, in one sentence.")
    skills: list[str] = Field(description="The skills to probe this topic covers.")
    seeds: list[Seed] = Field(description="1 to 3 starting questions.")


class ClaimToVerify(BaseModel):
    claim: str = Field(description="What the résumé claims, in a few neutral words.")
    resume_quote: str = Field(description="Verbatim text from the résumé making the claim.")
    skill: str = Field(description="The skill to probe or must-have it relates to.")


class InterviewPlan(BaseModel):
    """The stored plan: each topic's skills by name."""

    topics: list[Topic]
    claims_to_verify: list[ClaimToVerify]


class TopicAnswer(BaseModel):
    kind: TopicKind = Field(
        description="warm_up for the first topic, candidate_questions for the last, else skills."
    )
    title: str = Field(description="A short topic name shown to the candidate, 2 to 5 words.")
    goal: str = Field(description="What the interviewer wants to learn, in one sentence.")
    skills: list[int] = Field(
        description=(
            "The numbers of the skills to probe this topic covers, from the numbered list; "
            "[] for warm_up and candidate_questions."
        )
    )
    seeds: list[Seed] = Field(description="1 to 3 starting questions.")


class PlanAnswer(BaseModel):
    """What the model returns."""

    topics: list[TopicAnswer]
    claims_to_verify: list[ClaimToVerify]
