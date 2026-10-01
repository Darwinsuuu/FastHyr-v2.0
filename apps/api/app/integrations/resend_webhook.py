"""Resend webhook signatures. Resend signs with Svix: HMAC-SHA256 over
`{svix-id}.{svix-timestamp}.{body}` with the base64 secret after `whsec_`, sent as one or more
`v1,<base64>` values in `svix-signature`. Old timestamps are refused to stop replays."""

import base64
import hashlib
import hmac
import time

TOLERANCE_SECONDS = 5 * 60


def verify(
    secret: str,
    *,
    message_id: str | None,
    timestamp: str | None,
    signatures: str | None,
    body: bytes,
    now: float | None = None,
) -> bool:
    if not (secret and message_id and timestamp and signatures):
        return False
    try:
        sent_at = int(timestamp)
        key = base64.b64decode(secret.removeprefix("whsec_"))
    except ValueError:
        return False
    if abs((now if now is not None else time.time()) - sent_at) > TOLERANCE_SECONDS:
        return False
    signed = f"{message_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    for candidate in signatures.split():
        version, _, value = candidate.partition(",")
        if version == "v1" and hmac.compare_digest(value, expected):
            return True
    return False


def sign(secret: str, *, message_id: str, timestamp: str, body: bytes) -> str:
    """The `svix-signature` value for `body`, for tests and local hand testing."""
    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"{message_id}.{timestamp}.".encode() + body
    return "v1," + base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
