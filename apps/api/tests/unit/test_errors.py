"""Every error is problem+json with a stable code and the request ID, and never echoes input."""

from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import NotFoundError
from app.main import create_app
from tests.unit.test_auth import VERIFIER


class Body(BaseModel):
    email: str
    age: int


def make_client() -> TestClient:
    app = create_app(token_verifier=VERIFIER)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret detail ada@example.com")

    @app.get("/missing")
    async def missing() -> None:
        raise NotFoundError()

    @app.post("/validate")
    async def validate(body: Body) -> None:
        return None

    return TestClient(app, raise_server_exceptions=False)


def test_app_error_is_problem_json_with_request_id() -> None:
    response = make_client().get("/missing")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "not_found"
    assert body["request_id"] == response.headers["x-request-id"]


def test_validation_error_does_not_echo_submitted_values() -> None:
    response = make_client().post("/validate", json={"email": "ada@example.com", "age": "old"})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"
    assert "ada@example.com" not in response.text
    assert "old" not in response.text


def test_unexpected_error_hides_details() -> None:
    response = make_client().get("/boom")

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert "ada@example.com" not in response.text
    assert response.headers["x-request-id"]


def test_valid_incoming_request_id_is_kept_and_bad_one_replaced() -> None:
    client = make_client()

    kept = client.get("/health", headers={"X-Request-Id": "abc12345-trace"})
    replaced = client.get("/health", headers={"X-Request-Id": "bad id\nwith newline"})

    assert kept.headers["x-request-id"] == "abc12345-trace"
    assert replaced.headers["x-request-id"] != "bad id\nwith newline"


def test_unknown_route_is_not_found_problem() -> None:
    response = make_client().get("/v1/nope")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_openapi_is_served_under_v1() -> None:
    response = make_client().get("/v1/openapi.json")

    assert response.status_code == 200
    assert "/v1/me/workspaces" in response.json()["paths"]
