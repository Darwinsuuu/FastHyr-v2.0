"""Putting an interview's recording together with ffmpeg (INTV-006, MEDIA.md §3).

Each attempt is one MediaRecorder stream that the browser uploaded in pieces; joined byte for
byte in order, the pieces are that stream again (WebM from most browsers, fragmented MP4 from
Safari). `build()` remuxes each attempt without re-encoding, joins the attempts, and makes the
files people and later jobs use: the recording, `audio.m4a` for transcription (INTV-008) and a
poster frame. It re-encodes (H.264/AAC in MP4) only when the attempts can't be joined as they
are, for example after a resume in a different browser.

Everything runs in a temporary folder the caller owns; nothing here touches Storage or the
database, and nothing is logged about the content.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger("app.recording")

Kind = Literal["webm", "mp4"]

# Re-encoding is the slow path; give each ffmpeg run room, but not forever.
FFMPEG_TIMEOUT_SECONDS = 25 * 60
POSTER_WIDTH = 640

_DURATION = re.compile(r"Duration: (\d+):(\d\d):(\d\d(?:\.\d+)?)")
_VIDEO = re.compile(r"Stream #\d+:\d+.*: Video: (?!mjpeg|png)")
_AUDIO = re.compile(r"Stream #\d+:\d+.*: Audio: ")
_SIZE = re.compile(r"Video: .*?, (\d{2,5})x(\d{2,5})")


class FfmpegError(Exception):
    """ffmpeg exited with an error (its output stays out of logs: it can quote metadata)."""


@dataclass(frozen=True)
class Part:
    """One attempt's stream, joined from its chunks."""

    path: Path
    kind: Kind


@dataclass(frozen=True)
class Probe:
    duration: float | None
    video: bool
    audio: bool
    size: tuple[int, int] | None


@dataclass(frozen=True)
class Built:
    recording: Path
    kind: Kind
    video: bool
    audio: Path | None
    poster: Path | None
    duration_seconds: int


def content_type(kind: Kind, video: bool) -> str:
    return f"{'video' if video else 'audio'}/{kind}"


async def run_ffmpeg(ffmpeg: str, *args: str) -> str:
    """Runs ffmpeg and returns what it wrote to stderr. Raises `FfmpegError` on failure."""
    process = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), FFMPEG_TIMEOUT_SECONDS)
    except TimeoutError as error:
        process.kill()
        await process.wait()
        raise FfmpegError("ffmpeg timed out") from error
    if process.returncode != 0:
        raise FfmpegError(f"ffmpeg exited with {process.returncode}")
    return stderr.decode("utf-8", "replace")


async def probe(ffmpeg: str, path: Path) -> Probe:
    """What a file holds, from ffmpeg's own description of its input (`ffmpeg -i` with no
    output exits with an error by design, so the exit code is ignored)."""
    process = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-i",
        str(path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    text = stderr.decode("utf-8", "replace")
    duration = None
    if match := _DURATION.search(text):
        hours, minutes, seconds = match.groups()
        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    size = None
    if match := _SIZE.search(text):
        size = (int(match.group(1)), int(match.group(2)))
    return Probe(
        duration=duration,
        video=bool(_VIDEO.search(text)),
        audio=bool(_AUDIO.search(text)),
        size=size,
    )


async def remux(ffmpeg: str, part: Part, out: Path) -> Path | None:
    """The attempt as a proper file (duration, index, timestamps from 0) without re-encoding.
    None when ffmpeg can't read it, e.g. its first chunk, which holds the header, is missing."""
    target = out.with_suffix(f".{part.kind}")
    flags = ["-movflags", "+faststart"] if part.kind == "mp4" else []
    try:
        await run_ffmpeg(
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-fflags",
            "+genpts+discardcorrupt",
            "-i",
            str(part.path),
            "-map",
            "0",
            "-c",
            "copy",
            *flags,
            str(target),
        )
    except FfmpegError:
        return None
    found = await probe(ffmpeg, target)
    if not (found.audio or found.video) or not found.duration:
        return None
    return target


async def concat_copy(ffmpeg: str, parts: list[Path], kind: Kind, out: Path) -> Path:
    """Joins same-format attempts with the concat demuxer, without re-encoding."""
    listing = out.with_name("parts.txt")
    listing.write_text("".join(f"file '{part.as_posix()}'\n" for part in parts))
    target = out.with_suffix(f".{kind}")
    flags = ["-movflags", "+faststart"] if kind == "mp4" else []
    await run_ffmpeg(
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(listing),
        "-map",
        "0",
        "-c",
        "copy",
        *flags,
        str(target),
    )
    return target


async def concat_encode(
    ffmpeg: str, parts: list[Path], probes: list[Probe], out: Path, *, video: bool
) -> Path:
    """Joins attempts that can't be joined as they are, re-encoding to H.264/AAC MP4 at the
    first attempt's frame size."""
    width, height = next((p.size for p in probes if p.size), (1280, 720))
    width, height = width - width % 2, height - height % 2
    inputs: list[str] = []
    filters: list[str] = []
    labels = ""
    for index, part in enumerate(parts):
        inputs += ["-i", str(part)]
        if video:
            filters.append(
                f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{index}]"
            )
            labels += f"[v{index}]"
        filters.append(f"[{index}:a]aresample=48000[a{index}]")
        labels += f"[a{index}]"
    filters.append(f"{labels}concat=n={len(parts)}:v={int(video)}:a=1{'[v]' if video else ''}[a]")
    target = out.with_suffix(".mp4")
    codecs = ["-map", "[a]", "-c:a", "aac", "-b:a", "64k"]
    if video:
        codecs = [
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            *codecs,
        ]
    await run_ffmpeg(
        ffmpeg,
        "-y",
        "-v",
        "error",
        *inputs,
        "-filter_complex",
        ";".join(filters),
        *codecs,
        "-movflags",
        "+faststart",
        str(target),
    )
    return target


async def build(ffmpeg: str, parts: list[Part], workdir: Path, *, video: bool) -> Built | None:
    """The interview's recording from its attempts, in order. Attempts ffmpeg can't read are
    left out; None when none can be read. `video` is the interview's format (voice-only
    interviews record audio only)."""
    usable: list[tuple[Path, Kind]] = []
    for index, part in enumerate(parts):
        remuxed = await remux(ffmpeg, part, workdir / f"attempt-{index}")
        if remuxed is None:
            logger.warning("recording attempt %d could not be read; left out", index)
            continue
        usable.append((remuxed, part.kind))
    if not usable:
        return None

    files = [path for path, _ in usable]
    probes = [await probe(ffmpeg, path) for path in files]
    with_video = video and all(found.video for found in probes)
    recording, kind = await _join(ffmpeg, usable, probes, workdir / "recording", video=with_video)
    final = await probe(ffmpeg, recording)
    duration = final.duration or sum(found.duration or 0 for found in probes)

    audio = workdir / "audio.m4a"
    await run_ffmpeg(
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-i",
        str(recording),
        "-vn",
        "-ac",
        "1",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        str(audio),
    )

    poster: Path | None = None
    if with_video:
        poster = workdir / "poster.jpg"
        at = min(5.0, duration / 2)
        try:
            await run_ffmpeg(
                ffmpeg,
                "-y",
                "-v",
                "error",
                "-ss",
                f"{at:.2f}",
                "-i",
                str(recording),
                "-frames:v",
                "1",
                "-vf",
                f"scale='min({POSTER_WIDTH},iw)':-2",
                "-q:v",
                "4",
                str(poster),
            )
        except FfmpegError:
            poster = None
        if poster is not None and not poster.exists():
            poster = None

    return Built(
        recording=recording,
        kind=kind,
        video=with_video,
        audio=audio,
        poster=poster,
        duration_seconds=round(duration),
    )


async def _join(
    ffmpeg: str, usable: list[tuple[Path, Kind]], probes: list[Probe], out: Path, *, video: bool
) -> tuple[Path, Kind]:
    files = [path for path, _ in usable]
    same_streams = all(found.video == video for found in probes)
    if len(files) == 1 and same_streams:
        return files[0], usable[0][1]
    kinds = {kind for _, kind in usable}
    if len(kinds) == 1 and same_streams:
        kind = usable[0][1]
        try:
            return await concat_copy(ffmpeg, files, kind, out), kind
        except FfmpegError:
            logger.info("recording attempts could not be joined as they are; re-encoding")
    return await concat_encode(ffmpeg, files, probes, out, video=video), "mp4"


def ffmpeg_path(configured: str) -> str:
    """`FFMPEG_PATH`, or the static binary that ships with imageio-ffmpeg."""
    if configured:
        return configured
    import imageio_ffmpeg

    path: str = imageio_ffmpeg.get_ffmpeg_exe()
    return path
