# Judge-safe demo video script

Target: **2 minutes 45 seconds**. The public video must stay below three minutes. Speak
in English and use no third-party music, customer data, credentials, access tokens or
provider payloads.

This is the recording script for the current single-merchant, localhost-only MVP. It
shows a genuine PayPal Sandbox read and a Claude-assisted **pending** proposal. It does
not claim production readiness, merchant-wide accounts-receivable coverage, a ledger,
webhook synchronization or autonomous collection. The evidence boundary is documented
in [#101](https://github.com/himarbravo/paypal-invoice-steward/issues/101).

## Pre-recording safety checks

1. Use a clean checkout and run `./scripts/check.sh`. Record the successful result
   separately; do not put a terminal containing paths, environment variables or secrets
   in the video.
2. Use only a dedicated PayPal Sandbox Business merchant and fictional customers. Crop
   or redact any Sandbox dashboard names, emails, invoice references and amounts that
   are not deliberately synthetic.
3. Keep `STEWARD_SANDBOX_WRITES=disabled` for this recording. The normal demonstration
   must not create, send, remind, refund or mark any provider object as paid.
4. Enable `STEWARD_SANDBOX_LLM=enabled` only while intentionally demonstrating Claude
   with synthetic data. It authorizes a third-party model data transfer; disable it
   after recording.
5. Run only on `localhost`; do not use a public tunnel, reverse proxy or exposed port.
   The project has no hosted-demo authentication boundary.
6. Start with a fresh browser profile or a clean app state, then check the status line
   before recording: it must identify **PayPal sandbox** and Claude accurately.

## 2:45 recording plan

### 0:00–0:18 — problem and promise

Show the dashboard without selecting an invoice row.

> "Small businesses lose time chasing invoices and guessing their cash position. PayPal
> Invoice Steward turns current Sandbox invoice data into an AI-assisted review flow —
> but the agent proposes and a person decides."

### 0:18–0:43 — live PayPal Sandbox read

Refresh the ledger and show the Sandbox status line plus the inventory-freshness
indicator. Do not zoom into customer data. Explain the scope precisely.

> "This is a live PayPal Sandbox read for one configured merchant application. The app
> validates the complete accessible page walk twice before showing financial figures.
> It is not claiming to be the merchant's complete accounting ledger."

### 0:43–1:20 — Claude produces a reviewable proposal

In the chat, enter a synthetic request such as:

> "Assess the receivables situation, then prepare — do not send — a synthetic EUR 12
> invoice for Sandbox Demo Customer."

Show the Claude response and the resulting pending proposal card. Do **not** click
Confirm.

> "Claude can inspect a minimized view of the financial state and prepare an exact
> proposal. The customer-facing details remain local. The proposal is still pending;
> the model has no send tool."

### 1:20–1:52 — human approval and safety boundary

Open the proposal details and point to the reviewed amount, recipient and action. Keep
the confirmation unclicked.

> "A person must review the exact payload before any action. The backend rechecks the
> provider state, blocks stale or ambiguous data, and prevents a second confirmation
> from creating another provider action. Sandbox writes are disabled for this demo."

### 1:52–2:18 — believable financial integrity

Show the forecast or aging view, then the inventory scope/freshness notice. If a
synthetic refund, missing-balance or incomplete-list screen is shown, identify it as an
**offline safety simulation**, never as a live PayPal event.

> "The forecast uses provider-reported outstanding balances when available. Missing,
> refunded or inconsistent states are blocked for manual review instead of guessed."

### 2:18–2:45 — impact and honest close

Return to the overview and show the status line.

> "Invoice Steward makes follow-up safer and faster for a small business: real PayPal
> Sandbox data, Claude-assisted proposals, and human control before every external
> action. It is open source and intentionally sandbox-only for this MVP."

## Optional separately authorized Sandbox-write insert

Do **not** add this sequence by default. If the operator explicitly authorizes one new
synthetic Sandbox action for the recording, use a dedicated recipient and record the
approval, one provider action and provider read-back. Stop if any identity, status,
amount, recipient or provider response is unexpected. Immediately restore
`STEWARD_SANDBOX_WRITES=disabled` afterwards. Never portray an earlier action or an
offline fixture as a current live send.

## Recording review

Before publishing, replay the video at 1.5× speed and confirm:

- It is under three minutes and visibly shows the working application.
- PayPal Sandbox and Claude are both shown truthfully.
- No credentials, `.env`, terminal secrets, real names/emails, unredacted invoice IDs,
  private URLs or dashboard account information appear.
- Any simulated failure is labelled as offline; no unsupported financial or compliance
  claim appears.
- The viewer can understand the customer problem, the AI's role, the human approval
  boundary and the impact without reading the repository.

For the complete release checklist, see [submission-checklist.md](submission-checklist.md).
