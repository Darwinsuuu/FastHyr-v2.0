"""`resume_assessment@v1`: what a redacted résumé shows against a pipeline's criteria
(AI_PIPELINE.md §1 step 3). The model judges each part; the fit score and the pass/fail decision
are computed in code (`app/screening/assess.py`, ADR-013)."""

from typing import Literal

from pydantic import BaseModel, Field


class MustHaveResult(BaseModel):
    criterion: str = Field(description="The must-have exactly as listed.")
    met: bool
    evidence_quote: str = Field(
        description="Verbatim text from the résumé showing it, or an empty string when not met."
    )
    strength: Literal[0, 1, 2, 3] = Field(
        description="0 none, 1 mentioned only, 2 good evidence, 3 strong evidence."
    )
    degree_requirement: bool = Field(
        description="True when this must-have only asks for a degree or diploma."
    )
    note: str


class NiceToHaveResult(BaseModel):
    criterion: str = Field(description="The nice-to-have exactly as listed.")
    found: bool
    where: str = Field(description="Where in the résumé, e.g. the role and years, or 'Not found'.")
    evidence_quote: str = Field(
        description="Verbatim text from the résumé showing it, or an empty string when not found."
    )


class Experience(BaseModel):
    relevant_years: float = Field(ge=0, le=60)
    required_hint: str = Field(description="What the role asks for, e.g. '4+ years backend'.")
    score: int = Field(ge=0, le=100)
    note: str


class SkillDepth(BaseModel):
    score: int = Field(ge=0, le=100)
    note: str


class Impact(BaseModel):
    value: str = Field(description="The measurable result, e.g. '-40%' or '4M'.")
    statement: str = Field(description="What it measures, e.g. 'p99 latency on gRPC services'.")


class Claim(BaseModel):
    requirement: str
    type: Literal["must_have", "nice_to_have", "skill"]
    found: str = Field(description="What the résumé says about it, in a few words.")
    strength: Literal[1, 2, 3]


class TimelineEntry(BaseModel):
    employer: str
    title: str
    start_year: int | None
    end_year: int | None = Field(description="Null when current or not stated.")
    current: bool
    relevant: bool = Field(description="True when the role is relevant to this job.")


class CareerSnapshot(BaseModel):
    total_years: float = Field(ge=0, le=60)
    companies: int = Field(ge=0)
    average_years_per_role: float = Field(ge=0, le=60)
    title_promotions: int = Field(ge=0)


class ResumeAssessment(BaseModel):
    must_haves: list[MustHaveResult]
    nice_to_haves: list[NiceToHaveResult]
    experience: Experience
    skill_depth: SkillDepth
    impact: list[Impact]
    claims: list[Claim]
    timeline: list[TimelineEntry]
    career_snapshot: CareerSnapshot
