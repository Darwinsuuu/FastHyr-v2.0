"""Candidate consent (FR-COMP-01, PRIVACY.md §3). Records keep the notice version the candidate
agreed to and when: APPLY-003 stores the result on `applications.consent_version / consent_at`,
INTV-003 on `interviews` (and `biometric_consent_version` for the face check)."""

from dataclasses import dataclass
from datetime import datetime

from app.compliance.notices import Notice, NoticeKind, NoticeSet, released
from app.core.errors import NoticeOutdatedError, NoticeUnknownError


@dataclass(frozen=True)
class Consent:
    notice_id: str  # e.g. "apply@v1", stored as the record's consent version
    at: datetime


def accept(
    kind: NoticeKind, notice_id: str, *, now: datetime, notices: NoticeSet | None = None
) -> Consent:
    """Checks the candidate agreed to the current `kind` notice and returns what to store.
    An unknown id or one of another kind is `422 notice_unknown`; an older version is
    `409 notice_outdated`, so the page shows the current words before the record is made."""
    notices = notices or released()
    notice = notices.by_id(notice_id)
    if notice is None or notice.kind != kind:
        raise NoticeUnknownError()
    if notice.version != notices.current(kind).version:
        raise NoticeOutdatedError()
    return Consent(notice_id=notice.id, at=now)


def current(kind: NoticeKind) -> Notice:
    return released().current(kind)
