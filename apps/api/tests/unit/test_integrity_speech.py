"""ASMT-002 (ADR-016, AI_PIPELINE.md §5): a third voice is flagged from 3 s; answer delays are
judged against the session's own baseline and need two outliers; the read-aloud pattern picks
windows for the model, which flags only with enough confidence and must judge every window."""

import asyncio
import uuid
from typing import Any

import pytest
from pydantic import BaseModel

from app.ai import fakes
from app.ai.client import AIOutputError
from app.ai.prompts import Prompt
from app.integrity import read_aloud, speech
from app.interview.assessment import Line

READ = (
    "Firstly, a distributed cache improves read latency by keeping frequently accessed data "
    "close to the application. Secondly, it reduces load on the primary database, which "
    "improves throughput. Thirdly, invalidation must be handled with care using time to live "
    "values and eviction on writes. In conclusion, it is a trade-off."
)


def session(delays: list[int], *, long_at: int | None = None) -> list[Line]:
    """Question/answer pairs with the given answer delays (ms); the answer at `long_at` is long,
    even and fluent."""
    lines: list[Line] = []
    at = 0
    for index, delay in enumerate(delays):
        lines.append(Line(at, at + 3_000, "interviewer", f"Question {index + 1}?", 1))
        at += 3_000 + delay
        if index == long_at:
            half = len(READ) // 2
            lines.append(Line(at, at + 13_000, "candidate", READ[:half], 1))
            lines.append(Line(at + 13_000, at + 26_000, "candidate", READ[half:], 1))
            at += 26_000
        else:
            lines.append(Line(at, at + 5_000, "candidate", "Um, we used small, careful steps.", 1))
            at += 5_000
        at += 1_000
    return lines


def test_a_third_voice_is_flagged_from_three_seconds() -> None:
    lines = [
        Line(0, 2_000, "other", "Hello?", 0),
        Line(10_000, 12_000, "other", "Say the part about caching.", 0),
        Line(13_500, 15_000, "other", "And the trade-off.", 0),
    ]
    [flag] = speech.second_voice(lines)
    assert (flag.type, flag.start_ms, flag.end_ms) == ("second_voice", 10_000, 15_000)
    assert flag.detail == {"seconds": 3.5, "segments": 2}
    assert 0.6 <= flag.confidence < 1


def test_answers_carry_their_delay_except_across_a_reconnect() -> None:
    found = speech.answers(session([1_000, 2_000, 1_500]), attempt_starts_ms=[14_000])
    assert [answer.delay_ms for answer in found] == [1_000, None, 1_500]
    assert found[0].fillers_per_100 > 0


def test_two_long_delays_against_the_baseline_are_unusual_timing() -> None:
    found = speech.answers(session([1_000, 1_200, 900, 1_100, 1_000, 9_000, 12_000]))
    flag = speech.unusual_timing(found)
    assert flag is not None
    assert flag.type == "unusual_timing"
    assert [late["delay_ms"] for late in flag.detail["late"]] == [9_000, 12_000]
    assert flag.start_ms == found[5].question_end_ms
    assert flag.end_ms == found[6].start_ms
    assert flag.confidence <= 0.8


def test_one_long_pause_or_a_short_session_is_not_unusual() -> None:
    assert speech.unusual_timing(speech.answers(session([1_000] * 6 + [12_000]))) is None
    short = speech.answers(session([1_000, 15_000, 15_000]))
    assert speech.unusual_timing(short) is None
    assert not speech.timing_ran(short)


def test_a_slow_session_is_its_own_baseline() -> None:
    # Someone who always takes about 8 s raises nothing.
    found = speech.answers(session([8_000, 9_000, 7_500, 8_500, 8_000, 9_500]))
    assert speech.unusual_timing(found) is None


def test_read_aloud_windows_are_long_even_answers_after_long_pauses() -> None:
    found = speech.answers(session([1_000, 1_000, 1_000, 1_000, 8_000, 9_000], long_at=4))
    windows = speech.read_aloud_windows(found)
    assert windows is not None
    # The last answer paused too, but it is short and hesitant.
    assert [window.number for window in windows] == [5]
    assert speech.read_aloud_windows(found[:3]) is None


class JudgeAI:
    model = "stub"

    def __init__(self, *answers: dict[str, Any]) -> None:
        self.answers = list(answers)
        self.calls = 0

    async def structured[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt: Prompt,
        variables: dict[str, str],
        schema: type[T],
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        temperature: float | None = None,
    ) -> T:
        self.calls += 1
        assert "Bea" not in variables["windows"]
        return schema.model_validate(self.answers.pop(0))


def judged(*windows: tuple[int, bool, float]) -> dict[str, Any]:
    return {
        "windows": [
            {"window": number, "read_aloud": flag, "confidence": confidence, "rationale": "Even."}
            for number, flag, confidence in windows
        ]
    }


def windows() -> tuple[list[speech.Answer], speech.Baseline]:
    lines = session([1_000, 1_000, 1_000, 1_000, 8_000, 1_000, 9_000], long_at=4)
    lines[0] = Line(0, 3_000, "interviewer", "Hi Bea, question 1?", 1)
    found = speech.answers(lines)
    base = speech.baseline(found)
    assert base is not None
    return [found[4], found[6]], base


def test_the_model_flags_only_confident_windows() -> None:
    picked, base = windows()
    ai = JudgeAI(judged((2, False, 0.2), (1, True, 0.75)))
    found = asyncio.run(
        read_aloud.judge(ai, picked, base, mask=lambda text: text.replace("Bea", "[NAME]"))
    )
    [flag] = found
    assert (flag.type, flag.start_ms, flag.end_ms) == (
        "read_aloud",
        picked[0].start_ms,
        picked[0].end_ms,
    )
    assert flag.confidence == 0.75
    assert flag.detail["rationale"] == "Even."
    assert flag.detail["delay_ms"] == 8_000

    unsure = JudgeAI(judged((1, True, 0.5), (2, True, 0.59)))
    assert asyncio.run(read_aloud.judge(unsure, picked, base, mask=str.lower)) == []


def test_a_judgement_that_skips_a_window_is_asked_again_then_fails() -> None:
    picked, base = windows()
    ai = JudgeAI(judged((1, True, 0.9)), judged((1, False, 0.1), (2, False, 0.1)))
    assert asyncio.run(read_aloud.judge(ai, picked, base, mask=str.lower)) == []
    assert ai.calls == 2

    bad = JudgeAI(judged((1, True, 1.4), (2, True, 0.9)), judged((1, True, 0.9)))
    with pytest.raises(AIOutputError):
        asyncio.run(read_aloud.judge(bad, picked, base, mask=str.lower))


def test_the_fake_judges_every_window() -> None:
    picked, base = windows()
    variables = read_aloud.variables(picked, base, str.lower)
    answer = fakes.integrity_read_aloud(variables)
    assert [item["window"] for item in answer["windows"]] == [1, 2]
