# ADR-004: Stripe for monthly plans, credit packs and trial credits

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
The design bills with monthly plans that include credits, plus one-time extra-credit packs. A new workspace needs a way to try FastHyr before paying.

## Decision
- **Stripe** is the payment processor. One Stripe Customer per workspace.
- **Plans** (Stripe subscription prices, USD, monthly): Starter $99 / 80 credits, Growth $299 / 300 credits, Scale $799 / 1,000 credits.
- **Extra-credit packs** (one-time prices): 100 / $160, 250 / $375, 500 / $700, 1,000 / $1,300. Each pack's credits expire 12 months after purchase.
- **Trial:** every new workspace gets a one-time grant of **20 trial credits** that expire after **30 days** (values are config, not code). No card needed to start.
- Plan credits are granted when a subscription invoice is paid, expire at the end of that billing period, and do not roll over.
- Upgrades apply immediately with proration and raise the current period's plan credits to the new plan's amount; downgrades apply at the next renewal.
- "Manage subscription" and "Update card" open the **Stripe Customer Portal**. Buying a pack uses the saved default card (PaymentIntent, with 3-D Secure handled by Stripe.js).
- FastHyr's own **credit ledger** (in Postgres) is the source of truth for credit balances; Stripe is the source of truth for money and invoices.

## Consequences
- Webhooks (`invoice.paid`, `invoice.payment_failed`, `customer.subscription.*`, `payment_intent.succeeded`) must be idempotent and are the only way credits are granted for payments.
- Invoice PDFs come from Stripe (`invoice_pdf`).
- Tax handling (Stripe Tax) is an open question for launch — see `product/ROADMAP.md`.
