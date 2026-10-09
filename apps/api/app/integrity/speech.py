"""The checks on the transcript (ADR-016, AI_PIPELINE.md §5): pure functions over its lines.

- `second_voice()`: speech the diariser gave to a third voice (`other`, INTV-008), joined
  across short gaps, flagged from 3 s.
- `answers()`: each candidate answer with its timing: the pause after the question, its pace
  and how even that pace is, and its filler words.
- `unusual_timing()`: answer delays far above the session's own baseline (median + 3 scaled
  MADs, at least 4 s more), flagged when it happens at least twice.
- `read_aloud_windows()`: answers with the read-aloud pattern (a long pause, then a long, even,
  fluent answer) that the model then judges (`app/integrity/read_aloud.py`).

Nothing here logs transcript text, and no flag's detail holds any.
"""

import itertools
import re
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from app.integrity.config import DEFAULT, Thresholds
from app.integrity.flags import Found, clamp, confidence
from app.interview.assessment import Line

# Scaled MAD: comparable to a standard deviation for normally distributed delays.
MAD_SCALE = 1.4826
_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)?")
_FILLER = re.compile(r"\b(?:u+h+|u+m+|uhm+|e+r+m*|a+h+|h+m+|mm+|you know|i mean)\b", re.IGNORECASE)


def words(text: str) -> int:
    return len(_WORD.findall(text))


# --- Second voice -----------------------------------------------------------------------------


def second_voice(lines: Sequence[Line], thresholds: Thresholds = DEFAULT) -> list[Found]:
    th = thresholds
    spans: list[list[int]] = []  # [start, end, speech ms, lines]
    for line in lines:
        if line.speaker != "other" or line.end_ms <= line.start_ms:
            continue
        if spans and line.start_ms - spans[-1][1] <= th.voice_join_ms:
            span = spans[-1]
            span[1] = max(span[1], line.end_ms)
            span[2] += line.end_ms - line.start_ms
            span[3] += 1
        else:
            spans.append([line.start_ms, line.end_ms, line.end_ms - line.start_ms, 1])
    return [
        Found(
            type="second_voice",
            start_ms=start,
            end_ms=end,
            # More speech from the other voice makes it less likely to be a stray sound.
            confidence=confidence(0.6 + 0.35 * clamp((speech - th.second_voice_min_ms) / 12_000)),
            detail={"seconds": round(speech / 1000, 1), "segments": count},
        )
        for start, end, speech, count in spans
        if speech >= th.second_voice_min_ms
    ]


# --- Answers ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    """A candidate's reply to the interviewer's turn just before it."""

    number: int  # 1-based, in order
    question: str
    text: str
    question_end_ms: int
    start_ms: int
    end_ms: int
    # The pause after the question; None when an attempt started in between (a reconnect).
    delay_ms: int | None
    words: int
    speech_ms: int
    rate_wpm: float
    # Coefficient of variation of the per-line pace; None with fewer than two timed lines.
    rate_variation: float | None
    fillers_per_100: float


def _turns(lines: Sequence[Line]) -> list[list[Line]]:
    """Consecutive lines of the interviewer or the candidate; other voices are left out."""
    turns: list[list[Line]] = []
    for line in lines:
        if line.speaker not in ("interviewer", "candidate") or not line.text.strip():
            continue
        if turns and turns[-1][0].speaker == line.speaker:
            turns[-1].append(line)
        else:
            turns.append([line])
    return turns


def _rate(lines: Sequence[Line]) -> tuple[float, float | None]:
    total_words = sum(words(line.text) for line in lines)
    speech_ms = sum(max(0, line.end_ms - line.start_ms) for line in lines)
    rate = total_words / (speech_ms / 60_000) if speech_ms > 0 else 0.0
    paces = [
        words(line.text) / ((line.end_ms - line.start_ms) / 60_000)
        for line in lines
        if line.end_ms - line.start_ms >= 1_000 and words(line.text) >= 3
    ]
    variation = None
    if len(paces) >= 2 and statistics.fmean(paces) > 0:
        variation = statistics.pstdev(paces) / statistics.fmean(paces)
    return rate, variation


def answers(lines: Sequence[Line], attempt_starts_ms: Sequence[int] = ()) -> list[Answer]:
    found: list[Answer] = []
    turns = _turns(lines)
    for previous, turn in itertools.pairwise(turns):
        if turn[0].speaker != "candidate" or previous[0].speaker != "interviewer":
            continue
        question_end = max(line.end_ms for line in previous)
        start = turn[0].start_ms
        reconnected = any(question_end < at <= start for at in attempt_starts_ms)
        text = " ".join(line.text.strip() for line in turn)
        count = words(text)
        rate, variation = _rate(turn)
        found.append(
            Answer(
                number=len(found) + 1,
                question=" ".join(line.text.strip() for line in previous),
                text=text,
                question_end_ms=question_end,
                start_ms=start,
                end_ms=max(line.end_ms for line in turn),
                delay_ms=None if reconnected else max(0, start - question_end),
                words=count,
                speech_ms=sum(max(0, line.end_ms - line.start_ms) for line in turn),
                rate_wpm=rate,
                rate_variation=variation,
                fillers_per_100=100 * len(_FILLER.findall(text)) / count if count else 0.0,
            )
        )
    return found


@dataclass(frozen=True)
class Baseline:
    delay_ms: float  # median
    mad_ms: float  # scaled median absolute deviation
    rate_wpm: float  # median
    answers: int


def baseline(found: Sequence[Answer]) -> Baseline | None:
    timed = [answer for answer in found if answer.delay_ms is not None]
    if not timed:
        return None
    delays = [answer.delay_ms for answer in timed if answer.delay_ms is not None]
    median = statistics.median(delays)
    mad = statistics.median(abs(delay - median) for delay in delays) * MAD_SCALE
    rates = [answer.rate_wpm for answer in timed if answer.rate_wpm > 0] or [0.0]
    return Baseline(
        delay_ms=median, mad_ms=mad, rate_wpm=statistics.median(rates), answers=len(timed)
    )


# --- Timing -----------------------------------------------------------------------------------


def delay_limit(base: Baseline, thresholds: Thresholds = DEFAULT) -> float:
    th = thresholds
    excess = max(th.timing_mad_factor * base.mad_ms, th.timing_min_excess_ms)
    return max(base.delay_ms + excess, th.timing_min_delay_ms)


def unusual_timing(found: Sequence[Answer], thresholds: Thresholds = DEFAULT) -> Found | None:
    """One flag over the answers whose delay is an outlier for this session, when there are
    enough of them; None otherwise (also with too few answers for a baseline)."""
    th = thresholds
    base = baseline(found)
    if base is None or base.answers < th.timing_min_answers:
        return None
    limit = delay_limit(base, th)
    late = [answer for answer in found if answer.delay_ms is not None and answer.delay_ms > limit]
    if len(late) < th.timing_min_outliers:
        return None
    share = len(late) / base.answers
    return Found(
        type="unusual_timing",
        start_ms=late[0].question_end_ms,
        end_ms=late[-1].start_ms,
        # Timing alone is weak evidence: more and a larger share of late answers raise it a
        # little, never above 0.8.
        confidence=confidence(min(0.8, 0.4 + 0.1 * (len(late) - th.timing_min_outliers) + share)),
        detail={
            "baseline_delay_ms": round(base.delay_ms),
            "limit_ms": round(limit),
            "answers": base.answers,
            "late": [
                {
                    "answer": answer.number,
                    "question_end_ms": answer.question_end_ms,
                    "delay_ms": answer.delay_ms,
                }
                for answer in late
            ],
        },
    )


def timing_ran(found: Sequence[Answer], thresholds: Thresholds = DEFAULT) -> bool:
    base = baseline(found)
    return base is not None and base.answers >= thresholds.timing_min_answers


# --- Read aloud -------------------------------------------------------------------------------


def read_aloud_windows(
    found: Sequence[Answer], thresholds: Thresholds = DEFAULT
) -> list[Answer] | None:
    """The answers worth the model's judgement, in time order; None when the session has too
    few answers to judge any of them against."""
    th = thresholds
    base = baseline([answer for answer in found if answer.words >= 5])
    if base is None or base.answers < th.read_aloud_min_answers:
        return None
    pause = max(th.read_pause_min_ms, th.read_pause_factor * base.delay_ms)
    picked = [
        answer
        for answer in found
        if answer.delay_ms is not None
        and answer.delay_ms >= pause
        and answer.words >= th.read_min_words
        and answer.fillers_per_100 <= th.read_max_fillers_per_100
        and (answer.rate_variation is None or answer.rate_variation <= th.read_max_rate_variation)
    ]
    picked.sort(key=lambda answer: answer.delay_ms or 0, reverse=True)
    return sorted(picked[: th.read_max_windows], key=lambda answer: answer.start_ms)
