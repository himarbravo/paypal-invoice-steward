# Architecture

> Living document. Update it in the same PR that changes a module or the relationship between modules. For where files live, see [project-structure.md](project-structure.md).

## Overview

<!-- What the system does and how data flows from input to output. A short diagram helps. -->

Pending.

## Modules

| Module        | Status  | Notes |
|---------------|---------|-------|
| `core`        | In progress | `models`, `ports`, `forecast`, `proposals`, `agent` ([ADR 0004](adr/0004-invoice-steward-architecture.md)) |
| `persistence` | In progress | `store` (SQLite `ProposalStore`), `paypal_sandbox`, `paypal_demo`, `anthropic_client` |
| `ui`          | In progress | `config`, `web`, `static/index.html` |

## Relevant decisions

See [adr/](adr/).
