"""Speech to text for the authoritative interview transcript (ADR-007, MEDIA.md §4, INTV-008).

    result = await transcriber.transcribe(
        path, duration=seconds, workspace_id=workspace_id, entity_id=interview_id
    )
    for segment in result.segments:   # start/end in seconds from the start of the file
        segment.speaker               # the diariser's own labels: "A", "B", …

One call transcribes one audio file of at most 10 minutes (the caller splits longer audio) with
speaker separation. The diariser's labels mean nothing across files; the caller maps them to
interviewer, candidate and other. Every call writes an `ai_calls` row in its own session, so
the log survives the caller's rollback. Nothing here logs what was said.

The diarising model takes no prompt, so `VERSION` names the request settings below instead; bump
it when they change.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

import openai
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.client import FIXTURES_DIR, AIOutputError, AIUnavailableError
from app.core.config import Settings
from app.models import AICall
from app.repositories import ai_calls

logger = logging.getLogger("app.ai")

PURPOSE = "interview_transcription"
VERSION = "transcription@v1"


@dataclass(frozen=True)
class RawSegment:
    start: float
    end: float
    speaker: str
    text: str


@dataclass(frozen=True)
class Transcription:
    segments: list[RawSegment]
    duration: float


class Transcriber(Protocol):
    model: str  # recorded with the transcript

    async def transcribe(
        self,
        path: Path,
        *,
        duration: float,
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Transcription: ...


def _cost(price: dict[str, float] | None, usage: Any, audio_seconds: float) -> Decimal | None:
    """USD from `OPENAI_PRICES`: per-million-token prices (`audio_input` for audio tokens,
    else `input`; `output`) when the answer reports tokens, else `per_minute`."""
    if price is None:
        return None
    usd: float | None = None
    if getattr(usage, "type", None) == "tokens":
        details = getattr(usage, "input_token_details", None)
        audio = int(getattr(details, "audio_tokens", 0) or 0)
        text = int(usage.input_tokens) - audio
        if "input" in price and "output" in price:
            usd = (
                text * price["input"]
                + audio * price.get("audio_input", price["input"])
                + int(usage.output_tokens) * price["output"]
            ) / 1_000_000
    elif "per_minute" in price:
        usd = audio_seconds / 60 * price["per_minute"]
    return None if usd is None else Decimal(str(round(usd, 6)))


class _CallLog:
    def __init__(
        self, sessionmaker: async_sessionmaker[AsyncSession], prices: dict[str, dict[str, float]]
    ) -> None:
        self.sessionmaker = sessionmaker
        self.prices = prices

    async def record(
        self,
        *,
        model: str,
        workspace_id: uuid.UUID | None,
        entity_id: uuid.UUID | None,
        started: float,
        status: str,
        audio_seconds: float,
        usage: Any = None,
    ) -> None:
        call = AICall(
            workspace_id=workspace_id,
            purpose=PURPOSE,
            entity_id=entity_id,
            model=model,
            prompt_version=VERSION,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            audio_seconds=Decimal(str(round(audio_seconds, 2))),
            cost_usd=_cost(self.prices.get(model), usage, audio_seconds),
            latency_ms=round((time.monotonic() - started) * 1000),
            status=status,
        )
        async with self.sessionmaker() as session:
            await ai_calls.add(session, call)


class OpenAITranscriber:
    def __init__(
        self,
        settings: Settings,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        client: openai.AsyncOpenAI | None = None,
    ) -> None:
        self.model = settings.openai_transcribe_model
        self.log = _CallLog(sessionmaker, settings.openai_prices)
        # A 10-minute piece can take a while to transcribe.
        self.openai = client or openai.AsyncOpenAI(
            api_key=settings.openai_api_key or "missing", timeout=300, max_retries=2
        )

    async def transcribe(
        self,
        path: Path,
        *,
        duration: float,
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Transcription:
        if not self.model:
            raise AIUnavailableError("OPENAI_TRANSCRIBE_MODEL is not set")
        started = time.monotonic()
        try:
            with path.open("rb") as audio:
                result = await self.openai.audio.transcriptions.create(
                    model=self.model,
                    file=(path.name, audio, "audio/mp4"),
                    response_format="diarized_json",
                    chunking_strategy="auto",
                    stream=False,
                )
        except openai.OpenAIError as error:
            await self.log.record(
                model=self.model,
                workspace_id=workspace_id,
                entity_id=entity_id,
                started=started,
                status="error",
                audio_seconds=duration,
            )
            logger.warning("transcription: openai error (%s)", type(error).__name__)
            raise AIUnavailableError() from error
        segments = _segments(getattr(result, "segments", None))
        await self.log.record(
            model=self.model,
            workspace_id=workspace_id,
            entity_id=entity_id,
            started=started,
            status="ok" if segments is not None else "invalid_output",
            audio_seconds=float(getattr(result, "duration", None) or duration),
            usage=getattr(result, "usage", None),
        )
        if segments is None:
            raise AIOutputError()
        return Transcription(
            segments=segments, duration=float(getattr(result, "duration", None) or duration)
        )


def _segments(raw: Any) -> list[RawSegment] | None:
    """The answer's segments, or None when it isn't a diarised answer."""
    if not isinstance(raw, list):
        return None
    segments: list[RawSegment] = []
    for item in raw:
        try:
            start, end = float(item.start), float(item.end)
            speaker, text = str(item.speaker), str(item.text).strip()
        except (AttributeError, TypeError, ValueError):
            return None
        if end < start or start < 0:
            return None
        if text:
            segments.append(RawSegment(start=start, end=end, speaker=speaker, text=text))
    return segments


class FakeTranscriber:
    """`AI_FAKE=1`: every file reads as the web's scripted interview
    (`fixtures/transcription@v1.json`), its lines spread over the file's length in proportion
    to their words, logged with model `fake`. Tests pass `segments` to answer with their own."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession] | None = None,
        *,
        segments: list[list[RawSegment]] | None = None,
    ) -> None:
        self.model = "fake"
        self.log = _CallLog(sessionmaker, {}) if sessionmaker is not None else None
        self.queued = segments
        self.calls: list[float] = []

    async def transcribe(
        self,
        path: Path,
        *,
        duration: float,
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Transcription:
        started = time.monotonic()
        self.calls.append(duration)
        segments = self.queued.pop(0) if self.queued else _scripted(duration)
        if self.log is not None:
            await self.log.record(
                model=self.model,
                workspace_id=workspace_id,
                entity_id=entity_id,
                started=started,
                status="ok",
                audio_seconds=duration,
            )
        return Transcription(segments=segments, duration=duration)


def _scripted(duration: float) -> list[RawSegment]:
    lines = json.loads((FIXTURES_DIR / f"{VERSION}.json").read_text(encoding="utf-8"))["segments"]
    words = [len(line["text"].split()) + 2 for line in lines]  # +2: a pause after each line
    scale = duration / sum(words) if duration > 0 else 0
    segments: list[RawSegment] = []
    at = 0.0
    for line, count in zip(lines, words, strict=True):
        length = (count - 2) * scale
        segments.append(
            RawSegment(start=at, end=at + length, speaker=line["speaker"], text=line["text"])
        )
        at += count * scale
    return segments


def transcriber_from_settings(
    settings: Settings, sessionmaker: async_sessionmaker[AsyncSession]
) -> Transcriber:
    if settings.ai_fake:
        return FakeTranscriber(sessionmaker)
    return OpenAITranscriber(settings, sessionmaker)
