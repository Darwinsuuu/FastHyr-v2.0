"""Structured logs and request IDs (FND-009). Log IDs only, never personal data.

Every log line, from our `logging.getLogger("app...")` loggers, uvicorn and arq alike, goes
through structlog: one JSON object per line on hosted environments (`LOG_FORMAT=json`), readable
key=value lines locally. IDs bound with `bind_ids()` (request, user, workspace, job) ride along on
every line logged in the same request or job, and the scrub rules in `app.core.scrub` run last.
"""

import logging
import re
import time
import uuid
from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any, Literal

import sentry_sdk
import structlog
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.scrub import scrub

REQUEST_ID_HEADER = "X-Request-Id"
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
# Accept a caller's ID only if it looks like one, so headers can't inject into logs.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

LogFormat = Literal["json", "console"]
# Third-party loggers routed through the same pipeline.
_LOGGERS = ("app", "uvicorn", "uvicorn.error", "arq", "fastapi")
# uvicorn's access log is replaced by the "request" line below: its lines carry the client's IP
# and the full URL with its query string.
_SILENCED = ("uvicorn.access",)
_request_logger = logging.getLogger("app.request")


def current_request_id() -> str | None:
    return _request_id.get()


def request_id_of(request: Request) -> str | None:
    value = request.scope.get("state", {}).get("request_id")
    return value if isinstance(value, str) else current_request_id()


def bind_ids(**ids: object) -> None:
    """Adds IDs (`user_id`, `workspace_id`, `job`, `job_id`, …) to every later log line in this
    request or job, and as tags on any Sentry event from it. Only pass IDs and code names."""
    values = {key: str(value) for key, value in ids.items() if value is not None}
    structlog.contextvars.bind_contextvars(**values)
    for key, value in values.items():
        sentry_sdk.set_tag(key, value)


def _route_of(scope: Scope) -> str:
    """The path with its parameters put back as `{name}` (`/v1/invites/{key}`), never the raw
    path, which can hold invite codes or tokens."""
    if scope.get("route") is None:
        return "unmatched"
    segments = str(scope.get("path", "")).split("/")
    params = {str(value): name for name, value in (scope.get("path_params") or {}).items()}
    return "/".join(f"{{{params[s]}}}" if s in params else s for s in segments)


class RequestIdMiddleware:
    """Reuses a valid incoming `X-Request-Id` or creates one, returns it on the response, and
    logs one "request" line per request: method, route template, status and duration."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Request(scope).headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = _request_id.set(request_id)
        structlog.contextvars.clear_contextvars()
        bind_ids(request_id=request_id)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            _request_logger.info(
                "request",
                extra={
                    "method": scope["method"],
                    "route": _route_of(scope),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            _request_id.reset(token)
            structlog.contextvars.clear_contextvars()


def _scrub_event(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    scrubbed: MutableMapping[str, Any] = scrub(dict(event_dict))
    return scrubbed


def _drop_color_message(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    # uvicorn duplicates its message with ANSI colours under this key.
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(level: int | str = logging.INFO, fmt: LogFormat = "console") -> None:
    """Sets up structlog and routes the standard library's loggers through it. Safe to call
    more than once (the API and the worker each call it at start-up)."""
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _drop_color_message,
    ]
    renderer: Any = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            # Exceptions are logged as text; scrub after formatting so tracebacks are masked too.
            structlog.processors.format_exc_info,
            _scrub_event,
            renderer,
        ],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    for name in _LOGGERS:
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.setLevel(level)
        logger.propagate = False
    for name in _SILENCED:
        logging.getLogger(name).disabled = True


def get_logger(name: str) -> Any:
    """A structlog logger for new code: `log.info("pipeline published", pipeline_id=...)`."""
    return structlog.stdlib.get_logger(name)
