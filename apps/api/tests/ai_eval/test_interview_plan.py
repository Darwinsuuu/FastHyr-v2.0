"""`interview_plan@v1` against the real model (INTV-001, AI_PIPELINE.md §7): each golden résumé is
redacted, assessed and planned exactly as the worker does, and the plan passes every check
(`app/interview/plan.py`: order, coverage of every skill to probe, verbatim résumé quotes, no
personal detail) with its topic and quote counts in the case's ranges.

    AI_EVAL=1 OPENAI_API_KEY=… OPENAI_TEXT_MODEL=… uv run pytest tests/ai_eval -k plan

Each case names a `resume_assessment@v1` case (`assessment_case`) for the résumé and pipeline,
and adds the pipeline's interview settings.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.ai.client import AIOutputError, OpenAIClient
from app.ai.schemas.interview_plan import PlanAnswer
from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.interview import plan as planning
from app.screening import assess
from app.screening.redact import redact
from tests.ai_eval.harness import CASES_DIR, require_ai_eval

CASES = CASES_DIR / planning.PROMPT_VERSION
ASSESSMENTS = CASES_DIR / assess.PROMPT_VERSION
RESUMES = CASES_DIR / "resume_redaction@v1"


class Recording:
    """Passes calls to the real client and keeps the last plan, so a rejected plan's problems
    can be shown (the cases are synthetic résumés, so printing them is fine)."""

    def __init__(self, client: OpenAIClient) -> None:
        self.client = client
        self.model = client.model
        self.last: Any = None

    async def structured[T: BaseModel](self, **kwargs: Any) -> T:
        answer: T = await self.client.structured(**kwargs)
        self.last = answer
        return answer


def load(path: Path) -> dict[str, Any]:
    case: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return case


async def plan_all(cases: list[tuple[str, dict[str, Any]]]) -> dict[str, dict[str, float]]:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        client = Recording(OpenAIClient(settings, create_sessionmaker(engine)))
        results: dict[str, dict[str, float]] = {}
        for name, case in cases:
            screen = load(ASSESSMENTS / f"{case['assessment_case']}.json")
            resume = load(RESUMES / f"{screen['resume_case']}.json")["variables"]
            redacted = await redact(
                client, resume["resume_text"], known_names=[resume["full_name"]]
            )
            criteria = assess.Criteria(**screen["pipeline"])
            answer = await assess.assess(client, criteria, redacted.text)
            pipeline = screen["pipeline"]
            context = planning.Context(
                job_title=pipeline["job_title"],
                job_description=pipeline["job_description"],
                seniority=pipeline["seniority"],
                tone=case["tone"],
                interview_format=case["interview_format"],
                skills_to_probe=case["skills_to_probe"],
                must_haves=pipeline["must_haves"],
                open_to=pipeline["open_to"],
                company_about=case["company_about"],
                resume_text=redacted.text,
                screening_claims=[claim.model_dump() for claim in answer.claims],
            )
            try:
                plan = await planning.generate(client, context, candidate_name=resume["full_name"])
            except AIOutputError as error:
                issues: list[str] = []
                if isinstance(client.last, PlanAnswer):
                    stored, issues = planning.resolve(client.last, context)
                    issues += planning.problems(stored, context, resume["full_name"])
                raise AssertionError(f"{name}: plan unusable: {issues}") from error
            results[name] = {
                "topics": len(plan.topics),
                "resume_quotes": sum(
                    1 for topic in plan.topics for seed in topic.seeds if seed.resume_quote
                ),
            }
        return results
    finally:
        await engine.dispose()


def test_interview_plan_cases() -> None:
    require_ai_eval()
    cases = [(path.stem, load(path)) for path in sorted(CASES.glob("*.json"))]
    results = asyncio.run(plan_all(cases))

    misses = []
    for name, case in cases:
        for key, (low, high) in case["expect"].items():
            value = results[name][key]
            if not low <= value <= high:
                misses.append(f"{name}: {key} = {value}, expected {low} to {high}")
    assert not misses, "\n".join(misses)
