"""OpenAI Realtime for the live interview (ADR-007, ADR-021, MEDIA.md §2), behind an interface so
tests and `AI_FAKE=1` run without OpenAI.

    call = await realtime.create_call(sdp=offer, session=config)   # the browser's offer → answer
    sideband = await realtime.attach(call.call_id)                  # server-side control socket
    await sideband.send({"type": "session.update", ...})
    event = await sideband.recv()                                   # None once the call is over
    await realtime.hangup(call.call_id)

The API opens the call with the server key, so it always knows the call id and no OpenAI key
reaches the browser; audio flows between the browser and OpenAI only. Nothing here logs SDP,
instructions or event contents.
"""

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import openai
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from app.core.config import Settings

logger = logging.getLogger("app.ai")

OPENAI_API_URL = "https://api.openai.com/v1"
# The browser's offer is a few KB; anything far larger isn't one.
MAX_SDP_BYTES = 64 * 1024


class RealtimeUnavailableError(Exception):
    """OpenAI couldn't create, attach to or end the call."""


class RealtimeOfferRejectedError(Exception):
    """OpenAI refused the browser's SDP offer (malformed, or no audio)."""


@dataclass(frozen=True)
class RealtimeCall:
    call_id: str
    sdp: str  # the answer for the browser's RTCPeerConnection


class Sideband(Protocol):
    """The server's own connection to a call: JSON events in and out."""

    async def send(self, event: dict[str, Any]) -> None: ...

    async def recv(self) -> dict[str, Any] | None:
        """The next server event, or None once the call or the socket is closed."""
        ...

    async def close(self) -> None: ...


class RealtimeProvider(Protocol):
    model: str

    async def create_call(self, *, sdp: str, session: dict[str, Any]) -> RealtimeCall: ...

    async def attach(self, call_id: str) -> Sideband: ...

    async def hangup(self, call_id: str) -> None:
        """Ends the call. Ending one that is already over is not an error."""
        ...


class _WebSocketSideband:
    def __init__(self, connection: ClientConnection) -> None:
        self.connection = connection

    async def send(self, event: dict[str, Any]) -> None:
        # A closed call is reported by recv().
        with contextlib.suppress(ConnectionClosed):
            await self.connection.send(json.dumps(event))

    async def recv(self) -> dict[str, Any] | None:
        while True:
            try:
                message = await self.connection.recv()
            except ConnectionClosed:
                return None
            try:
                event = json.loads(message)
            except ValueError:
                continue
            if isinstance(event, dict):
                return event

    async def close(self) -> None:
        await self.connection.close()


class OpenAIRealtime:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = OPENAI_API_URL,
        timeout: float = 20,
        client: openai.AsyncOpenAI | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.openai = client or openai.AsyncOpenAI(
            api_key=api_key or "missing", base_url=self.base_url, timeout=timeout, max_retries=1
        )

    async def create_call(self, *, sdp: str, session: dict[str, Any]) -> RealtimeCall:
        if not self.model:
            raise RealtimeUnavailableError("OPENAI_REALTIME_MODEL is not set")
        try:
            result = await self.openai.realtime.calls.create(
                sdp=sdp,
                session=session,  # type: ignore[arg-type]
            )
        except openai.BadRequestError as error:
            raise RealtimeOfferRejectedError() from error
        except openai.OpenAIError as error:
            logger.warning("realtime: create call failed (%s)", type(error).__name__)
            raise RealtimeUnavailableError() from error
        # The new call's id is the last part of `Location: /v1/realtime/calls/{call_id}`.
        location = result.response.headers.get("location", "")
        call_id = location.rstrip("/").rsplit("/", 1)[-1]
        if not call_id:
            raise RealtimeUnavailableError("no call id in the answer")
        return RealtimeCall(call_id=call_id, sdp=result.text)

    async def attach(self, call_id: str) -> Sideband:
        url = self.base_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        try:
            connection = await connect(
                f"{url}/realtime?call_id={call_id}",
                additional_headers={"Authorization": f"Bearer {self.api_key}"},
                open_timeout=15,
                max_size=2**24,
            )
        except (OSError, TimeoutError, WebSocketException) as error:
            logger.warning("realtime: attach failed (%s)", type(error).__name__)
            raise RealtimeUnavailableError() from error
        return _WebSocketSideband(connection)

    async def hangup(self, call_id: str) -> None:
        try:
            await self.openai.realtime.calls.hangup(call_id)
        except openai.NotFoundError:
            pass
        except openai.OpenAIError as error:
            logger.warning("realtime: hangup failed (%s)", type(error).__name__)
            raise RealtimeUnavailableError() from error


class _IdleSideband:
    """A call nobody talks on: waits until it is hung up."""

    def __init__(self, ended: asyncio.Event) -> None:
        self.ended = ended
        self.sent: list[dict[str, Any]] = []

    async def send(self, event: dict[str, Any]) -> None:
        self.sent.append(event)

    async def recv(self) -> dict[str, Any] | None:
        await self.ended.wait()
        return None

    async def close(self) -> None:
        self.ended.set()


class FakeRealtime:
    """`AI_FAKE=1`: calls get a canned answer (a browser can't connect with it) and an idle
    sideband, so the session's time limits, heartbeats and endings all run locally. Local web
    builds recognise the answer (`s=fake`) and play a scripted conversation instead
    (apps/web lib/interview/fake-realtime.ts)."""

    def __init__(self) -> None:
        self.model = "fake"
        self.created: list[dict[str, Any]] = []
        self.hung_up: list[str] = []
        self._ended: dict[str, asyncio.Event] = {}

    async def create_call(self, *, sdp: str, session: dict[str, Any]) -> RealtimeCall:
        call_id = f"rtc_fake_{len(self.created) + 1}"
        self.created.append({"call_id": call_id, "session": session})
        return RealtimeCall(call_id=call_id, sdp="v=0\r\ns=fake\r\n")

    async def attach(self, call_id: str) -> Sideband:
        return _IdleSideband(self._ended.setdefault(call_id, asyncio.Event()))

    async def hangup(self, call_id: str) -> None:
        self.hung_up.append(call_id)
        self._ended.setdefault(call_id, asyncio.Event()).set()


def realtime_from_settings(settings: Settings) -> RealtimeProvider:
    if settings.ai_fake:
        return FakeRealtime()
    return OpenAIRealtime(api_key=settings.openai_api_key, model=settings.openai_realtime_model)
