# BILL-004: Subscribe and change plan

| Field | Value |
|---|---|
| Epic | BILL — Billing & credits |
| Milestone | M6 Billing & analytics |
| Status | Backlog |
| Size | M |
| Depends on | [BILL-003](../BILL/BILL-003-billing-invoices-page.md) |
| Requirements | FR-BILL-06 |
| Gap areas | — |
| Design | Frame BillingInvoices (change plan) + A-06 |
| Docs to read | — |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Admins start a subscription and upgrade or downgrade with the rules shown in the design.

## Scope
**In:**
- Checkout for first subscription
- Upgrade (prorated now + plan credit top-up)
- Downgrade at renewal (schedule) with 'Switches to…' label
- Plan credits granted on invoice.paid

**Out:**
- —

## Acceptance criteria
- [ ] Upgrade raises this month's plan credits
- [ ] Downgrade keeps current plan until renewal
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
