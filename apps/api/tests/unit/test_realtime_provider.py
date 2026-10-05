"""INTV-004: the OpenAI Realtime provider opens calls with the browser's offer (ADR-021)."""

import asyncio

import httpx2
import openai
import pytest

from app.ai.realtime import OpenAIRealtime, RealtimeOfferRejectedError, RealtimeUnavailableError


def provider(handler: object, model: str = "rt-test") -> OpenAIRealtime:
    client = openai.AsyncOpenAI(
        api_key="sk-test",
        base_url="https://openai.test/v1",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),  # type: ignore[arg-type]
        max_retries=0,
    )
    return OpenAIRealtime(
        api_key="sk-test", model=model, base_url="https://openai.test/v1", client=client
    )


def test_a_call_is_opened_with_the_offer_and_session_and_returns_the_answer() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.read().decode()
        return httpx2.Response(
            201,
            text="v=0\r\ns=answer\r\n",
            headers={"Location": "/v1/realtime/calls/rtc_123", "Content-Type": "application/sdp"},
        )

    call = asyncio.run(
        provider(handler).create_call(sdp="v=0\r\ns=offer\r\n", session={"type": "realtime"})
    )
    assert (call.call_id, call.sdp) == ("rtc_123", "v=0\r\ns=answer\r\n")
    assert seen["path"] == "/v1/realtime/calls"
    assert seen["auth"] == "Bearer sk-test"
    body = str(seen["body"])
    assert "s=offer" in body and '{"type":"realtime"}' in body


def test_a_refused_offer_and_an_outage_are_told_apart() -> None:
    def refused(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(400, json={"error": {"message": "bad sdp"}})

    def down(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(503, json={"error": {"message": "unavailable"}})

    with pytest.raises(RealtimeOfferRejectedError):
        asyncio.run(provider(refused).create_call(sdp="v=0", session={}))
    with pytest.raises(RealtimeUnavailableError):
        asyncio.run(provider(down).create_call(sdp="v=0", session={}))
    with pytest.raises(RealtimeUnavailableError):
        asyncio.run(provider(down, model="").create_call(sdp="v=0", session={}))
