"""Pipeline setup input (FR-PIPE-01..04): drafts take partial setup, values stay in range."""

import pytest
from pydantic import ValidationError

from app.schemas.pipelines import PipelineSetup


def test_a_draft_can_be_saved_with_any_part_of_the_setup() -> None:
    setup = PipelineSetup.model_validate({"title": " Data Analyst ", "must_haves": ["SQL", "SQL"]})
    assert setup.changes() == {"title": "Data Analyst", "must_haves": ["SQL"]}


@pytest.mark.parametrize(
    "body",
    [
        {"credits_to_reserve": 25},  # steps of 10
        {"credits_to_reserve": 0},
        {"link_expiry_days": 4},
        {"duration_days": 45},
        {"resume_pass_bar": 101},
        {"must_haves": None},  # lists can be emptied, not nulled
        {"opens_at": "2026-12-01T09:00:00"},  # needs a time zone
        {"unknown_field": 1},
    ],
)
def test_out_of_range_setup_is_rejected(body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PipelineSetup.model_validate(body)


def test_null_clears_optional_fields() -> None:
    assert PipelineSetup.model_validate({"location": None}).changes() == {"location": None}
