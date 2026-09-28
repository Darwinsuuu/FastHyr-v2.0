# ADR-010: One credit is used when a candidate applies

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
Most screens say "1 applicant = 1 credit, used when someone applies". Getting started said "each completed AI interview uses credits".

## Decision
A credit is used **when an application is submitted**, drawn from the pipeline's reserve. Screened-out applicants still use their credit (résumé screening costs money too).

## Consequences
- Getting started copy changes to: "Each applicant uses 1 credit, so top up before applicants start arriving."
- When a pipeline's reserve is used up, it pauses itself ("Paused · out of credits") and its apply page stops accepting applications.
- Applications that fail technically before submission (upload errors) never use a credit. Duplicate applications are blocked, not charged (see `product/REQUIREMENTS.md` FR-APPLY).
