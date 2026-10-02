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

from pydantic import BaseModel

from app.ai.client import AIOutputError, OpenAIClient
from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.screening import assess
from app.screening.redact import redact
from tests.ai_eval.harness import CASES_DIR, PARITY_LIMIT, parity_gap, require_ai_eval

CASES = CASES_DIR / assess.PROMPT_VERSION
RESUMES = CASES_DIR / "resume_redaction@v1"


class Recording:
    """Passes calls to the real client and keeps the last assessment answer, so a rejected
    answer can be shown (the cases are synthetic résumés, so printing quotes is fine)."""

    def __init__(self, client: OpenAIClient) -> None:
        self.client = client
        self.model = client.model
        self.last: Any = None

    async def structured[T: BaseModel](self, **kwargs: Any) -> T:
        answer: T = await self.client.structured(**kwargs)
        self.last = answer
        return answer


def unverified(answer: Any, resume_text: str) -> list[str]:
    rows = [(m.criterion, m.evidence_quote) for m in answer.must_haves if m.met]
    rows += [(n.criterion, n.evidence_quote) for n in answer.nice_to_haves if n.found]
    return [f"{c}: {q!r}" for c, q in rows if not assess.quoted(q, resume_text)]


def load(path: Path) -> dict[str, Any]:
    case: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return case


async def screen_all(cases: list[tuple[str, dict[str, Any]]]) -> dict[str, dict[str, float]]:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        client = Recording(OpenAIClient(settings, create_sessionmaker(engine)))
        results: dict[str, dict[str, float]] = {}
        for name, case in cases:
            resume = load(RESUMES / f"{case['resume_case']}.json")["variables"]
            redacted = await redact(
                client, resume["resume_text"], known_names=[resume["full_name"]]
            )
            criteria = assess.Criteria(**case["pipeline"])
            try:
                answer = await assess.assess(client, criteria, redacted.text)
            except AIOutputError as error:
                bad = unverified(client.last, redacted.text) if client.last else []
                raise AssertionError(f"{name}: answer unusable; quotes not found: {bad}") from error
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
