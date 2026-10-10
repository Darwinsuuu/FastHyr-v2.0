"""`integrity_read_aloud@v1` against the real model (ASMT-002, AI_PIPELINE.md §5 and §7): each
golden transcript goes through the same steps as the integrity job (answers, the session's
baseline, the read-aloud windows, the masked judgement) and the number of read-aloud flags lands
in the case's range. Pairs (the same story in native and non-native phrasing) must get the same
number of flags: phrasing is never a reason to flag.

    AI_EVAL=1 OPENAI_API_KEY=… OPENAI_TEXT_MODEL=… \
        uv run pytest tests/ai_eval/test_integrity_read_aloud.py

Each case gives the candidate's name for masking and the transcript as
`[start s, end s, speaker, text]` lines.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from app.ai.client import AIOutputError, OpenAIClient
from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.integrity import read_aloud, speech
from app.interview.assessment import Line
from app.screening.redact import redact_rules
from tests.ai_eval.harness import CASES_DIR, require_ai_eval

CASES = CASES_DIR / read_aloud.PROMPT_VERSION


def load(path: Path) -> dict[str, Any]:
    case: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return case


async def judge_all(cases: list[tuple[str, dict[str, Any]]]) -> dict[str, int]:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        client = OpenAIClient(settings, create_sessionmaker(engine))
        results: dict[str, int] = {}
        for name, case in cases:
            lines = [
                Line(round(start * 1000), round(end * 1000), speaker, text, None)
                for start, end, speaker, text in case["lines"]
            ]
            answers = speech.answers(lines)
            windows = speech.read_aloud_windows(answers)
            base = speech.baseline([answer for answer in answers if answer.words >= 5])
            assert windows and base, f"{name}: no read-aloud window to judge"
            known = [case["candidate_name"]]
            try:
                found = await read_aloud.judge(
                    client,
                    windows,
                    base,
                    mask=lambda text, known=known: redact_rules(text, known).text,
                )
            except AIOutputError as error:
                raise AssertionError(f"{name}: answer unusable twice") from error
            results[name] = len(found)
        return results
    finally:
        await engine.dispose()


def test_integrity_read_aloud_cases() -> None:
    require_ai_eval()
    cases = [(path.stem, load(path)) for path in sorted(CASES.glob("*.json"))]
    results = asyncio.run(judge_all(cases))

    misses = []
    pairs: dict[str, list[int]] = {}
    for name, case in cases:
        low, high = case["expect"]["flags"]
        if not low <= results[name] <= high:
            misses.append(f"{name}: {results[name]} read-aloud flags, expected {low} to {high}")
        if case.get("pair"):
            pairs.setdefault(case["pair"], []).append(results[name])
    for pair, counts in pairs.items():
        if len(set(counts)) > 1:
            misses.append(f"pair {pair}: flags differ by phrasing {counts}")
    print(json.dumps(results, indent=2))
    assert not misses, "\n".join(misses)
