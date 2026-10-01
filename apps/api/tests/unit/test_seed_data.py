"""The Acme Talent sample data (scripts/seed.py) stays possible and matches the design."""

import importlib.util
from pathlib import Path
from types import ModuleType

SEED_PATH = Path(__file__).resolve().parents[2] / "scripts" / "seed.py"


def load_seed() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed", SEED_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_pipeline_status_appears_and_credits_fit_the_reserve() -> None:
    seed = load_seed()
    statuses = {p.status for p in seed.PIPELINES}
    assert statuses == {
        "draft",
        "scheduled",
        "live",
        "paused",
        "paused_no_credits",
        "closed",
        "cancelled",
    }
    for p in seed.PIPELINES:
        assert 0 <= p.used_this_month <= p.used <= p.reserve, p.title
        if p.status in {"draft", "scheduled"}:
            assert p.used == 0, p.title
        if p.status == "paused_no_credits":
            assert p.used == p.reserve, p.title
        else:
            assert p.used < p.reserve or p.status in {"closed", "cancelled"} or not p.reserve


def test_sample_departments_and_members_line_up() -> None:
    seed = load_seed()
    names = {name for name, _, _ in seed.DEPARTMENTS}
    assert all(p.department is None or p.department in names for p in seed.PIPELINES)
    assert all(set(u.departments) <= names for u in seed.USERS)
    assert [u.is_owner for u in seed.USERS].count(True) == 1


def test_plan_has_110_left_as_in_the_credit_usage_frame() -> None:
    seed = load_seed()
    this_month = sum(p.used_this_month for p in seed.PIPELINES)
    assert seed.PLAN_CREDITS - this_month == 110
