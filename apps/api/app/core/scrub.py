"""Scrub rules shared by logs and Sentry (SECURITY.md §3, NFR-03): IDs only, never personal data.

Values under personal or secret keys are replaced wholesale; email addresses and bearer tokens
inside any other string are masked. Structures are copied, never changed in place.
"""

import re
from collections.abc import Mapping
from typing import Any

FILTERED = "[Filtered]"
EMAIL_MASK = "[email]"

# Keys whose values are personal data or secrets, compared lower-case with `-` read as `_`. A key
# matches if it equals one of these or ends with `_<key>` (so `candidate_email`, `x_api_key`).
SENSITIVE_KEYS = frozenset(
    {
        "email",
        "emails",
        "name",
        "names",
        "full_name",
        "first_name",
        "last_name",
        "display_name",
        "phone",
        "address",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "token_hash",
        "code",
        "authorization",
        "cookie",
        "cookies",
        "set_cookie",
        "api_key",
        "apikey",
        "dsn",
        "resume",
        "resume_text",
        "transcript",
        "query_string",
    }
)
# Keys that look sensitive by suffix but only ever hold IDs, codes or names of code.
SAFE_KEYS = frozenset(
    {
        "error_code",
        "status_code",
        "logger_name",
        "event_name",
        "job_name",
        "function_name",
        "module_name",
        "file_name",
        "filename",
        "server_name",
        "transaction_name",
    }
)

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
# Supabase/JWT-shaped tokens: three base64url parts, the first starting `eyJ`.
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")

_MAX_DEPTH = 12


def is_sensitive_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    normal = key.lower().replace("-", "_")
    if normal in SAFE_KEYS:
        return False
    return normal in SENSITIVE_KEYS or any(normal.endswith(f"_{k}") for k in SENSITIVE_KEYS)


def scrub_text(text: str) -> str:
    text = BEARER.sub("Bearer " + FILTERED, text)
    text = JWT.sub(FILTERED, text)
    return EMAIL.sub(EMAIL_MASK, text)


def scrub(value: Any, _depth: int = 0) -> Any:
    """A copy of `value` with sensitive keys filtered and emails and tokens masked in strings."""
    if _depth > _MAX_DEPTH:
        return FILTERED
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, Mapping):
        return {
            key: FILTERED if is_sensitive_key(key) and item is not None else scrub(item, _depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        items = [scrub(item, _depth + 1) for item in value]
        return items if isinstance(value, list) else tuple(items)
    return value
