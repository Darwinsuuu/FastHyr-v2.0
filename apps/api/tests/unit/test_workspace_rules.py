"""AUTH-003 and AUTH-004: workspace slugs, pasted invite codes and the join page's masked email."""

import pytest

from app.services.workspaces import (
    SLUG_MAX,
    mask_email,
    next_free_slug,
    normalize_invite_code,
    slugify,
)


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Acme Talent", "acme-talent"),
        ("  Café Talent, Inc. ", "cafe-talent-inc"),
        ("R&D -- Team 2", "r-d-team-2"),
        ("人才", "workspace"),
        ("!!!", "workspace"),
    ],
)
def test_slugify_is_lowercase_ascii_joined_by_single_hyphens(name: str, slug: str) -> None:
    assert slugify(name) == slug


def test_slug_leaves_room_for_a_suffix() -> None:
    base = slugify("a" * 200)
    assert next_free_slug(base, {base}) == f"{base}-2"
    assert len(f"{base}-99") <= SLUG_MAX


def test_next_free_slug_counts_up_past_taken_ones() -> None:
    assert next_free_slug("acme", set()) == "acme"
    assert next_free_slug("acme", {"acme", "acme-2", "acme-4"}) == "acme-3"


@pytest.mark.parametrize(
    "pasted",
    [
        "AB12-CD34",
        " ab12-cd34 ",
        "https://fasthyr.com/join/ab12-cd34",
        "fasthyr.com/join/AB12-CD34/",
        "https://fasthyr.com/join/AB12-CD34?utm=mail",
    ],
)
def test_invite_codes_are_accepted_as_pasted(pasted: str) -> None:
    assert normalize_invite_code(pasted) == "AB12-CD34"


@pytest.mark.parametrize(
    ("email", "masked"),
    [("dana.cruz@acme.com", "d•••@acme.com"), ("j@x.io", "j•••@x.io")],
)
def test_masked_email_keeps_the_first_letter_and_domain(email: str, masked: str) -> None:
    assert mask_email(email) == masked
