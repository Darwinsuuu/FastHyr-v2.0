"""FND-013: AI calls send a strict JSON schema, validate the answer, retry an invalid answer
once then raise, and write an ai_calls row (tokens, cost, latency, prompt version) for every
try. OpenAI is replaced by a mock HTTP transport, so no network is used."""

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import asyncpg
import httpx2
import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai.client import AIOutputError, AIUnavailableError, FakeAIClient, OpenAIClient
from app.ai.prompts import load_prompt
from app.core.config import Settings
from tests.conftest import Supabase

PROMPTS = Path(__file__).parent.parent / "ai_prompts"
VARIABLES = {"company": "Acme Talent", "job_title": "Backend engineer"}
GOOD = {"summary": "A backend role", "seniority": "senior", "skills": ["python"]}


class Summary(BaseModel):
    summary: str
    seniority: str
    skills: list[str]


def response_body(text: str, *, status: str = "completed") -> dict[str, Any]:
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 1,
        "status": status,
        "model": "test-model",
        "output": [
            {
                "type": "message",
                "id": "msg_1",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "usage": {
            "input_tokens": 1200,
            "output_tokens": 300,
            "total_tokens": 1500,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }


class MockOpenAI:
    """Answers each Responses API request with the next queued (status, body)."""

    def __init__(self, answers: list[tuple[int, dict[str, Any]]]) -> None:
        self.answers = answers
        self.requests: list[dict[str, Any]] = []

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(json.loads(request.content))
        status, body = self.answers.pop(0)
        return httpx2.Response(status, json=body)


Work = Callable[[async_sessionmaker[AsyncSession]], Awaitable[Any]]


def run(supabase: Supabase, work: Work) -> Any:
    async def main() -> Any:
        url = supabase.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(url)
        try:
            return await work(async_sessionmaker(engine, expire_on_commit=False))
        finally:
            await engine.dispose()

    return asyncio.run(main())


def calls_for(supabase: Supabase, entity_id: uuid.UUID) -> list[asyncpg.Record]:
    async def fetch() -> list[asyncpg.Record]:
        connection = await asyncpg.connect(supabase.owner_database_url)
        try:
            rows: list[asyncpg.Record] = await connection.fetch(
                "select model, prompt_version, purpose, status, input_tokens, output_tokens, "
                "cost_usd, latency_ms from ai_calls where entity_id = $1 order by created_at",
                entity_id,
            )
            await connection.execute("delete from ai_calls where entity_id = $1", entity_id)
            return rows
        finally:
            await connection.close()

    return asyncio.run(fetch())


def call(supabase: Supabase, mock: MockOpenAI, entity_id: uuid.UUID) -> Summary:
    settings = Settings(
        openai_api_key="sk-test",
        openai_text_model="test-model",
        openai_prices={"test-model": {"input": 2.0, "output": 8.0}},
    )

    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> Summary:
        transport = httpx2.MockTransport(mock.handler)
        async with httpx2.AsyncClient(transport=transport) as http:
            client = OpenAIClient(settings, sessionmaker, http_client=http, max_retries=0)
            return await client.structured(
                purpose="example",
                prompt=load_prompt("example", 1, PROMPTS),
                variables=VARIABLES,
                schema=Summary,
                entity_id=entity_id,
            )

    result: Summary = run(supabase, work)
    return result


def test_valid_answer_is_returned_and_logged(supabase: Supabase) -> None:
    mock = MockOpenAI([(200, response_body(json.dumps(GOOD)))])
    entity_id = uuid.uuid4()

    result = call(supabase, mock, entity_id)

    assert result == Summary(**GOOD)
    [request] = mock.requests
    assert request["model"] == "test-model"
    assert request["instructions"] == "You summarise a job title for Acme Talent. Reply in JSON."
    assert request["input"] == "Job title: Backend engineer"
    assert request["store"] is False
    text_format = request["text"]["format"]
    assert (text_format["type"], text_format["strict"]) == ("json_schema", True)
    assert text_format["schema"]["additionalProperties"] is False
    assert set(text_format["schema"]["required"]) == {"summary", "seniority", "skills"}

    [row] = calls_for(supabase, entity_id)
    assert (row["model"], row["prompt_version"], row["purpose"], row["status"]) == (
        "test-model",
        "example@v1",
        "example",
        "ok",
    )
    assert (row["input_tokens"], row["output_tokens"]) == (1200, 300)
    # 1200 * $2/M + 300 * $8/M
    assert row["cost_usd"] == Decimal("0.004800")
    assert row["latency_ms"] >= 0


def test_invalid_answer_is_retried_once(supabase: Supabase) -> None:
    mock = MockOpenAI(
        [
            (200, response_body('{"summary": "missing fields"}')),
            (200, response_body(json.dumps(GOOD))),
        ]
    )
    entity_id = uuid.uuid4()

    assert call(supabase, mock, entity_id) == Summary(**GOOD)
    assert [row["status"] for row in calls_for(supabase, entity_id)] == ["invalid_output", "ok"]


def test_invalid_answer_twice_raises(supabase: Supabase) -> None:
    mock = MockOpenAI(
        [
            (200, response_body("not json")),
            (200, response_body(json.dumps(GOOD), status="incomplete")),
        ]
    )
    entity_id = uuid.uuid4()

    with pytest.raises(AIOutputError):
        call(supabase, mock, entity_id)
    assert [row["status"] for row in calls_for(supabase, entity_id)] == [
        "invalid_output",
        "invalid_output",
    ]


def test_openai_failure_raises_unavailable_and_is_logged(supabase: Supabase) -> None:
    mock = MockOpenAI([(500, {"error": {"message": "boom", "type": "server_error"}})])
    entity_id = uuid.uuid4()

    with pytest.raises(AIUnavailableError):
        call(supabase, mock, entity_id)
    [row] = calls_for(supabase, entity_id)
    assert (row["status"], row["input_tokens"]) == ("error", 0)


def test_fake_client_answers_from_fixtures_without_network(supabase: Supabase) -> None:
    entity_id = uuid.uuid4()

    async def work(sessionmaker: async_sessionmaker[AsyncSession]) -> Summary:
        fake = FakeAIClient(sessionmaker, fixtures_dir=PROMPTS)
        return await fake.structured(
            purpose="example",
            prompt=load_prompt("example", 1, PROMPTS),
            variables=VARIABLES,
            schema=Summary,
            entity_id=entity_id,
        )

    result: Summary = run(supabase, work)

    assert result.seniority == "senior"
    [row] = calls_for(supabase, entity_id)
    assert (row["model"], row["status"]) == ("fake", "ok")
