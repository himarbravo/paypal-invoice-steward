# scripts/

Development utilities: generating data, profiling, maintenance tasks.

- They are not part of the installed package.
- `src/` never imports anything from here.
- Every script starts with a docstring or comment explaining what it does and how to run it.

| Script | Purpose |
|--------|---------|
| `check.sh` | Runs the same checks as CI |
| `setup_github.sh` | Sets up labels, squash merge and `main` protection (run by a person) |
