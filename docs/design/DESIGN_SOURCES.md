# Design sources

| Source | Link | What it's for |
|---|---|---|
| **Product design canvas** — "FastHyr — Product Design" (Claude Design) | https://claude.ai/artifact/5K5XeumMMTTgj4f37pzwvW | The MVP screens: 23 interactive frames in 8 sections |
| **FastHyr Design System** (Claude Design) | https://claude.ai/artifact/1zb54CSHVs2p3tV1dTM1mt | Brand book, tokens, components (Button, Signal, InsightCard, QuestionPrompt), logo rules |
| Design tokens (copy in repo) | [`tokens.json`](tokens.json) | Source for `apps/web/styles/tokens.css` |
| Frame-by-frame inventory | [`../_sources/design-canvas-inventory.md`](../_sources/design-canvas-inventory.md) | Text record of every frame, field and state |
| Screens not in the canvas | [`SCREEN_SPECS.md`](SCREEN_SPECS.md) | Text wireframes for new/changed screens |
| Responsive rules | [`RESPONSIVE.md`](RESPONSIVE.md) | Mobile-first breakpoints and how each desktop pattern adapts |

## How to use the canvas when building a screen
1. Find the frame in [`SCREENS.md`](SCREENS.md) (frame file name → route → task).
2. Open the canvas and the frame. Frames are **interactive** (`is_interactive`): click through modals, tabs and states — many states only appear after interaction (e.g. share modal, reject dialog, report progress).
3. With Claude tooling, a frame's source can be read with the Artifact tool: `read` `https://claude.ai/artifact/5K5XeumMMTTgj4f37pzwvW` with `path: "project/<Frame>.dc.html"`. The markup shows exact copy, spacing and colours; the `<script>` block shows sample data and state logic.
4. **Build with tokens and components, not the frame's inline styles.** Frames use inline hex values; map them to tokens (`DESIGN_SYSTEM.md` §2).
5. Frames are desktop (1440 px). Build **mobile first** and adapt using [`RESPONSIVE.md`](RESPONSIVE.md).
6. Sample data in frames (Acme Talent, Bea Garcia, numbers) is illustrative. Real data comes from the API.
7. If a frame conflicts with an ADR, the ADR wins (conflict list at the end of the inventory).

## Keeping design and docs in sync
- New screens are specified in `SCREEN_SPECS.md` first (ADR-018). If they are later drawn in the canvas, link the frame here and mark the spec "Designed".
- Pending canvas updates (for whoever edits the canvas next): add résumé pass bar + nice-to-haves to NewPipeline step 1 (ADR-013); remove "6–10 questions" copy on Candidates page (ADR-012); rename interviewer from "Ava" in CandidateProfile transcript/topics (ADR-018); add Advance action (ADR-017); change Getting started credit copy (ADR-010); remove demo personas/7 tones/languages (ADR-012).
