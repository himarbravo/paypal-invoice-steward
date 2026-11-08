# Payment posting, refund corrections, and approval matrix

**Scope:** PayPal Invoice Steward hackathon: one operator-owned **PayPal sandbox** business app, local-only, synthetic invoices; no collection of real funds. Parent requirement [#66](https://github.com/himarbravo/paypal-invoice-steward/issues/66); narrow hardening [#106](https://github.com/himarbravo/paypal-invoice-steward/issues/106). Financial gate #84 stays open until live sandbox evidence.

## Correct lifecycle interpretation

PayPal distinguishes `CANCELLED`/`AUTO_CANCELLED` from `REFUNDED`, `PARTIALLY_REFUNDED`, `MARKED_AS_REFUNDED`, and `REFUNDED_EXTERNAL`. Partial refunds can increase an invoice's outstanding balance. Our read-only model maps all refund-family statuses to **`refund_review`**, retains the exact `provider_status`, and explicitly **does not** infer a collectible outstanding balance, refund amount, payment settlement, or cancel the debt in accounting.

Any refund-review invoice in the fetched, app-visible inventory blocks aggregate invoice dashboard balances, aging, forecast and model-driven bulk reminder preparation (HTTP 503 where applicable). The refund remains accessible by direct provider lookup through the adapter for a human to examine; it is not silently counted as settled. A future supported reconciliation would have to read full payment/refund transactions, distinguish hosted and manually marked flows, and validate an authoritative remaining balance before re-enabling aggregates.

## Operation and authorization matrix

| Action / provider endpoint | Present behavior | Required controls before a future rollout |
| --- | --- | --- |
| `GET /v2/invoicing/invoices`, `GET /v2/invoicing/invoices/{id}` | **Supported, sandbox-only**, with OAuth invoicing permission; inventory fails closed on incomplete pages | Verify single account/app visibility, date freshness, all pages, refund and dispute exceptions; not a ledger |
| `POST /v2/invoicing/invoices`, `POST .../{id}/send`, `POST .../{id}/remind` | **Supported only after exact-payload human approval** and explicit `STEWARD_SANDBOX_WRITES=enabled`. For reminders, approval is followed by live invoice GET and status/balance/recipient preflight | No autonomous sends or production use; planned reminder stays blocked after any refund/status/balance/recipient change |
| `POST /v2/invoicing/invoices/{id}/payments` | **Not implemented.** External payment recording only; PayPal-hosted payments already record automatically | Human controller identity/authority, independent receipt evidence, exact amount/currency/date, stable external transaction ID, no duplicate allocation, audit and manual approval |
| `DELETE /v2/invoicing/invoices/{id}/payments/{transaction_id}` | **Not implemented.** Correct **external** payment entries; not PayPal-hosted captures | Independent matching by transaction ID, original entry provenance, two-person review for consequential corrections and durable audit |
| `POST /v2/invoicing/invoices/{id}/refunds` | **Not implemented.** Records **offline/external** refunds, not PayPal-hosted refunds | Validate original payment/refund links, amount/currency, authorization and re-read of invoice; never create an apparent PayPal-hosted refund |
| `DELETE /v2/invoicing/invoices/{id}/refunds/{transaction_id}` | **Not implemented.** External refund corrections only | Strict transaction identity, reversal audit, independent approval; not hosted refund removal |
| Payments Refund API (hosted PayPal refund) | **Not implemented.** Requires separate Payments API authority and accounting controls | Explicit user identity, proper payment/capture ID, refund authorization and audit; outside hackathon scope |
| Customer credit decisions, write-offs, actual charge/capture, cross-merchant posting | **Forbidden / not implemented** | No LLM execution tools or local-only consent can authorize these |

**Identity and authorization limit:** The hackathon localhost app has no per-user authentication or role-based access control. The local human confirmation is **not** proof of a named finance officer's legal authority. The approval matrix is a future gate, not a claim the controls exist. PayPal `app_id` proves an app, not a merchant owner's identity (#73). No payment/refund write operation is exposed in the agent `TOOLS`, FastAPI routes or `PayPalPort`.

## Freshness and preflight contract

A reminder proposal stores a reviewed snapshot: invoice ID/number, recipient email, currency, due date, and verified remaining amount. At confirmation, while in a single-execution proposal state, the backend fetches the invoice **again**. It blocks safely if refund-review, cancelled, paid, unknown, missing, zero due, unverified due, or any reviewed field changes. A local preflight rejection records `blocked` and `failed`, **not** a false assertion that PayPal refused the operation. Provider GET failure is reported under its existing rejected/unknown handling; the application sends no reminder when preflight cannot finish. This is not atomic with a later PayPal POST: a state change between GET and POST still requires provider enforcement and eventual reconciliation.

**Existing pending reminders from older versions** without the reviewed snapshot fail closed rather than silently acquiring approval after an upgrade. No refund/payment DELETE or POST endpoints are added by this change.

Equivalent **invoice** requests reuse one local proposal while its outcome is `pending`, `executing`, or `unverified`, even when separate local SQLite connections request it concurrently. Its PayPal reference and `proposed` audit event are created in the same local transaction. This stops a local duplicate-proposal race; it is not a provider idempotency key, merchant-wide duplicate detector, or a substitute for verified Sandbox read-back.

If the local process is interrupted after reserving an invoice proposal, its `executing` state stays blocked from any create/send retry. The reservation and its `confirmed` attribution are committed in one local transaction before a provider write begins. Likewise, each terminal, dismissal, or recovery state change and its matching audit event are committed together; a failed audit insert rolls back the state change. A read-only verification observation is recorded only while its original in-flight state still exists, so a stale lookup cannot appear after a concurrent terminal transition. The operator may use **Check PayPal** for one read-only lookup by the existing reference. Only an exact approved invoice in a confirmed sent/paid state becomes `done` and records `recovered`; missing, draft, mismatched, unconfirmed, or unavailable responses remain unresolved. Reminders have no automatic recovery and require direct provider/operator checking. This guarantees local state/audit coherence, not a lease timeout, provider idempotency, or evidence of a live Sandbox write.

## Unresolved acceptance

- No end-to-end merchant sandbox account validation, transaction idempotency ledger, verified external receipt, refund identity and allocation, or accounting-system reconciliation.
- No dispute/hold system, human roles/entitlements, signed correction approval, operator audit exports, or durable webhook handling.
- `REFUNDED` and `MARKED_AS_REFUNDED` are *not* asserted to have the same origin; the exact provider status is kept and reconciliation is required. Never treat provider transaction source as independent settlement evidence.
- Partial refund reactivation and aging correctness require actual provider read-back and accounting evidence; the safer demo behavior is to show **unavailable** instead of a false total.

**Source A:** [PayPal Invoicing v2 API endpoint list](https://developer.paypal.com/api/invoicing/v2/), [PayPal Invoicing operation reference](https://developer.paypal.com/invoicing/reference/), [invoice lifecycle](https://developer.paypal.com/invoicing/core-concepts/). **Source B:** industry accounts-receivable controls (specific IOFM teaching material has not been independently verified). No PCI, hosted merchant onboarding or legal compliance claim.
