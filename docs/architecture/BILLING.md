# Billing and credits

Decisions: ADR-004 (Stripe, plans, packs, trial) and ADR-010 (1 credit per applicant, on apply).
**Stripe owns money; FastHyr's credit ledger owns credits.**

## 1. Catalogue (config: `app/core/billing_catalog.py`, mirrored in Stripe)
| Item | Stripe object | Credits | Price (USD) | Credit expiry |
|---|---|---|---|---|
| Starter | recurring price, monthly | 80 / month | $99 | end of billing period |
| Growth | recurring price, monthly | 300 / month | $299 | end of billing period |
| Scale | recurring price, monthly | 1,000 / month | $799 | end of billing period |
| Pack 100 / 250 / 500 / 1,000 | one-time prices | 100 / 250 / 500 / 1,000 | $160 / $375 / $700 / $1,300 | 12 months after purchase |
| Trial | — (no Stripe object) | 20 | free | 30 days after workspace creation |

Stripe price IDs are env/config per environment. Prices are shown from config, not hard-coded in the UI.

## 2. Balances
- **Balance** = Σ `credit_batches.remaining` where `expires_at > now()`.
- **Reserved (open)** = Σ over pipelines in `scheduled|live|paused|paused_no_credits` of `credits_reserved − credits_used`.
- **Free** = Balance − Reserved (can be negative after expiries; see §4).

## 3. Operations (only `services/credits.py`; each in one DB transaction, `SELECT … FOR UPDATE` on the workspace's batches)
| Operation | Effect | Ledger kind |
|---|---|---|
| Grant trial | new `trial` batch 20, expires +30 d | `grant_trial` |
| Grant plan credits (on `invoice.paid` for a subscription period) | new `plan` batch = plan credits, expires at period end | `grant_plan` |
| Upgrade mid-period | increase the current `plan` batch `amount`/`remaining` by (new − old plan credits) | `grant_plan` |
| Purchase pack (on `payment_intent.succeeded`) | new `extra` batch, expires +12 months | `purchase` |
| Reserve (publish / top-up) | check `credits ≤ Free`; increase `pipelines.credits_reserved` | `reserve` / `top_up` (amount 0, reserve_change +n) |
| Consume (apply) | check pipeline `credits_used < credits_reserved` and Balance ≥ 1; decrement `remaining` on the batch chosen by order below; `credits_used += 1` | `consume` (−1) |
| Release (close / cancel) | `credits_reserved = credits_used` | `release` (reserve_change −n) |
| Expire (cron) | set `remaining = 0` on expired batches | `expire` (−remaining) |

**Consumption order:** `plan` batch first → then `trial` → then `extra` batches by earliest `expires_at` (= oldest purchase first).

After a consume: if `credits_used == credits_reserved` → pipeline `paused_no_credits` (+ Overview alert, email to pipeline owner). If Balance reaches 0 → every live pipeline in the workspace → `paused_no_credits`.

## 4. Edge cases
- **Reserve larger than balance after expiry** (plan credits expired but pipelines still hold reserves): Free goes negative; the UI shows "Your reserves are bigger than your credits" and consumption still stops at Balance 0. Buying or renewing fixes it automatically.
- **Race at the last credit:** the consume transaction locks the pipeline row; the second applicant gets `409 pipeline_not_accepting` and no credit is used.
- **Refunds / chargebacks:** handled manually in Stripe in MVP; an `adjust` ledger entry records any credit correction (Admin tooling via SQL runbook).
- **Failed renewal:** no plan batch is granted until the invoice is paid; existing batches keep working; Billing shows "Payment failed · Pay now" (Stripe hosted invoice link).

## 5. Stripe flows
- **Customer:** created lazily on first billing action; metadata `workspace_id`.
- **First subscription / change plan:** API creates a Stripe Checkout Session (mode `subscription`) for a workspace without a subscription; for existing subscriptions, `subscriptions.update` with `proration_behavior=always_invoice` for upgrades, and a subscription schedule (phase change at period end) for downgrades.
- **Buy pack:** `PaymentIntent` with `customer`, `payment_method = default`, `confirm = true`, `off_session = false`; the client confirms with Stripe.js if 3-D Secure is required. No default card → open Customer Portal / SetupIntent first.
- **Manage subscription / update card:** Stripe Customer Portal session.
- **Invoices:** read from Stripe and cached in `stripe_invoices`; PDF via `invoice_pdf`.
- **Billing details:** stored locally and synced to the Stripe customer (name, email, address, tax ID).

## 6. Webhooks (idempotent via `stripe_events.id`)
| Event | Action |
|---|---|
| `checkout.session.completed` | link subscription to workspace |
| `customer.subscription.created/updated/deleted` | upsert `subscriptions` (plan, status, period, pending plan) |
| `invoice.paid` | cache invoice; if subscription invoice for a new period → grant plan credits; if proration invoice for upgrade → top up plan batch |
| `invoice.payment_failed` | mark status; email Admins |
| `payment_intent.succeeded` (metadata `kind=credit_pack`) | grant extra batch |
| `customer.updated` | sync default payment method summary |

## 7. Usage analytics
Credit usage page reads `credit_ledger` (activity table, grouped per pipeline per day for `consume`), `credit_batches` (split and expiry), pipelines (reserve table with pace = consumed in last 26 days / 26), and department joins for "used this month by department".
