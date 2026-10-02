"""`resume_assessment@v1` against the real model (SCREEN-002, AI_PIPELINE.md §7): each golden
résumé is redacted and assessed exactly as the screening job does, the fit score, decision and
must-haves met land in the case's ranges, and counterfactual pairs (the same résumé with a
different name, gender, age, school and address) score within ±3 points.

    AI_EVAL=1 OPENAI_API_KEY=… OPENAI_TEXT_MODEL=… uv run pytest tests/ai_eval -k assessment

Each case names a `resume_redaction@v1` case for its résumé (`resume_case`) and gives the
pipeline it is assessed against.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from app.ai.client import OpenAIClient
from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.screening import assess
from app.screening.redact import redact
from tests.ai_eval.harness import CASES_DIR, PARITY_LIMIT, parity_gap, require_ai_eval

CASES = CASES_DIR / assess.PROMPT_VERSION
RESUMES = CASES_DIR / "resume_redaction@v1"


def load(path: Path) -> dict[str, Any]:
    case: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return case


async def screen_all(cases: list[tuple[str, dict[str, Any]]]) -> dict[str, dict[str, float]]:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        client = OpenAIClient(settings, create_sessionmaker(engine))
        results = {}
        for name, case in cases:
            resume = load(RESUMES / f"{case['resume_case']}.json")["variables"]
            redacted = await redact(
                client, resume["resume_text"], known_names=[resume["full_name"]]
            )
            criteria = assess.Criteria(**case["pipeline"])
            answer = await assess.assess(client, criteria, redacted.text)
            decision = assess.score(answer, criteria)
            results[name] = {
                "score": decision.score,
                "passed": int(decision.passed),
                "must_haves_met": sum(1 for row in decision.must_haves if row["met"]),
            }
        return results
    finally:
        await engine.dispose()


def test_resume_assessment_cases() -> None:
    require_ai_eval()
    cases = [(path.stem, load(path)) for path in sorted(CASES.glob("*.json"))]
    results = asyncio.run(screen_all(cases))

    misses = []
    pairs: dict[str, dict[str, float]] = {}
    for name, case in cases:
        for key, (low, high) in case["expect"].items():
            value = results[name][key]
            if not low <= value <= high:
                misses.append(f"{name}: {key} = {value}, expected {low} to {high}")
        if case.get("pair"):
            pairs.setdefault(case["pair"], {})[name] = results[name]["score"]
    for pair, scores in pairs.items():
        if parity_gap(scores) > PARITY_LIMIT:
            misses.append(f"{pair}: scores {scores} differ by more than {PARITY_LIMIT}")
    assert not misses, "\n".join(misses)
