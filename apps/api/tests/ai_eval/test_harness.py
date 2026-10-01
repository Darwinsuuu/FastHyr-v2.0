"""Checks the evaluation helpers themselves (no model calls). Prompt tasks add their own
`test_<prompt>.py` here that call `require_ai_eval()` first."""

from pydantic import BaseModel

from tests.ai_eval.harness import EvalCase, out_of_range, parity_gap


class Answer(BaseModel):
    score: int
    must_haves: list[dict[str, bool]]


def test_ranges_and_dotted_paths() -> None:
    answer = Answer(score=72, must_haves=[{"met": True}])
    case = EvalCase("c1", {}, {"score": (60, 80), "must_haves.0.met": (1, 1)}, None)

    assert out_of_range(answer, case) == []
    strict = EvalCase("c2", {}, {"score": (80, 100)}, None)
    assert out_of_range(answer, strict) == ["c2: score = 72, expected 80 to 100"]


def test_parity_gap_is_the_spread_within_a_pair() -> None:
    assert parity_gap({"maria": 71, "mark": 74}) == 3
    assert parity_gap({}) == 0
