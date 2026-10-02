"""`resume_redaction@v1`: the personal details in a résumé that rules can't find reliably
(AI_PIPELINE.md §1 step 2b). The model returns exact text; code does the masking."""

from typing import Literal

from pydantic import BaseModel, Field

SpanKind = Literal["name", "gender", "age", "school", "address", "personal", "photo"]


class RedactionSpan(BaseModel):
    text: str = Field(description="The exact text as it appears in the résumé.")
    kind: SpanKind


class ResumeRedaction(BaseModel):
    spans: list[RedactionSpan]
