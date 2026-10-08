"""Turning diarised speech into the interview's transcript (INTV-008, MEDIA.md §4). Pure
functions: the transcribe_interview job (`services/transcripts.py`) does the I/O.

1. `plan_pieces()` cuts long audio into pieces of at most 10 minutes, at a silence where there
   is one, each with a little overlap so no word is lost at a cut.
2. `merge()` puts the pieces' segments back on the recording's clock; a segment belongs to the
   piece whose own range holds its midpoint, so the overlap isn't transcribed twice.
3. `assign_speakers()` maps each piece's diariser labels (A, B…, which mean nothing across
   pieces) to `interviewer`, `candidate` and `other`, using what the server saw the interviewer
   say and when (`interview_events`).
4. `assign_topics()` places every line in a plan topic from the `set_topic` times.

Times on the call (server clock) become recording times through each attempt's place in the
recording: `recording_offset_ms + (t - connected_at)`, since the browser starts recording an
attempt when its connection comes up, the moment it sends its first heartbeat.
"""

import itertools
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from app.ai.transcription import RawSegment

MAX_PIECE_SECONDS = 600.0
MIN_PIECE_SECONDS = 300.0
OVERLAP_SECONDS = 2.0

# Speaker mapping.
NEARBY_MS = 15_000  # how far apart a line and an interviewer response can be and still match
MS_PER_WORD = 400  # an interviewer response's length when the call didn't say when it stopped
SAME_WORDS = 0.8  # share of a line's words that makes it the interviewer's own words
MIN_WORDS = 4  # fewer content words than this can't be told apart by words
INSIDE_MS = 1_000  # tolerance for a line falling inside an interviewer response
# Topics: a topic change applies from the first interviewer line starting at most this long
# before it, so the question that opens a topic is in that topic.
TOPIC_LEAD_MS = 1_000

Speaker = str  # "interviewer" | "candidate" | "other"

_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)?")
# Common words that say nothing about who is speaking.
# fmt: off
_STOP = frozenset({
    "the", "and", "you", "your", "for", "are", "but", "not", "this", "that", "with", "have",
    "was", "were", "what", "when", "where", "which", "who", "how", "why", "can", "could",
    "would", "should", "will", "just", "about", "there", "their", "they", "them", "then",
    "than", "from", "into", "out", "our", "its", "it's", "i'm", "i've", "yes", "yeah", "okay",
    "also", "all", "any", "some", "very", "really", "been", "being", "had", "has", "did",
    "does", "doing", "let's", "me", "my", "we", "us", "so",
})
# fmt: on


def content_words(text: str) -> set[str]:
    return {word for word in _WORD.findall(text.lower()) if len(word) >= 3 and word not in _STOP}


# --- 1. Pieces --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Piece:
    start: float  # the audio sent, in seconds of the recording (own range plus overlap)
    end: float
    own_start: float  # the part of the recording this piece's segments stand for
    own_end: float

    @property
    def length(self) -> float:
        return self.end - self.start


def plan_pieces(
    duration: float,
    silences: Sequence[tuple[float, float]],
    *,
    max_seconds: float = MAX_PIECE_SECONDS,
    min_seconds: float = MIN_PIECE_SECONDS,
    overlap: float = OVERLAP_SECONDS,
) -> list[Piece]:
    """Pieces of at most `max_seconds` (plus overlap), each cut in the longest silence between
    `min_seconds` and `max_seconds` into it, or at `max_seconds` when there is none."""
    cuts: list[float] = []
    own_start = 0.0
    while duration - own_start > max_seconds:
        low, high = own_start + min_seconds, own_start + max_seconds
        quiet = [
            (end - start, (start + end) / 2)
            for start, end in silences
            if low <= (start + end) / 2 <= high
        ]
        cut = max(quiet)[1] if quiet else high
        cuts.append(cut)
        own_start = cut
    bounds = [0.0, *cuts, duration]
    return [
        Piece(
            start=max(0.0, own_start - overlap),
            end=min(duration, own_end + overlap),
            own_start=own_start,
            own_end=own_end,
        )
        for own_start, own_end in itertools.pairwise(bounds)
    ]


# --- 2. Merging -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Heard:
    """A diarised segment on the recording's clock."""

    start_ms: int
    end_ms: int
    piece: int
    label: str  # the diariser's label within its piece
    text: str

    @property
    def mid_ms(self) -> float:
        return (self.start_ms + self.end_ms) / 2


def merge(pieces: Sequence[Piece], answers: Sequence[Sequence[RawSegment]]) -> list[Heard]:
    """`answers[i]` are piece i's segments, timed from the start of the piece."""
    heard: list[Heard] = []
    last = len(pieces) - 1
    for index, (piece, segments) in enumerate(zip(pieces, answers, strict=True)):
        for segment in segments:
            start = piece.start + max(0.0, segment.start)
            end = max(start, piece.start + segment.end)
            mid = (start + end) / 2
            inside = piece.own_start <= mid < piece.own_end or (
                index == last and mid >= piece.own_start
            )
            if not inside or not segment.text.strip():
                continue
            heard.append(
                Heard(
                    start_ms=round(start * 1000),
                    end_ms=round(end * 1000),
                    piece=index,
                    label=segment.speaker,
                    text=segment.text.strip(),
                )
            )
    heard.sort(key=lambda line: (line.start_ms, line.end_ms))
    return heard


# --- The call's timeline on the recording's clock ---------------------------------------------


@dataclass(frozen=True)
class AttemptSpan:
    """One attempt's place in the recording."""

    attempt_id: object
    offset_ms: int
    length_ms: int
    origin: datetime  # the call time the attempt's recording starts at (connected_at)
    resume_from: int

    def at(self, moment: datetime) -> int:
        return self.offset_ms + round((moment - self.origin).total_seconds() * 1000)


@dataclass(frozen=True)
class Spoken:
    """An interviewer response on the recording's clock."""

    start_ms: int
    end_ms: int | None
    words: frozenset[str]

    @property
    def until_ms(self) -> int:
        return (
            self.end_ms
            if self.end_ms is not None
            else self.start_ms + MS_PER_WORD * max(len(self.words), 1)
        )


@dataclass(frozen=True)
class TopicMark:
    at_ms: int
    topic_index: int
    attempt: int  # index into the spans


@dataclass(frozen=True)
class CallEvent:
    """An `interview_events` row, as the transcript needs it."""

    attempt_id: object
    kind: str  # "ai_speech" | "topic"
    at: datetime
    ended_at: datetime | None = None
    text: str | None = None
    topic_index: int | None = None


def place_events(
    spans: Sequence[AttemptSpan], events: Sequence[CallEvent]
) -> tuple[list[Spoken], list[TopicMark]]:
    """Events of attempts that are in the recording, on its clock."""
    index = {span.attempt_id: number for number, span in enumerate(spans)}
    spoken: list[Spoken] = []
    marks: list[TopicMark] = []
    for event in events:
        number = index.get(event.attempt_id)
        if number is None:
            continue
        span = spans[number]
        if event.kind == "topic" and event.topic_index is not None:
            marks.append(TopicMark(span.at(event.at), event.topic_index, number))
        elif event.kind == "ai_speech":
            spoken.append(
                Spoken(
                    start_ms=span.at(event.at),
                    end_ms=span.at(event.ended_at) if event.ended_at else None,
                    words=frozenset(content_words(event.text or "")),
                )
            )
    spoken.sort(key=lambda item: item.start_ms)
    marks.sort(key=lambda item: item.at_ms)
    return spoken, marks


# --- 3. Speakers ------------------------------------------------------------------------------


def _same_words(line: Heard, words: set[str], spoken: Sequence[Spoken]) -> float:
    """The largest share of the line's words found in one nearby interviewer response."""
    if not words:
        return 0.0
    best = 0.0
    for item in spoken:
        if item.start_ms - NEARBY_MS > line.end_ms:
            break
        if item.until_ms + NEARBY_MS < line.start_ms:
            continue
        best = max(best, len(words & item.words) / len(words))
    return best


def _overlap_ms(line: Heard, spoken: Sequence[Spoken]) -> int:
    total = 0
    for item in spoken:
        if item.start_ms > line.end_ms:
            break
        total += max(0, min(line.end_ms, item.until_ms) - max(line.start_ms, item.start_ms))
    return total


def _inside(line: Heard, spoken: Sequence[Spoken]) -> bool:
    return any(
        item.end_ms is not None
        and item.start_ms - INSIDE_MS <= line.mid_ms <= item.end_ms + INSIDE_MS
        for item in spoken
    )


def _first_speaker_after(lines: Sequence[Heard], at_ms: int) -> str | None:
    return next((line.label for line in lines if line.end_ms > at_ms), None)


def _asks_most(lines: Sequence[Heard]) -> str | None:
    asked: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for line in lines:
        asked[line.label][0] += line.text.rstrip().endswith("?")
        asked[line.label][1] += 1
    if not asked:
        return None
    return max(asked, key=lambda label: (asked[label][0] / asked[label][1], asked[label][0]))


def assign_speakers(
    heard: Sequence[Heard],
    spoken: Sequence[Spoken],
    *,
    attempt_starts_ms: Sequence[int] = (0,),
) -> list[Speaker]:
    """`interviewer`, `candidate` or `other` for each line, piece by piece.

    In a piece with interviewer responses in it, the label whose lines carry the interviewer's
    own words and fall in its speaking times is the interviewer; of the rest, the label with
    the most speech is the candidate, and any further voice is `other`. A line the diariser
    gave another label is still the interviewer's when it is the interviewer's words while it
    was speaking (two voices merged under one label). A piece the diariser heard as one voice
    is told apart line by line. With no responses to go on, the interviewer is whoever speaks
    first after an attempt starts (it always opens), else the label asking most questions."""
    speakers: list[Speaker] = ["other"] * len(heard)
    by_piece: dict[int, list[int]] = defaultdict(list)
    for number, line in enumerate(heard):
        by_piece[line.piece].append(number)
    words = [content_words(line.text) for line in heard]

    for numbers in by_piece.values():
        lines = [heard[number] for number in numbers]
        first, last = lines[0].start_ms, lines[-1].end_ms
        near = [
            item
            for item in spoken
            if item.until_ms + NEARBY_MS >= first and item.start_ms - NEARBY_MS <= last
        ]
        labels = {line.label for line in lines}
        match = {number: _same_words(heard[number], words[number], near) for number in numbers}

        if near and len(labels) == 1:
            for number in numbers:
                line = heard[number]
                ours = match[number] >= SAME_WORDS or _inside(line, near)
                speakers[number] = "interviewer" if ours else "candidate"
            continue

        interviewer: str | None = None
        if near:
            score: dict[str, float] = defaultdict(float)
            for number in numbers:
                line = heard[number]
                seconds = (line.end_ms - line.start_ms) / 1000
                score[line.label] += seconds * match[number] + _overlap_ms(line, near) / 1000
            best = max(score, key=lambda label: score[label])
            interviewer = best if score[best] > 0 else None
        if interviewer is None:
            starts = [at for at in attempt_starts_ms if first - NEARBY_MS <= at <= last]
            interviewer = (
                _first_speaker_after(lines, starts[0]) if starts else None
            ) or _asks_most(lines)

        talk: dict[str, int] = defaultdict(int)
        for line in lines:
            if line.label != interviewer:
                talk[line.label] += line.end_ms - line.start_ms
        candidate = max(talk, key=lambda label: talk[label]) if talk else None

        for number in numbers:
            line = heard[number]
            if line.label == interviewer or (
                near
                and len(words[number]) >= MIN_WORDS
                and match[number] >= SAME_WORDS
                and _inside(line, near)
            ):
                speakers[number] = "interviewer"
            elif line.label == candidate:
                speakers[number] = "candidate"
            else:
                speakers[number] = "other"
    return speakers


# --- 4. Topics --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Line:
    start_ms: int
    end_ms: int
    speaker: Speaker
    text: str
    topic_index: int | None = None


def _span_of(line: Line, spans: Sequence[AttemptSpan]) -> int | None:
    """The attempt a line was said in: the last one starting at or before it."""
    found: int | None = None
    for number, span in enumerate(spans):
        if span.offset_ms <= line.start_ms:
            found = number
    return found if found is not None else (0 if spans else None)


def assign_topics(
    lines: Sequence[Line], spans: Sequence[AttemptSpan], marks: Sequence[TopicMark]
) -> list[Line]:
    """Each line's plan topic. An attempt starts on the topic it resumed from; a topic change
    applies from the first interviewer line that starts no more than `TOPIC_LEAD_MS` before it
    (the question that opens the topic), or from the change itself if none follows."""
    if not spans:
        return [replace(line, topic_index=None) for line in lines]
    of_line = [_span_of(line, spans) for line in lines]
    changes: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for mark in marks:
        boundary = next(
            (
                line.start_ms
                for line, attempt in zip(lines, of_line, strict=True)
                if attempt == mark.attempt
                and line.speaker == "interviewer"
                and line.start_ms >= mark.at_ms - TOPIC_LEAD_MS
            ),
            mark.at_ms,
        )
        changes[mark.attempt].append((boundary, mark.topic_index))
    for found in changes.values():
        found.sort()

    placed: list[Line] = []
    for line, attempt in zip(lines, of_line, strict=True):
        if attempt is None:
            placed.append(replace(line, topic_index=None))
            continue
        topic = spans[attempt].resume_from
        for boundary, index in changes.get(attempt, []):
            if boundary <= line.start_ms:
                topic = index
        placed.append(replace(line, topic_index=topic))
    return placed


def build(
    heard: Sequence[Heard], spans: Sequence[AttemptSpan], events: Sequence[CallEvent]
) -> list[Line]:
    """The transcript: lines in recording order with their speaker and topic."""
    spoken, marks = place_events(spans, events)
    speakers = assign_speakers(
        heard, spoken, attempt_starts_ms=[span.offset_ms for span in spans] or [0]
    )
    lines = [
        Line(start_ms=item.start_ms, end_ms=item.end_ms, speaker=speaker, text=item.text)
        for item, speaker in zip(heard, speakers, strict=True)
    ]
    return assign_topics(lines, spans, marks)
