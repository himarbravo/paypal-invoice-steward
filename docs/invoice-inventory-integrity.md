# PayPal invoice inventory: scope, completeness and source precedence

**MVP scope:** one operator-owned PayPal **sandbox business merchant**, one configured application and its authenticated invoice API access. This document describes the **bounded invoice list fetch**, not a full accounts-receivable ledger or a certified reconciliation. Related: [#75](https://github.com/himarbravo/paypal-invoice-steward/issues/75), [#102](https://github.com/himarbravo/paypal-invoice-steward/issues/102), #71, #55 and hackathon gate #84.

## What the implementation verifies

- The adapter calls **GET /v2/invoicing/invoices** with `page=1,2,...`, `page_size=50` and `total_required=true`. The API documentation defines the `total_pages` and `total_items` response fields.
- It requires both totals to be nonnegative integers on every page, with unchanged values across the read. It rejects malformed `items`, missing/empty invoice IDs, duplicates, impossible counts, and a final unique count that differs from `total_items`.
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
- There is currently **no persistent last-success watermark, per-invoice update cursor, historical backfill, or storage of reconciliation coverage and exceptions**. Consequently the application must not claim a continuously fresh 100% invoice feed. A new request queries PayPal again; a failed request returns no data rather than falling back to an older snapshot.
- There is **no automatic rate-limit backoff** and no automatic reconciliation of unverified/missing invoices across APIs. A 429 or 5xx is reported as an error; manually retry a safe read only when appropriate. The existing proposal service handles write uncertainty separately.
- Invoice amount currently represents its source-supplied face amount, not a verified remaining balance after partial payments/refunds. Payment allocations and refund semantics are separate work (#55/#66). Aging and cash forecasts are **advisory**, not accounting balances.
- During a demo, show a user-visible error when the list fails, and never quote a forecast based on a truncated list. Do not claim the successful mock tests prove the account's actual complete inventory.

## Further acceptance for parent #75 (not implemented here)

1. Test list and show operations against a real **synthetic PayPal sandbox** merchant and record scope/permissions, not credentials.
2. Define and implement a durable, explicitly dated reconciliation watermark, missing-record exception queue and measurable app-visible coverage; design safe backfill/resume and rate-limit behavior.
3. Reconcile app-scoped webhooks, direct GET, dashboard updates and financial exceptions; verify behavior for partial refunds and out-of-order events.
4. Define any stronger consistency guarantees and prove them under concurrent PayPal updates; this bounded page walk alone cannot guarantee an immutable snapshot.
5. No external ledger integration or multi-merchant onboarding in the hackathon MVP; treat them as out of scope, not completed requirements.

**Source A:** [PayPal Invoicing v2 List invoices](https://developer.paypal.com/api/invoicing/v2/invoices-list/) (pagination fields, page sizes); [PayPal Webhooks guide](https://developer.paypal.com/api/webhooks/overview/) (app-scoped events, delivery constraints). **Source B:** [NIST AI RMF](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) (traceability and risk visibility). Enforcement and limits are **product policies**, not PayPal requirements.
