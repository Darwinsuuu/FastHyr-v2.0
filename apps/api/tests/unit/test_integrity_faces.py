"""ASMT-002 (ADR-016, MEDIA.md §5): the reference face comes from the first minute; a different
face is flagged after 3 samples in a row and no face after 20 s, with times and confidence; the
local face model loads from the committed weights and finds no face in an empty frame."""

import numpy as np

from app.integrity import faces
from app.integrity.config import Thresholds
from app.integrity.faces import Sample


def person(index: int, noise: float = 0.0, seed: int = 0) -> faces.Embedding:
    vector = np.zeros(128, dtype=np.float32)
    vector[index] = 1.0
    if noise:
        vector += np.random.default_rng(seed).normal(0, noise, 128).astype(np.float32)
    return faces.unit(vector)


def timeline(*parts: tuple[int | None, int]) -> list[Sample]:
    """(person or None, seconds) parts, sampled every 2 s."""
    samples: list[Sample] = []
    for who, seconds in parts:
        for _ in range(seconds // 2):
            at = len(samples) * 2_000
            embedding = None if who is None else person(who, 0.05, seed=len(samples))
            samples.append(Sample(at_ms=at, embedding=embedding))
    return samples


def test_a_steady_candidate_raises_nothing() -> None:
    assert faces.analyse(timeline((0, 300))) == []


def test_a_different_face_is_flagged_after_three_samples_in_a_row() -> None:
    found = faces.analyse(timeline((0, 60), (1, 6), (0, 30), (1, 4), (0, 20)))

    [flag] = found
    assert (flag.type, flag.start_ms, flag.end_ms) == ("different_face", 60_000, 66_000)
    assert flag.detail["samples"] == 3
    assert flag.detail["mean_similarity"] < 0.363
    assert 0.5 <= flag.confidence < 1


def test_leaving_the_frame_for_20_seconds_is_flagged() -> None:
    found = faces.analyse(timeline((0, 60), (None, 18), (0, 20), (None, 30), (0, 10)))

    [flag] = found
    assert (flag.type, flag.start_ms, flag.end_ms) == ("no_face", 98_000, 128_000)
    assert flag.detail == {"seconds": 30, "samples": 15}


def test_the_last_flag_ends_with_the_recording() -> None:
    [flag] = faces.analyse(timeline((0, 60), (None, 40)), end_ms=99_000)
    assert (flag.start_ms, flag.end_ms) == (60_000, 99_000)


def test_the_reference_is_the_face_of_the_first_minute() -> None:
    # Someone else glances in during the first minute; the candidate is still the reference,
    # and the one who glanced in is flagged when they stay.
    samples = timeline((0, 20), (1, 2), (0, 40), (1, 10), (0, 10))
    reference = faces.reference(samples)
    assert reference is not None and float(reference @ person(0)) > 0.9
    [flag] = faces.analyse(samples)
    assert (flag.type, flag.start_ms) == ("different_face", 62_000)


def test_without_any_face_only_no_face_is_flagged() -> None:
    [flag] = faces.analyse(timeline((None, 30)))
    assert flag.type == "no_face"
    assert faces.reference(timeline((None, 30))) is None


def test_thresholds_are_config() -> None:
    strict = Thresholds(different_face_min_samples=2, no_face_min_ms=10_000)
    types = [flag.type for flag in faces.analyse(timeline((0, 60), (1, 4), (None, 10)), strict)]
    assert types == ["different_face", "no_face"]


def test_frames_are_scaled_down_with_even_sides() -> None:
    assert faces.frame_size((1280, 720), 640) == (640, 360)
    assert faces.frame_size((321, 241), 640) == (320, 240)
    assert faces.frame_size((1080, 1920), 640) == (640, 1138)


def test_the_local_face_model_finds_no_face_in_an_empty_frame() -> None:
    model = faces.OpenCVFaces()
    assert model.embed(np.full((360, 640, 3), 128, dtype=np.uint8)) is None
