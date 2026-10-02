"""WS-001: logo and banner checks (type from the bytes, size, shape, re-encoding that drops
metadata) and the company profile form's rules."""

import io

import pytest
from PIL import Image
from pydantic import ValidationError

from app.core.errors import (
    ImageDimensionsTooLargeError,
    ImageInvalidError,
    ImageTooLargeError,
    LogoNotSquareError,
    LogoTooSmallError,
)
from app.schemas.company_profile import UpdateCompanyProfileRequest
from app.services.images import BrandingKind, clean_branding_image


def image_bytes(width: int, height: int, fmt: str = "PNG", **save: object) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (31, 77, 67)).save(out, format=fmt, **save)
    return out.getvalue()


def test_logo_is_reencoded_without_trailing_data() -> None:
    data = image_bytes(300, 300) + b"<script>alert(1)</script>"

    clean = clean_branding_image(data, BrandingKind.LOGO)

    assert clean.content_type == "image/png"
    assert b"script" not in clean.data
    assert (clean.width, clean.height) == (300, 300)


def test_large_logo_and_banner_are_scaled_down() -> None:
    logo = clean_branding_image(image_bytes(2000, 2000), BrandingKind.LOGO)
    banner = clean_branding_image(image_bytes(2400, 800, "JPEG"), BrandingKind.BANNER)

    assert (logo.width, logo.height) == (1024, 1024)
    assert (banner.width, banner.height, banner.extension) == (1200, 400, "jpg")


def test_banner_metadata_is_dropped() -> None:
    exif = Image.Exif()
    exif[0x010E] = "GPS and camera details"  # ImageDescription
    data = image_bytes(1200, 400, "JPEG", exif=exif.tobytes())
    assert b"camera details" in data

    clean = clean_branding_image(data, BrandingKind.BANNER)

    assert b"camera details" not in clean.data


@pytest.mark.parametrize(
    ("data", "kind", "error"),
    [
        (image_bytes(300, 200), BrandingKind.LOGO, LogoNotSquareError),
        (image_bytes(200, 200), BrandingKind.LOGO, LogoTooSmallError),
        (image_bytes(300, 300, "JPEG"), BrandingKind.LOGO, ImageInvalidError),
        (image_bytes(300, 300, "GIF"), BrandingKind.BANNER, ImageInvalidError),
        (b"<svg xmlns='http://www.w3.org/2000/svg'/>", BrandingKind.LOGO, ImageInvalidError),
        (b"%PDF-1.7 not an image", BrandingKind.BANNER, ImageInvalidError),
        (image_bytes(5000, 100), BrandingKind.BANNER, ImageDimensionsTooLargeError),
        (b"\x89PNG" + b"0" * (2 * 1024 * 1024), BrandingKind.LOGO, ImageTooLargeError),
    ],
)
def test_images_that_cannot_be_used(data: bytes, kind: BrandingKind, error: type) -> None:
    with pytest.raises(error):
        clean_branding_image(data, kind)


def test_truncated_png_is_invalid() -> None:
    with pytest.raises(ImageInvalidError):
        clean_branding_image(image_bytes(300, 300)[:200], BrandingKind.LOGO)


def test_form_rules() -> None:
    body = UpdateCompanyProfileRequest.model_validate(
        {
            "company_name": "  Acme Talent ",
            "website": "acme.com",
            "careers_url": "  ",
            "industry": "",
            "hq_country": "PH",
            "timezone": "Asia/Manila",
            "about": " Warm words ",
        }
    )

    assert body.company_name == "Acme Talent"
    assert body.website == "https://acme.com"
    assert body.careers_url is None
    assert body.industry is None
    assert body.about == "Warm words"


@pytest.mark.parametrize(
    "changes",
    [
        {"company_name": "  "},
        {"website": "javascript:alert(1)"},
        {"website": "https://user:pw@acme.com"},
        {"website": "not a url"},
        {"industry": "mining"},
        {"hq_country": "Philippines"},
        {"timezone": "Mars/Olympus"},
        {"about": "x" * 601},
    ],
)
def test_form_rejects(changes: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        UpdateCompanyProfileRequest.model_validate({"company_name": "Acme", **changes})
