"""Runs evaluation cases against the real model through `app/ai/` (AI_PIPELINE.md §7)."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.client import OpenAIClient
from app.ai.prompts import Prompt
from app.core.config import get_settings

CASES_DIR = Path(__file__).parent / "cases"
PARITY_LIMIT = 3


def require_ai_eval() -> None:
    """Skips unless AI_EVAL=1 and a key and model are configured."""
    settings = get_settings()
    if os.environ.get("AI_EVAL") != "1" or not settings.openai_api_key:
        pytest.skip("AI evaluation runs only with AI_EVAL=1 and OPENAI_API_KEY")


@dataclass(frozen=True)
class EvalCase:
    name: str
    variables: dict[str, str]
    expect: dict[str, tuple[float, float]]
    pair: str | None


def load_cases(prompt_tag: str) -> list[EvalCase]:
    folder = CASES_DIR / prompt_tag
    cases = []
    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        cases.append(
            EvalCase(
                name=path.stem,
                variables=data["variables"],
                expect={key: (low, high) for key, (low, high) in data.get("expect", {}).items()},
                pair=data.get("pair"),
            )
        )
    return cases


def value_at(answer: BaseModel, dotted: str) -> Any:
    value: Any = answer.model_dump()
    for part in dotted.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def out_of_range(answer: BaseModel, case: EvalCase) -> list[str]:
    """The expectations the answer misses, as readable lines (empty when all pass)."""
    misses = []
    for path, (low, high) in case.expect.items():
        value = value_at(answer, path)
        if not low <= value <= high:
            misses.append(f"{case.name}: {path} = {value}, expected {low} to {high}")
    return misses


def parity_gap(scores: dict[str, float]) -> float:
    """The largest score difference within one counterfactual pair."""
    return max(scores.values()) - min(scores.values()) if scores else 0.0


async def run_case[T: BaseModel](
    sessionmaker: async_sessionmaker[AsyncSession],
    prompt: Prompt,
    schema: type[T],
    case: EvalCase,
) -> T:
    client = OpenAIClient(get_settings(), sessionmaker)
    return await client.structured(
        purpose=f"ai_eval:{prompt.name}",
        prompt=prompt,
        variables=case.variables,
        schema=schema,
        temperature=0,
    )
