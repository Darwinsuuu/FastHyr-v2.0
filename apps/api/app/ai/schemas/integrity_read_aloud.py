"""`integrity_read_aloud@v1`: the model's judgement on answers whose timing looks read aloud
(AI_PIPELINE.md §5, ADR-016). Windows are referred to by number; their times come from code
(`app/integrity/read_aloud.py`)."""

from pydantic import BaseModel, Field


class WindowJudgement(BaseModel):
    window: int = Field(description="The window's number from the list.")
    read_aloud: bool = Field(
        description=(
            "True only when several signs together suggest the answer was read from prepared "
            "text rather than spoken freely."
        )
    )
    confidence: float = Field(
        description="How sure you are of read_aloud, from 0.0 to 1.0 (0.5 = cannot tell)."
    )
    rationale: str = Field(
        description=(
            "One plain sentence for the hiring team about the delivery only (pause, pace, "
            "structure, wording), never about the person."
        )
    )


class ReadAloudJudgement(BaseModel):
    windows: list[WindowJudgement] = Field(description="One judgement for every window listed.")
