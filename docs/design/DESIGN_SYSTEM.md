# Design system (implementation guide)

The brand book lives in the Claude Design artifact (DESIGN_SOURCES.md). This file tells engineers how to implement it in `apps/web`. Tokens: [`tokens.json`](tokens.json).

## 1. The idea: both sides of the table
| | Hiring side (TA, HM, Admin) | Candidate side |
|---|---|---|
| Lead colour | `evergreen` | `persimmon` |
| Feel | calm, well-kept ledger; compact | warm room with good light; spacious |
| Density | `body-sm`, `space-4` card padding, tables | `body`, `space-12` stage padding, one thing per screen |
| Primary button | `<Button side="ta">` | `<Button side="candidate">` — at most one per screen |
| Signature component | `InsightCard` | `QuestionPrompt` |

`persimmon` appears on TA screens only inside the Turn mark and when quoting a candidate; `evergreen` appears on candidate screens only in the mark and header.

## 2. Tokens
Generated into CSS variables (`apps/web/styles/tokens.css`, by `pnpm --filter web tokens` from `tokens.json`; `make lint` fails if it is stale) for two themes: **Paper** (light, default) and **Night** (dark, `[data-theme="dark"]`, or the system setting when no `data-theme` is set). Tailwind v4's theme maps to the variables (`bg-surface`, `text-ink`, `text-ink-muted`, `bg-evergreen`, `text-on-evergreen`, `border-line`, `rounded-md`, `shadow-raised`, `font-display`, `text-body-sm`, …). Full text styles, family included, are `type-*` utilities (`type-question`, `type-label`, `type-heading`…). Spacing uses Tailwind's default 4 px scale, which equals the `space-*` tokens (`p-4` = `space-4` = 16 px). Fonts load through `next/font` (`apps/web/app/fonts.ts`).

| Group | Tokens |
|---|---|
| Surfaces | `surface` (page), `surface-raised` (cards, inputs, interview stage), `surface-sunk` (résumé wells, table stripes, progress tracks) |
| Lines | `line` (dividers), `line-strong` (input/secondary-button borders, ≥3:1) |
| Text | `ink`, `ink-muted` |
| Brand | `evergreen` / `on-evergreen` / `evergreen-soft`; `persimmon` / `on-persimmon` / `persimmon-ink` (persimmon text) / `persimmon-soft`; `marigold` / `on-marigold` (highlighter only); `sage` (illustration only) |
| Signals | `signal-strong` (blue, filled disc), `signal-watch` (amber, half disc), `signal-gap` (red, ring) |
| Focus | `focus` — 2px solid ring, 2px offset on every interactive element |
| Type | families `display` (Fraunces), `sans` (Hanken Grotesk), `mono` (IBM Plex Mono); styles `display-xl` 56/60, `display-lg` 40/46, `question` 24/32 italic, `heading` 24/30 650, `title` 18/26 600, `body` 16/24, `body-sm` 14/20, `label` 12/16 650 uppercase 0.06em, `mono` 13/20 |
| Spacing | `space-1` 4 · `space-2` 8 · `space-3` 12 · `space-4` 16 · `space-6` 24 · `space-8` 32 · `space-12` 48 · `space-16` 64 |
| Radius | `radius-sm` 6 (inputs) · `radius-md` 12 (buttons, cards) · `radius-lg` 24 (candidate stage, sheets) · `radius-pill` (signals, step dots) |
| Shadow | `shadow-raised` (interview stage, popovers only; cards use a `line` border) |

Frame hex → token mapping (frames use inline hex): `#F7F2EA` surface · `#FFFCF7` surface-raised · `#EDE5D8`/`#EFE7DA` surface-sunk · `#DDD3C3` line · `#8A7F70`/`#A89C88`/`#CFC4B2` line-strong (use token) · `#1E2A26` ink · `#5A625D` ink-muted · `#1F4D43` evergreen · `#D5E2D3` evergreen-soft · `#C4471F` persimmon · `#9E3818`/`#A8391A` persimmon-ink · `#F8DCCB` persimmon-soft · `#F2B84B` marigold · `#C9D9C4` sage · `#22668A` signal-strong/focus · `#B03E26` signal-gap/error.

## 3. Rules that are easy to get wrong
- **Scores vs signals (updated by ADR-011):** TA screens show numeric scores with their calculation. Signals label evidence and sub-skills, always glyph + word (never colour alone). Never show scores, signals or flags to candidates. `signal-gap` never means "reject".
- One `display-*` per screen. Fraunces is for headlines, the live question and quoted generated questions (`question` style, italic).
- Quote résumé text verbatim in `mono` on `surface-sunk`; highlight the one phrase a question came from in `marigold`.
- Sentence case everywhere; uppercase only in `label`. No emoji, no exclamation marks in product copy.
- Motion: 200–320 ms ease-out; questions fade up 8 px; nothing bounces; respect `prefers-reduced-motion`.
- Icons: Phosphor Regular, 20 px, 1.5 px stroke, coloured like adjacent text. Icon-only buttons need `aria-label` + tooltip. On candidate screens icons always sit with a word.
- Company logo on candidate screens appears smaller than and after the FastHyr mark: "Acme · interviews with FastHyr". (The Apply page header shows the employer first as designed — that frame is the exception for the careers-page context.)
- The Turn mark: `fasthyr-mark.svg` on light grounds, `fasthyr-mark-reversed.svg` on Night/evergreen; wordmark is live type (Fraunces 600, −0.02em). Loading state "thinking…" alternates the two halves.
- Contrast: all text pairs ≥ 4.5:1 (3:1 at 24 px+), control borders and focus ring ≥ 3:1, in both themes.

## 4. Responsive
All components and screens are mobile first — see [`RESPONSIVE.md`](RESPONSIVE.md) for breakpoints and how each desktop pattern adapts.

## 5. Components (`components/ui`)
Built in FND-012. Every component, variant and state is shown at `/dev/ui` on the app host (local and development only). Overlays and controls use Radix primitives styled with token classes; icons are `@phosphor-icons/react`. Part 1 (core) is built; part 2 (data, signature pieces and charts) is next.

| Component | Notes / variants | File |
|---|---|---|
| `Button` | `variant` primary/secondary/quiet × `side` ta/candidate × `size` sm/md/lg; loading state; destructive (uses `signal-gap` border/text for quiet destructive, filled `signal-gap` for confirm dialogs, as in the frames) | `button.tsx` (`Button`, `IconButton`) |
| `Input`, `Textarea`, `Select`, `Checkbox`, `Toggle` (switch), `Slider` (rubric/pass mark), `NumberStepper` (credits), `ChipInput` (must-haves, skills), `PhoneInput` (country code + number), `FileDrop` (PDF/image), `SearchInput` | label + hint + error message pattern from frames | `field.tsx`, `input.tsx`, `select.tsx`, `checkbox.tsx`, `toggle.tsx`, `slider.tsx`, `number-stepper.tsx`, `chip-input.tsx`, `phone-input.tsx`, `file-drop.tsx` |
| `SegmentedControl` | week/30 days, work setup, tabs-as-pills | `segmented-control.tsx` |
| `Tabs` | underline tabs (pipeline, profile) | `tabs.tsx` |
| `Table` + `Pagination` (+ rows-per-page) | TA density | part 2 |
| `Dialog` / `ConfirmDialog` / `TypeToConfirmDialog` ("I understand") | radius-lg sheets | `dialog.tsx`: full-screen sheet with sticky buttons on phones, centred from `md` |
| `Menu` (row actions), `Popover`, `Tooltip` | Radix | `menu.tsx` (bottom sheet on phones), `popover.tsx`, `tooltip.tsx` (opens on tap and focus too) |
| `Badge` / `StatusPill` | pipeline status, stage, fit | `badge.tsx`, `status-pill.tsx` (`PipelineStatusPill`, `StagePill`) |
| `Signal` | strong/watch/gap glyph + word | part 2 |
| `ScoreBar`, `WeightedCalc` ("How we got to 91") | | part 2 |
| `InsightCard`, `QuestionPrompt` | from the design system | part 2 |
| `Stepper` | wizard (vertical), demo (horizontal) | part 2 |
| `JobProgressDialog` | report/PDF progress pattern | `job-progress-dialog.tsx` |
| `EmptyState`, `Skeleton`, `Toast` | | `empty-state.tsx` (with the Turn, `components/brand/turn-mark.tsx`), `skeleton.tsx`, `toast.tsx` (`useToast`) |
| `Avatar` (initials), `WorkspaceAvatar` | colour pairs from frames | `avatar.tsx` (`Avatar`, `WorkspaceAvatar`) |
| Charts (`components/charts`) | Funnel/flow, stacked weekly bars, histogram with pass-mark line, horizontal bars, radar, line with pass-mark, split bar | part 2 |
