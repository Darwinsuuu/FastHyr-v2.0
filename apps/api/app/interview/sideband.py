"""The server's side of a live interview attempt (MEDIA.md §2, AI_PIPELINE.md §3), run by the
`run_realtime_session` job for as long as the call lasts.

`SessionController.run()` attaches to the call the API opened, applies the interviewer's
instructions and tools, sends the opening cue so the interviewer speaks first (once the browser's
first heartbeat says its connection is up, so the greeting isn't lost), then reacts to the
call's events and to the clock:

- Tool calls: `set_topic` stores the furthest topic reached (a resume continues after it),
  `show_resume_quote` is acknowledged (the browser shows the quote from its own copy of the
  event), and `end_interview` completes the interview and hangs up once the goodbye has played.
  The server answers every tool call; the browser never does.
- The browser can send session events on its data channel. An instructions or tools change,
  and any system or typed message the server didn't add, is reverted; after three the attempt
  ends as `error`.
- At 25 minutes of talk (all attempts together) a wrap-up message, 20 seconds before the cap a
  goodbye, and at the cap the call is hung up (`time_cap`).
- A closed socket that can't be re-attached means the call is over: the attempt ends as
  `disconnect` (or `error` if the browser never reported a connection).

One `ai_calls` row per run records the tokens the call used, its audio seconds and its cost.
Nothing here logs what was said.
"""

import asyncio
import json
import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import interviewer
from app.ai.realtime import RealtimeProvider, RealtimeUnavailableError, Sideband
from app.models import AICall, Interview, InterviewAttempt
from app.repositories import ai_calls
from app.repositories.interviews import InterviewAttemptRepository
from app.services import interview_sessions as sessions

logger = logging.getLogger("app.interview")

PURPOSE = "interview_realtime"
# Items the server adds carry this id prefix, so the browser's own can be told apart.
SERVER_ITEM = "fhsys_"


@dataclass(frozen=True)
class Timing:
    goodbye_lead: float = 20  # seconds before the cap the goodbye is asked for
    goodbye_grace: float = 10  # longest wait for the goodbye to play after end_interview
    max_tampers: int = 3
    reattach_tries: int = 1
    check_every: float = 15  # seconds between looks for an end made elsewhere
    # The opening waits for the browser to report its connection, polled this often, for at
    # most `opening_wait` seconds.
    opening_poll: float = 0.5
    opening_wait: float = 15


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    audio_input_tokens: int = 0
    audio_output_tokens: int = 0

    def add(self, usage: dict[str, Any]) -> None:
        self.input_tokens += int(usage.get("input_tokens") or 0)
        self.output_tokens += int(usage.get("output_tokens") or 0)
        self.audio_input_tokens += int(
            (usage.get("input_token_details") or {}).get("audio_tokens") or 0
        )
        self.audio_output_tokens += int(
            (usage.get("output_token_details") or {}).get("audio_tokens") or 0
        )

    def cost(self, price: dict[str, float] | None) -> Decimal | None:
        """USD from per-million-token prices: `input`/`output` for text, `audio_input`/
        `audio_output` for audio (text prices when those are missing)."""
        if price is None:
            return None
        text_in = self.input_tokens - self.audio_input_tokens
        text_out = self.output_tokens - self.audio_output_tokens
        usd = (
            text_in * price["input"]
            + text_out * price["output"]
            + self.audio_input_tokens * price.get("audio_input", price["input"])
            + self.audio_output_tokens * price.get("audio_output", price["output"])
        ) / 1_000_000
        return Decimal(str(round(usd, 6)))


@dataclass
class _State:
    instructions: interviewer.Instructions
    topic_count: int
    deadline: datetime
    wrap_up_at: datetime
    wrap_up_sent: bool
    goodbye_sent: bool = False
    ending_reason: str | None = None
    ending_at: datetime | None = None
    # When to look in the database for an end made elsewhere (the candidate, a heartbeat, a
    # newer attempt or the watchdog).
    check_at: datetime | None = None
    # The opening cue, until it is sent: when to look again for the connection, and the
    # latest it goes out anyway.
    opening_at: datetime | None = None
    opening_by: datetime | None = None
    tampers: int = 0
    continue_after_response: bool = False
    usage: Usage = field(default_factory=Usage)


def _now() -> datetime:
    return datetime.now(UTC)


class SessionController:
    def __init__(
        self,
        session: AsyncSession,
        realtime: RealtimeProvider,
        workspace_id: Any,
        attempt_id: Any,
        *,
        prices: dict[str, dict[str, float]] | None = None,
        timing: Timing | None = None,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self.session = session
        self.realtime = realtime
        self.attempts = InterviewAttemptRepository(session, workspace_id)
        self.attempt_id = attempt_id
        self.prices = prices or {}
        self.timing = timing or Timing()
        self.clock = clock

    async def run(self, *, opening: bool = True) -> str | None:
        """Runs the attempt until its call ends. Returns how it ended, or None when it was
        already over. Pass `opening=False` when re-attaching after a failed run, so the
        interviewer doesn't greet the candidate again."""
        attempt = await self._attempt()
        if attempt is None or attempt.ended_at is not None or not attempt.realtime_session_id:
            await self.session.rollback()
            return None
        interview = await self._interview(attempt)
        prepared = await sessions.prepare(
            self.session,
            interview,
            seconds_left=attempt.seconds_allowed,
            resume_from=attempt.resume_from,
        )
        call_id = attempt.realtime_session_id
        state = _State(
            instructions=prepared.instructions,
            topic_count=len(prepared.topics),
            deadline=sessions.deadline(attempt),
            wrap_up_at=attempt.started_at + timedelta(seconds=sessions.wrap_up_after(attempt)),
            wrap_up_sent=attempt.wrap_up_sent_at is not None,
        )
        await self.session.commit()

        started = time.monotonic()
        sideband = await self.realtime.attach(call_id)
        reason: str | None = None
        try:
            await self._apply(sideband, state)
            if opening:
                now = self.clock()
                state.opening_at = now
                state.opening_by = now + timedelta(seconds=self.timing.opening_wait)
            reason = await self._loop(sideband, state, call_id)
        finally:
            await sideband.close()
            await self._log_usage(state, started, ok=reason != "error")
        return reason

    # --- The loop -----------------------------------------------------------------------------

    async def _loop(self, sideband: Sideband, state: _State, call_id: str) -> str:
        reattaches = 0
        while True:
            now = self.clock()
            reason = await self._timers(sideband, state, now)
            if reason is not None:
                return await self._finish(state, call_id, reason)
            wait = (self._next_timer(state) - now).total_seconds()
            try:
                event = await asyncio.wait_for(sideband.recv(), timeout=max(wait, 0.01))
            except TimeoutError:
                continue
            if event is None:
                # The socket closed: re-attach once in case only our connection dropped.
                if await self._ended_elsewhere():
                    return await self._finish(state, call_id, "ended")
                if reattaches < self.timing.reattach_tries:
                    reattaches += 1
                    try:
                        await sideband.close()
                        sideband = await self.realtime.attach(call_id)
                        await self._apply(sideband, state)
                        continue
                    except RealtimeUnavailableError:
                        pass
                return await self._finish(state, call_id, state.ending_reason or "disconnect")
            reason = await self._handle(sideband, state, event)
            if reason is not None:
                return await self._finish(state, call_id, reason)

    def _next_timer(self, state: _State) -> datetime:
        times = [state.deadline]
        if state.check_at is not None:
            times.append(state.check_at)
        if state.opening_at is not None:
            times.append(state.opening_at)
        if not state.wrap_up_sent:
            times.append(state.wrap_up_at)
        if not state.goodbye_sent:
            times.append(state.deadline - timedelta(seconds=self.timing.goodbye_lead))
        if state.ending_at is not None:
            times.append(state.ending_at)
        return min(times)

    async def _timers(self, sideband: Sideband, state: _State, now: datetime) -> str | None:
        if state.ending_at is not None and now >= state.ending_at:
            return state.ending_reason
        if now >= state.deadline:
            return "time_cap"
        if state.opening_at is not None and now >= state.opening_at:
            await self._open_when_connected(sideband, state, now)
        if state.check_at is None or now >= state.check_at:
            state.check_at = now + timedelta(seconds=self.timing.check_every)
            if await self._ended_elsewhere():
                return "ended"
        if not state.wrap_up_sent and now >= state.wrap_up_at:
            state.wrap_up_sent = True
            minutes = max(1, math.ceil((state.deadline - now).total_seconds() / 60))
            await self._system_message(sideband, "wrap", interviewer.wrap_up_message(minutes))
            await self._mark_wrap_up(now)
        goodbye_at = state.deadline - timedelta(seconds=self.timing.goodbye_lead)
        if not state.goodbye_sent and now >= goodbye_at and state.ending_reason is None:
            state.goodbye_sent = True
            await self._system_message(sideband, "bye", interviewer.GOODBYE_MESSAGE)
            await sideband.send({"type": "response.create"})
        return None

    async def _open_when_connected(self, sideband: Sideband, state: _State, now: datetime) -> None:
        attempt = await self._attempt()
        connected = attempt is not None and attempt.connected_at is not None
        await self.session.rollback()
        if connected or (state.opening_by is not None and now >= state.opening_by):
            state.opening_at = None
            await self._system_message(sideband, "open", state.instructions.opening)
            await sideband.send({"type": "response.create"})
        else:
            state.opening_at = now + timedelta(seconds=self.timing.opening_poll)

    async def _handle(self, sideband: Sideband, state: _State, event: dict[str, Any]) -> str | None:
        kind = event.get("type")
        if kind == "response.function_call_arguments.done":
            return await self._tool_call(sideband, state, event)
        if kind == "response.done":
            response = event.get("response") or {}
            state.usage.add(response.get("usage") or {})
            if state.continue_after_response:
                state.continue_after_response = False
                spoke = any(item.get("type") == "message" for item in response.get("output") or [])
                if not spoke and state.ending_reason is None:
                    await sideband.send({"type": "response.create"})
        elif kind == "output_audio_buffer.stopped" and state.ending_reason is not None:
            return state.ending_reason
        elif kind == "session.updated":
            changed = (event.get("session") or {}).get("instructions") != state.instructions.text
            tools = {tool.get("name") for tool in (event.get("session") or {}).get("tools") or []}
            if changed or tools != interviewer.TOOL_NAMES:
                return await self._tampered(sideband, state, revert=self._apply)
        elif kind in ("conversation.item.added", "conversation.item.created"):
            item = event.get("item") or {}
            if _foreign(item):
                item_id = item.get("id")

                async def delete(sideband: Sideband, state: _State) -> None:
                    await sideband.send({"type": "conversation.item.delete", "item_id": item_id})

                return await self._tampered(sideband, state, revert=delete)
        elif kind == "error":
            error = event.get("error") or {}
            logger.warning("realtime error event (%s)", error.get("code") or error.get("type"))
        return None

    async def _tool_call(
        self, sideband: Sideband, state: _State, event: dict[str, Any]
    ) -> str | None:
        name = event.get("name")
        try:
            arguments = json.loads(event.get("arguments") or "{}")
        except ValueError:
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        output: dict[str, Any] = {"ok": True}
        if name == "set_topic":
            number = arguments.get("number")
            if isinstance(number, int) and 1 <= number <= state.topic_count:
                await self._reach_topic(number - 1)
                state.continue_after_response = True
            else:
                output = {"ok": False, "error": f"number must be 1 to {state.topic_count}"}
                state.continue_after_response = True
        elif name == "show_resume_quote":
            state.continue_after_response = True
        elif name == "end_interview":
            reason = (
                "candidate_ended" if arguments.get("reason") == "candidate_request" else "wrap_up"
            )
            if state.ending_reason is None:
                state.ending_reason = reason
                state.ending_at = self.clock() + timedelta(seconds=self.timing.goodbye_grace)
                await self._end(reason)
        else:
            output = {"ok": False, "error": "unknown tool"}
        await sideband.send(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": event.get("call_id"),
                    "output": json.dumps(output),
                },
            }
        )
        return None

    async def _tampered(
        self,
        sideband: Sideband,
        state: _State,
        *,
        revert: Callable[[Sideband, _State], Any],
    ) -> str | None:
        state.tampers += 1
        logger.warning("realtime session changed by the browser (%d)", state.tampers)
        if state.tampers >= self.timing.max_tampers:
            return "error"
        await revert(sideband, state)
        return None

    # --- Talking to the call ------------------------------------------------------------------

    async def _apply(self, sideband: Sideband, state: _State) -> None:
        await sideband.send(
            {
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "instructions": state.instructions.text,
                    "tools": interviewer.TOOLS,
                    "tool_choice": "auto",
                },
            }
        )

    async def _system_message(self, sideband: Sideband, label: str, text: str) -> None:
        item_id = f"{SERVER_ITEM}{label}_{int(time.time() * 1000) % 10**9}"
        await sideband.send(
            {
                "type": "conversation.item.create",
                "item": {
                    "id": item_id,
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": text}],
                },
            }
        )

    # --- The database -------------------------------------------------------------------------

    async def _attempt(self, *, lock: bool = False) -> InterviewAttempt | None:
        return await self.attempts.get(self.attempt_id, lock=lock)

    async def _interview(self, attempt: InterviewAttempt) -> Interview:
        return await self.attempts.lock_interview(attempt.interview_id)

    async def _ended_elsewhere(self) -> bool:
        attempt = await self._attempt()
        ended = attempt is None or attempt.ended_at is not None
        await self.session.rollback()
        return ended

    async def _reach_topic(self, index: int) -> None:
        attempt = await self._attempt(lock=True)
        if attempt is not None and (attempt.topic_index is None or index > attempt.topic_index):
            attempt.topic_index = index
        await self.session.commit()

    async def _mark_wrap_up(self, now: datetime) -> None:
        attempt = await self._attempt(lock=True)
        if attempt is not None and attempt.wrap_up_sent_at is None:
            attempt.wrap_up_sent_at = now
        await self.session.commit()

    async def _end(self, reason: str) -> bool:
        """Ends the attempt in the database (the call is hung up by the caller)."""
        attempt = await self._attempt()
        if attempt is None or attempt.ended_at is not None:
            await self.session.rollback()
            return False
        interview = await self._interview(attempt)
        attempt = await self._attempt(lock=True)
        if attempt is None or attempt.ended_at is not None:
            await self.session.rollback()
            return False
        if reason == "disconnect" and attempt.connected_at is None:
            reason = "error"
        await sessions.end_attempt(self.session, interview, attempt, reason, self.clock())
        await self.session.commit()
        return True

    async def _finish(self, state: _State, call_id: str, reason: str) -> str:
        if reason != "ended":
            await self._end(reason)
        # Also when it ended elsewhere: hanging up twice is harmless, and covers a hang-up
        # that failed there.
        try:
            await self.realtime.hangup(call_id)
        except RealtimeUnavailableError:
            logger.warning("could not hang up a realtime call")
        attempt = await self._attempt()
        ended_as = attempt.end_reason if attempt else None
        await self.session.rollback()
        return ended_as or reason

    async def _log_usage(self, state: _State, started: float, *, ok: bool) -> None:
        current = await self._attempt()
        talk = current.talk_seconds if current is not None else 0
        await self.session.rollback()
        model = self.realtime.model
        call = AICall(
            workspace_id=self.attempts.workspace_id,
            purpose=PURPOSE,
            entity_id=self.attempt_id,
            model=model,
            prompt_version=state.instructions.version,
            input_tokens=state.usage.input_tokens,
            output_tokens=state.usage.output_tokens,
            audio_seconds=Decimal(talk),
            cost_usd=state.usage.cost(self.prices.get(model)),
            latency_ms=round((time.monotonic() - started) * 1000),
            status="ok" if ok else "error",
        )
        await ai_calls.add(self.session, call)


def _foreign(item: dict[str, Any]) -> bool:
    """A conversation item the browser added on its data channel: a system message the server
    didn't send, or a typed user message (the candidate only speaks)."""
    if str(item.get("id") or "").startswith(SERVER_ITEM):
        return False
    role = item.get("role")
    if item.get("type") != "message":
        return False
    if role == "system":
        return True
    if role == "user":
        return any(part.get("type") == "input_text" for part in item.get("content") or [])
    return False
