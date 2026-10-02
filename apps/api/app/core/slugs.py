"""URL slugs for apply links (FR-PIPE-15): `…/apply/{workspace-slug}/{pipeline-slug}`.

Slugs are ASCII, lowercase and hyphenated, derived from a title. A taken slug gets `-2`, `-3`…
"""

import re
import unicodedata
from collections.abc import Collection

MAX_LENGTH = 60
FALLBACK = "role"


def slugify(title: str, *, max_length: int = MAX_LENGTH) -> str:
    """'Frontend Engineer (React)' → 'frontend-engineer-react'. Accents are dropped
    ('Diseñador' → 'disenador'); a title with no letters or digits becomes 'role'."""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    slug = slug[:max_length].rstrip("-")
    return slug or FALLBACK


def unique_slug(base: str, taken: Collection[str], *, max_length: int = MAX_LENGTH) -> str:
    """`base`, or `base-2`, `base-3`… whichever isn't in `taken`, within `max_length`."""
    if base not in taken:
        return base
    number = 2
    while True:
        suffix = f"-{number}"
        candidate = base[: max_length - len(suffix)].rstrip("-") + suffix
        if candidate not in taken:
            return candidate
        number += 1
