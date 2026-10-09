"""Read-aloud judgement (ADR-016, AI_PIPELINE.md §5): the answers `speech.read_aloud_windows()`
picked go to `integrity_read_aloud@v1` with their timing against the session's baseline. The
model answers per window number; times, confidence threshold and the flag come from code. An
answer that skips or repeats a window, or gives a confidence outside 0..1, is asked for once
more, then `AIOutputError`.

The candidate's name and contact details are masked before the model sees anything (G2).
"""

import logging
import uuid
from collections.abc import Callable, Sequence

from app.ai.client import AIClient, AIOutputError
from app.ai.prompts import load_prompt
from app.ai.schemas.integrity_read_aloud import ReadAloudJudgement
from app.integrity.config import DEFAULT, Thresholds
from app.integrity.flags import Found, confidence
from app.integrity.speech import Answer, Baseline
from app.interview.assessment import clock

logger = logging.getLogger("app.integrity")

PROMPT = ("integrity_read_aloud", 1)
PROMPT_VERSION = f"{PROMPT[0]}@v{PROMPT[1]}"
ANSWER_TRIES = 2


def _seconds(ms: float) -> str:
    return f"{ms / 1000:.1f} s"


def window_text(number: int, answer: Answer, mask: Callable[[str], str]) -> str:
    variation = "n/a" if answer.rate_variation is None else f"{answer.rate_variation:.2f}"
    return "\n".join(
        [
            f"Window {number} [{clock(answer.start_ms)}]",
            f"Question: {mask(answer.question)}",
            f"Answer: {mask(answer.text)}",
            f"Pause before answering: {_seconds(answer.delay_ms or 0)}; "
            f"pace: {answer.rate_wpm:.0f} words per minute; "
            f"pace variation across the answer: {variation}; "
            f"filler words per 100 words: {answer.fillers_per_100:.1f}",
        ]
    )


def variables(
    windows: Sequence[Answer], base: Baseline, mask: Callable[[str], str]
) -> dict[str, str]:
    return {
        "baseline_pause": _seconds(base.delay_ms),
        "baseline_pace": f"{base.rate_wpm:.0f}",
        "answer_count": str(base.answers),
        "windows": "\n\n".join(
            window_text(number, answer, mask) for number, answer in enumerate(windows, 1)
        ),
    }


def problems(answer: ReadAloudJudgement, count: int) -> list[str]:
    numbers = [item.window for item in answer.windows]
    issues: list[str] = []
    if sorted(numbers) != list(range(1, count + 1)):
        issues.append("windows")
    if any(not 0 <= item.confidence <= 1 for item in answer.windows):
        issues.append("confidence")
    return issues


async def judge(
    ai: AIClient,
    windows: Sequence[Answer],
    base: Baseline,
    *,
    mask: Callable[[str], str] = lambda text: text,
    thresholds: Thresholds = DEFAULT,
    workspace_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
) -> list[Found]:
    """`read_aloud` flags for the windows the model judged read aloud with enough confidence."""
    if not windows:
        return []
    prompt = load_prompt(*PROMPT)
    for attempt in range(1, ANSWER_TRIES + 1):
        answer = await ai.structured(
            purpose="integrity_read_aloud",
            prompt=prompt,
            variables=variables(windows, base, mask),
            schema=ReadAloudJudgement,
            workspace_id=workspace_id,
            entity_id=entity_id,
            temperature=0,
        )
        issues = problems(answer, len(windows))
        if not issues:
            return [
                Found(
                    type="read_aloud",
                    start_ms=windows[item.window - 1].start_ms,
                    end_ms=windows[item.window - 1].end_ms,
                    confidence=confidence(item.confidence),
                    detail={
                        "answer": windows[item.window - 1].number,
                        "question_end_ms": windows[item.window - 1].question_end_ms,
                        "delay_ms": windows[item.window - 1].delay_ms,
                        "baseline_delay_ms": round(base.delay_ms),
                        "rate_wpm": round(windows[item.window - 1].rate_wpm),
                        "baseline_rate_wpm": round(base.rate_wpm),
                        "rationale": item.rationale.strip(),
                    },
                )
                for item in sorted(answer.windows, key=lambda item: item.window)
                if item.read_aloud and item.confidence >= thresholds.read_min_confidence
            ]
        logger.warning("read-aloud judgement unusable on try %d: %s", attempt, ", ".join(issues))
    raise AIOutputError()
