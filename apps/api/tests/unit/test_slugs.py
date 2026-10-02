"""Apply-link slugs (FR-PIPE-15): readable, ASCII, and unique within a workspace."""

from app.core.slugs import slugify, unique_slug


def test_slug_is_lowercase_ascii_with_hyphens() -> None:
    assert slugify("Frontend Engineer (React)") == "frontend-engineer-react"
    assert slugify("  Diseñador UX / UI  ") == "disenador-ux-ui"
    assert slugify("C++ & C# Developer") == "c-c-developer"
    assert slugify("!!!") == "role"


def test_slug_is_cut_at_60_characters_without_a_trailing_hyphen() -> None:
    slug = slugify("Senior " * 20)
    assert len(slug) <= 60
    assert not slug.endswith("-")


def test_taken_slug_gets_the_next_free_number() -> None:
    assert unique_slug("designer", set()) == "designer"
    assert unique_slug("designer", {"designer"}) == "designer-2"
    assert unique_slug("designer", {"designer", "designer-2"}) == "designer-3"
    long = "a" * 60
    assert unique_slug(long, {long}) == "a" * 58 + "-2"
