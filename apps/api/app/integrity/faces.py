"""The same-face check (ADR-016, MEDIA.md §5), video interviews with biometric consent only.

1. `scan()` has ffmpeg sample one frame every 2 s from the recording, scaled down, and streams
   the raw frames through a pipe: no frame is written anywhere. For each frame the face model
   (`OpenCVFaces`: YuNet to find faces, SFace to describe them, both local, `weights/`) gives
   the unit-length embedding of the largest clear face, or none.
2. `analyse()` builds the reference face from the first 60 s (the medoid of those faces and the
   faces like it) and flags `different_face` where the face in frame stops matching it for 3
   samples in a row, and `no_face` where no face is visible for 20 s or more.

Embeddings stay in this process's memory for the length of the job and are never stored,
logged or sent anywhere; flags keep only times and similarity numbers.
"""

import logging
import statistics
import subprocess
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np
import numpy.typing as npt

from app.integrity.config import DEFAULT, Thresholds
from app.integrity.flags import Found, clamp, confidence

logger = logging.getLogger("app.integrity")

WEIGHTS = Path(__file__).parent / "weights"
DETECTOR_FILE = WEIGHTS / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_FILE = WEIGHTS / "face_recognition_sface_2021dec_int8.onnx"
# Recorded with every face flag.
FACE_MODEL = "yunet-2023mar+sface-2021dec-int8"

Frame = npt.NDArray[np.uint8]  # height x width x 3, BGR
Embedding = npt.NDArray[np.float32]


class FaceModel(Protocol):
    name: str

    def embed(self, frame: Frame) -> Embedding | None:
        """The unit-length embedding of the largest clear face in the frame, or None."""
        ...


class OpenCVFaces:
    """YuNet + SFace through OpenCV, on the CPU. Not thread-safe: one per scan."""

    name = FACE_MODEL

    def __init__(self, thresholds: Thresholds = DEFAULT) -> None:
        self.thresholds = thresholds
        self.detector = cv2.FaceDetectorYN.create(
            str(DETECTOR_FILE), "", (320, 320), thresholds.face_min_score
        )
        self.recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_FILE), "")
        self._size: tuple[int, int] | None = None

    def embed(self, frame: Frame) -> Embedding | None:
        height, width = frame.shape[:2]
        if self._size != (width, height):
            self.detector.setInputSize((width, height))
            self._size = (width, height)
        _, faces = self.detector.detect(frame)
        if faces is None or len(faces) == 0:
            return None
        clear = [
            face
            for face in faces
            if min(face[2], face[3]) >= self.thresholds.face_min_size
            and face[14] >= self.thresholds.face_min_score
        ]
        if not clear:
            return None
        largest = max(clear, key=lambda face: float(face[2] * face[3]))
        aligned = self.recognizer.alignCrop(frame, largest)
        feature = np.asarray(self.recognizer.feature(aligned), dtype=np.float32).reshape(-1)
        return unit(feature)


def unit(vector: npt.NDArray[Any]) -> Embedding:
    norm = float(np.linalg.norm(vector))
    result: Embedding = (vector / norm if norm > 0 else vector).astype(np.float32)
    return result


@dataclass(frozen=True)
class Sample:
    at_ms: int  # on the recording's clock
    embedding: Embedding | None  # None: no clear face


# --- 1. Frames --------------------------------------------------------------------------------


def frame_size(size: tuple[int, int], max_width: int) -> tuple[int, int]:
    """The sampled frames' size: the video's, scaled down to `max_width`, both sides even."""
    width, height = size
    target = min(width, max_width)
    target -= target % 2
    scaled = max(2, round(height * target / width / 2) * 2)
    return target, scaled


def frames(
    ffmpeg: str, video: Path, size: tuple[int, int], interval_ms: int
) -> Iterator[tuple[int, Frame]]:
    """(time, frame) every `interval_ms`, decoded by ffmpeg straight into memory."""
    width, height = size
    rate = 1000 / interval_ms
    process = subprocess.Popen(  # the frames never touch the disk
        [
            ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(video),
            "-an",
            "-vf",
            f"fps={rate:g},scale={width}:{height}",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdout is not None
    length = width * height * 3
    index = 0
    try:
        while True:
            data = process.stdout.read(length)
            if len(data) < length:
                break
            frame: Frame = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)
            yield index * interval_ms, frame
            index += 1
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.kill()
        process.wait()


def scan(
    ffmpeg: str,
    video: Path,
    size: tuple[int, int],
    model: FaceModel,
    thresholds: Thresholds = DEFAULT,
) -> list[Sample]:
    """Every sampled frame's face. CPU-bound: callers run it in a thread."""
    shape = frame_size(size, thresholds.frame_max_width)
    return [
        Sample(at_ms=at, embedding=model.embed(frame))
        for at, frame in frames(ffmpeg, video, shape, thresholds.frame_interval_ms)
    ]


# --- 2. Analysis ------------------------------------------------------------------------------


def reference(samples: Sequence[Sample], thresholds: Thresholds = DEFAULT) -> Embedding | None:
    """The candidate's face: from the faces in the first 60 s (or the first few faces found),
    the one most like the others, averaged with those that match it."""
    faces = [sample for sample in samples if sample.embedding is not None]
    early = [sample for sample in faces if sample.at_ms < thresholds.reference_window_ms]
    if len(early) < thresholds.reference_min_faces:
        early = faces[: thresholds.reference_min_faces]
    if not early:
        return None
    matrix = np.stack([sample.embedding for sample in early if sample.embedding is not None])
    similarity = matrix @ matrix.T
    medoid = int(np.argmax(similarity.mean(axis=1)))
    members = matrix[similarity[medoid] >= thresholds.face_min_similarity]
    return unit(members.mean(axis=0))


def _no_face(run: Sequence[Sample], interval: int, end_ms: int | None, th: Thresholds) -> Found:
    start = run[0].at_ms
    end = run[-1].at_ms + interval
    if end_ms is not None:
        end = min(end, end_ms)
    seconds = (end - start) / 1000
    return Found(
        type="no_face",
        start_ms=start,
        end_ms=end,
        # Longer stretches are less likely to be a glance away or a dropped frame.
        confidence=confidence(0.6 + 0.35 * clamp((end - start - th.no_face_min_ms) / 40_000)),
        detail={"seconds": round(seconds), "samples": len(run)},
    )


def _different(
    run: Sequence[tuple[Sample, float]], interval: int, end_ms: int | None, th: Thresholds
) -> Found:
    start = run[0][0].at_ms
    end = run[-1][0].at_ms + interval
    if end_ms is not None:
        end = min(end, end_ms)
    mean = statistics.fmean(similarity for _, similarity in run)
    margin = clamp((th.face_min_similarity - mean) / th.face_min_similarity)
    length = clamp((len(run) - th.different_face_min_samples) / 5)
    return Found(
        type="different_face",
        start_ms=start,
        end_ms=end,
        # Lower similarity and a longer run make a different person more likely.
        confidence=confidence(0.5 + 0.3 * margin + 0.19 * length),
        detail={
            "samples": len(run),
            "mean_similarity": round(mean, 3),
            "min_similarity": round(min(similarity for _, similarity in run), 3),
            "threshold": th.face_min_similarity,
        },
    )


def analyse(
    samples: Sequence[Sample], thresholds: Thresholds = DEFAULT, *, end_ms: int | None = None
) -> list[Found]:
    """`no_face` and `different_face` flags from the sampled faces, in time order. `end_ms`
    (the recording's length) caps the last flag's end."""
    th = thresholds
    interval = th.frame_interval_ms
    found: list[Found] = []

    missing: list[Sample] = []
    for sample in [*samples, None]:
        if sample is not None and sample.embedding is None:
            missing.append(sample)
            continue
        if missing and len(missing) * interval >= th.no_face_min_ms:
            found.append(_no_face(missing, interval, end_ms, th))
        missing = []

    ref = reference(samples, th)
    if ref is not None:
        run: list[tuple[Sample, float]] = []
        for sample in [*samples, None]:
            if sample is not None and sample.embedding is not None:
                similarity = float(ref @ sample.embedding)
                if similarity < th.face_min_similarity:
                    run.append((sample, similarity))
                    continue
            # A match, a frame with no face or the end closes the run.
            if len(run) >= th.different_face_min_samples:
                found.append(_different(run, interval, end_ms, th))
            run = []
    found.sort(key=lambda flag: (flag.start_ms, flag.type))
    return found
