# PayPal invoice inventory: scope, completeness and source precedence

**MVP scope:** one operator-owned PayPal **sandbox business merchant**, one configured application and its authenticated invoice API access. This document describes the **bounded invoice list fetch**, not a full accounts-receivable ledger or a certified reconciliation. Related: [#75](https://github.com/himarbravo/paypal-invoice-steward/issues/75), [#102](https://github.com/himarbravo/paypal-invoice-steward/issues/102), #71, #55 and hackathon gate #84.

## What the implementation verifies

- The adapter calls **GET /v2/invoicing/invoices** with `page=1,2,...`, `page_size=50` and `total_required=true`. The API documentation defines the `total_pages` and `total_items` response fields.
- It requires both totals to be nonnegative integers on every page, with unchanged values across the read. Sandbox may omit `items` for an exactly zero/zero inventory; only that omitted-key shape becomes an empty list. It rejects malformed or otherwise missing `items`, missing/empty invoice IDs, duplicates, impossible counts, and a final unique count that differs from `total_items`.
- A short page **never** means the inventory is complete; the reported page count determines whether another page must be requested.
- Safety limit: **at most 20 pages × 50 invoices = 1,000**. If the provider declares more, the adapter refuses the operation rather than truncating silently. This is a **product resource limit**, not an official PayPal invoice cap.
- A missing page, rate limit, authorization failure, network error, provider 5xx, changing totals or malformed metadata **never yields a partial list**. The application does not substitute cached/demo fixtures. For pagination-specific failure, `/api/invoices` and `/api/forecast` return HTTP 503 with an explicit incomplete-inventory warning. Other PayPal errors retain their existing safe handling.
- The tests are offline `httpx.MockTransport` simulations of this contract, not evidence that a real sandbox merchant returned those pages.

## Source boundary and decision rule

| Data source | Authority and rule |
|---|---|
| Current invoice **GET** response | Use for the state of a specific invoice at the moment the provider responds; the proposal-confirmation workflow rechecks before sending, subject to its own limitations |
| Invoice **list** page walk | A count-consistent enumeration **accessible to the configured PayPal API application/credentials** at read time; adequate only for *bounded advisory* calculations |
| Webhook events | **Hints, not the full inventory or an authoritative current balance**. PayPal webhooks are app-scoped, may arrive late/out of order and are not integrated as a durable stream in this MVP |
| Local proposal notes | Operator-intended communication/actions, **never financial settlement evidence** |
| External books/general ledger | Not integrated. The app **does not** assert ledger matching, true outstanding receivable or merchant-wide complete coverage |

**Do not label "all invoices visible to this API" as "all invoices owned by the business."** Application-scoped webhooks, permissions, legacy applications, dashboard changes and external payment records can differ. The OAuth `app_id` identifies an application, not proof of merchant ownership (#73).

## Freshness, watermark and known limits

- Reads are **on demand**, not a durable synchronization job. A successful call gives a locally validated **page walk**, not an atomic PayPal snapshot. Counts and duplicate detection catch some concurrent updates; a replacement of one invoice by another during pagination could escape detection if totals remain unchanged.
- SQLite records the latest attempt, latest completed page walk, observed IDs/count and unresolved missing IDs, partitioned by mode and a digest of the configured app client ID. `/api/inventory-status` and the browser expose this history. No credentials, customer text or balances are added to this journal. A failure retains the previous observation but never returns cached financial data. Interrupted attempts remain unverified after restart; superseded responses cannot overwrite newer attempts.
- A previously observed ID missing from a later walk blocks financial totals until it reappears. Missing IDs persist across repeated reads and restarts; disappearance never means paid, cancelled or deleted. Inspect the sandbox dashboard/account scope and resolve the source discrepancy. There is no automated clearance or backfill. Do not delete the database just to bypass the warning.
- The status becomes stale after five minutes, on a clock regression, failed/interrupted read or missing record. Five minutes is a conservative product display policy, **not a PayPal freshness guarantee**; each financial request still reads again. The displayed timestamp is a completed page walk, not continuously current data or settlement proof.
- There is **no automatic rate-limit backoff** and no automatic reconciliation of unverified/missing invoices across APIs. A 429 or 5xx is reported as an error; manually retry a safe read only when appropriate. The existing proposal service handles write uncertainty separately.
- Invoice face amount and PayPal-reported `due_amount` are separate. Aging, forecast and reminders use verified remaining balances; missing balances or refund-review states block affected calculations. Payment allocation and refund reconciliation remain separate work (#55/#66). These are **advisory**, not accounting balances.
- During a demo, show a user-visible error when the list fails, and never quote a forecast based on a truncated list. Do not claim the successful mock tests prove the account's actual complete inventory.

## Further acceptance for parent #75 (not implemented here)

1. Test list and show operations against a real **synthetic PayPal sandbox** merchant and record scope/permissions, not credentials.
2. Extend the bounded observation journal into reconciled exceptions, per-invoice source timestamps and safe backfill/resume/rate-limit behavior. Current counts measure observed records, not merchant-wide coverage.
3. Reconcile app-scoped webhooks, direct GET, dashboard updates and financial exceptions; verify behavior for partial refunds and out-of-order events.
4. Define any stronger consistency guarantees and prove them under concurrent PayPal updates; this bounded page walk alone cannot guarantee an immutable snapshot.
5. No external ledger integration or multi-merchant onboarding in the hackathon MVP; treat them as out of scope, not completed requirements.

**Source A:** [PayPal Invoicing v2 List invoices](https://developer.paypal.com/api/invoicing/v2/invoices-list/) (pagination fields, page sizes); [PayPal Webhooks guide](https://developer.paypal.com/api/webhooks/overview/) (app-scoped events, delivery constraints). **Source B:** [NIST AI RMF](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) (traceability and risk visibility). Enforcement and limits are **product policies**, not PayPal requirements.

## Scoped polling-only fallback for Gate 2

The localhost MVP performs on-demand reads at page refresh and when tools need inventory. There is **no background poller, webhook subscription, receiver or verified event stream**. Duplicate, forged, delayed or out-of-order webhook payloads cannot change application state because there is no ingestion endpoint. Refresh explicitly after dashboard changes; never describe this as real-time synchronization. Direct invoice GET revalidation still happens before approved actions; a provider-side change between GET and POST remains possible.

This is the bounded fallback explicitly allowed by #84; it does not close #71's webhook implementation requirements. A future receiver must use the [PayPal REST verification contract](https://developer.paypal.com/api/rest/webhooks/rest/) (including raw-body handling or the verify-signature API), durable acceptance, merchant association, deduplication and API reconciliation before financial effects. Mock events are not proof of a genuine app delivery. No public tunnel or webhook endpoint is introduced by this fallback.
