from pydantic import BaseModel

from app.compliance.notices import Notice as NoticeText
from app.compliance.notices import NoticeKind, NoticeLink


class Notice(BaseModel):
    """A versioned candidate notice (FR-COMP-01). The page fills `{company}` and each `choices`
    key (e.g. `{interview}` with `choices.interview[pipeline.interview_format]`)."""

    id: str  # "<kind>@v<N>": what the consent request sends back and the record stores
    kind: NoticeKind
    version: int
    statement: str  # the checkbox label
    details: list[str]  # "What this means"
    links: list[NoticeLink]
    choices: dict[str, dict[str, str]]

    @classmethod
    def of(cls, notice: NoticeText) -> "Notice":
        return cls(
            id=notice.id,
            kind=notice.kind,
            version=notice.version,
            statement=notice.statement,
            details=list(notice.details),
            links=list(notice.links),
            choices=notice.choices,
        )


class CurrentNotices(BaseModel):
    """The current version of every notice."""

    apply: Notice
    interview: Notice
    biometric: Notice
