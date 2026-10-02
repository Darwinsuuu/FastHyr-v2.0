"""SCREEN-001: résumé text comes out in reading order (two-column pages read column by column,
right-aligned dates stay on their row), and a résumé without enough text is unreadable."""

from app.screening.extract import extract_text, normalise
from tests.pdf_fixtures import plain_pdf, text_pdf


def lines_of(text: str) -> list[str]:
    return [line for line in text.splitlines() if line]


def test_one_column_page_reads_line_by_line() -> None:
    placements = [
        (72, 72 + i * 14, f"Built service number {i} in Python and Go") for i in range(30)
    ]

    extraction = extract_text(text_pdf(placements))

    assert extraction.readable
    assert extraction.pages == 1
    assert extraction.column_pages == 0
    assert lines_of(extraction.text)[:2] == [
        "Built service number 0 in Python and Go",
        "Built service number 1 in Python and Go",
    ]


def test_two_column_page_reads_the_columns_one_after_the_other() -> None:
    banner = [(50, 50, "Senior Backend Engineer with ten years of payments experience")]
    sidebar = [(50, 100 + i * 14, f"Skill {i}: Python, Kafka") for i in range(20)]
    # The main column's lines sit between the sidebar's, as in a real two-column layout.
    main = [(320, 107 + i * 14, f"Experience line {i} at Lakbay Logistics") for i in range(25)]

    extraction = extract_text(text_pdf(banner + sidebar + main))

    lines = lines_of(extraction.text)
    assert extraction.column_pages == 1
    assert lines[0] == "Senior Backend Engineer with ten years of payments experience"
    assert lines[1:21] == [f"Skill {i}: Python, Kafka" for i in range(20)]
    assert lines[21:] == [f"Experience line {i} at Lakbay Logistics" for i in range(25)]


def test_right_aligned_dates_stay_on_their_row() -> None:
    rows = []
    for i in range(20):
        rows += [
            (72, 72 + i * 14, f"Backend engineer at company {i}"),
            (470, 72 + i * 14, "2019 - 2021"),
        ]

    extraction = extract_text(text_pdf(rows))

    assert extraction.column_pages == 0
    assert lines_of(extraction.text)[0] == "Backend engineer at company 0 2019 - 2021"


def test_too_little_text_is_unreadable() -> None:
    # A scan has no text layer; this page has one word.
    assert not extract_text(plain_pdf()).readable
    assert not extract_text(text_pdf([(72, 72, "Experience " * 15)])).readable


def test_a_damaged_file_is_unreadable_not_an_error() -> None:
    extraction = extract_text(b"%PDF-1.7\nnot really a pdf")

    assert not extraction.readable
    assert extraction.text == ""


def test_normalise_fixes_ligatures_glyph_junk_and_line_end_hyphens() -> None:
    raw = "Efﬁcient   data (cid:12)pipe-\nlines\n\n\n\nfor 2019-\n2021"

    assert normalise(raw) == "Efficient data pipelines\n\nfor 2019-\n2021"
