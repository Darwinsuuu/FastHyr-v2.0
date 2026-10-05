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
