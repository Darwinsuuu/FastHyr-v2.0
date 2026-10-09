"""Integrity check thresholds (MEDIA.md §5, AI_PIPELINE.md §5, FRAUD_INTEGRITY.md §5).

They live here, in one place, so they can be tuned against the "No concern" rate people give
flags (target: false positives on fewer than 5% of interviews). A change here changes
`RULES_VERSION`, which every rule-based flag records in `ai_decisions`.
"""

from dataclasses import dataclass

RULES_VERSION = "integrity_rules@v1"


@dataclass(frozen=True)
class Thresholds:
    # --- Faces (video only) ---
    # One frame every 2 s.
    frame_interval_ms: int = 2_000
    # Frames are scaled down to this width at most before detection.
    frame_max_width: int = 640
    # YuNet's confidence for a detection to count as a face.
    face_min_score: float = 0.7
    # Faces smaller than this (pixels, the box's shorter side, after scaling) are ignored:
    # too small to compare, usually something in the background.
    face_min_size: int = 40
    # The reference face comes from the first 60 s; with fewer than `reference_min_faces` faces
    # there, from the first `reference_min_faces` faces found.
    reference_window_ms: int = 60_000
    reference_min_faces: int = 3
    # SFace's published cosine-similarity threshold for "same person".
    face_min_similarity: float = 0.363
    # A different face must persist this many samples in a row (6 s) to be flagged.
    different_face_min_samples: int = 3
    # No face for at least this long is flagged.
    no_face_min_ms: int = 20_000

    # --- Voices ---
    # Speech the transcript gives to a third voice, joined across gaps up to `voice_join_ms`,
    # is flagged from this length.
    second_voice_min_ms: int = 3_000
    voice_join_ms: int = 2_000

    # --- Timing ---
    # Answers needed for a session baseline.
    timing_min_answers: int = 5
    # A delay is an outlier when it is above the session's median by more than
    # max(`timing_mad_factor` x scaled MAD, `timing_min_excess_ms`) and at least
    # `timing_min_delay_ms` long.
    timing_mad_factor: float = 3.0
    timing_min_excess_ms: int = 4_000
    timing_min_delay_ms: int = 6_000
    # At least this many outlier answers make an `unusual_timing` flag; one long pause to
    # think is normal.
    timing_min_outliers: int = 2

    # --- Read aloud ---
    # Answers needed before any answer is judged against the session.
    read_aloud_min_answers: int = 4
    # A window for the model: a long pause before the answer (at least `read_pause_min_ms` and
    # `read_pause_factor` x the session's median), a long answer, few filler words and an even
    # pace.
    read_pause_min_ms: int = 4_000
    read_pause_factor: float = 2.5
    read_min_words: int = 40
    read_max_fillers_per_100: float = 1.0
    read_max_rate_variation: float = 0.25
    # At most this many windows go to the model (the longest pauses first).
    read_max_windows: int = 6
    # The model's confidence needed for a flag.
    read_min_confidence: float = 0.6


DEFAULT = Thresholds()
