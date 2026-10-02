import re
import uuid
from datetime import datetime
from functools import cache
from typing import Annotated, Literal
from urllib.parse import urlsplit
from zoneinfo import available_timezones

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, field_validator

from app.services.images import BrandingKind

COMPANY_NAME_MAX = 120
ABOUT_MAX = 600
URL_MAX = 300

# Stable keys; the web shows their labels (frame CompanyProfile).
Industry = Literal[
    "technology",
    "finance",
    "healthcare",
    "bpo",
    "retail",
    "manufacturing",
    "government",
    "other",
]
CompanySize = Literal["1-50", "51-200", "201-1000", "1001-5000", "5000+"]

_HOST = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def _web_url(value: str) -> str:
    """An http(s) URL with a real-looking host. A bare `acme.com` gets `https://`."""
    url = value if re.match(r"^https?://", value, re.IGNORECASE) else f"https://{value}"
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme.lower() not in ("http", "https") or not _HOST.match(host):
        raise ValueError("Enter a web address like yourcompany.com")
    if parts.username or parts.password or parts.port:
        raise ValueError("Enter a web address like yourcompany.com")
    return url


def _country(value: str) -> str:
    if not re.fullmatch(r"[A-Z]{2}", value):
        raise ValueError("Choose a country from the list")
    return value


@cache
def _time_zones() -> frozenset[str]:
    return frozenset(available_timezones())


def _time_zone(value: str) -> str:
    if value not in _time_zones():
        raise ValueError("Choose a time zone from the list")
    return value


Trimmed = StringConstraints(strip_whitespace=True)
CompanyName = Annotated[str, Trimmed, StringConstraints(min_length=1, max_length=COMPANY_NAME_MAX)]
WebUrl = Annotated[
    str, Trimmed, StringConstraints(min_length=1, max_length=URL_MAX), AfterValidator(_web_url)
]
Country = Annotated[str, Trimmed, AfterValidator(_country)]
TimeZone = Annotated[str, Trimmed, AfterValidator(_time_zone)]
About = Annotated[str, Trimmed, StringConstraints(max_length=ABOUT_MAX)]


class CompanyProfile(BaseModel):
    company_name: str
    website: str | None
    industry: str | None
    company_size: str | None
    hq_country: str | None
    timezone: str | None
    about: str | None
    careers_url: str | None
    # Signed Storage URLs that work for 15 minutes; null when there is no image.
    logo_url: str | None
    banner_url: str | None
    updated_at: datetime


class UpdateCompanyProfileRequest(BaseModel):
    """The whole form. Optional fields sent as null or "" are cleared.

    `logo_upload_id` / `banner_upload_id` attach the image uploaded with that ID from
    `POST /workspace/company-profile/branding-upload`; `remove_logo` / `remove_banner` drop it.
    """

    company_name: CompanyName
    website: WebUrl | None = None
    industry: Industry | None = None
    company_size: CompanySize | None = None
    hq_country: Country | None = None
    timezone: TimeZone | None = None
    about: About | None = None
    careers_url: WebUrl | None = None
    logo_upload_id: uuid.UUID | None = None
    banner_upload_id: uuid.UUID | None = None
    remove_logo: bool = False
    remove_banner: bool = False

    @field_validator(
        "website",
        "industry",
        "company_size",
        "hq_country",
        "timezone",
        "about",
        "careers_url",
        mode="before",
    )
    @classmethod
    def blank_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class BrandingUploadRequest(BaseModel):
    kind: BrandingKind


class BrandingUpload(BaseModel):
    """PUT the file to `url` (or `uploadToSignedUrl(path, token, file)` in supabase-js) within
    10 minutes, then send `upload_id` with the profile."""

    upload_id: uuid.UUID
    url: str
    path: str
    token: str
    max_bytes: int = Field(description="Largest file the API accepts")
