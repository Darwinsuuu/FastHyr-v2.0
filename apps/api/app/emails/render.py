"""Rendering an email: parameters, the body allow-list, the layout and the plain-text part.

Workspace templates are HTML that TA users edit, so the body is cleaned with an allow-list
(p, br, strong, em, a[href], ul, li; NOTIFICATIONS.md §2) before it goes into the layout, and
parameter values are escaped. The plain-text alternative is generated from the final body.
"""

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

import nh3
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ALLOWED_TAGS = {"p", "br", "strong", "em", "a", "ul", "li"}
ALLOWED_ATTRIBUTES = {"a": {"href"}}
ALLOWED_URL_SCHEMES = {"https", "http", "mailto"}

# `[Candidate.firstname]`-style parameters (NOTIFICATIONS.md §2).
PARAMETER = re.compile(r"\[([A-Za-z]+\.[A-Za-z]+)\]")

_environment = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html", "jinja"]),
    trim_blocks=True,
)


@dataclass(frozen=True)
class Button:
    label: str
    url: str


@dataclass(frozen=True)
class Branding:
    """A company's email header: banner, else logo, else name (WS-001)."""

    company_name: str
    logo_url: str | None = None
    banner_url: str | None = None


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


def sanitize(body_html: str) -> str:
    """Keeps only the allow-listed tags and attributes; links get rel="noopener noreferrer"."""
    return nh3.clean(
        body_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )


def fill_parameters(template: str, values: dict[str, str], *, escape: bool) -> str:
    """Replaces each known `[Name.field]` with its value (HTML-escaped when `escape`). Unknown
    parameters stay as written; MSG-001 rejects them when a template is saved."""

    def replace(match: re.Match[str]) -> str:
        value = values.get(match.group(1))
        if value is None:
            return match.group(0)
        return html.escape(value) if escape else value

    return PARAMETER.sub(replace, template)


def render(
    *,
    subject: str,
    body_html: str,
    parameters: dict[str, str] | None = None,
    site_url: str,
    company: str | None = None,
    banner_url: str | None = None,
    logo_url: str | None = None,
    heading: str | None = None,
    preheader: str | None = None,
    button: Button | None = None,
    after_html: str | None = None,
) -> RenderedEmail:
    """Fills parameters, sanitises `body_html` and puts it in the layout. `company` makes it a
    company email ("Sent by {company} via FastHyr"); without it the email is from FastHyr. The
    header shows `banner_url`, else `logo_url`, else the company name.
    `after_html` is trusted markup from code (never user input), shown after the button."""
    values = parameters or {}
    subject_text = fill_parameters(subject, values, escape=False)
    body = sanitize(fill_parameters(body_html, values, escape=True))
    page = _environment.get_template("layout.html.jinja").render(
        subject=subject_text,
        preheader=preheader,
        heading=heading,
        body_html=Markup(body),
        button=button,
        after_html=Markup(after_html) if after_html else None,
        company=company,
        banner_url=banner_url,
        logo_url=logo_url,
        site_url=site_url.rstrip("/"),
    )
    text_parts = [heading or "", html_to_text(body)]
    if button:
        text_parts.append(f"{button.label}: {button.url}")
    if after_html:
        text_parts.append(html_to_text(after_html))
    text_parts.append(f"Sent by {company} via FastHyr" if company else "The FastHyr team")
    text = "\n\n".join(part for part in text_parts if part.strip())
    return RenderedEmail(subject=subject_text, html=page, text=text + "\n")


class _TextExtractor(HTMLParser):
    BLOCKS = frozenset({"p", "div", "h1", "h2", "h3", "ul", "ol", "table", "tr"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.href: str | None = None
        self.link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCKS:
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "a":
            self.href = dict(attrs).get("href")
            self.link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCKS:
            self.parts.append("\n\n")
        elif tag == "a":
            text = "".join(self.link_text).strip()
            href = self.href or ""
            if href and href != text and not href.startswith("mailto:"):
                self.parts.append(f" ({href})")
            self.href = None

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data)
        self.parts.append(text)
        if self.href is not None:
            self.link_text.append(text)


def html_to_text(markup: str) -> str:
    """A readable plain-text version: paragraphs, line breaks, bullets and link URLs."""
    parser = _TextExtractor()
    parser.feed(markup)
    parser.close()
    text = "".join(parser.parts)
    lines = [line.strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
