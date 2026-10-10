"""Short synthetic recordings shaped like MediaRecorder's output, made with the same ffmpeg the
worker uses: "live" WebM (no duration or index, as Chrome and Firefox write it) and fragmented
MP4 (as Safari writes it). `chunks()` cuts a file into pieces the way a timeslice does."""

import functools
import subprocess
import tempfile
from pathlib import Path

from app.interview.recording import ffmpeg_path


@functools.cache
def ffmpeg() -> str:
    return ffmpeg_path("")


def _make(args: list[str], suffix: str) -> bytes:
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / f"clip{suffix}"
        subprocess.run([ffmpeg(), "-v", "error", "-y", *args, str(out)], check=True)
        return out.read_bytes()


@functools.cache
def webm(seconds: float = 3, *, video: bool = True, tone: int = 440) -> bytes:
    sources = ["-f", "lavfi", "-i", f"sine=frequency={tone}:sample_rate=48000"]
    codecs = ["-c:a", "libopus"]
    if video:
        sources = ["-f", "lavfi", "-i", "testsrc=size=320x240:rate=15", *sources]
        codecs = ["-c:v", "libvpx", "-deadline", "realtime", "-b:v", "200k", *codecs]
    return _make([*sources, "-t", str(seconds), *codecs, "-live", "1", "-f", "webm"], ".webm")


@functools.cache
def fragmented_mp4(seconds: float = 3, *, size: str = "320x240") -> bytes:
    return _make(
        [
            "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=15",
            "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=48000",
            "-t", str(seconds),
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            "-f", "mp4",
        ],
        ".mp4",
    )  # fmt: skip


def chunks(data: bytes, count: int) -> list[bytes]:
    """`data` cut into `count` pieces that join back byte for byte."""
    size = -(-len(data) // count)
    return [data[start : start + size] for start in range(0, len(data), size)]


@functools.cache
def scenes(parts: tuple[tuple[str, float], ...], *, size: str = "320x240") -> bytes:
    """A WebM of solid-colour scenes, e.g. (("red", 40), ("black", 24)), with a quiet audio
    track: stand-ins for faces that tests' colour face model tells apart (ASMT-002)."""
    sources: list[str] = []
    for colour, seconds in parts:
        sources += ["-f", "lavfi", "-i", f"color=c={colour}:s={size}:r=5:d={seconds}"]
    total = sum(seconds for _, seconds in parts)
    sources += ["-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono:d={total}"]
    joined = "".join(f"[{index}:v]" for index in range(len(parts)))
    return _make(
        [
            *sources,
            "-filter_complex", f"{joined}concat=n={len(parts)}:v=1:a=0[v]",
            "-map", "[v]", "-map", f"{len(parts)}:a",
            "-c:v", "libvpx", "-deadline", "realtime", "-b:v", "100k",
            "-c:a", "libopus",
            "-f", "webm",
        ],
        ".webm",
    )  # fmt: skip
