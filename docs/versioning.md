# Versions and releases

## 1. Principle: versions live in Git, not in folders

- **Forbidden:** creating folders or copies such as `v1/`, `v2/`, `old/`, `final_project.py`, `backup/`.
- A version is a **Git tag** on a `main` commit. To look at any old version:
  ```bash
  git checkout v0.3.0       # inspect
  git switch main           # go back
  ```
- Deleted code is recovered from history (`git log -- path`, `git show <commit>:path`), not from copies.

---

## 2. Scheme: Semantic Versioning (SemVer)

Format `MAJOR.MINOR.PATCH`, for example `1.4.2`.

| Bump    | When                                                                    | Example in this project                                   |
|---------|-------------------------------------------------------------------------|-----------------------------------------------------------|
| `MAJOR` | **Breaking** change: old saved data or public API stop working          | Changing the format of a configuration file               |
| `MINOR` | **New, compatible** functionality                                       | Adding a new command                                      |
| `PATCH` | Bug **fix**, without changing intended behaviour                        | Fixing a wrong calculation                                |

When a number goes up, the ones to its right go back to 0: `0.4.3` → `0.5.0`.

### `0.x` phase (current phase)
While `MAJOR` is `0`, the project is in early development:
- Breaking changes bump `MINOR` (`0.4.0` → `0.5.0`).
- Compatible changes and fixes bump `PATCH`.
- `1.0.0` is published when the public API and data formats are considered stable. That decision is recorded with an ADR.

### Pre-releases (optional)
To test before publishing: `0.5.0rc1`, `0.5.0rc2` → `0.5.0` (PEP 440 format, compatible with pip).

---

## 3. From commits to version

The Conventional Commit types (see [AGENTS.md](../AGENTS.md)) decide the bump:

| Commits since the last version           | Bump (in 1.x+) | Bump (in 0.x)  |
|------------------------------------------|----------------|----------------|
| Any with `!` or `BREAKING CHANGE:`       | MAJOR          | MINOR          |
| Any `feat:`                              | MINOR          | MINOR or PATCH |
| Only `fix:`, `perf:`                     | PATCH          | PATCH          |
| Only `docs:`, `test:`, `chore:`, `ci:`…  | no release needed | no release needed |

---

## 4. Where the version lives

**Single source of truth: `version` in [pyproject.toml](../pyproject.toml).**

- `paypal_invoice_steward.__version__` reads it automatically from the installed package. The version is **never** written by hand anywhere else.
- The Git tag must match: `version = "0.2.0"` ↔ tag `v0.2.0`.

---

## 5. CHANGELOG.md

Format [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

- Every PR that changes behaviour adds a line under **`[Unreleased]`**, in the right category:
  `Added` · `Changed` · `Deprecated` · `Removed` · `Fixed` · `Security`
- It is written for users: what changes for them, not internal details.
- PRs that are only `docs`/`test`/`chore`/`ci` need no entry.

---

## 6. Release procedure (step by step)

It is done on its own branch and goes through a PR, like any other change.

```bash
# 1. Start from an up-to-date main
git switch main && git pull --ff-only
git switch -c chore/release-v0.2.0

# 2. Bump the version in pyproject.toml
#    version = "0.2.0"

# 3. In CHANGELOG.md:
#    - Rename [Unreleased] to [0.2.0] - YYYY-MM-DD
#    - Create an empty [Unreleased] section above it
#    - Update the comparison links at the end

# 4. Verify
ruff check . && ruff format --check . && pytest

# 5. Commit and PR
git commit -am "chore(release): v0.2.0"
git push -u origin HEAD
gh pr create --title "chore(release): v0.2.0" --body "Release v0.2.0. See CHANGELOG."

# 6. After the (squash) merge, tag the resulting commit on main
git switch main && git pull --ff-only
git tag -a v0.2.0 -m "v0.2.0"
git push origin v0.2.0

# 7. Publish the release on GitHub with the CHANGELOG notes
gh release create v0.2.0 --title "v0.2.0" --notes-file <(sed -n '/^## \[0.2.0\]/,/^## \[/p' CHANGELOG.md | sed '$d')
```

**Tags are never moved or deleted** once published. If a release goes wrong, a new PATCH version with the fix is published.

---

## 7. Hotfix on a published version

While only the latest version is maintained (the current situation), a hotfix is a normal `fix/` followed by a PATCH release.

If an old version ever has to be maintained (e.g. `0.4.x` while `main` is at `0.6`):

```bash
git switch -c release/0.4 v0.4.2      # maintenance branch from the tag
git switch -c fix/88-save-crash
# ... fix + PR against release/0.4 ...
# release v0.4.3 from release/0.4; then bring the fix to main with cherry-pick
```

`release/X.Y` branches are only created when needed, and that is recorded in an ADR.

---

## 8. Data compatibility

Files the user creates or saves with the project (configuration, exported data, saved state) are contracts with the user:
- They include a `schema_version` field.
- Changing their format in a breaking way = breaking bump (MINOR in `0.x`, MAJOR in `1.x+`).
- If reasonable, the project migrates old formats automatically.
