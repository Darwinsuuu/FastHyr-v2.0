# FastHyr documentation

## Reading order for someone new
1. [`../AGENTS.md`](../AGENTS.md) — the whole project in one page, plus the hard rules.
2. [`product/BRD.md`](product/BRD.md) → [`product/GLOSSARY.md`](product/GLOSSARY.md) → [`product/WORKFLOW.md`](product/WORKFLOW.md).
3. [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md).
4. [`design/SCREENS.md`](design/SCREENS.md) and the design canvas.
5. [`process/DEV_WORKFLOW.md`](process/DEV_WORKFLOW.md) → [`tasks/BOARD.md`](tasks/BOARD.md).

## Folders
| Folder | Contents |
|---|---|
| [`_sources/`](_sources/) | Raw inputs, never edited: Claude project instructions, design-canvas inventory |
| [`product/`](product/) | BRD, personas, glossary, workflow & state machines, gap areas G1–G9, requirements (FR/NFR), user stories, roadmap & open questions |
| [`architecture/`](architecture/) | Overview, stack, frontend, backend, multi-tenancy, database, storage, API, AI pipeline, media, billing, notifications, security, deployment |
| [`compliance/`](compliance/) | AI-in-hiring regulations, privacy & data lifecycle, bias & fairness, fraud & integrity |
| [`design/`](design/) | Design sources, design-system implementation guide, tokens, mobile-first responsive rules, screen inventory, specs for screens not in the canvas, voice & tone |
| [`decisions/`](decisions/) | Architecture & product decision records (ADRs) |
| [`process/`](process/) | Dev workflow, branching & git conventions (commit and PR formats), testing strategy, Definition of Done, templates |
| [`tasks/`](tasks/) | Task board and one file per task, grouped by epic |
| [`reviews/`](reviews/) | Code review records, one per task and round |

## Keeping docs true
- Docs change in the same PR as the behaviour they describe.
- Decisions change only through a new ADR.
- `_sources/` is history; everything else is current.
