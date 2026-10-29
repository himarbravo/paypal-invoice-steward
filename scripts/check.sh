#!/usr/bin/env bash
# Runs the same checks as CI. Use it before opening or updating a PR.
#
# Usage (from the repository root, with the environment activated):  ./scripts/check.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ruff check .
ruff format --check .
mypy
pytest
