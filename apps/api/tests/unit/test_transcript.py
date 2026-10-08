"""INTV-008: turning diarised speech into the interview transcript (app/interview/transcript.py):
cutting long audio, merging the pieces, mapping the diariser's labels to speakers, and placing
lines in plan topics."""

from datetime import UTC, datetime, timedelta

import pytest

from app.ai.transcription import RawSegment
from app.interview import transcript
from app.interview.transcript import AttemptSpan, CallEvent, Heard, Piece

T0 = datetime(2026, 10, 7, 9, 0, tzinfo=UTC)
FIRST = "attempt-1"
SECOND = "attempt-2"

GREETING = (
    "Hi, I'm the AI interviewer. Thanks for making time today. This is a relaxed conversation "
    "about your experience. Ready to start?"
)
WARM_UP = "Great. To warm up, tell me a bit about what you're working on right now."
KUBERNETES = "Your résumé mentions migrating forty services to Kubernetes. How did you choose?"


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def said(seconds: float, until: float | None, text: str, attempt: str = FIRST) -> CallEvent:
    return CallEvent(
        attempt_id=attempt,
        kind="ai_speech",
        at=at(seconds),
        ended_at=at(until) if until is not None else None,
        text=text,
    )


def topic(seconds: float, index: int, attempt: str = FIRST) -> CallEvent:
    return CallEvent(attempt_id=attempt, kind="topic", at=at(seconds), topic_index=index)


def line(start: float, end: float, label: str, text: str, piece: int = 0) -> Heard:
    return Heard(
        start_ms=round(start * 1000), end_ms=round(end * 1000), piece=piece, label=label, text=text
    )


ONE_ATTEMPT = [AttemptSpan(FIRST, offset_ms=0, length_ms=600_000, origin=T0, resume_from=0)]


def speakers(heard: list[Heard], events: list[CallEvent], spans=ONE_ATTEMPT) -> list[str]:
    return [item.speaker for item in transcript.build(heard, spans, events)]


# --- Pieces -----------------------------------------------------------------------------------


def test_short_audio_is_one_piece() -> None:
    assert transcript.plan_pieces(420.0, [(100.0, 102.0)]) == [Piece(0.0, 420.0, 0.0, 420.0)]


def test_long_audio_is_cut_in_the_longest_silence_with_overlap() -> None:
    silences = [(200.0, 210.0), (580.0, 582.0), (590.0, 591.0), (1150.0, 1153.0)]
    pieces = transcript.plan_pieces(1500.0, silences)
    # The silence at 200 s is too early (pieces are at least 5 minutes); 580-582 is the longest
    # one between 5 and 10 minutes in.
    assert [(piece.own_start, piece.own_end) for piece in pieces] == [
        (0.0, 581.0),
        (581.0, 1151.5),
        (1151.5, 1500.0),
    ]
    assert [(piece.start, piece.end) for piece in pieces] == [
        (0.0, 583.0),
        (579.0, 1153.5),
        (1149.5, 1500.0),
    ]
    assert all(piece.own_end - piece.own_start <= 600 for piece in pieces)


def test_audio_with_no_silence_is_cut_every_ten_minutes() -> None:
    pieces = transcript.plan_pieces(1500.0, [])
    assert [(piece.own_start, piece.own_end) for piece in pieces] == [
        (0.0, 600.0),
        (600.0, 1200.0),
        (1200.0, 1500.0),
    ]


def test_merging_keeps_each_overlapping_line_once_on_the_recordings_clock() -> None:
    pieces = transcript.plan_pieces(900.0, [])  # 0-600 (sent to 602) and 600-900 (from 598)
    first = [
        RawSegment(590.0, 595.0, "A", "Before the cut."),
        RawSegment(599.0, 601.5, "B", "Across the cut."),
    ]
    second = [
        RawSegment(1.0, 3.5, "A", "Across the cut."),  # 599-601.5 again
        RawSegment(10.0, 12.0, "B", "After the cut."),
    ]
    heard = transcript.merge(pieces, [first, second])
    assert [(item.start_ms, item.end_ms, item.piece, item.text) for item in heard] == [
        (590_000, 595_000, 0, "Before the cut."),
        (599_000, 601_500, 1, "Across the cut."),
        (608_000, 610_000, 1, "After the cut."),
    ]


# --- Speakers ---------------------------------------------------------------------------------


def test_the_interviewer_is_the_voice_saying_its_words_whatever_the_label() -> None:
    events = [said(0.5, 8.0, GREETING), said(12.0, 16.0, WARM_UP)]
    heard = [
        # The diariser heard the candidate first (background noise before the greeting).
        line(0.0, 0.4, "A", "Hello?"),
        line(0.8, 8.2, "B", GREETING),
        line(9.0, 11.0, "A", "Yes, ready. Thanks for having me."),
        line(12.1, 16.3, "B", WARM_UP),
        line(17.0, 25.0, "A", "I lead a small platform team running the payments services."),
    ]
    assert speakers(heard, events) == [
        "candidate",
        "interviewer",
        "candidate",
        "interviewer",
        "candidate",
    ]


def test_a_third_voice_is_kept_as_other() -> None:
    events = [said(0.0, 8.0, GREETING), said(30.0, 35.0, KUBERNETES)]
    heard = [
        line(0.2, 8.1, "A", GREETING),
        line(9.0, 20.0, "B", "Yes. I have been leading a platform team for three years now."),
        line(20.5, 23.0, "C", "Tell them about the outage."),
        line(24.0, 29.0, "B", "Right, and before that I worked on payments."),
        line(30.1, 35.2, "A", KUBERNETES),
    ]
    assert speakers(heard, events) == [
        "interviewer",
        "candidate",
        "other",
        "candidate",
        "interviewer",
    ]


def test_labels_are_mapped_piece_by_piece() -> None:
    # The diariser's labels start again in every piece: here they swap.
    events = [said(0.0, 8.0, GREETING), said(700.0, 705.0, KUBERNETES)]
    heard = [
        line(0.1, 8.0, "A", GREETING, piece=0),
        line(9.0, 30.0, "B", "Thanks. I lead a small platform team.", piece=0),
        line(690.0, 699.0, "A", "That was the hardest part of the migration.", piece=1),
        line(700.2, 705.1, "B", KUBERNETES, piece=1),
        line(706.0, 720.0, "A", "We started with stateless services that had good tests.", piece=1),
    ]
    assert speakers(heard, events) == [
        "interviewer",
        "candidate",
        "candidate",
        "interviewer",
        "candidate",
    ]


def test_the_interviewers_words_under_the_candidates_label_go_back_to_it() -> None:
    events = [said(0.0, 8.0, GREETING), said(20.0, 25.0, WARM_UP), said(40.0, 45.0, KUBERNETES)]
    heard = [
        line(0.1, 8.0, "A", GREETING),
        line(9.0, 19.0, "B", "Yes, ready. Thanks for having me today."),
        # Merged into the candidate's label by the diariser.
        line(20.1, 25.0, "B", WARM_UP),
        line(26.0, 39.0, "B", "I lead a small platform team that runs the payments services."),
        line(40.1, 45.0, "A", KUBERNETES),
        # The candidate echoing part of the question is still the candidate.
        line(46.0, 52.0, "B", "How did we choose? We started with stateless services."),
    ]
    assert speakers(heard, events) == [
        "interviewer",
        "candidate",
        "interviewer",
        "candidate",
        "interviewer",
        "candidate",
    ]


def test_a_piece_heard_as_one_voice_is_told_apart_line_by_line() -> None:
    events = [said(0.0, 8.0, GREETING), said(20.0, 25.0, WARM_UP)]
    heard = [
        line(0.1, 8.0, "A", GREETING),
        line(9.0, 19.0, "A", "Yes, ready. Thanks for having me today."),
        line(20.1, 25.0, "A", WARM_UP),
        line(26.0, 39.0, "A", "I lead a small platform team that runs the payments services."),
    ]
    assert speakers(heard, events) == ["interviewer", "candidate", "interviewer", "candidate"]


def test_without_the_calls_timeline_the_interviewer_is_who_opens_and_asks() -> None:
    heard = [
        line(0.5, 8.0, "B", GREETING),
        line(9.0, 19.0, "A", "Yes, ready. Thanks for having me today."),
        line(20.0, 25.0, "B", WARM_UP),
        # A later piece: no attempt starts in it, so the label asking questions is the
        # interviewer.
        line(700.0, 710.0, "A", "And then we moved the databases last.", piece=1),
        line(711.0, 716.0, "B", "Why the databases last?", piece=1),
        line(717.0, 730.0, "A", "They were the riskiest part.", piece=1),
    ]
    assert speakers(heard, []) == [
        "interviewer",
        "candidate",
        "interviewer",
        "candidate",
        "interviewer",
        "candidate",
    ]


# --- Topics -----------------------------------------------------------------------------------


def test_lines_follow_the_topics_and_a_question_opens_its_topic() -> None:
    events = [
        said(0.0, 8.0, GREETING),
        # "Thanks." is said, then set_topic(2), then the warm-up question.
        said(18.0, 24.0, "Thanks. " + WARM_UP),
        topic(19.5, 1),
        said(40.0, 45.0, KUBERNETES),
        topic(39.5, 2),
    ]
    heard = [
        line(0.1, 8.0, "A", GREETING),
        line(9.0, 17.0, "B", "Yes, ready. Thanks for having me today."),
        line(18.1, 19.0, "A", "Thanks."),
        line(19.8, 24.0, "A", WARM_UP),
        line(25.0, 39.0, "B", "I lead a small platform team that runs the payments services."),
        line(40.1, 45.0, "A", KUBERNETES),
        line(46.0, 52.0, "B", "We started with stateless services."),
    ]
    lines = transcript.build(heard, ONE_ATTEMPT, events)
    assert [item.topic_index for item in lines] == [0, 0, 0, 1, 1, 2, 2]


def test_a_resumed_attempt_starts_on_its_topic_at_its_place_in_the_recording() -> None:
    # The first attempt recorded 60 s; the second resumed from topic 3 an hour later, its
    # connection up at 3600 s on the call clock.
    spans = [
        AttemptSpan(FIRST, offset_ms=0, length_ms=60_000, origin=T0, resume_from=0),
        AttemptSpan(SECOND, offset_ms=60_000, length_ms=60_000, origin=at(3600), resume_from=3),
    ]
    events = [
        said(0.0, 8.0, GREETING),
        topic(30.0, 2),
        said(30.2, 36.0, KUBERNETES),
        said(3600.5, 3606.0, "Welcome back. " + WARM_UP, attempt=SECOND),
        topic(3640.0, 4, attempt=SECOND),
        said(3640.2, 3645.0, "What would you like to ask me about the role?", attempt=SECOND),
    ]
    heard = [
        line(0.1, 8.0, "A", GREETING),
        line(30.3, 36.0, "A", KUBERNETES),
        line(37.0, 59.0, "B", "We started with the stateless services first."),
        line(60.6, 66.0, "A", "Welcome back. " + WARM_UP),
        line(67.0, 99.0, "B", "I lead a small platform team that runs payments."),
        line(100.3, 105.0, "A", "What would you like to ask me about the role?"),
        line(106.0, 119.0, "B", "How big is the team?"),
    ]
    lines = transcript.build(heard, spans, events)
    assert [(item.speaker, item.topic_index) for item in lines] == [
        ("interviewer", 0),
        ("interviewer", 2),
        ("candidate", 2),
        ("interviewer", 3),
        ("candidate", 3),
        ("interviewer", 4),
        ("candidate", 4),
    ]


def test_with_no_attempts_in_the_recording_lines_have_no_topic() -> None:
    lines = transcript.build([line(0.0, 2.0, "A", "Hello.")], [], [])
    assert [(item.speaker, item.topic_index) for item in lines] == [("interviewer", None)]


@pytest.mark.parametrize(
    ("text", "words"),
    [
        ("Your résumé says you migrated 40 services!", {"résumé", "says", "migrated", "services"}),
        ("It's what I'm doing", set()),
    ],
)
def test_content_words(text: str, words: set[str]) -> None:
    assert transcript.content_words(text) == words
