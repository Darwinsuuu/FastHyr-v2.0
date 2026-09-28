# BILL-003: Billing & invoices page

| Field | Value |
|---|---|
| Epic | BILL — Billing & credits |
| Milestone | M6 Billing & analytics |
| Status | Backlog |
| Size | M |
| Depends on | [BILL-001](../BILL/BILL-001-stripe-foundation-and-webhooks.md), [BILL-002](../BILL/BILL-002-credit-ledger-service.md), [DASH-001](../DASH/DASH-001-app-shell.md) |
| Requirements | FR-BILL-05, FR-BILL-09, FR-BILL-10 |
| Gap areas | — |
| Design | Frame BillingInvoices + A-06 |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins see their plan, credits, payment method, billing details and invoices in one place.

## Scope
**In:**
- Plan card (incl. trial state A-06)
- Credits card + expiry table
- Payment method summary + Customer Portal link
- Billing details edit (synced to Stripe)
- Invoices table, detail modal, PDF

**Out:**
- —

## Acceptance criteria
- [ ] Failed payment state with Pay now
- [ ] Admin only
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
