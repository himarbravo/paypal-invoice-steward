# 0003. English as the single project language

- **Status:** Accepted
- **Date:** 2026-10-29

## Context

The seed this project comes from (`himarbravo/project-seed`) writes identifiers in English and docstrings, comments and documentation in Spanish. Two things make a mixed language a problem here:

- The project is a PayPal AI Hackathon entry. The official rules require the description, testing instructions, video and all other materials in English, and the judges read the repository.
- Himar asked on 2026-10-29 for everything in the project, and in the seed, to be in English.

## Decision

Everything in the repository and on GitHub is written in English: code, docstrings, comments, documentation, ADRs, issues, pull requests, commit messages, CI messages and script output.

Accepted ADRs keep their rule of not being modified, with one exception: ADRs 0000 to 0002 are translated to English once, without changing their meaning. The translation is done in its own PR so the diff can be checked against the original.

## Alternatives considered

- **English only for submission materials** (README, description, testing instructions), Spanish for the rest: less work, but judges would find half the repository in Spanish, and the project owner asked for English throughout.
- **Leave ADRs 0001 and 0002 in Spanish** as historical records: respects ADR immutability literally, but leaves Spanish text in a repository whose rule is now English only.

## Consequences

- AGENTS.md section 4 changes: identifiers, docstrings, comments and documentation are all in English.
- Commit summaries are written in English (AGENTS.md 2.3).
- The remaining Spanish text is translated in a follow-up issue.
- Future ADRs, including any that replace ADR 0001 or 0002, are written in English.
