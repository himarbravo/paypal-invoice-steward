#!/usr/bin/env bash
# Configures the GitHub repository so the AGENTS.md protocol enforces itself:
# labels, squash merge only and `main` protection.
#
# A person with admin rights runs it once, AFTER the first push to `main`
# (once protection is on, nobody can push directly).
#
# Usage (from the repository root):  ./scripts/setup_github.sh
set -euo pipefail

repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "Configuring $repo"

label() { gh label create "$1" --color "$2" --description "$3" --force -R "$repo" >/dev/null; }
label "type:feature"  "1D76DB" "New functionality or improvement"
label "type:bug"      "D73A4A" "Something does not work as it should"
label "type:refactor" "5319E7" "Internal change without behaviour change"
label "type:docs"     "0E8A16" "Documentation"
label "type:chore"    "BFBFBF" "Maintenance, CI, configuration"
echo "Labels created."

gh repo edit "$repo" --enable-squash-merge --enable-merge-commit=false \
    --enable-rebase-merge=false --delete-branch-on-merge
echo "Merge: squash only, and the branch is deleted on merge."

# Nobody pushes directly to main (admins included); every PR needs green CI.
# No approvals are required, so it works for one-person projects.
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
    echo "Branch main protected."
else
    echo "Could not protect main. Private repositories need a paid GitHub plan;" >&2
    echo "until then, the rule depends on people following AGENTS.md." >&2
    exit 1
fi
