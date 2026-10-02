"""Résumé text extraction with pdfplumber (AI_PIPELINE.md §1 step 1).

Most résumés are one column and read fine line by line. Two-column résumés (a sidebar of skills
next to the experience) don't: pdfplumber reads across the page, so a sidebar line lands between
two lines of a job entry. Each page is checked for a gutter, a vertical gap in the middle of the
page that no line below the header runs across. When there is one, the page is read as its
full-width header, then the left column, then the right column.

A right-aligned date column ("Senior engineer ........ 2019 - 2021") also leaves a gap, but it is
narrow and its entries sit on the same lines as the text they belong to, so it doesn't count as a
column. (In most résumés, full-width bullet lines below each entry already rule it out.)

Text with fewer than `MIN_CHARACTERS` non-space characters (a scan, or a picture of a résumé) is
unreadable: the application waits for a person, never an automatic rejection (WORKFLOW.md §3).
"""

import io
import itertools
import logging
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pdfplumber
from pdfplumber.page import Page

logger = logging.getLogger("app.screening")

Word = dict[str, Any]  # a pdfplumber word: text, x0, x1, top, bottom

MIN_CHARACTERS = 200
# Where a gutter may be, as a share of the page width.
GUTTER_ZONE = (0.25, 0.75)
GUTTER_STEP = 2.0
# Each column holds at least this share of the page's body words.
MIN_COLUMN_SHARE = 0.15
# A right side narrower than this share of the page width whose lines mostly share a line with
# the left side is a table column (dates, places), so its rows stay whole. A narrow sidebar on
# the left is still a column.
MIN_COLUMN_WIDTH = 0.25
MAX_SHARED_LINES = 0.5
MIN_WORDS = 20
# Lines running across the gutter may only sit at the top (the name banner); the columns below
# must hold most of the page.
MIN_BODY_SHARE = 0.6
# Words on one line closer than this (points) are one run of text, not two columns.
MAX_WORD_GAP = 12.0
LINE_TOLERANCE = 3.0

_CID = re.compile(r"\(cid:\d+\)")
_HYPHEN_BREAK = re.compile(r"([a-z])-\n([a-z])")
_SPACES = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class Extraction:
    text: str
    pages: int
    column_pages: int

    @property
    def readable(self) -> bool:
        return characters(self.text) >= MIN_CHARACTERS


UNREADABLE = Extraction(text="", pages=0, column_pages=0)


def characters(text: str) -> int:
    """Non-space characters, the measure for "is there enough text"."""
    return sum(1 for char in text if not char.isspace())


def extract_text(data: bytes) -> Extraction:
    """The résumé's text in reading order, normalised. A file pdfplumber can't open counts as
    unreadable (upload already checked it is a PDF; FND-011)."""
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            parts: list[str] = []
            column_pages = 0
            for page in pdf.pages:
                text, columns = _page_text(page)
                parts.append(text)
                column_pages += columns
            return Extraction(
                text=normalise("\n\n".join(parts)), pages=len(pdf.pages), column_pages=column_pages
            )
    except Exception as error:  # pdfminer raises many kinds on damaged files
        logger.info("resume extraction failed (%s)", type(error).__name__)
        return UNREADABLE


def _page_text(page: Page) -> tuple[str, int]:
    words = page.extract_words()
    gutter = find_gutter(words, float(page.width))
    if gutter is None:
        return page.extract_text() or "", 0
    x, header_bottom = gutter
    width, height = float(page.width), float(page.height)
    regions = [
        (0.0, 0.0, width, header_bottom),
        (0.0, header_bottom, x, height),
        (x, header_bottom, width, height),
    ]
    texts = [
        page.within_bbox(region).extract_text() or "" for region in regions if region[3] > region[1]
    ]
    return "\n\n".join(text for text in texts if text.strip()), 1


def find_gutter(words: Sequence[Word], width: float) -> tuple[float, float] | None:
    """The x of a gap between two text columns and the bottom of the full-width header above
    them, or None for a one-column page. Of all the gaps that qualify, the middle of the widest
    run is used."""
    if len(words) < MIN_WORDS:
        return None
    lines = _lines(words)
    valid: list[tuple[float, float]] = []
    x = width * GUTTER_ZONE[0]
    while x <= width * GUTTER_ZONE[1]:
        header_bottom = _columns_below(lines, len(words), x, width)
        if header_bottom is not None:
            valid.append((x, header_bottom))
        x += GUTTER_STEP
    if not valid:
        return None
    runs: list[list[tuple[float, float]]] = [[valid[0]]]
    for previous, current in itertools.pairwise(valid):
        if current[0] - previous[0] > GUTTER_STEP * 1.5:
            runs.append([])
        runs[-1].append(current)
    widest = max(runs, key=len)
    return widest[len(widest) // 2]


def _lines(words: Sequence[Word]) -> list[list[Word]]:
    """Words grouped into lines by their top edge, top of the page first."""
    lines: list[list[Word]] = []
    for word in sorted(words, key=lambda w: float(w["top"])):
        if lines and float(word["top"]) - float(lines[-1][0]["top"]) <= LINE_TOLERANCE:
            lines[-1].append(word)
        else:
            lines.append([word])
    return lines


def _bridges(line: Sequence[Word], x: float) -> bool:
    """Whether the line's text runs across `x`: a word crosses it, or the words either side of
    it are a word space apart rather than a gutter apart."""
    if any(w["x0"] < x < w["x1"] for w in line):
        return True
    left = [float(w["x1"]) for w in line if w["x1"] <= x]
    right = [float(w["x0"]) for w in line if w["x0"] >= x]
    return bool(left and right) and min(right) - max(left) <= MAX_WORD_GAP


def _columns_below(
    lines: Sequence[Sequence[Word]], total: int, x: float, width: float
) -> float | None:
    """When the page splits into two columns at `x`, the bottom of the header above them (0 for
    none); otherwise None. Only lines at the top may run across `x`: the header is everything
    down to the last such line."""
    bridging = [index for index, line in enumerate(lines) if _bridges(line, x)]
    header = lines[: bridging[-1] + 1] if bridging else []
    body = lines[len(header) :]
    body_words = [w for line in body for w in line]
    if len(body_words) < MIN_BODY_SHARE * total:
        return None
    left = [w for w in body_words if w["x1"] <= x]
    right = [w for w in body_words if w["x0"] >= x]
    if min(len(left), len(right)) < MIN_COLUMN_SHARE * len(body_words):
        return None
    if _span(right) < MIN_COLUMN_WIDTH * width and _mostly_shared(body, x):
        return None
    return max((float(w["bottom"]) for line in header for w in line), default=0.0)


def _mostly_shared(lines: Sequence[Sequence[Word]], x: float) -> bool:
    """Whether most lines with text right of `x` also have text left of it, as rows of a table
    do."""
    right = [line for line in lines if any(w["x0"] >= x for w in line)]
    shared = [line for line in right if any(w["x1"] <= x for w in line)]
    return bool(right) and len(shared) / len(right) > MAX_SHARED_LINES


def _span(words: Sequence[Word]) -> float:
    return float(max(w["x1"] for w in words) - min(w["x0"] for w in words))


def normalise(text: str) -> str:
    """NFKC (ligatures, full-width forms), no `(cid:N)` glyph junk, words split by a line-end
    hyphen joined, runs of spaces and blank lines collapsed."""
    text = unicodedata.normalize("NFKC", text)
    text = _CID.sub("", text)
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    lines = [_SPACES.sub(" ", line).strip() for line in text.splitlines()]
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
