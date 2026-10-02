"""COMP-002: the notice routes. No sign-in and no workspace data; every released version stays
readable so a record's consent can be shown word for word."""

from fastapi.testclient import TestClient

from app.compliance.notices import released
from app.main import create_app

client = TestClient(create_app())
NOTICE_KEYS = {"id", "kind", "version", "statement", "details", "links", "choices"}


def test_current_notices_need_no_sign_in() -> None:
    response = client.get("/v1/public/notices")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"apply", "interview", "biometric"}
    for kind, notice in body.items():
        assert set(notice) == NOTICE_KEYS
        assert notice["id"] == released().current(kind).id
        assert notice["id"] == f"{kind}@v{notice['version']}"


def test_one_current_notice() -> None:
    response = client.get("/v1/public/notices/apply")
    assert response.status_code == 200
    assert response.json()["id"] == released().current("apply").id
    assert set(response.json()["choices"]["interview"]) == {"video_voice", "voice_only"}


def test_a_released_version_by_number() -> None:
    response = client.get("/v1/public/notices/interview/1")
    assert response.status_code == 200
    assert response.json()["id"] == "interview@v1"


def test_unknown_versions_and_kinds() -> None:
    missing = client.get("/v1/public/notices/apply/999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    assert client.get("/v1/public/notices/marketing").status_code == 422
    assert client.get("/v1/public/notices/apply/0").status_code == 422
