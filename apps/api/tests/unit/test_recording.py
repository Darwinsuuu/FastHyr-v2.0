"""Putting a recording together with ffmpeg (INTV-006): each attempt's chunks joined back into
its stream, attempts joined without re-encoding when they match, and re-encoded when they
don't."""

import asyncio
from pathlib import Path

from app.interview import recording
from app.interview.recording import Part
from tests.media_fixtures import chunks, ffmpeg, fragmented_mp4, webm


def part(folder: Path, name: str, data: bytes, kind: recording.Kind) -> Part:
    path = folder / f"{name}.raw"
    # Joined from timeslice chunks, as the job does.
    path.write_bytes(b"".join(chunks(data, 4)))
    return Part(path=path, kind=kind)


def build(folder: Path, parts: list[Part], *, video: bool = True) -> recording.Built | None:
    workdir = folder / "work"
    workdir.mkdir()
    return asyncio.run(recording.build(ffmpeg(), parts, workdir, video=video))


def probe(path: Path) -> recording.Probe:
    return asyncio.run(recording.probe(ffmpeg(), path))


def test_two_webm_attempts_join_without_re_encoding(tmp_path: Path) -> None:
    built = build(
        tmp_path,
        [part(tmp_path, "a", webm(3), "webm"), part(tmp_path, "b", webm(2, tone=300), "webm")],
    )

    assert built is not None
    assert (built.kind, built.video, built.duration_seconds) == ("webm", True, 5)
    assert recording.content_type(built.kind, built.video) == "video/webm"
    final = probe(built.recording)
    assert final.video and final.audio
    assert built.audio is not None and probe(built.audio).audio
    assert not probe(built.audio).video
    assert built.poster is not None and built.poster.stat().st_size > 0


def test_safari_mp4_becomes_a_playable_mp4(tmp_path: Path) -> None:
    built = build(tmp_path, [part(tmp_path, "a", fragmented_mp4(3), "mp4")])

    assert built is not None
    assert (built.kind, built.duration_seconds) == ("mp4", 3)
    # Fast start: the index comes first, so playback starts before the whole file loads.
    data = built.recording.read_bytes()
    assert data.index(b"moov") < data.index(b"mdat")
    assert b"moof" not in data


def test_attempts_from_different_browsers_are_re_encoded_to_mp4(tmp_path: Path) -> None:
    built = build(
        tmp_path,
        [part(tmp_path, "a", webm(2), "webm"), part(tmp_path, "b", fragmented_mp4(2), "mp4")],
    )

    assert built is not None
    assert (built.kind, built.video, built.duration_seconds) == ("mp4", True, 4)
    assert probe(built.recording).size == (320, 240)


def test_an_attempt_without_its_first_chunk_is_left_out(tmp_path: Path) -> None:
    headless = tmp_path / "headless.raw"
    headless.write_bytes(b"".join(chunks(webm(3), 4)[1:]))

    built = build(tmp_path, [Part(headless, "webm"), part(tmp_path, "b", webm(2), "webm")])

    assert built is not None
    assert built.duration_seconds == 2


def test_nothing_readable_gives_no_recording(tmp_path: Path) -> None:
    broken = tmp_path / "broken.raw"
    broken.write_bytes(b"".join(chunks(webm(3), 4)[1:]))

    assert build(tmp_path, [Part(broken, "webm")]) is None


def test_voice_only_records_audio_without_a_poster(tmp_path: Path) -> None:
    built = build(tmp_path, [part(tmp_path, "a", webm(3, video=False), "webm")], video=False)

    assert built is not None
    assert (built.kind, built.video, built.poster) == ("webm", False, None)
    assert recording.content_type(built.kind, built.video) == "audio/webm"
