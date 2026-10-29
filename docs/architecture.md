# Architecture

> Living document. Update it in the same PR that changes a module or the relationship between modules. For where files live, see [project-structure.md](project-structure.md).

## Overview

Invoice Steward reads invoices from PayPal, forecasts when they will be paid, and lets an assistant prepare invoices and reminders that a person must confirm.

```
 browser ──► ui/web.py ──► core/agent.py ──► core/proposals.py ──► (pending proposal)
                │                                   ▲
                │   person clicks "Send" ───────────┘ confirm(hash)
                │                                   │
                ▼                                   ▼
        core/forecast.py ◄── PayPalPort ◄──  persistence/paypal_sandbox.py
                                              persistence/paypal_demo.py
                         ProposalStore ◄──  persistence/store.py (SQLite)
                         LLMClient     ◄──  persistence/anthropic_client.py
```

1. A chat message goes to the assistant (`LLMAgent` with Claude, or `OfflineAgent`).
2. The assistant can only call read tools and `propose_*` tools. Proposing validates the policy and stores a *pending* proposal with a payload hash; nothing is sent.
3. The interface shows the proposal as a card. Confirming sends the hash the person reviewed.
4. `ProposalService.confirm` moves the proposal to *executing* with a compare-and-swap, looks the invoice up by its reference, then creates and sends it, or sends the reminder.
5. The outcome is *done*, *failed* (PayPal refused) or *unverified* (unknown); an unverified invoice is resolved with "Check PayPal".

## Modules

| Module | Status | Notes |
|--------|--------|-------|
| `core` | Done | `models`, `ports`, `forecast`, `proposals`, `agent` |
| `persistence` | Done | `store` (SQLite), `paypal_sandbox`, `paypal_demo`, `anthropic_client` |
| `ui` | Done | `config`, `web`, `static/index.html` |

`core` reaches the outside world only through the ports in `core/ports.py`; `ui/web.py` wires the concrete implementations. See [ADR 0004](adr/0004-invoice-steward-architecture.md).

## Relevant decisions

See [adr/](adr/).
