"""Sentry for the API and the worker (FND-009, DEPLOYMENT.md §5, SECURITY.md §3).

`init_sentry()` does nothing when SENTRY_DSN is empty, so local development and tests send
nothing. When it is set, events carry the release (git SHA), environment, component and the IDs
bound with `app.core.logging.bind_ids()`, and never personal data: no request bodies, cookies,
query strings or local variables, the user is an ID only, and `before_send` /
`before_breadcrumb` apply the scrub rules in `app.core.scrub` to whatever text is left.

Send a test event to check a deployment's DSN (from a Render shell, or `make sentry-test`):

    python -m app.core.observability --component api      # or worker
"""

import argparse
import logging
from typing import Any, Literal, cast
from urllib.parse import urlsplit, urlunsplit

import sentry_sdk
from sentry_sdk.integrations.arq import ArqIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.types import Event, Hint

from app.core.config import Settings, get_settings
from app.core.scrub import scrub, scrub_text

Component = Literal["api", "worker"]

# Request headers worth keeping on an event; everything else (Authorization, Cookie, …) is dropped.
_SAFE_HEADERS = frozenset(
    {"content-type", "content-length", "user-agent", "x-request-id", "x-workspace-id", "origin"}
)
# Contexts the SDK fills with facts about the machine and trace, not about people.
_SDK_CONTEXTS = frozenset({"trace", "runtime", "os", "device", "app", "cloud_resource", "response"})


def strip_query(url: str) -> str:
    """The URL without its query string or fragment, which may hold tokens or emails."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def scrub_event(sentry_event: Event, _hint: Hint | None = None) -> Event:
    """`before_send`: removes anything that could be personal data from an event."""
    # Event is a TypedDict whose fields may hold SDK wrappers; work on it as a plain dict.
    event = cast(dict[str, Any], sentry_event)
    request = event.get("request")
    if request:
        headers = request.get("headers") or {}
        event["request"] = {
            "method": request.get("method"),
            "url": scrub_text(strip_query(request.get("url") or "")),
            "headers": {k: v for k, v in headers.items() if k.lower() in _SAFE_HEADERS},
        }
    user = event.get("user")
    if user:
        event["user"] = {"id": user["id"]} if user.get("id") else {}
    for key in ("extra", "tags"):
        if key in event:
            event[key] = scrub(event[key])
    contexts = event.get("contexts")
    if contexts:
        event["contexts"] = {
            name: value if name in _SDK_CONTEXTS else scrub(value)
            for name, value in contexts.items()
        }
    if isinstance(event.get("message"), str):
        event["message"] = scrub_text(event["message"])
    logentry = event.get("logentry")
    if logentry:
        event["logentry"] = scrub(logentry)
    for exception in (event.get("exception") or {}).get("values", []):
        if isinstance(exception.get("value"), str):
            exception["value"] = scrub_text(exception["value"])
        for frame in (exception.get("stacktrace") or {}).get("frames", []):
            frame.pop("vars", None)
            for key in ("pre_context", "context_line", "post_context"):
                if key in frame:
                    frame[key] = scrub(frame[key])
    breadcrumbs = event.get("breadcrumbs")
    if breadcrumbs:
        values = breadcrumbs.get("values", []) if isinstance(breadcrumbs, dict) else breadcrumbs
        cleaned = [crumb for crumb in (scrub_breadcrumb(c) for c in values) if crumb]
        if isinstance(breadcrumbs, dict):
            breadcrumbs["values"] = cleaned
        else:
            event["breadcrumbs"] = cleaned
    event.pop("server_name", None)
    return sentry_event


def scrub_breadcrumb(crumb: dict[str, Any], _hint: Hint | None = None) -> dict[str, Any] | None:
    """`before_breadcrumb`: masks emails and tokens in messages and drops URL query strings."""
    crumb = dict(crumb)
    if isinstance(crumb.get("message"), str):
        crumb["message"] = scrub_text(crumb["message"])
    data = crumb.get("data")
    if isinstance(data, dict):
        data = scrub(data)
        for key in ("url", "http.url"):
            if isinstance(data.get(key), str):
                data[key] = strip_query(data[key])
        data.pop("http.query", None)
        data.pop("http.fragment", None)
        crumb["data"] = data
    return crumb


def init_sentry(settings: Settings, component: Component, transport: Any = None) -> bool:
    """Starts the Sentry SDK if SENTRY_DSN is set. Returns whether it did. Tests pass a
    `transport` that keeps events in memory."""
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.app_env,
        release=settings.release,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        server_name="",
        before_send=scrub_event,
        before_send_transaction=scrub_event,
        before_breadcrumb=scrub_breadcrumb,
        integrations=[
            # Log lines become breadcrumbs only; errors are captured on purpose (the 500 handler
            # and the job wrapper), so a warning that is handled never pages anyone.
            LoggingIntegration(level=logging.INFO, event_level=None),
        ],
        # The job wrapper captures final failures itself, with job tags and without arguments.
        disabled_integrations=[ArqIntegration],
        transport=transport,
    )
    sentry_sdk.set_tag("component", component)
    return True


def capture_test_event(settings: Settings, component: Component) -> str | None:
    """Sends one test error and waits for it to leave. Returns the event ID, or None when
    SENTRY_DSN is empty."""
    if not init_sentry(settings, component):
        return None
    try:
        raise RuntimeError(f"FastHyr Sentry test event ({component})")
    except RuntimeError as error:
        event_id = sentry_sdk.capture_exception(error)
    sentry_sdk.flush(timeout=10)
    return event_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test event to this service's Sentry.")
    parser.add_argument("--component", choices=["api", "worker"], default="api")
    args = parser.parse_args()
    event_id = capture_test_event(get_settings(), args.component)
    if event_id is None:
        print("SENTRY_DSN is empty; nothing was sent.")
    else:
        print(f"Sent test event {event_id}. Look for it in the {args.component} project.")


if __name__ == "__main__":
    main()
