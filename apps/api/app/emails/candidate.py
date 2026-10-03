"""Rendering a workspace's candidate email template (NOTIFICATIONS.md §1-3).

Rejection emails always end with the human-review line (ADR-015), whatever the template says;
link parameters standing in the text become links; every parameter the template uses must have
a value, so a candidate never receives a literal "[Interview.link]".
"""

import re

from app.emails.defaults import (
    LINK_PARAMETERS,
    REJECTION_KEYS,
    REVIEW_LINE_HTML,
    REVIEW_LINK,
    TemplateKey,
)
from app.emails.render import PARAMETER, Branding, RenderedEmail, render

_ANCHOR = re.compile(r"<a\b[^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)
_LINK_PARAMETER = re.compile(
    r"\[(" + "|".join(re.escape(name) for name in sorted(LINK_PARAMETERS)) + r")\]"
)


class MissingParameterError(ValueError):
    """The caller didn't supply a value for a parameter the template uses."""


def with_review_line(key: TemplateKey, body_html: str) -> str:
    """A rejection body with the review line added when the editor left `[Review.link]` out."""
    if key in REJECTION_KEYS and f"[{REVIEW_LINK}]" not in body_html:
        return body_html + REVIEW_LINE_HTML
    return body_html


def link_parameters(body_html: str) -> str:
    """Wraps link parameters that stand in the text (not inside an existing link) in a link to
    themselves, so the URL is clickable once filled."""

    def wrap(text: str) -> str:
        return _LINK_PARAMETER.sub(r'<a href="[\1]">[\1]</a>', text)

    parts: list[str] = []
    position = 0
    for anchor in _ANCHOR.finditer(body_html):
        parts.append(wrap(body_html[position : anchor.start()]))
        parts.append(anchor.group(0))
        position = anchor.end()
    parts.append(wrap(body_html[position:]))
    return "".join(parts)


def render_template(
    *,
    key: TemplateKey,
    subject: str,
    body_html: str,
    values: dict[str, str],
    site_url: str,
    branding: Branding,
) -> RenderedEmail:
    """The email for one candidate, from "{Company} via FastHyr" with the company's branding."""
    body = link_parameters(with_review_line(key, body_html))
    used = set(PARAMETER.findall(subject)) | set(PARAMETER.findall(body))
    missing = sorted(name for name in used if not values.get(name))
    if missing:
        raise MissingParameterError(", ".join(missing))
    return render(
        subject=subject,
        body_html=body,
        parameters=values,
        site_url=site_url,
        company=branding.company_name,
        banner_url=branding.banner_url,
        logo_url=branding.logo_url,
    )
