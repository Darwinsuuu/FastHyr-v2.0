"""Checks for the company logo and email banner (FR-WS-01, STORAGE.md "Branding").

The file type comes from the bytes, never the browser. Every accepted image is decoded and
re-encoded, which drops metadata (EXIF, GPS, comments) and anything appended after the image
data. SVG logos are rasterised to PNG in the browser before upload, so the server never parses
SVG. Large images are scaled down: emails don't need more and load faster.
"""

import io
import warnings
from dataclasses import dataclass
from enum import StrEnum

from PIL import Image, UnidentifiedImageError

from app.core.errors import (
    ImageDimensionsTooLargeError,
    ImageInvalidError,
    ImageTooLargeError,
    LogoNotSquareError,
    LogoTooSmallError,
)

MAX_BYTES = 2 * 1024 * 1024
# Decompression-bomb guard: a 2 MB file can still claim enormous dimensions.
MAX_SIDE = 4096
LOGO_MIN_SIDE = 256
LOGO_MAX_SIDE = 1024
BANNER_MAX_WIDTH = 1200


class BrandingKind(StrEnum):
    LOGO = "logo"
    BANNER = "banner"


@dataclass(frozen=True)
class CleanImage:
    data: bytes
    content_type: str
    extension: str
    width: int
    height: int


_FORMATS = {
    BrandingKind.LOGO: {"PNG"},
    BrandingKind.BANNER: {"PNG", "JPEG"},
}


def clean_branding_image(data: bytes, kind: BrandingKind) -> CleanImage:
    """Validates `data` as a logo or banner and returns a re-encoded copy, or raises an
    `ImageInvalidError` subclass naming what's wrong."""
    if len(data) > MAX_BYTES:
        raise ImageTooLargeError()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                image_format = probe.format
                width, height = probe.size
                if image_format not in _FORMATS[kind]:
                    raise ImageInvalidError()
                if width > MAX_SIDE or height > MAX_SIDE:
                    raise ImageDimensionsTooLargeError()
                probe.verify()
            # `verify()` leaves the image unusable, so decode a fresh copy.
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                decoded = image.copy()
    except ImageInvalidError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Warning) as error:
        raise ImageInvalidError() from error

    if kind is BrandingKind.LOGO:
        if width != height:
            raise LogoNotSquareError()
        if width < LOGO_MIN_SIDE:
            raise LogoTooSmallError()
        return _encode_png(_fit(decoded, LOGO_MAX_SIDE, LOGO_MAX_SIDE))

    banner = _fit(decoded, BANNER_MAX_WIDTH, MAX_SIDE)
    if image_format == "JPEG":
        return _encode_jpeg(banner)
    return _encode_png(banner)


def _fit(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    if image.width <= max_width and image.height <= max_height:
        return image
    fitted = image.copy()
    fitted.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    return fitted


def _encode_png(image: Image.Image) -> CleanImage:
    if image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
        image = image.convert("RGBA")
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return CleanImage(out.getvalue(), "image/png", "png", image.width, image.height)


def _encode_jpeg(image: Image.Image) -> CleanImage:
    if image.mode != "RGB":
        image = image.convert("RGB")
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=88, optimize=True, progressive=True)
    return CleanImage(out.getvalue(), "image/jpeg", "jpg", image.width, image.height)
