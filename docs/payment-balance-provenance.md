# Payment provenance and residual-balance boundary — #104 / parent #55

**Scope:** one operator-owned PayPal sandbox Business account; read-only interpretation of Invoicing v2 objects. **No payment posting, settlement, capture, refund, mark-as-paid or bookkeeping writes** are added by this change. A synthetic local demo is not PayPal evidence.

## Authoritative fields and what they mean

- **`amount`**: invoice **face value**; never the amount still owed after a partial payment.
- **`due_amount`**: PayPal-reported outstanding balance in the invoice currency. Only this field is used for PayPal-sourced open receivable forecasts, aging and reminder text. EUR/USD/GBP require a finite, nonnegative decimal with no more than two decimal places and a matching `currency_code`.
- **`payments.paid_amount` and `payments.transactions`**: read-only payment records, not a separate ledger to repost or independently reallocate. The implementation deliberately does **not** calculate `due_amount = amount - SUM(transactions)`: duplicates, refunds, discounts and provider accounting rules may invalidate such a naive formula.
- **`payments.transactions[].type`**: PayPal's `PAYPAL` versus `EXTERNAL` report, used only as payment-origin evidence. `PAID` and `MARKED_AS_PAID` provider statuses are retained in `provider_status`, while the app's coarse `status` is preserved for older features. Mixed, invalid or repeated transaction IDs remain ambiguous; no duplicate allocation is performed.
- **`payments.transactions[].payment_date`**: date of a reported transaction if present and valid. A fully paid invoice only gets a `paid` date if **all** reported transaction dates are available, with the latest date selected; missing/contradictory evidence leaves it `null`. **Never replace missing payment date with invoice due date.**
- **`balance_source`**: `paypal_due_amount` on a verifiable PayPal balance, `unverified` when missing or malformed, `synthetic` for the local fake backend / manually constructed test invoices only. The default of the legacy Python `Invoice` constructor is synthetic for backward compatibility; an actual PayPal normalizer sets the source explicitly.

## Fail-closed boundaries

- If **any open PayPal invoice** lacks a valid residual, the financial forecast is unavailable (HTTP 503, safe error). Aging and tool-based collection advice also stop instead of substituting nominal amounts or silently dropping the invoice.
- An overdue payment reminder cannot be drafted when its remaining balance is unknown **or zero**. When verified, the reminder summary and message display the residual rather than the face amount.
- The browser's "owed" aggregate uses PayPal `remaining_amount` when verified; the invoice table explicitly labels `amount` as **Invoice face**. Existing stale-UI clearing from #102 remains in place.
- Synthetic offline data retains its demo behavior and remains **explicitly not provider/merchant proof**.

## Not covered by this read-only slice

1. Idempotent matching of actual payment transaction IDs across rescans and webhook deliveries, duplicate external posting, and allocation/audit history.
2. Provider `effective_due_amount` and discount/surcharge variations; partial refunds, cancellations and marked-as-refunded states need issue #66 plus account-specific tests. Existing coarse status mapping is **not** an adequate accounting ledger.
3. Exchange rates, 3-decimal currencies, dispute handling and a transaction-by-transaction reconciliation ledger.
4. Freshness and merchant-wide invoice coverage: parent [#75](https://github.com/himarbravo/paypal-invoice-steward/issues/75) remains open. A verified `due_amount` is provider-reported for that read only; it is not a durable reconciled general-ledger balance.
5. Live sandbox integration evidence: all tests here use synthetic invoices or MockTransport. An actual sandbox read-back is required before claiming provider-verified behavior.

**Source A:** [PayPal Invoicing invoice schema](https://developer.paypal.com/api/invoicing/v2/definitions/invoice/) (`due_amount`, payments and refunds), [payments definition](https://developer.paypal.com/api/invoicing/v2/definitions/payments) (transaction origins and dates), [invoice lifecycle](https://developer.paypal.com/invoicing/core-concepts/) (`PAID`, `MARKED_AS_PAID`, `PARTIALLY_PAID`). The fail-closed policy and currency scope are **product design**, not an asserted PayPal mandate.
