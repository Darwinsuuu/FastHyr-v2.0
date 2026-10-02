"""Versioned candidate notices and consent texts (FR-COMP-01, PRIVACY.md §3).

Each text is a file `<kind>@v<N>.toml` in this folder:

    statement = "I agree that {company} can review my application ..."   # the checkbox label
    details = ["...", "..."]                                            # "What this means"
    links = ["privacy", "ai_in_hiring"]
    [choices.interview]                                                 # wording per pipeline
    video_voice = "an AI interview by video and voice"
    voice_only = "an AI interview by voice"

Placeholders are `{company}` and the `choices` keys; the page fills them in. A released file is
never edited: `versions.lock` holds the SHA-256 of every released file and loading refuses one that
changed or has no lock line. To change a text, copy it to the next version, edit the copy and run
`python -m app.compliance.notices lock`, which adds lines for new files and never rewrites one.
Records (applications, interviews) store the `<kind>@v<N>` id the candidate agreed to; every
released version stays loadable so the exact words can be shown later.
"""

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Literal, get_args

NOTICES_DIR = Path(__file__).parent
LOCK_FILE = "versions.lock"

NoticeKind = Literal["apply", "interview", "biometric"]
NoticeLink = Literal["privacy", "ai_in_hiring", "terms"]
KINDS: tuple[NoticeKind, ...] = get_args(NoticeKind)
LINKS: tuple[NoticeLink, ...] = get_args(NoticeLink)

FILE_NAME = re.compile(r"^(?P<kind>[a-z_]+)@v(?P<version>[1-9][0-9]*)\.toml$")
PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
FIXED_PLACEHOLDERS = {"company"}


class NoticeError(Exception):
    """A notice file is malformed, changed after release, or missing from the lock."""


@dataclass(frozen=True)
class Notice:
    kind: NoticeKind
    version: int
    statement: str
    details: tuple[str, ...]
    links: tuple[NoticeLink, ...]
    choices: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """What a record stores, e.g. `apply@v1`."""
        return f"{self.kind}@v{self.version}"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_lock(directory: Path) -> dict[str, str]:
    path = directory / LOCK_FILE
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in data.items()
    ):
        raise NoticeError(f"{LOCK_FILE} must map notice ids to SHA-256 hashes")
    return data


def _notice_files(directory: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(directory.glob("*.toml")):
        match = FILE_NAME.match(path.name)
        if not match:
            raise NoticeError(f"{path.name}: notice files are named <kind>@v<N>.toml")
        if match["kind"] not in KINDS:
            raise NoticeError(f"{path.name}: unknown kind; add it to NoticeKind first")
        files[path.name.removesuffix(".toml")] = path
    return files


def _strings(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise NoticeError(f"{where} must be a list of non-empty strings")
    return tuple(value)


def _parse(notice_id: str, path: Path) -> Notice:
    kind, version = notice_id.split("@v")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise NoticeError(f"{path.name}: {error}") from error
    unknown = set(data) - {"statement", "details", "links", "choices"}
    if unknown:
        raise NoticeError(f"{path.name}: unknown keys {sorted(unknown)}")
    statement = data.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        raise NoticeError(f"{path.name}: statement is required")
    details = _strings(data.get("details", []), f"{path.name}: details")
    links = _strings(data.get("links", []), f"{path.name}: links")
    bad_links = [link for link in links if link not in LINKS]
    if bad_links:
        raise NoticeError(f"{path.name}: unknown links {bad_links}")
    raw_choices = data.get("choices", {})
    choices: dict[str, dict[str, str]] = {}
    if not isinstance(raw_choices, dict):
        raise NoticeError(f"{path.name}: choices must be tables of wording")
    for name, options in raw_choices.items():
        if (
            not isinstance(options, dict)
            or not options
            or not all(isinstance(text, str) and text for text in options.values())
        ):
            raise NoticeError(f"{path.name}: choices.{name} must map options to wording")
        choices[name] = dict(options)
    allowed = FIXED_PLACEHOLDERS | set(choices)
    for text in (statement, *details, *(t for o in choices.values() for t in o.values())):
        for name in PLACEHOLDER.findall(text):
            if name not in allowed:
                raise NoticeError(f"{path.name}: unknown placeholder {{{name}}}")
    return Notice(
        kind=kind,  # type: ignore[arg-type]  # checked against KINDS in _notice_files
        version=int(version),
        statement=statement.strip(),
        details=details,
        links=links,  # type: ignore[arg-type]  # checked against LINKS above
        choices=choices,
    )


@dataclass(frozen=True)
class NoticeSet:
    """Every released notice, by id."""

    notices: dict[str, Notice]

    def get(self, kind: str, version: int) -> Notice | None:
        return self.notices.get(f"{kind}@v{version}")

    def by_id(self, notice_id: str) -> Notice | None:
        return self.notices.get(notice_id)

    def current(self, kind: NoticeKind) -> Notice:
        versions = [n for n in self.notices.values() if n.kind == kind]
        if not versions:
            raise NoticeError(f"no released {kind} notice")
        return max(versions, key=lambda notice: notice.version)


def load_notices(directory: Path = NOTICES_DIR) -> NoticeSet:
    """Loads and checks every notice file against the lock."""
    lock = _read_lock(directory)
    files = _notice_files(directory)
    notices: dict[str, Notice] = {}
    for notice_id, path in files.items():
        expected = lock.get(notice_id)
        if expected is None:
            raise NoticeError(
                f"{path.name} isn't released; run `python -m app.compliance.notices lock`"
            )
        if file_hash(path) != expected:
            kind, version = notice_id.split("@v")
            raise NoticeError(
                f"{path.name} changed after release. Undo the edit and copy it to "
                f"{kind}@v{int(version) + 1}.toml instead"
            )
        notices[notice_id] = _parse(notice_id, path)
    orphans = sorted(set(lock) - set(files))
    if orphans:
        raise NoticeError(f"released notices are missing their files: {orphans}")
    for kind in KINDS:
        NoticeSet(notices).current(kind)
    return NoticeSet(notices)


@cache
def released() -> NoticeSet:
    """The notices in this folder, loaded once per process."""
    return load_notices()


def lock_new_files(directory: Path = NOTICES_DIR) -> list[str]:
    """Adds lock lines for notice files that have none. Existing lines are never rewritten."""
    lock = _read_lock(directory)
    files = _notice_files(directory)
    added = [notice_id for notice_id in files if notice_id not in lock]
    for notice_id in added:
        _parse(notice_id, files[notice_id])
        lock[notice_id] = file_hash(files[notice_id])
    if added:
        text = json.dumps(dict(sorted(lock.items())), indent=2) + "\n"
        (directory / LOCK_FILE).write_text(text, encoding="utf-8")
    return added
