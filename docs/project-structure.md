# Project map: where everything is and where it goes

Before creating a file, check this guide. If something does not fit anywhere, **do not invent a folder**: open an issue and propose the change with an ADR (see [adr/](adr/)).

---

## 1. Overview

```
paypal-invoice-steward/
├── AGENTS.md                      # Working protocol (GitHub, branches, commits, PRs)
├── CLAUDE.md                      # Imports AGENTS.md for Claude Code
├── GEMINI.md                      # Imports AGENTS.md for Gemini CLI
├── LICENSE                        # Project license (MIT by default)
├── README.md                      # What the project is and how to start it
├── CHANGELOG.md                   # Change history by version
├── pyproject.toml                 # Metadata, VERSION, dependencies and tool config
├── .editorconfig                  # Basic style shared by all editors
├── .gitignore                     # What Git must never store
│
├── .github/
│   ├── workflows/                 # CI: lint, types and tests (ci.yml); PR conventions (pr.yml)
│   ├── dependabot.yml             # Automatic dependency and action updates
│   ├── ISSUE_TEMPLATE/            # Issue templates (feature, bug, task)
│   ├── copilot-instructions.md    # Points Copilot to AGENTS.md
│   └── pull_request_template.md
│
├── docs/
│   ├── project-structure.md       # ← this file
│   ├── architecture.md            # How the system works inside
│   ├── versioning.md              # How versions and releases are made
│   └── adr/                       # Architecture decision records
│
├── src/paypal_invoice_steward/    # PROJECT CODE (the Python package)
│   ├── __init__.py                # Exposes __version__
│   ├── __main__.py                # Entry point (python -m paypal_invoice_steward)
│   ├── core/                      # Domain core: concepts, rules and interfaces
│   ├── persistence/               # Input/output: files, network, databases, APIs
│   └── ui/                        # CLI and presentation
│
├── tests/                         # Tests: same structure as src/paypal_invoice_steward/
│   ├── core/  persistence/  ui/
│   ├── test_architecture.py       # Enforces the dependency rules
│   └── test_package.py
│
└── scripts/                       # Development utilities (not part of the package)
```

---

## 2. What goes in each folder

### `src/paypal_invoice_steward/`: the product
All the code that is installed with the package. We use the *src layout*: tests always run against the installed package, never against loose files.

Each subpackage describes its responsibility and what it may depend on in its `__init__.py`. **Read it before adding code there.**

| Subpackage    | Contains                                          | Example files                  |
|---------------|---------------------------------------------------|--------------------------------|
| `core`        | Domain concepts and rules, base interfaces        | `models.py`, `rules.py`        |
| `persistence` | Reading and writing data outside the program      | `loader.py`, `export.py`       |
| `ui`          | What the user sees or uses                        | `cli.py`, `render.py`          |

These are the three minimum layers. A small project may delete the one it does not use; a large one will add domain subpackages between `core` and `persistence` (with an issue and an ADR).

### `tests/`: the tests
- **Mirror of `src/`**: the test for `src/paypal_invoice_steward/core/rules.py` goes in `tests/core/test_rules.py`.
- Files `test_<module>.py`, functions `test_<behaviour>()`.
- Shared fixtures in `conftest.py`, in the lowest folder where they are used.
- If a test needs randomness, **fix the seed**.

### `docs/`: documentation for people
- `architecture.md`: general technical overview. Updated when a module or a relationship between modules changes.
- `adr/`: one important decision = one numbered file. See [adr/0000-template.md](adr/0000-template.md).
- `versioning.md`: versions and releases process.

### `scripts/`: helper tools
Development scripts: generating test data, profiling, etc. They are **not** imported from `src/`. If a script becomes useful to the end user, it becomes a package command.

### `.github/`: process automation
CI and templates. Changed only through a PR of type `ci:` or `chore:`.

---

## 3. Dependency rules between modules

Dependencies between subpackages go in **one direction only**: the most stable at the bottom, the most changeable at the top. Never in a circle.

```
          ┌──────┐
          │  ui  │  (nobody depends on ui)
          └──┬───┘
             │
      ┌──────▼──────┐
      │ persistence │  (the domain never imports it)
      └──────┬──────┘
             │
        ┌────▼────┐
        │  core   │  (depends on nobody)
        └─────────┘
```

Arrows point to what may be imported. **Never upwards.** If `core` needs something from outside (reading a file, for example), it defines an interface and `persistence` implements it.

These rules are checked by [tests/test_architecture.py](../tests/test_architecture.py). If the test fails, fix the import; the test's dependency table only changes together with an ADR.

---

## 4. Deciding where something new goes

| If you are going to…                       | It goes in                                         |
|--------------------------------------------|----------------------------------------------------|
| Add a domain concept or rule               | `src/paypal_invoice_steward/core/`                 |
| Read or save a new data format             | `src/paypal_invoice_steward/persistence/`          |
| Add a command or a view                    | `src/paypal_invoice_steward/ui/`                   |
| Add a test                                 | `tests/`, in the mirror path                       |
| Add a development script                   | `scripts/`                                         |
| Add a dependency                           | `pyproject.toml` (justify it in the PR)            |
| Make a non-trivial design decision         | `docs/adr/NNNN-title.md`                           |
| Create a new top-level subpackage          | Issue and ADR **before** creating it               |

**When to split a file:** if a module goes beyond about 300-400 lines or mixes two responsibilities, it becomes a subpackage (`rules.py` → `rules/__init__.py`, `rules/pricing.py`...).

---

## 5. Naming conventions

| Element           | Convention              | Example                     |
|-------------------|-------------------------|-----------------------------|
| Packages/modules  | `snake_case`, singular  | `core/rules.py`             |
| Classes           | `PascalCase`            | `class Report`              |
| Functions/vars    | `snake_case`            | `compute_total()`           |
| Constants         | `UPPER_SNAKE_CASE`      | `MAX_RETRIES`               |
| Private           | `_` prefix              | `_update_cache()`           |
| Tests             | `test_<what>.py`        | `tests/core/test_rules.py`  |
| ADRs              | `NNNN-kebab-title.md`   | `0003-data-format.md`       |

Everything is written in **English**: identifiers, docstrings, comments and documentation ([ADR 0003](adr/0003-english-project-language.md)).
