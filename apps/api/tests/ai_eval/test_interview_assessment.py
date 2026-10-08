"""`interview_assessment@v1` against the real model (ASMT-001, AI_PIPELINE.md §4 and §7): each
golden transcript is turned into masked, numbered turns and scored exactly as the scoring job
does; the overall score and decision land in the case's ranges, every criterion keeps 2 to 4
pieces of checked evidence, and counterfactual pairs score within ±5 on communication: the same
answers with different personal details (name, gender, age, family, origin), and the same
answers in native and non-native phrasing.

    AI_EVAL=1 OPENAI_API_KEY=… OPENAI_TEXT_MODEL=… uv run pytest tests/ai_eval -k interview

Each case gives the context (`app.interview.assessment.Context`), the candidate's name for
masking, and the transcript as `[start s, end s, speaker, text, topic]` lines.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from app.ai.client import AIOutputError, OpenAIClient
from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.interview import assessment
from app.screening.redact import redact_rules
from tests.ai_eval.harness import CASES_DIR, parity_gap, require_ai_eval

CASES = CASES_DIR / assessment.PROMPT_VERSION
RUBRIC = assessment.Rubric(
    weight_technical=50, weight_communication=30, weight_culture=20, pass_mark=70
)
# The acceptance criterion for transcript counterfactuals (ASMT-001).
COMMUNICATION_PARITY = 5


def load(path: Path) -> dict[str, Any]:
    case: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return case


def turns_of(case: dict[str, Any]) -> list[assessment.Turn]:
    lines = [
        assessment.Line(round(start * 1000), round(end * 1000), speaker, text, topic)
        for start, end, speaker, text, topic in case["lines"]
    ]
    known = [case["candidate_name"]]
    return assessment.turns(lines, lambda text: redact_rules(text, known).text)


async def score_all(cases: list[tuple[str, dict[str, Any]]]) -> dict[str, dict[str, float]]:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        client = OpenAIClient(settings, create_sessionmaker(engine))
        results: dict[str, dict[str, float]] = {}
        for name, case in cases:
            context = assessment.Context(**case["context"])
            found = turns_of(case)
            try:
                answer = await assessment.assess(client, context, found)
            except AIOutputError as error:
                raise AssertionError(f"{name}: answer unusable twice") from error
            decision = assessment.decide(answer, context, found, RUBRIC)
            evidence = [len(row["evidence"]) for row in decision.criteria.values()]
            results[name] = {
                "overall_score": decision.overall_score,
                "passed": int(decision.passed),
                "communication": decision.criteria["communication"]["score"],
                "evidence_min": min(evidence),
            }
        return results
    finally:
        await engine.dispose()


def test_interview_assessment_cases() -> None:
    require_ai_eval()
    cases = [(path.stem, load(path)) for path in sorted(CASES.glob("*.json"))]
    results = asyncio.run(score_all(cases))

    misses = []
    pairs: dict[str, dict[str, float]] = {}
    for name, case in cases:
        seen = " ".join(turn.text for turn in turns_of(case))
        if any(part in seen for part in case["candidate_name"].split()):
            misses.append(f"{name}: the candidate's name reached the model")
        for key, (low, high) in case["expect"].items():
            value = results[name][key]
            if not low <= value <= high:
                misses.append(f"{name}: {key} = {value}, expected {low} to {high}")
        if case.get("pair"):
            pairs.setdefault(case["pair"], {})[name] = results[name]["communication"]
    for pair, scores in pairs.items():
        if parity_gap(scores) > COMMUNICATION_PARITY:
            misses.append(f"{pair}: communication {scores} differ by more than ±5")
    print(json.dumps(results, indent=2))  # the owner pastes this back
    assert not misses, "\n".join(misses)
