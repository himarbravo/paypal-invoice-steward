# PayPal Invoice Steward

AI agent that chases late PayPal invoices and forecasts cash flow; it proposes, a human confirms.

> Status: early development (`0.x`). See [CHANGELOG.md](CHANGELOG.md).

## Requirements

- Python 3.11 or later

## Development install

```bash
git clone https://github.com/himarbravo/paypal-invoice-steward.git
cd paypal-invoice-steward
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
paypal-invoice-steward              # or: python -m paypal_invoice_steward
```

## Development

```bash
pytest                  # tests
ruff check .            # lint
ruff format .           # format
mypy                    # types
./scripts/check.sh      # all of the above, as in CI
```

## Documentation

| Document | Purpose |
|----------|---------|
| [AGENTS.md](AGENTS.md) | How we work: issues, branches, commits, PRs |
| [docs/project-structure.md](docs/project-structure.md) | Where everything is and where it goes |
| [docs/architecture.md](docs/architecture.md) | How it works inside |
| [docs/versioning.md](docs/versioning.md) | Versions and releases |
| [docs/adr/](docs/adr/) | Architecture decisions |

## License

[MIT](LICENSE). If the project needs another one, change `LICENSE` and the `license` field in `pyproject.toml`.
