# FND-012: UI kit (design-system components)

| Field | Value |
|---|---|
| Epic | FND — Foundation |
| Milestone | M0 Foundation |
| Status | Backlog |
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
- [ ] Every component keyboard-accessible with visible focus
- [ ] Both themes pass contrast
- [ ] Gallery shows all variants
- [ ] Mobile variants built in: dialogs become full-screen sheets, menus become bottom sheets, tables have a card-list mode, touch targets ≥ 44 px (design/RESPONSIVE.md)
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- Match paddings/radii from frames; map hex to tokens

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Functional: type-to-confirm dialog only enables on the exact phrase; pagination changes page

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
