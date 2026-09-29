"""Access-token verification: only valid, unexpired Supabase tokens for our project pass."""

import asyncio
import time
import uuid
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.api.deps import get_verified_user
from app.core.auth import TokenVerifier, bearer_token
from app.core.errors import EmailNotVerifiedError, UnauthenticatedError

ISSUER = "http://127.0.0.1:54321/auth/v1"
AUDIENCE = "authenticated"
KID = "test-key"


class StaticKeys:
    """Stands in for the JWKS endpoint: one known key ID."""

    def __init__(self, public_key: Any) -> None:
        self.jwk = jwt.PyJWK.from_dict(
            {**jwt.algorithms.ECAlgorithm.to_jwk(public_key, as_dict=True), "kid": KID},
            algorithm="ES256",
        )

    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK:
        if jwt.get_unverified_header(token).get("kid") != KID:
            raise jwt.PyJWKClientError("Unable to find a signing key that matches")
        return self.jwk


PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
VERIFIER = TokenVerifier(StaticKeys(PRIVATE_KEY.public_key()), issuer=ISSUER, audience=AUDIENCE)
USER_ID = uuid.uuid4()


def make_token(key: Any = PRIVATE_KEY, kid: str = KID, **overrides: Any) -> str:
    claims = {
        "sub": str(USER_ID),
        "aud": AUDIENCE,
        "iss": ISSUER,
        "exp": int(time.time()) + 3600,
        "email": "ada@example.com",
        "user_metadata": {"email_verified": True},
        **overrides,
    }
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": kid})


def test_valid_token_gives_the_user() -> None:
    user = VERIFIER.verify_sync(make_token())

    assert user.user_id == USER_ID
    assert user.email == "ada@example.com"
    assert user.email_verified is True


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(make_token(exp=int(time.time()) - 10), id="expired"),
        pytest.param(make_token(aud="anon"), id="wrong audience"),
        pytest.param(make_token(iss="https://other.supabase.co/auth/v1"), id="wrong issuer"),
        pytest.param(make_token(key=ec.generate_private_key(ec.SECP256R1())), id="bad signature"),
        pytest.param(make_token(kid="unknown"), id="unknown key"),
        pytest.param(make_token(sub="not-a-uuid"), id="bad subject"),
        pytest.param(jwt.encode({"sub": str(USER_ID)}, "x" * 32, algorithm="HS256"), id="hs256"),
        pytest.param("not-a-jwt", id="garbage"),
    ],
)
def test_bad_tokens_are_unauthenticated(token: str) -> None:
    with pytest.raises(UnauthenticatedError):
        VERIFIER.verify_sync(token)


def test_token_without_expiry_is_rejected() -> None:
    claims = {"sub": str(USER_ID), "aud": AUDIENCE, "iss": ISSUER}
    token = jwt.encode(claims, PRIVATE_KEY, algorithm="ES256", headers={"kid": KID})

    with pytest.raises(UnauthenticatedError):
        VERIFIER.verify_sync(token)


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer ", "Bearer"])
def test_missing_bearer_is_unauthenticated(header: str | None) -> None:
    with pytest.raises(UnauthenticatedError):
        bearer_token(header)


def test_unverified_email_cannot_pass_the_verified_user_check() -> None:
    """FR-AUTH-03: workspace create and join depend on `get_verified_user`."""
    unverified = VERIFIER.verify_sync(make_token(user_metadata={"email_verified": False}))
    missing = VERIFIER.verify_sync(make_token(user_metadata={}))
    verified = VERIFIER.verify_sync(make_token())

    for user in (unverified, missing):
        with pytest.raises(EmailNotVerifiedError):
            asyncio.run(get_verified_user(user))
    assert asyncio.run(get_verified_user(verified)) is verified
