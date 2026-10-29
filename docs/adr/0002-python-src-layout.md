# 0002. Python 3.11+ with src layout, pip and pyproject.toml

- **Status:** Accepted
- **Date:** 2026-10-02

> Translated to English on 2026-10-29 without changing its meaning, as allowed by [ADR 0003](0003-english-project-language.md).

## Context

A language and a way to package the project must be chosen. Code clarity, a broad library ecosystem and ease of testing matter.

## Decision

- **Python ≥ 3.11.**
- **src layout** (`src/paypal_invoice_steward/`) packaged with `pyproject.toml` and the `hatchling` backend.
- Environment with `venv` + `pip install -e ".[dev]"`.
- **ruff** for lint and format, and **pytest** for tests.
- The version is defined only in `pyproject.toml` (see [versioning.md](../versioning.md)).

## Alternatives considered

- **Flat layout** (`paypal_invoice_steward/` at the root): simpler, but lets tests pass by importing files without installing the package.
- **uv / poetry:** faster and with a built-in lockfile; they can be adopted later with a new ADR without changing the structure.

## Consequences

- The package has to be installed in editable mode for development.
- No lockfile for now: dependencies are declared with a minimum version. Review this when adding runtime dependencies.
