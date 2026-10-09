"""What an integrity check found, before it is stored as an `integrity_flags` row."""

from dataclasses import dataclass, field
from typing import Any, Literal

FlagType = Literal["different_face", "no_face", "second_voice", "read_aloud", "unusual_timing"]


@dataclass(frozen=True)
class Found:
    type: FlagType
    start_ms: int  # on the recording's clock
    end_ms: int
    confidence: float  # 0..1
    # Numbers the flag was raised on (and, for read_aloud, the model's rationale). Never an
    # embedding, a frame or transcript text.
    detail: dict[str, Any] = field(default_factory=dict)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def confidence(value: float) -> float:
    """Rounded to two places and kept below certainty: a flag is never proof."""
    return round(clamp(value, 0.0, 0.99), 2)
