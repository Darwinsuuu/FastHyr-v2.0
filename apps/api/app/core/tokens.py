"""Link tokens (interview and review links): a random token goes in the link and the link's
table keeps only its SHA-256, so the token is checked by hash lookup."""

import hashlib
import secrets


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    """A URL-safe token and its hash."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)
