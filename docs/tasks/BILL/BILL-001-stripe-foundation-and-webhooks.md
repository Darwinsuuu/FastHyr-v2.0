# BILL-001: Stripe foundation and webhooks

| Field | Value |
|---|---|
| Epic | BILL — Billing & credits |
| Milestone | M2 Pipelines |
| Status | Ready |
| Size | M |
| Depends on | [FND-004](../FND/FND-004-api-skeleton-auth-request-context-permissions-erro.md), [FND-008](../FND/FND-008-background-worker-and-job-framework.md) |
| Requirements | FR-BILL-01 |
| Gap areas | — |
| Design | — |
| Docs to read | [`architecture/BILLING.md §1, §5–6`](../../architecture/BILLING.md), [`decisions/ADR-004-stripe-plans-and-credits.md`](../../decisions/ADR-004-stripe-plans-and-credits.md) |

Always read [`AGENTS.md`](../../../AGENTS.md) first. Requirement IDs are in [`product/REQUIREMENTS.md`](../../product/REQUIREMENTS.md); gap areas in [`product/CONSIDERATIONS.md`](../../product/CONSIDERATIONS.md).

## Goal
Stripe products, customers and webhooks are wired so billing features can build on them.

## Scope
**In:**
- Catalogue config + `stripe_bootstrap.py`
- Customer creation per workspace
- `/webhooks/stripe` with signature check → `stripe_events` → worker
- `subscriptions`, `stripe_invoices`, `billing_details` migrations
- Stripe CLI forwarding in local dev

**Out:**
- —

## Acceptance criteria
- [ ] Webhook processing idempotent
- [ ] Test-mode events update tables
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
