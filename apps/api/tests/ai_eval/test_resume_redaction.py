"""`resume_redaction@v1` against the real model (SCREEN-001, BIAS_FAIRNESS.md §3): with the
rules and the model together, every personal detail in `must_remove` is gone, the evidence in
`must_keep` stays, and each counterfactual pair redacts to the same text.

    AI_EVAL=1 OPENAI_API_KEY=… OPENAI_TEXT_MODEL=… uv run pytest tests/ai_eval -k redaction

`fake_spans` in each case is what `tests/unit/test_resume_redaction.py` answers in place of the
model; this test ignores it.
"""

import asyncio
import difflib
import json
from pathlib import Path
from typing import Any

from app.ai.client import OpenAIClient
from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.screening.redact import PROMPT, redact
from tests.ai_eval.harness import CASES_DIR, require_ai_eval

CASES = CASES_DIR / f"{PROMPT[0]}@v{PROMPT[1]}"


def load(path: Path) -> dict[str, Any]:
    case: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return case


async def redact_all(cases: list[tuple[str, dict[str, Any]]]) -> dict[str, str]:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        client = OpenAIClient(settings, create_sessionmaker(engine))
        texts = {}
        for name, case in cases:
            variables = case["variables"]
            redaction = await redact(
                client, variables["resume_text"], known_names=[variables["full_name"]]
            )
            texts[name] = redaction.text
        return texts
    finally:
        await engine.dispose()


def test_resume_redaction_cases() -> None:
    require_ai_eval()
    cases = [(path.stem, load(path)) for path in sorted(CASES.glob("*.json"))]
    texts = asyncio.run(redact_all(cases))

    misses = []
    pairs: dict[str, list[str]] = {}
    for name, case in cases:
        text = texts[name]
        misses += [f"{name}: kept {d!r}" for d in case["must_remove"] if d.lower() in text.lower()]
        misses += [f"{name}: lost {e!r}" for e in case["must_keep"] if e not in text]
        pairs.setdefault(case["pair"], []).append(name)
    for pair, names in pairs.items():
        first = texts[names[0]]
        for other in names[1:]:
            if texts[other] != first:
                diff = "\n".join(
                    difflib.unified_diff(
                        first.splitlines(), texts[other].splitlines(), lineterm="", n=0
                    )
                )
                misses.append(f"{pair}: {names[0]} and {other} differ\n{diff}")
    assert not misses, "\n".join(misses)
