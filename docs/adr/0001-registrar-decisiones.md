# 0001. Record architecture decisions with ADRs

- **Status:** Accepted
- **Date:** 2026-10-02

> Translated to English on 2026-10-29 without changing its meaning, as allowed by [ADR 0003](0003-english-project-language.md).

## Context

The project will accumulate code and several people and agents will work on it. Without a record, the reason for each decision is lost and settled questions get discussed again.

## Decision

Every non-trivial design decision is documented in `docs/adr/NNNN-title.md`, starting from [0000-template.md](0000-template.md). ADRs are immutable: if a decision changes, a new one is created and the old one becomes "Superseded by".

## Consequences

- An ADR must be written before creating a top-level module, adding an important dependency or changing a data format.
- The history of reasoning stays in the repository, next to the code.
