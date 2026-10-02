"""Candidate notices and consent texts (FR-COMP-01, API.md "Public"): no sign-in, no workspace
data. Every released version stays readable so a record's consent can be shown word for word."""

from typing import Annotated

from fastapi import APIRouter, Path

from app.compliance.notices import NoticeKind, released
from app.core.errors import PROBLEM_RESPONSES, NotFoundError
from app.schemas.notices import CurrentNotices, Notice

router = APIRouter(prefix="/public/notices", tags=["public"], responses=PROBLEM_RESPONSES)


@router.get("", response_model=CurrentNotices)
async def get_current_notices() -> CurrentNotices:
    """The current version of every notice."""
    notices = released()
    return CurrentNotices(
        apply=Notice.of(notices.current("apply")),
        interview=Notice.of(notices.current("interview")),
        biometric=Notice.of(notices.current("biometric")),
    )


@router.get("/{kind}", response_model=Notice)
async def get_current_notice(kind: NoticeKind) -> Notice:
    """The current version of one notice."""
    return Notice.of(released().current(kind))


@router.get("/{kind}/{version}", response_model=Notice)
async def get_notice_version(
    kind: NoticeKind, version: Annotated[int, Path(ge=1, le=10_000)]
) -> Notice:
    """One released version, current or not. Unknown is 404."""
    notice = released().get(kind, version)
    if notice is None:
        raise NotFoundError()
    return Notice.of(notice)
