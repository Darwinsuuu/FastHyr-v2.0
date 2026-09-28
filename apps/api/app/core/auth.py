"""Supabase access-token verification (SECURITY.md §1).

Tokens are checked against the project's published signing keys (JWKS): signature, `exp`, `aud`
and `iss`. Keys are cached, and fetched again when a token names a key we haven't seen (rotation).
"""

import uuid
from dataclasses import dataclass
from typing import Any, Protocol

import jwt
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.errors import UnauthenticatedError

# Supabase signs with ES256 (default) or RS256. HS256 shared secrets are never accepted.
ALGORITHMS = ["ES256", "RS256"]
JWKS_CACHE_SECONDS = 600


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    email: str | None
    email_verified: bool


class SigningKeySource(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK: ...


class TokenVerifier:
    def __init__(self, keys: SigningKeySource, *, issuer: str, audience: str) -> None:
        self._keys = keys
        self._issuer = issuer
        self._audience = audience

    @classmethod
    def from_settings(cls, settings: Settings) -> "TokenVerifier":
        keys = jwt.PyJWKClient(
            settings.jwks_url, cache_keys=True, lifespan=JWKS_CACHE_SECONDS, timeout=5
        )
        return cls(keys, issuer=settings.jwt_issuer, audience=settings.supabase_jwt_audience)

    async def verify(self, token: str) -> CurrentUser:
        # PyJWKClient fetches over blocking I/O; keep it off the event loop.
        return await run_in_threadpool(self.verify_sync, token)

    def verify_sync(self, token: str) -> CurrentUser:
        try:
            key = self._keys.get_signing_key_from_jwt(token)
            claims: dict[str, Any] = jwt.decode(
                token,
                key.key,
                algorithms=ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
            user_id = uuid.UUID(str(claims["sub"]))
        except (jwt.PyJWTError, ValueError) as error:
            raise UnauthenticatedError() from error

        metadata = claims.get("user_metadata") or {}
        email = claims.get("email") or None
        return CurrentUser(
            user_id=user_id,
            email=email,
            email_verified=bool(metadata.get("email_verified", False)),
        )


def bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthenticatedError()
    return token.strip()
