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
2. `cp .env.example .env` and fill in `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` and, optionally, `ANTHROPIC_API_KEY`.
3. `paypal-invoice-steward`

The PayPal client refuses any base URL that is not the sandbox, so a misconfiguration cannot touch real money.

## Safety model

| Risk | What prevents it |
|------|------------------|
| The model sends something it should not | The agent's tools only read and *propose*. A test checks that no tool can send, confirm, pay, cancel or delete. |
| You approve one thing and another is sent | Each proposal carries a hash of its content. Confirming requires the hash you reviewed. |
| Double click or two tabs | Status changes are compare-and-swap in SQLite: exactly one request executes. |
| Timeout after PayPal already sent | The proposal becomes *unverified*, never *failed*. "Check PayPal" looks the invoice up by its reference (`STW-xxxxxxxx`, used as the invoice number) before anything is retried, so there are no duplicates. |
| Reminder with an unknown outcome | Never retried automatically; a person checks PayPal first. |
| Unexpected PayPal status | Shown as unknown, left out of the forecast, no reminders. |
| Risky input | Server-side policy: maximum amount, EUR/USD/GBP only, 1 to 90 day terms, reminders only for open invoices that are overdue or due within 3 days, 3-day cooldown. |

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

## Documentation

| Document | Purpose |
|----------|---------|
| [AGENTS.md](AGENTS.md) | How we work: issues, branches, commits, PRs |
| [docs/architecture.md](docs/architecture.md) | How it works inside |
| [docs/project-structure.md](docs/project-structure.md) | Where everything is and where it goes |
| [docs/demo-script.md](docs/demo-script.md) | Script for the under-3-minute demo video |
| [docs/versioning.md](docs/versioning.md) | Versions and releases |
| [docs/adr/](docs/adr/) | Architecture decisions |

## Built with

Python, FastAPI, SQLite, httpx, PayPal Invoicing v2 API (sandbox), Anthropic Claude API (tool use).

## License

[MIT](LICENSE).
