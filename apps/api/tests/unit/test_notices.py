"""COMP-002: candidate notices are versioned. A released text can't change; a change is a new
version, and records keep the version they agreed to."""

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.compliance.notices import (
    KINDS,
    NOTICES_DIR,
    NoticeError,
    load_notices,
    lock_new_files,
    released,
)
from app.core.errors import NoticeOutdatedError, NoticeUnknownError
from app.services import consents

NOW = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)

V1 = """statement = "I agree that {company} can review my application."
details = ["A person on the {company} team decides."]
links = ["privacy"]
"""
V2 = """statement = "I agree that {company} can review my application and invite me to {interview}."
details = ["A person on the {company} team decides."]
links = ["privacy", "ai_in_hiring"]

[choices.interview]
video_voice = "an AI interview by video and voice"
voice_only = "an AI interview by voice"
"""
OTHER = 'statement = "I understand this session is recorded."\n'


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    """A notices folder with released apply@v1, interview@v1 and biometric@v1."""
    (tmp_path / "apply@v1.toml").write_text(V1, encoding="utf-8")
    (tmp_path / "interview@v1.toml").write_text(OTHER, encoding="utf-8")
    (tmp_path / "biometric@v1.toml").write_text(OTHER, encoding="utf-8")
    lock_new_files(tmp_path)
    return tmp_path


def test_released_notices_match_the_lock() -> None:
    notices = load_notices()
    assert {notice.kind for notice in notices.notices.values()} == set(KINDS)
    for kind in KINDS:
        assert notices.current(kind).statement


def test_the_shipped_apply_notice_fills_every_interview_format() -> None:
    notice = released().current("apply")
    assert set(notice.choices["interview"]) == {"video_voice", "voice_only"}
    assert "{company}" in notice.statement and "{interview}" in notice.statement


def test_an_edited_released_notice_is_refused(folder: Path) -> None:
    (folder / "apply@v1.toml").write_text(V1.replace("review", "check"), encoding="utf-8")
    with pytest.raises(NoticeError, match=re.escape("copy it to apply@v2.toml")):
        load_notices(folder)


def test_a_notice_without_a_lock_line_is_refused(folder: Path) -> None:
    (folder / "apply@v2.toml").write_text(V2, encoding="utf-8")
    with pytest.raises(NoticeError, match="isn't released"):
        load_notices(folder)


def test_a_new_version_becomes_current_and_the_old_one_stays_readable(folder: Path) -> None:
    (folder / "apply@v2.toml").write_text(V2, encoding="utf-8")
    assert lock_new_files(folder) == ["apply@v2"]
    notices = load_notices(folder)
    assert notices.current("apply").id == "apply@v2"
    old = notices.by_id("apply@v1")
    assert old is not None and old.statement.startswith("I agree that {company} can review")


def test_locking_never_rewrites_a_released_line(folder: Path) -> None:
    lock_before = (folder / "versions.lock").read_text(encoding="utf-8")
    (folder / "apply@v1.toml").write_text(V2, encoding="utf-8")
    assert lock_new_files(folder) == []
    assert (folder / "versions.lock").read_text(encoding="utf-8") == lock_before
    with pytest.raises(NoticeError, match="changed after release"):
        load_notices(folder)


def test_a_released_file_cannot_be_deleted(folder: Path) -> None:
    (folder / "apply@v1.toml").unlink()
    with pytest.raises(NoticeError, match="missing their files"):
        load_notices(folder)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('statement = "Hello {name}"\n', "unknown placeholder"),
        ('statement = ""\n', "statement is required"),
        ('statement = "Hi"\nlinks = ["blog"]\n', "unknown links"),
        ('statement = "Hi"\nfooter = "x"\n', "unknown keys"),
    ],
)
def test_malformed_notices_are_refused(tmp_path: Path, text: str, message: str) -> None:
    (tmp_path / "apply@v1.toml").write_text(text, encoding="utf-8")
    with pytest.raises(NoticeError, match=message):
        lock_new_files(tmp_path)


def test_file_names_are_checked(folder: Path) -> None:
    shutil.copy(folder / "apply@v1.toml", folder / "apply-v3.toml")
    with pytest.raises(NoticeError, match=re.escape("<kind>@v<N>.toml")):
        load_notices(folder)


def test_the_shipped_folder_has_only_notice_files() -> None:
    names = {path.name for path in NOTICES_DIR.iterdir() if not path.name.startswith("__")}
    assert all(name.endswith(".toml") or name == "versions.lock" for name in names)


def test_accept_returns_the_version_and_time_to_store(folder: Path) -> None:
    consent = consents.accept("apply", "apply@v1", now=NOW, notices=load_notices(folder))
    assert consent == consents.Consent(notice_id="apply@v1", at=NOW)


def test_accept_refuses_an_older_version(folder: Path) -> None:
    (folder / "apply@v2.toml").write_text(V2, encoding="utf-8")
    lock_new_files(folder)
    notices = load_notices(folder)
    with pytest.raises(NoticeOutdatedError):
        consents.accept("apply", "apply@v1", now=NOW, notices=notices)
    assert consents.accept("apply", "apply@v2", now=NOW, notices=notices).notice_id == "apply@v2"


@pytest.mark.parametrize("notice_id", ["apply@v9", "interview@v1", "apply", ""])
def test_accept_refuses_unknown_or_other_kinds(folder: Path, notice_id: str) -> None:
    with pytest.raises(NoticeUnknownError):
        consents.accept("apply", notice_id, now=NOW, notices=load_notices(folder))
