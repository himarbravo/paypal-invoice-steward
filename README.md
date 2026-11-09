# PayPal Invoice Steward

An AI agent that helps a small business get paid. It watches your PayPal invoices, forecasts when the money will actually arrive, and prepares invoices and payment reminders for you to approve.

**The agent proposes. You decide.** It can read invoices and prepare actions, but it has no tool that sends anything. Every invoice and reminder goes out only after a person confirms a card showing exactly what will be sent.

Built for the PayPal AI Hackathon with the PayPal Invoicing v2 API (sandbox) and Claude.

> Status: early development (`0.x`). See [CHANGELOG.md](CHANGELOG.md).

## What it does

- **Cash-flow forecast.** Learns how fast each customer really pays and simulates 2,000 futures to show the expected income per week for the next 8 weeks, with a likely range. Invoices already far later than their customer's habit are treated cautiously.
- **Reminders for late invoices.** "Remind my late customers" prepares one reminder card per overdue invoice.
- **New invoices from a sentence.** "Invoice Alba Design Studio billing@albadesign.example 450 EUR for a logo refresh" prepares an invoice card.
- **Safe by design.** A lost or failed PayPal call never creates a duplicate invoice (see below).

## Run it in one minute (demo mode, no accounts)

Requires Python 3.11 or later.

```bash
git clone https://github.com/himarbravo/paypal-invoice-steward.git
cd paypal-invoice-steward
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
paypal-invoice-steward          # then open http://127.0.0.1:8000
```

Demo mode uses a built-in fake PayPal with five customers and 23 invoices, so everything works offline. Without an Anthropic key, a rule-based assistant understands the suggested prompts. Open **Simulate a PayPal problem** to see what happens when PayPal refuses a request or its answer is lost.

## Run it against the PayPal sandbox, with Claude

1. Create a **Sandbox** app in the [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/) (Apps & Credentials) and copy its client ID and secret. Invoicing needs a sandbox **Business** account.
2. Give that Sandbox Business account a few **fictional** open invoices, for example by logging in to the Sandbox site as the business account and using its invoicing page. Use more than one currency (EUR, USD, GBP) if you want to see separate forecasts, and give one or two a due date within 3 days: reminders are only prepared for invoices that are overdue or due within 3 days, and this app cannot create overdue invoices. A fresh Sandbox with no invoices shows an empty overview.
3. Install as in demo mode, then create your local configuration in the repository folder:

   ```bash
   cp .env.example .env
   ```

   Fill in `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`. To use Claude, also set `ANTHROPIC_API_KEY` **and** `STEWARD_SANDBOX_LLM=enabled` (remove the leading `#` from that line; explained below); a key without that line stops startup with `Sandbox external AI requires STEWARD_SANDBOX_LLM=enabled`. Without a key, the rule-based assistant is used.
4. Start the app from that same folder (it loads only that working directory's `.env`) and open http://127.0.0.1:8000:

   ```bash
   paypal-invoice-steward
   ```

5. Check the badges at the top right: **PayPal sandbox**, **Claude enabled (chat sent to external AI)** (or **Offline assistant**) and **Read-only: outbound sends blocked**. Ask, for example, "Prepare reminders for every invoice due within 3 days": the reminder cards stay pending, and sending them is blocked until you opt into Sandbox writes (below).

The PayPal client only accepts `https://api-m.sandbox.paypal.com` (an optional trailing slash is allowed), never a hostname that merely contains `sandbox`. Incomplete credentials or an unrecognized `STEWARD_MODE` cause startup to fail instead of silently showing fake data. The MVP connects to one merchant's own sandbox app credentials; third-party merchant onboarding is not implemented. On each new OAuth token, it requires the documented invoicing permission, a Bearer token and an app ID; optional `PAYPAL_APP_ID` checks that application ID. This **does not prove the business account's merchant identity** or establish separate PayPal read/write invoicing scopes. See [sandbox authorization boundary](docs/sandbox-authorization.md).

**External AI is also opt-in for real PayPal sandbox data.** With both sandbox credentials and `ANTHROPIC_API_KEY` present, startup refuses to send any chat to Claude until you explicitly set `STEWARD_SANDBOX_LLM=enabled` in your local `.env`. This permits external processing of the **raw text you type**, so use only synthetic customers and invoices. It does **not** provide customer consent or satisfy GDPR requirements. The status line announces external AI usage. See [privacy and data lifecycle](docs/privacy-data-lifecycle.md) for data flows and retention gaps.

**Sandbox starts read-only even when credentials are configured.** You can inspect invoices and prepare proposals, but confirming an invoice or reminder returns HTTP 403 and leaves the proposal pending. To demonstrate real sandbox API sends, explicitly set `STEWARD_SANDBOX_WRITES=enabled` **and** a 3–64 character `STEWARD_OPERATOR_ID` in your **uncommitted** `.env`, then restart the app. Only the exact value `enabled` opts in; `yes`, `1` and `true` are rejected. The server records that configured label on the approval event before any provider write. It is a local audit label only: it is not login, proof of identity, authorization, RBAC, tenant isolation or non-repudiation. Use the app only with your own single merchant's sandbox credentials on localhost, and disable writes when finished. Demo mode remains simulated and is not proof of PayPal integration.

## Hackathon demo access boundary

**This release has no user login. Run it only on your own computer.** The supported
CLI accepts only `127.0.0.1`, `localhost` and `::1` as bind addresses; the
application also rejects direct remote peers, untrusted Host headers and cross-origin
browser writes. **Do not publish it using a reverse proxy, tunnel, exposed Docker
port or hosted URL**: those can bypass the local-only assumption. A hosted demo
requires authentication, HTTPS and session/CSRF protection first.

The offline demo uses **synthetic invoices and a fake PayPal backend**. It is useful
to test safely, but it does **not** establish working PayPal API integration or
meaningful AI use for hackathon judging. For that, run a separate test against your
**own PayPal sandbox business account** and AI tool, using credentials kept in a
local, uncommitted `.env`. Never put real credentials or private invoices in a
public repository, public video or test fixtures.

## Safety model

**Sandbox reminders use PayPal-generated email content.** Custom notes are unsupported, so Claude is not offered a note field in Sandbox; the approval card explains this and warns that the local cooldown does not control PayPal automatic reminders or other contact. Send/remind requests explicitly request no additional CC recipients. Scheduled and payment-pending invoices cannot be reminded. See [external reminder policy](docs/external-reminder-policy.md) for operator checks and the provider verification still required.

**Invoice reads are on demand.** The browser shows the last completed page walk and missing-record count. Failed reads return no cached figures; previously observed invoices that disappear block financial totals pending investigation. This app-visible observation is not an atomic snapshot or a merchant ledger. No webhooks or continuous sync are implemented. See [inventory scope and freshness](docs/invoice-inventory-integrity.md).

**Local contact holds:** use the invoice table to hold reminders during a dispute, complaint or contact review. Holds also block pending reminder confirmations, survive restarts and require manual release. They cannot recall requests already in flight or stop PayPal's independent schedules. The model cannot change holds; the local operator handles external escalation.

| Risk | What prevents it |
|------|------------------|
| The model sends something it should not | The agent's tools only read and *propose*. A test checks that no tool can send, confirm, pay, cancel or delete. |
| You approve one thing and another is sent | Confirmation recomputes the stored payload hash and compares it with the reviewed hash, then revalidates invoice policy. Altered payloads, unsupported action kinds and nonfinite amounts are refused. This is an integrity check, not authentication of the local database. |
| Double click or two tabs | Status changes are compare-and-swap in SQLite: exactly one request executes. |
| Timeout after PayPal already sent | The proposal becomes *unverified*. Reference lookup requires complete count-consistent search results (at most ten) and rereads a unique match by ID. Incomplete, ambiguous or changed results block retries. Search plus create/send is not atomic and still needs real sandbox verification. |
| Reminder with an unknown outcome | Never retried automatically; a person checks PayPal first. |
| Unexpected PayPal status | Shown as unknown, left out of the forecast, no reminders. |
| Refunded or partially refunded PayPal invoice | Flagged for manual refund reconciliation, **not** mislabeled cancelled. Cash forecast, aging and invoice dashboard totals are unavailable until reconciled. No automatic refund or payment correction. [Approval and endpoint matrix](docs/payment-posting-safety-matrix.md). |
| Approved reminder becomes stale before send | PayPal invoice is reread immediately before sending. A change in status, amount due, currency, due date or recipient blocks the reminder and records a local refusal. |
| Partially paid invoice or unavailable residual balance | PayPal's verified `due_amount` is used for the outstanding amount, aging, forecast and reminder text, separate from original invoice face value. Missing/mismatched balances block advice and reminders; no payment date is guessed. See [payment provenance and limitations](docs/payment-balance-provenance.md). |
| Invoice inventory is incomplete or pagination metadata changes | No partial totals or cash forecast. The API reports an error; the UI clears stale figures rather than leaving old amounts visible. This protects only the **bounded API page walk**, not the merchant's entire ledger. [Limitations](docs/invoice-inventory-integrity.md). |
| Untrusted PayPal error message contains PII or secrets | API responses, model tool results and proposal/audit errors expose only safe categories and a bounded HTTP code; raw upstream error details are not echoed. |
| Malicious customer names/notes in PayPal data | The Claude tool boundary receives a restricted numeric/ID-only view of invoices, forecasts and aging, never free-text customer names, email addresses or proposal summaries. Full details remain in the local approval UI; the model still cannot execute actions. |
| Risky input | Server-side policy: maximum amount, EUR/USD/GBP only, 1 to 90 day terms, reminders only for open invoices that are overdue or due within 3 days, 3-day cooldown. Confirmation atomically reserves the unchanged proposal and checks same-invoice executions, uncertain outcomes and cooldown across connections/restarts. A crashed execution remains blocked for operator investigation. |
| Invoice ID contains path or URL syntax, or PayPal returns another invoice | Reject malformed IDs before any network request and require the read-back ID to equal the requested ID. This binds a request to one resource; merchant ownership still requires sandbox verification. |
| Created/recovered invoice differs from approval, or send is not confirmed | Check reference, recipient, name, face amount, currency, due term, ordered line items and note before sending and verifying. Completion needs a known sent/paid state; scheduled/draft/refund/unknown or malformed-content read-backs stay unverified. A provider-side read-to-write race remains unresolved. |
| Missing invoice date, due date, face amount or currency | Stop the read instead of inventing today's date, a due date, an item-sum total or USD. This conservative MVP supports explicit ISO dates and EUR/USD/GBP amounts; other terms/currencies need operator reconciliation. |

## Development

```bash
pip install -e ".[dev]"
pytest                  # tests (no network, no API keys)
ruff check .            # lint
ruff format .           # format
mypy                    # types (strict)
./scripts/check.sh      # all of the above, as in CI
```

The PayPal client is tested against a mocked HTTP transport and the agent against a scripted model. The test suite does not call the real PayPal sandbox or the Claude API.

The project deliberately constrains the Anthropic SDK to `anthropic>=1,<2`. In a clean
Python 3.14 environment, the tested 1.17.0 release imports and passes the complete suite;
the unconstrained 2.6.0 release did not complete its import within 20 seconds (#135). This
is a local development compatibility guard, not evidence of an Anthropic API request or
a permanent rejection of the 2.x API. The supported CI matrix remains Python 3.11/3.12.

## Documentation

| Document | Purpose |
|----------|---------|
| [AGENTS.md](AGENTS.md) | How we work: issues, branches, commits, PRs |
| [docs/architecture.md](docs/architecture.md) | How it works inside |
| [docs/project-structure.md](docs/project-structure.md) | Where everything is and where it goes |
| [docs/demo-script.md](docs/demo-script.md) | Script for the under-3-minute demo video |
| [docs/submission-checklist.md](docs/submission-checklist.md) | Judge-safe recording and submission checklist |
| [docs/versioning.md](docs/versioning.md) | Versions and releases |
| [docs/adr/](docs/adr/) | Architecture decisions |

## Built with

Python, FastAPI, SQLite, httpx, PayPal Invoicing v2 API (sandbox), Anthropic Claude API (tool use).

## License

[MIT](LICENSE).
