#!/usr/bin/env bash
# Configura el repositorio de GitHub para que el protocolo de AGENTS.md se cumpla solo:
# labels, solo squash merge y protección de `main`.
#
# Lo ejecuta una persona con permisos de administración, una vez, DESPUÉS del
# primer push a `main` (con la protección activa ya no se puede empujar directo).
#
# Uso (desde la raíz):  ./scripts/setup_github.sh
set -euo pipefail

repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "Configurando $repo"

label() { gh label create "$1" --color "$2" --description "$3" --force -R "$repo" >/dev/null; }
label "type:feature"  "1D76DB" "Nueva funcionalidad o mejora"
label "type:bug"      "D73A4A" "Algo no funciona como debería"
label "type:refactor" "5319E7" "Cambio interno sin cambiar comportamiento"
label "type:docs"     "0E8A16" "Documentación"
label "type:chore"    "BFBFBF" "Mantenimiento, CI, configuración"
echo "Labels creados."

gh repo edit "$repo" --enable-squash-merge --enable-merge-commit=false \
    --enable-rebase-merge=false --delete-branch-on-merge
echo "Merge: solo squash, y la rama se borra al mergear."

# Nadie empuja directo a main (tampoco administradores); todo PR necesita la CI en verde.
# No se exigen aprobaciones para que funcione en proyectos de una sola persona.
if gh api -X PUT "repos/$repo/branches/main/protection" --input - >/dev/null <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["required", "conventions"] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
then
    echo "Rama main protegida."
else
    echo "No se pudo proteger main. En repositorios privados hace falta un plan de pago" >&2
    echo "de GitHub; hasta entonces, la regla depende de que se respete AGENTS.md." >&2
    exit 1
fi
