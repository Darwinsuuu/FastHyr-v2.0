"""PDF checks and sanitising for uploaded résumés (STORAGE.md, NFR-02).

`validate_pdf` rejects anything that isn't a readable, unencrypted PDF within the limits, with a
stable error code. `sanitise_pdf` rewrites the file without active content: JavaScript, embedded
files, and actions other than plain links. Neither logs file contents.
"""

import io
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

import pikepdf
from pikepdf import Array, Dictionary, Object

from app.core.errors import (
    PdfEncryptedError,
    PdfMalformedError,
    PdfNotPdfError,
    PdfTooLargeError,
    PdfTooManyPagesError,
)

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 20
# Readers accept the header anywhere in the first 1 KB (some tools write a few bytes first).
HEADER_SEARCH_BYTES = 1024

# Keys whose value is active content or runs something when the file opens or is used.
_ACTIVE_KEYS = (
    "/OpenAction",  # runs when the document opens
    "/AA",  # additional actions: page open/close, field focus, keystrokes
    "/JS",  # JavaScript source
    "/JavaScript",  # document-level JavaScript name tree
    "/EmbeddedFiles",  # attached files name tree
    "/EF",  # the embedded file stream of a file specification
    "/XFA",  # XML forms, which can carry scripts
    "/RichMediaContent",
)
# Annotations that only exist to play or open something.
_ACTIVE_ANNOTATIONS = {
    "/FileAttachment",
    "/RichMedia",
    "/Movie",
    "/Sound",
    "/Screen",
    "/3D",
}
# Plain links stay: an internal jump, or a web or mail address.
_SAFE_ACTIONS = {"/GoTo", "/URI"}
_SAFE_URI_SCHEMES = ("http://", "https://", "mailto:")


@dataclass(frozen=True)
class PdfInfo:
    pages: int
    size: int


def validate_pdf(data: bytes) -> PdfInfo:
    """Checks, in order: size, the `%PDF-` header, that the file opens, encryption, page count."""
    if len(data) > MAX_PDF_BYTES:
        raise PdfTooLargeError()
    if b"%PDF-" not in data[:HEADER_SEARCH_BYTES]:
        raise PdfNotPdfError()
    try:
        with pikepdf.open(io.BytesIO(data)) as pdf:
            if pdf.is_encrypted:
                # Opened without a password, but still encrypted (an owner password only).
                raise PdfEncryptedError()
            pages = len(pdf.pages)
    except pikepdf.PasswordError as error:
        raise PdfEncryptedError() from error
    except pikepdf.PdfError as error:
        raise PdfMalformedError() from error
    if pages == 0:
        raise PdfMalformedError()
    if pages > MAX_PDF_PAGES:
        raise PdfTooManyPagesError()
    return PdfInfo(pages=pages, size=len(data))


def sanitise_pdf(data: bytes) -> bytes:
    """Returns a copy of a valid PDF (call `validate_pdf` first) without active content.

    Every object is visited, so nothing hides in a form field, outline item or name tree. The
    file is written again from the document root, so the objects removed here (the scripts and
    file streams themselves) aren't carried over.
    """
    try:
        with pikepdf.open(io.BytesIO(data)) as pdf:
            for obj in pdf.objects:
                _clean(obj)
            _clean(pdf.Root)
            for page in pdf.pages:
                _clean(page.obj)
            out = io.BytesIO()
            pdf.save(out, fix_metadata_version=False)
        clean = out.getvalue()
        if active_content(clean):
            # Shouldn't happen; refuse the file rather than store something unsafe.
            raise PdfMalformedError()
    except pikepdf.PdfError as error:
        raise PdfMalformedError() from error
    return clean


def active_content(data: bytes) -> list[str]:
    """What active content a PDF still has, e.g. `["/JS", "/Launch"]`. Empty for a clean file.
    `sanitise_pdf` checks its own output with this, and tests use it."""
    found: set[str] = set()
    with pikepdf.open(io.BytesIO(data)) as pdf:
        for obj in pdf.objects:
            for dictionary in _dictionaries(obj):
                found.update(key for key in _ACTIVE_KEYS if key in dictionary)
                for action in _actions_in(dictionary):
                    if not _is_safe_action(action):
                        found.add(str(action.get("/S")))
                found.update(
                    str(annotation.get("/Subtype"))
                    for annotation in _active_annotations(dictionary)
                )
    return sorted(found)


def _clean(obj: Object) -> None:
    for dictionary in _dictionaries(obj):
        for key in _ACTIVE_KEYS:
            if key in dictionary:
                del dictionary[key]
        for key in _ACTION_KEYS:
            value = dictionary.get(key)
            if isinstance(value, Dictionary) and not _is_safe_action(value):
                del dictionary[key]
        active = _active_annotations(dictionary)
        if active:
            dictionary["/Annots"] = Array(
                annotation for annotation in dictionary["/Annots"] if annotation not in active
            )


# Where an action dictionary sits: a link or outline item's `/A`, and `/Next` (actions chained
# after another).
_ACTION_KEYS = ("/A", "/Next")


def _actions_in(dictionary: Dictionary) -> list[Dictionary]:
    return [value for key in _ACTION_KEYS if isinstance(value := dictionary.get(key), Dictionary)]


def _active_annotations(dictionary: Dictionary) -> list[Object]:
    annotations = dictionary.get("/Annots")
    if not isinstance(annotations, Array):
        return []
    return [
        annotation
        for annotation in annotations
        if isinstance(annotation, Dictionary)
        and str(annotation.get("/Subtype", "")) in _ACTIVE_ANNOTATIONS
    ]


def _is_safe_action(action: Dictionary) -> bool:
    kind = str(action.get("/S", ""))
    if kind not in _SAFE_ACTIONS or "/Next" in action:
        return False
    if kind == "/URI":
        uri = str(action.get("/URI", "")).strip().lower()
        return uri.startswith(_SAFE_URI_SCHEMES)
    return True


def _dictionaries(obj: Object) -> Iterator[Dictionary]:
    """`obj` and the dictionaries written inside it (not ones it only refers to: those are
    visited as objects of their own). Streams count through their dictionary."""
    stack: list[Object] = [obj]
    while stack:
        current = stack.pop()
        if isinstance(current, pikepdf.Stream):
            yield current.stream_dict
            stack.extend(_direct(current.stream_dict.values()))
        elif isinstance(current, Dictionary):
            yield current
            stack.extend(_direct(current.values()))
        elif isinstance(current, Array):
            stack.extend(_direct(current))


def _direct(values: Iterable[Any]) -> list[Object]:
    return [
        value
        for value in values
        if isinstance(value, Dictionary | Array | pikepdf.Stream) and not value.is_indirect
    ]
