# ADR-020: Every page is responsive and built mobile first

- **Status:** Accepted
- **Date:** 2026-09-29
- **Deciders:** Darwin Labiste (product owner)
- **Replaces:** the earlier NFR-07 wording (TA app desktop-only at ≥ 1024 px)

## Context
The canvas frames are drawn at 1440 px. Candidates often apply and interview from phones, and TA users check candidates on the go.

## Decision
- **Every page** — marketing, candidate and the TA app — is responsive from a 360 px phone to large desktops.
- We build **mobile first**: base styles target phones; `sm`/`md`/`lg`/`xl`/`2xl` breakpoints (Tailwind defaults) add larger layouts.
- Desktop frames define the large-screen end state; `design/RESPONSIVE.md` defines how each pattern adapts (tables → cards, sidebar → drawer, dialogs → full-screen sheets, wizard stepper → compact header, sticky bottom action bars).

## Consequences
- Each UI task includes its mobile layout; reviewers check 360, 768, 1024 and 1440 px (Definition of Done).
- Some dense TA views (tables, charts, email editor) need extra mobile work; it's part of each task, not a later phase.
