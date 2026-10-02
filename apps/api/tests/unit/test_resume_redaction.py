"""SCREEN-001 (G2, FR-SCREEN-02): names, schools, graduation years, addresses and contact
details are removed before any scoring. Counterfactual résumés that differ only in those details
redact to the same text; work history, skills and employment dates are kept."""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from app.ai.prompts import Prompt
from app.ai.schemas.resume_redaction import ResumeRedaction
from app.screening.redact import apply_spans, redact, redact_rules

CASES = Path(__file__).parent.parent / "ai_eval" / "cases" / "resume_redaction@v1"


class StubAI:
    """Answers `resume_redaction` with the spans a correct model finds, recording what it saw."""

    model = "stub"

    def __init__(self, spans: list[dict[str, str]]) -> None:
        self.spans = spans
        self.seen: list[str] = []

    async def structured[T: BaseModel](
        self,
        *,
        purpose: str,
        prompt: Prompt,
        variables: dict[str, str],
        schema: type[T],
        workspace_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        temperature: float | None = None,
    ) -> T:
        assert schema is ResumeRedaction
        self.seen.append(variables["resume_text"])
        return schema.model_validate({"spans": self.spans})


def cases() -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(CASES.glob("*.json"))]


def run(case: dict[str, Any]) -> tuple[str, StubAI]:
    ai = StubAI(case["fake_spans"])
    variables = case["variables"]
    redaction = asyncio.run(
        redact(ai, variables["resume_text"], known_names=[variables["full_name"]])
    )
    return redaction.text, ai


@pytest.mark.parametrize("case", cases(), ids=lambda case: case["variables"]["full_name"])
def test_personal_details_are_removed_and_evidence_kept(case: dict[str, Any]) -> None:
    text, ai = run(case)

    for detail in case["must_remove"]:
        assert detail.lower() not in text.lower(), detail
    for evidence in case["must_keep"]:
        assert evidence in text, evidence
    # The model only ever sees text the rules already cleaned.
    assert case["variables"]["full_name"] not in ai.seen[0]
    assert "@example.com" not in ai.seen[0]


def test_counterfactual_pairs_redact_to_the_same_text() -> None:
    by_pair: dict[str, set[str]] = {}
    for case in cases():
        by_pair.setdefault(case["pair"], set()).add(run(case)[0])

    assert len(by_pair) >= 2
    for pair, texts in by_pair.items():
        assert len(texts) == 1, f"{pair} differs after redaction"


def test_contact_details_and_links() -> None:
    text = redact_rules(
        "paolo@example.com · +63 (2) 8123 4567 · https://paolo.dev · github.com/paolo\n"
        "Cut costs 40% from 2019-2021 across 3,000 stores on 12/03/2020"
    ).text

    assert text.splitlines()[0] == "[EMAIL] · [PHONE] · [LINK] · [LINK]"
    # Year ranges, numbers and dates aren't phone numbers.
    assert text.splitlines()[1] == "Cut costs 40% from 2019-2021 across 3,000 stores on 12/03/2020"


def test_labelled_personal_lines_keep_their_label() -> None:
    text = redact_rules(
        "Age: 34\nSex: F\nReligion: Roman Catholic\nHome address: Blk 4 Lot 2, Bacoor, Cavite\n"
        "Birthday - May 5, 1990\nHeight: 160 cm\nI am 34 years old."
    ).text

    assert text == (
        "Age: [AGE]\nSex: [GENDER]\nReligion: [PERSONAL DETAIL]\nHome address: [ADDRESS]\n"
        "Birthday - [DATE OF BIRTH]\nHeight: [PERSONAL DETAIL]\nI am [AGE]."
    )


def test_years_are_removed_in_education_but_kept_in_work_history() -> None:
    text = redact_rules(
        "Experience\nEngineer, Acme, 2016 - 2020\n\nEducation\nBS Computer Science\n"
        "2008 - 2012\n\nCertifications\nAWS Solutions Architect, 2021\n"
        "Graduated in 2012 with honours"
    ).text

    assert "Engineer, Acme, 2016 - 2020" in text
    assert "[YEAR] - [YEAR]" in text
    assert "AWS Solutions Architect, 2021" in text
    assert "Graduated in [YEAR] with honours" in text


def test_street_addresses() -> None:
    text = redact_rules(
        "Lives at 221B Baker Street, London\nBrgy. San Isidro, Antipolo\n"
        "Ran clinics in 40 barangay health centres."
    ).text

    assert text == "Lives at [ADDRESS]\n[ADDRESS]\nRan clinics in 40 barangay health centres."


def test_the_candidates_name_in_every_form_but_not_common_words() -> None:
    text = redact_rules(
        "MARIA YOUNG\nMaria Young | Young, Maria\nMentored young engineers.", ["Maria Young"]
    ).text

    assert text == "[NAME]\n[NAME] | [NAME], [NAME]\nMentored young engineers."


def test_model_spans_mask_every_occurrence_longest_first() -> None:
    redaction = redact_rules("Ateneo de Manila University (Ateneo)\nShe led the Ateneo team.")

    apply_spans(
        redaction,
        [("school", "Ateneo"), ("school", "Ateneo de Manila University"), ("gender", "she")],
    )

    assert redaction.text == "[SCHOOL] ([SCHOOL])\n[GENDER] led the [SCHOOL] team."
    assert redaction.masked["school"] == 3
    # Spans that are too short or already masks change nothing.
    apply_spans(redaction, [("name", "A"), ("name", "[SCHOOL]")])
    assert redaction.text == "[SCHOOL] ([SCHOOL])\n[GENDER] led the [SCHOOL] team."
