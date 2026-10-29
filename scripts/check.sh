#!/usr/bin/env bash
# Ejecuta los mismos checks que la CI. Úsalo antes de abrir o actualizar un PR.
#
# Uso (desde la raíz, con el entorno activado):  ./scripts/check.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ruff check .
ruff format --check .
mypy
pytest
