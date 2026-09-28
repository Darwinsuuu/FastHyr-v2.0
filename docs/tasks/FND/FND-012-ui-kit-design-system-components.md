# FND-012: UI kit (design-system components)

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | In review |
| Size | L |
| Depends on | [FND-005](../FND/FND-005-web-skeleton-hosts-tokens-fonts-auth-session-api-c.md) |
| Requirements | NFR-06 |
| Gap areas | — |
| Design | All frames |
| Docs to read | [`design/DESIGN_SYSTEM.md §4`](../../design/DESIGN_SYSTEM.md), [`design/VOICE_AND_TONE.md`](../../design/VOICE_AND_TONE.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
The shared component library exists so screens are assembled from tokens and components, not inline styles.

## Scope
**In:**
- Components listed in DESIGN_SYSTEM.md §4 incl. Button (side/variant/size), form controls, SegmentedControl, Tabs, Table + Pagination, Dialogs (confirm, type-to-confirm), Menu, Tooltip, Badge/StatusPill, Signal, Stepper, JobProgressDialog, EmptyState, Skeleton, Toast, Avatar
- Chart primitives in `components/charts`
- A `/dev/ui` gallery page (local and development only)

**Out:**
- Feature-specific composites

## Acceptance criteria
- [x] Every component keyboard-accessible with visible focus
- [x] Both themes pass contrast
- [x] Gallery shows all variants
- [x] Mobile variants built in: dialogs become full-screen sheets, menus become bottom sheets, tables have a card-list mode, touch targets ≥ 44 px (design/RESPONSIVE.md)
- [x] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [x] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Match paddings/radii from frames; map hex to tokens

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Functional: type-to-confirm dialog only enables on the exact phrase; pagination changes page

## Implementation plan
Approved by the owner on 2026-09-28. Shipped as two PRs so each review stays readable:
- **Part 1** (`feature/ui-kit-core`): actions, form controls, overlays, feedback, identity and status, and the `/dev/ui` gallery.
- **Part 2** (`feature/ui-kit-data`): `Table` with `Pagination` (card list on phones), `Signal`, `ScoreBar`, `WeightedCalc`, `InsightCard`, `QuestionPrompt`, `Stepper`, and the SVG chart primitives in `components/charts`.

Building blocks: Radix primitives for anything that needs focus trapping, keyboard support or positioning (Dialog, DropdownMenu, Popover, Tooltip, Tabs, Toast, Checkbox, Switch, Slider, Select), styled only with token classes; Phosphor icons (Regular, 20 px); `cn()` (`clsx` + `tailwind-merge`); hand-built SVG charts with no chart library. Paddings, radii and copy come from the canvas frames, with hex mapped to tokens.

Phone behaviour (RESPONSIVE.md): dialogs are full-screen sheets with sticky footer buttons, menus are bottom sheets, tabs scroll sideways, tooltips open on tap and focus, touch targets are at least 44 px.

Checks: keyboard and visible focus; a contrast script (`scripts/check-contrast.mjs`, run by lint) for every token pair the kit uses, in Paper and Night; the gallery in Chromium at 360, 768, 1024 and 1440 px. Unit tests after the hand checks: type-to-confirm enables only on the exact phrase, `Field` wiring, `NumberStepper` min and max (part 1); pagination (part 2).

## Log
- 2026-09-28: plan approved; part 1 on `feature/ui-kit-core`, PR #7.
- Part 1 built: `Button`/`IconButton`, `Field`, `Input`, `Textarea`, `SearchInput`, `Select`, `Checkbox`, `Toggle`, `Slider`, `NumberStepper`, `ChipInput`, `PhoneInput`, `FileDrop`, `SegmentedControl`, `Dialog`, `ConfirmDialog`, `TypeToConfirmDialog`, `Menu`, `Popover`, `Tooltip`, `Tabs`, `Toast` (`ToastProvider` in the TA layout), `Skeleton`, `EmptyState`, `JobProgressDialog`, `Avatar`, `WorkspaceAvatar`, `Badge`, `PipelineStatusPill`, `StagePill`, and `TurnMark` (`components/brand/`).
- Gallery at `app.fasthyr.localhost:3000/dev/ui`, gated by the new `NEXT_PUBLIC_APP_ENV` (shown for `local` and `development`, 404 for `qa` and `production`). It sits on the app host, so it needs a sign-in.
- Deviations: destructive primary buttons fill with `signal-gap` (the frames' `#B03E26`), so DESIGN_SYSTEM.md §5 no longer says `persimmon-ink`. Avatar initials on `sage` use `ink` rather than `evergreen`, because evergreen on sage is 3.6:1 in Night. Status pills never use red: `signal-gap` is evidence, not a verdict, so "Didn't pass" and "Not moving forward" are quiet outlined pills. The token `radius-lg` (24 px) replaces Tailwind's `rounded-lg`, so small corners use explicit 8 or 10 px.
- Component copy (close, cancel, file errors, status labels) is in `messages/en.json` under `ui` and `status`.
- Verified in Chromium against the local stack: no horizontal scroll at 360, 768, 1024 and 1440 px; Paper and Night; dialog as a full-screen sheet and menu as a bottom sheet at 360 px, centred dialog and dropdown at 1024 px; type-to-confirm stays disabled until "I understand"; tooltip opens on tap; job progress polls and closes on success.
- Tests: `components/ui/dialog.test.tsx`, `field.test.tsx`, `number-stepper.test.tsx`, `helpers.test.ts`, `scripts/contrast.test.ts`.
- Part 2 on `feature/ui-kit-data`: `Table` (card list below `md`), `Pagination`, `Signal`/`SignalCounts`, `ScoreBar`, `WeightedCalc`, `InsightCard`, `QuestionPrompt`, `Stepper` (vertical and horizontal, compact on phones), and `components/charts`: `FlowBand`, `BarChart`, `HorizontalBars`, `SplitBar`, `RadarChart`, `LineChart`. Specs came from the PipelinesV2, ManageMembers, CandidateProfile, Overview, PipelineView, NewPipeline, Demo and CreditUsage frames.
- New colour tokens `chart-2`, `chart-3`, `chart-muted` and `chart-amber` in `tokens.json`. The frames use these four greens and ambers for chart series, and no token covered them. Their Night values are new, picked to read on the Night surfaces.
- Charts are HTML bars or SVG with no library. Each one hides the visual from screen readers and renders a table of the same data instead. Bars show their value on hover or tap where the frames don't print it. SVG text is larger below `md` because the chart is drawn smaller there.
- Verified in Chromium: no sideways scroll at 360, 768, 1024 and 1440 px; Paper and Night; the table switches to cards on phones; pagination moves and clamps; `next build` succeeds.
- Tests: `lib/pagination.test.ts`, `components/ui/pagination.test.tsx`, `components/ui/score.test.ts`.
