# BILL-005: Buy extra credits

| Field | Value |
|---|---|
| Epic | BILL — Billing & credits |
| Milestone | M6 Billing & analytics |
| Status | Backlog |
| Size | S |
| Depends on | [BILL-003](../BILL/BILL-003-billing-invoices-page.md) |
| Requirements | FR-BILL-07 |
| Gap areas | — |
| Design | Frame BillingInvoices (buy credits) |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins buy credit packs with their saved card and see them immediately.

## Scope
**In:**
- Pack picker dialog
- PaymentIntent with 3-D Secure via Stripe.js
- Grant on payment success; done state with receipt number

**Out:**
- —

## Acceptance criteria
- [ ] Idempotent purchase
- [ ] No card → guided to add one
- [ ] Built mobile first and checked at 360, 768, 1024 and 1440 px ([`design/RESPONSIVE.md`](../../design/RESPONSIVE.md))
- [ ] [Definition of Done](../../process/DEFINITION_OF_DONE.md) satisfied

## Notes and edge cases
- —

## Test plan
_(Important functional tests only — write them after the feature works; see [`process/TESTING_STRATEGY.md`](../../process/TESTING_STRATEGY.md).)_
- Important functional tests only, written after the feature is tested by hand (process/TESTING_STRATEGY.md)
- Tenancy test for any new endpoint

## Implementation plan
_(Filled in by the implementer before coding; approved by the product owner.)_

## Log
_(Branch name, decisions, deviations, PR links, review files.)_
