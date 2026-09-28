"""Primary keys: UUID v7 (time-ordered) generated in the API; the database default is a fallback."""

import os
import time
import uuid


def new_id() -> uuid.UUID:
    """Return a UUID v7 (RFC 9562): 48-bit Unix milliseconds, then random bits."""
    unix_ms = time.time_ns() // 1_000_000
    value = (unix_ms & ((1 << 48) - 1)) << 80 | int.from_bytes(os.urandom(10))
    value = (value & ~(0xF << 76)) | (0x7 << 76)  # version 7
    value = (value & ~(0x3 << 62)) | (0x2 << 62)  # RFC 9562 variant
    return uuid.UUID(int=value)
