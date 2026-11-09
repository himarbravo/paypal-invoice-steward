# Judge-safe demo video script

Target: **2 minutes 40 seconds**. The public video must stay below three minutes. Speak
in English and use no third-party music, customer data, credentials, access tokens or
provider payloads.

This is the recording script for the current single-merchant, localhost-only MVP. It
shows a genuine PayPal Sandbox read, Claude-assisted **pending** proposals, one
operator-approved Sandbox invoice and an offline failure simulation that is labelled as
such. It does not claim production readiness, merchant-wide accounts-receivable coverage,
a ledger, webhook synchronization or autonomous collection. The evidence boundary is
documented in [#101](https://github.com/himarbravo/paypal-invoice-steward/issues/101).

## Pre-recording safety checks

1. Use a clean checkout and run `./scripts/check.sh`. Record the successful result
   separately; do not put a terminal containing paths, environment variables or secrets
   in the video.
2. Use only a dedicated PayPal Sandbox Business merchant and fictional customers. Crop
   or redact any Sandbox dashboard names, emails, invoice references and amounts that
   are not deliberately synthetic.
3. Seed the Sandbox beforehand with a few fictional open invoices in more than one
   currency (EUR, USD, GBP). Give at least two of them a payment term of 1 to 3 days:
   the app cannot create overdue invoices, and reminders are only prepared for invoices
   that are overdue or due within 3 days.
4. Start two local instances and record only the browser. Do not record a terminal.
   - Real mode (PayPal Sandbox and Claude), with Sandbox writes enabled for this process
     only, so the operator can approve one invoice on camera. Your `.env` is not edited;
     closing the process returns the app to read-only:

     ```bash
     STEWARD_SANDBOX_WRITES=enabled STEWARD_OPERATOR_ID=demo-approver paypal-invoice-steward
     ```

   - Offline simulation on port 8001 (fake PayPal, rule-based assistant, nothing leaves
     the computer):

     ```bash
     STEWARD_MODE=demo STEWARD_SANDBOX_LLM=disabled STEWARD_SANDBOX_WRITES=disabled \
     ANTHROPIC_API_KEY= STEWARD_DB=:memory: PORT=8001 paypal-invoice-steward
     ```

5. `STEWARD_SANDBOX_LLM=enabled` authorizes a third-party model data transfer. Keep it
   enabled only while intentionally demonstrating Claude with synthetic data.
6. Run only on `localhost`; do not use a public tunnel, reverse proxy or exposed port.
   The project has no hosted-demo authentication boundary.
7. Rehearse with **Dismiss**, never **Send invoice**: each approved send creates a real
   Sandbox invoice and changes the figures on screen.
8. Check the status badges at the top right before recording: they must read **PayPal
   sandbox** and **Claude enabled (chat sent to external AI)**.

## Prompts to paste

The prompts below were verified against a real Sandbox merchant with Claude. The invoice
prompt must include a customer email: the assistant will not invent one. No extra
wording is needed for the rest: in Sandbox, Claude is not offered a reminder note
(PayPal writes the reminder email), known PayPal IDs are replaced with the invoice
number before a reply is shown, and the chat renders simple formatting safely.

Summary and reminders:

```text
Give me a short summary of what is due soon and my cash flow forecast by currency. Then prepare reminders for every invoice due within 3 days.
```

New invoice:

```text
Prepare an invoice for Lumen Architects, billing@lumenarchitects.example: 1 item, Floor plan review, 60 EUR, due in 14 days.
```

Each approved send leaves a real invoice in the Sandbox. If a previous rehearsal already
created the Lumen invoice, cancel it in the Sandbox or use another fictional customer so
the table does not show it twice.

## 2:40 recording plan

### 0:00–0:15 — problem and promise

Show the dashboard of the real instance, status badges visible.

> "Small businesses lose hours chasing invoices and guessing their cash. PayPal Invoice
> Steward connects PayPal Invoicing and Claude so an AI can analyze and prepare the
> work, but a person always decides."

### 0:15–0:40 — live PayPal Sandbox read

Show the per-currency cards, the forecast charts and the invoice table. Do not zoom
into customer data.

> "This is a live read from one PayPal Sandbox merchant. The app validates the complete
> invoice list twice before showing any figure and never mixes currencies: euros,
> dollars and pounds each get their own forecast, from two thousand simulations of how
> each customer actually pays."

### 0:40–1:15 — Claude summarizes and prepares reminders

Paste the summary and reminders prompt. The answer takes about 15 seconds: keep talking.

> "Claude sees only a minimized view: amounts, dates and statuses, never customer names
> or emails, and it has no tool that sends anything. It can only read and propose."

Show the pending reminder cards. Do **not** click send.

> "It gives the likely outcome and the average for each currency, not one blended number,
> and prepares reminders for invoices due within three days. PayPal writes the reminder
> email, and the card says so. I am not sending these."

### 1:15–1:50 — operator approval and PayPal read-back

Paste the new invoice prompt and show the pending card with the exact payload.

> "Claude prepares a new invoice, but nothing exists yet. I review the exact customer,
> item, amount and terms."

This step performs one real Sandbox write and requires the separate operator
authorization described in [submission-checklist.md](submission-checklist.md). Click
**Send invoice** once, then show the sent stamp and the updated totals.

> "On approval, the app checks that what is sent is exactly what I reviewed, creates
> and sends the invoice through the PayPal API, and reads it back. A double click or a
> second tab sends it only once."

If the operator does not authorize a Sandbox write, leave the card pending and say that
Sandbox sends are enabled only by explicit operator choice.

### 1:50–2:20 — failure handling (offline simulation)

State clearly, on screen or aloud, that this part is an **offline simulation** (the panel
also carries an **Offline simulation** label). Switch to the offline instance, use the
suggested invoice prompt, open **Simulate a PayPal problem**, choose **PayPal sends it, but the answer is lost**, send the invoice, then
click **Check PayPal**.

> "This failure is simulated offline. PayPal sent the invoice but the answer was lost.
> The app marks it unverified and does not retry blindly. Check PayPal confirms it and
> exactly one invoice exists."

### 2:20–2:40 — impact and honest close

Return to the real instance and show the status badges.

> "Invoice Steward makes follow-up safer and faster: real PayPal Sandbox data,
> Claude-assisted proposals, and human approval before every external action. It is
> open source, runs locally and is intentionally Sandbox-only for this MVP."

## After recording

Stop both instances. Sandbox writes were enabled only for the real process, so nothing
needs to be reverted in `.env`; confirm `STEWARD_SANDBOX_WRITES` and
`STEWARD_SANDBOX_LLM` are `disabled` there.

## Recording review

Before publishing, replay the video at 1.5× speed and confirm:

- It is under three minutes and visibly shows the working application.
- PayPal Sandbox and Claude are both shown truthfully.
- No credentials, `.env`, terminal secrets, real names/emails, unredacted invoice IDs,
  private URLs or dashboard account information appear.
- The simulated failure is labelled as offline; no unsupported financial or compliance
  claim appears.
- The viewer can understand the customer problem, the AI's role, the human approval
  boundary and the impact without reading the repository.

For the complete release checklist, see [submission-checklist.md](submission-checklist.md).
