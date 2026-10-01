"""Structured text-model calls through the OpenAI Responses API (ADR-007).

    result = await ai.structured(
        purpose="resume_assessment",
        prompt=load_prompt("resume_assessment", 1),
        variables={"resume_text": redacted, ...},
        schema=ResumeAssessment,
        workspace_id=workspace_id,
        entity_id=application_id,
    )

The schema goes to the model as a strict JSON schema and the answer is validated with Pydantic.
An invalid answer (bad JSON, schema mismatch, refusal, cut off) is retried once, then raises
`AIOutputError`, never accepted silently (AI_PIPELINE.md §0). Network errors, rate limits and
5xx are retried by the SDK; if they persist, `AIUnavailableError`. Every try writes an
`ai_calls` row in its own session, so the log survives the caller's rollback.
"""

import functools
import json
import logging
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Protocol, cast

import httpx2
import openai
from openai.lib._pydantic import to_strict_json_schema
from openai.types.responses import ResponseTextConfigParam
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.prompts import Prompt, RenderedPrompt
from app.core.config import Settings
from app.models import AICall
from app.repositories import ai_calls

logger = logging.getLogger("app.ai")

FIXTURES_DIR = Path(__file__).parent / "fixtures"
# One retry after the first invalid answer (AI_PIPELINE.md §0).
OUTPUT_TRIES = 2


class AIOutputError(Exception):
    """The model's answer failed validation on every try."""

    code = "ai_invalid_output"


class AIUnavailableError(Exception):
    """OpenAI couldn't be reached or kept failing. Jobs retry these."""

    code = "ai_unavailable"


class AIClient(Protocol):
    async def structured[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt: Prompt,
        variables: dict[str, str],
        schema: type[T],
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        temperature: float | None = None,
    ) -> T: ...


class _CallLog:
    """Writes one ai_calls row per try."""

    def __init__(
        self, sessionmaker: async_sessionmaker[AsyncSession], prices: dict[str, dict[str, float]]
    ) -> None:
        self.sessionmaker = sessionmaker
        self.prices = prices

    def cost(self, model: str, input_tokens: int, output_tokens: int) -> Decimal | None:
        price = self.prices.get(model)
        if price is None:
            return None
        usd = (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000
        return Decimal(str(round(usd, 6)))

    async def record(
        self,
        *,
        purpose: str,
        prompt_version: str,
        model: str,
        workspace_id: uuid.UUID | None,
        entity_id: uuid.UUID | None,
        started: float,
        status: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        call = AICall(
            workspace_id=workspace_id,
            purpose=purpose,
            entity_id=entity_id,
            model=model,
            prompt_version=prompt_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.cost(model, input_tokens, output_tokens),
            latency_ms=round((time.monotonic() - started) * 1000),
            status=status,
        )
        async with self.sessionmaker() as session:
            await ai_calls.add(session, call)


def _validate[T: BaseModel](schema: type[T], text: str | None) -> T | None:
    if not text:
        return None
    try:
        return schema.model_validate_json(text)
    except ValidationError:
        return None


class OpenAIClient:
    def __init__(
        self,
        settings: Settings,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        http_client: httpx2.AsyncClient | None = None,
        max_retries: int = 2,
    ) -> None:
        self.model = settings.openai_text_model
        self.log = _CallLog(sessionmaker, settings.openai_prices)
        self.openai = openai.AsyncOpenAI(
            api_key=settings.openai_api_key or "missing",
            timeout=settings.openai_timeout_seconds,
            max_retries=max_retries,
            http_client=http_client,
        )

    async def structured[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt: Prompt,
        variables: dict[str, str],
        schema: type[T],
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        temperature: float | None = None,
    ) -> T:
        if not self.model:
            raise AIUnavailableError("OPENAI_TEXT_MODEL is not set")
        rendered = prompt.render(variables)
        text_format = cast(
            ResponseTextConfigParam,
            {
                "format": {
                    "type": "json_schema",
                    "name": schema.__name__,
                    "schema": to_strict_json_schema(schema),
                    "strict": True,
                }
            },
        )
        record = functools.partial(
            self.log.record,
            purpose=purpose,
            prompt_version=rendered.version,
            model=self.model,
            workspace_id=workspace_id,
            entity_id=entity_id,
        )
        for attempt in range(1, OUTPUT_TRIES + 1):
            started = time.monotonic()
            try:
                response = await self.openai.responses.create(
                    model=self.model,
                    instructions=rendered.system,
                    input=rendered.user,
                    text=text_format,
                    temperature=temperature if temperature is not None else openai.omit,
                    store=False,
                )
            except openai.OpenAIError as error:
                await record(started=started, status="error")
                logger.warning("ai %s: openai error (%s)", purpose, type(error).__name__)
                raise AIUnavailableError() from error
            usage = response.usage
            result = (
                _validate(schema, response.output_text) if response.status == "completed" else None
            )
            await record(
                started=started,
                status="ok" if result is not None else "invalid_output",
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
            )
            if result is not None:
                return result
            logger.warning("ai %s: invalid output on try %d", purpose, attempt)
        raise AIOutputError()


class FakeAIClient:
    """`AI_FAKE=1`: answers from `fixtures/<prompt>@v<N>.json` (or `responses` passed in tests),
    validated against the schema like a real answer, and logged with model `fake`."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        responses: dict[str, list[str]] | None = None,
        fixtures_dir: Path = FIXTURES_DIR,
    ) -> None:
        self.log = _CallLog(sessionmaker, {})
        self.responses = responses or {}
        self.fixtures_dir = fixtures_dir
        self.calls: list[RenderedPrompt] = []

    def _answer(self, version: str) -> str:
        queued = self.responses.get(version)
        if queued:
            return queued.pop(0)
        path = self.fixtures_dir / f"{version}.json"
        if not path.is_file():
            raise AIUnavailableError(f"no fake answer for {version}")
        return json.dumps(json.loads(path.read_text(encoding="utf-8")))

    async def structured[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt: Prompt,
        variables: dict[str, str],
        schema: type[T],
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        temperature: float | None = None,
    ) -> T:
        rendered = prompt.render(variables)
        self.calls.append(rendered)
        for _ in range(OUTPUT_TRIES):
            started = time.monotonic()
            result = _validate(schema, self._answer(rendered.version))
            await self.log.record(
                purpose=purpose,
                prompt_version=rendered.version,
                model="fake",
                workspace_id=workspace_id,
                entity_id=entity_id,
                started=started,
                status="ok" if result is not None else "invalid_output",
            )
            if result is not None:
                return result
        raise AIOutputError()


def ai_client_from_settings(
    settings: Settings, sessionmaker: async_sessionmaker[AsyncSession]
) -> AIClient:
    if settings.ai_fake:
        return FakeAIClient(sessionmaker)
    return OpenAIClient(settings, sessionmaker)
