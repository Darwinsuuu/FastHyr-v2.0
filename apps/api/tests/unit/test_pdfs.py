"""PDF checks and sanitising (FND-011): stable error codes, and no active content survives."""

import io

import pikepdf
import pytest

from app.core.errors import (
    PdfEncryptedError,
    PdfInvalidError,
    PdfMalformedError,
    PdfNotPdfError,
    PdfTooLargeError,
    PdfTooManyPagesError,
)
from app.services.pdfs import MAX_PDF_BYTES, active_content, sanitise_pdf, validate_pdf
from tests.pdf_fixtures import encrypted_pdf, hostile_pdf, plain_pdf


def test_accepts_a_plain_pdf() -> None:
    info = validate_pdf(plain_pdf(pages=20))
    assert info.pages == 20


@pytest.mark.parametrize(
    ("data", "error", "code"),
    [
        (b"PK\x03\x04 a zip, not a PDF", PdfNotPdfError, "pdf_not_pdf"),
        (b"%PDF-1.7\n" + b"0" * MAX_PDF_BYTES, PdfTooLargeError, "pdf_too_large"),
        (b"%PDF-1.7\nnot really a pdf", PdfMalformedError, "pdf_malformed"),
        (plain_pdf()[:200], PdfMalformedError, "pdf_malformed"),
        (encrypted_pdf(), PdfEncryptedError, "pdf_encrypted"),
        # Opens without a password but is still encrypted (owner password only).
        (encrypted_pdf(user_password=""), PdfEncryptedError, "pdf_encrypted"),
        (plain_pdf(pages=21), PdfTooManyPagesError, "pdf_too_many_pages"),
    ],
)
def test_rejects_bad_files_with_a_stable_code(
    data: bytes, error: type[PdfInvalidError], code: str
) -> None:
    with pytest.raises(error) as raised:
        validate_pdf(data)
    assert raised.value.code == code
    assert raised.value.status == 422


def test_sanitised_pdf_has_no_javascript_embedded_files_or_actions() -> None:
    hostile = hostile_pdf()
    assert {"/JS", "/OpenAction", "/EmbeddedFiles", "/Launch", "/FileAttachment"} <= set(
        active_content(hostile)
    )

    clean = sanitise_pdf(hostile)

    assert active_content(clean) == []
    assert b"app.alert" not in clean
    assert b"not really an exe" not in clean
    assert validate_pdf(clean).pages == 1


def test_sanitising_keeps_web_and_internal_links() -> None:
    clean = sanitise_pdf(hostile_pdf())
    with pikepdf.open(io.BytesIO(clean)) as pdf:
        actions = [annotation.A for annotation in pdf.pages[0].Annots if "/A" in annotation]
        assert [(str(action.S), str(action.get("/URI", ""))) for action in actions] == [
            ("/URI", "https://linkedin.com/in/x"),
            ("/GoTo", ""),
        ]


def test_a_plain_pdf_is_unchanged_in_content() -> None:
    clean = sanitise_pdf(plain_pdf(pages=3))
    with pikepdf.open(io.BytesIO(clean)) as pdf:
        assert len(pdf.pages) == 3
        assert pdf.pages[0].Contents.read_bytes() == b"BT /F1 12 Tf 72 720 Td (Experience) Tj ET"
