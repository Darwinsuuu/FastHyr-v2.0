# Development workflow

For the MVP, **Claude does the planning, building and reviewing** (ADR-018): Claude in claude.ai (the FastHyr project) for product planning, and Claude Code in this repo for implementation and review. The product owner approves scope and merges.

## The loop (one task at a time)

```
 1. Pick       2. Plan            3. Build           4. Test by hand    5. Unit tests       6. Review            7. Merge
 BOARD.md ──▶  task file "Plan" ─▶ feature/* branch ─▶ until the AC  ──▶  important         ─▶ review file     ──▶ into develop,
 (Ready)       section filled,     from develop,      pass               functional tests    reviews/<ID>-r1.md   BOARD.md → Done
               owner approves      few commits                           only, PR opened     fixes → r2 …
```

1. **Pick** the next task whose dependencies are Done from [`../tasks/BOARD.md`](../tasks/BOARD.md). Set it to **In progress**.
2. **Plan** (Claude Code, plan mode): read `AGENTS.md`, the task file and every doc it links. Write the "Implementation plan" section in the task file (files to touch, API changes, migrations, tests, open questions). If the plan changes a decision, stop and write/propose an ADR. The product owner approves the plan (or it's small enough to proceed — tasks marked `size: S`).
3. **Build** on a `feature/<short-name>` branch created **from `develop` only** — pull the latest `develop` first; never branch from `release` or `master`. One commit, or a few when the work has clearly separate steps, in the format `feature(<short-name>): …` ([`GIT_CONVENTIONS.md`](GIT_CONVENTIONS.md)). Update docs in the same PR when behaviour or contracts change.
4. **Test by hand** until the acceptance criteria pass; compare UI with the canvas frame.
5. **Write unit tests last**, only for the important functional behaviour ([`TESTING_STRATEGY.md`](TESTING_STRATEGY.md)). Self-check against [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md), run `make lint test`, open the PR into `develop` with the standard description ([`.github/pull_request_template.md`](../../.github/pull_request_template.md)).
6. **Review:** a fresh Claude session (no memory of the build) reviews the PR against the task's acceptance criteria, the DoD, G1–G9 and the security/tenancy rules, and writes `docs/reviews/<TASK-ID>-r<N>.md` from [`templates/REVIEW_TEMPLATE.md`](templates/REVIEW_TEMPLATE.md). Blocking findings go back to step 3; the next round is `r2`.
7. **Merge:** product owner merges the PR into `develop` (merge commit, no squash). Set the task to **Done** in `BOARD.md` with the PR link.

Releases are separate from tasks: when a set of Done tasks is ready, `develop` is merged into `release` for QA, then `release` into `master` for production ([`GIT_CONVENTIONS.md`](GIT_CONVENTIONS.md) §4).

## Rules for Claude sessions
- Start every session by reading `AGENTS.md`; then only the docs the task links (don't load everything).
- Never work without a task file. Small unplanned fixes get a task file too (`size: S`), or go in the current task's scope only if directly related.
- Don't change `docs/decisions/` except by adding a new ADR (proposed) — the owner accepts it.
- If the design, docs and code disagree: ADRs > `product/REQUIREMENTS.md` > `design/SCREEN_SPECS.md` > canvas frame > other docs. Record the conflict in the task's "Notes".
- Ask the product owner **one question at a time** when blocked on a product decision.
- Keep the task file current: tick acceptance criteria as they pass; record deviations.

## Statuses (BOARD.md)
`Backlog` → `Ready` (dependencies done, spec complete) → `In progress` → `In review` → `Done` (merged into `develop`). `Blocked` with a reason when waiting on a decision or dependency.
