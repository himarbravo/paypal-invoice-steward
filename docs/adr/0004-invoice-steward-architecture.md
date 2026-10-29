# 0004. Invoice Steward architecture on the seed's layers

- **Status:** Accepted
- **Date:** 2026-10-29

## Context

Invoice Steward was prototyped outside this repository as a flat `steward/` package: a FastAPI app, a PayPal Invoicing v2 client, an in-memory demo PayPal, a SQLite store, a cash-flow forecast and a Claude tool-use agent. It has to move into the seed's `core` / `persistence` / `ui` layers, where `core` imports nothing, `persistence` imports only `core`, and nobody imports `ui` (checked by `tests/test_architecture.py`).

Two parts of the prototype broke that rule: the proposal service used the SQLite store directly, and the agent was built around the Anthropic SDK.

## Decision

**Layers**

| Layer | Module | Responsibility |
|-------|--------|----------------|
| `core` | `models.py` | `Invoice` and invoice totals |
| `core` | `ports.py` | Interfaces: `PayPalPort`, `ProposalStore`, `LLMClient`; `PayPalError` and `PayPalUncertain` |
| `core` | `forecast.py` | Payment habits and Monte Carlo cash-flow forecast |
| `core` | `proposals.py` | Policy, payload hash, confirmation and idempotent execution |
| `core` | `agent.py` | Agent tools (read and propose only), tool-use loop, offline assistant |
| `persistence` | `store.py` | SQLite `ProposalStore` |
| `persistence` | `paypal_sandbox.py` | PayPal Invoicing v2 client (sandbox only) |
| `persistence` | `paypal_demo.py` | In-memory PayPal for the demo, with failure injection |
| `persistence` | `anthropic_client.py` | `LLMClient` backed by the Anthropic SDK |
| `ui` | `config.py` | Settings from environment variables |
| `ui` | `web.py`, `static/` | FastAPI app and single-page interface |

`core` reaches the outside world only through the three ports, and `ui` wires the concrete implementations together. The package entry point (`__main__.py`) starts the web server; it sits outside the three layers, so it may import `ui`.

**Runtime dependencies**, added in the PR that first needs each one:

- `httpx`: HTTP client for PayPal, with a mock transport for tests.
- `anthropic`: Claude API.
- `fastapi`, `uvicorn`: web app and server.
- `python-dotenv`: reading a local `.env`.

## Alternatives considered

- **Keep the flat package:** no migration work, but it ignores the seed's dependency rules and its architecture test.
- **Use the PayPal Agent Toolkit instead of our own client:** less code, but its agent tools execute actions (send, cancel), which the safety model forbids for the agent. It can still be used later behind `PayPalPort`, with a new ADR.

## Consequences

- `core` can be tested without network, database or API keys.
- Adding a PayPal or LLM backend means implementing a port in `persistence`, not touching `core`.
- The migration is split into one PR per part, in the order of the table, so each one passes CI on its own.
