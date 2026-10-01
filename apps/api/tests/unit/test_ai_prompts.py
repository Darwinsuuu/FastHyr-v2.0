"""FND-013: prompts are versioned files with System and User sections, and a missing
placeholder is an error instead of a half-filled prompt."""

from pathlib import Path

import pytest

from app.ai.prompts import PromptError, load_prompt

PROMPTS = Path(__file__).parent.parent / "ai_prompts"


def test_prompt_renders_with_its_version_tag() -> None:
    prompt = load_prompt("example", 1, PROMPTS)

    rendered = prompt.render({"company": "Acme Talent", "job_title": "Backend engineer"})

    assert rendered.version == "example@v1"
    assert rendered.system == "You summarise a job title for Acme Talent. Reply in JSON."
    assert rendered.user == "Job title: Backend engineer"


def test_missing_placeholder_is_an_error() -> None:
    prompt = load_prompt("example", 1, PROMPTS)

    with pytest.raises(PromptError):
        prompt.render({"company": "Acme Talent"})


def test_unknown_version_is_an_error() -> None:
    with pytest.raises(PromptError):
        load_prompt("example", 2, PROMPTS)


def test_prompt_needs_both_sections(tmp_path: Path) -> None:
    (tmp_path / "broken@v1.md").write_text("# System\nOnly a system part.\n")

    with pytest.raises(PromptError):
        load_prompt("broken", 1, tmp_path)
