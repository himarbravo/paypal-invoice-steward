# Paypal Invoice Steward

AI agent that chases late PayPal invoices and forecasts cash flow; it proposes, a human confirms.

> Estado: desarrollo inicial (`0.x`). Ver [CHANGELOG.md](CHANGELOG.md).

## Requisitos

- Python 3.11 o superior

## Instalación para desarrollo

```bash
git clone https://github.com/himarbravo/paypal-invoice-steward.git
cd paypal-invoice-steward
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Uso

```bash
paypal-invoice-steward              # o: python -m paypal_invoice_steward
```

## Desarrollo

```bash
pytest                  # tests
ruff check .            # lint
ruff format .           # formato
mypy                    # tipos
./scripts/check.sh      # todo lo anterior, como en la CI
```

## Documentación

| Documento | Para qué |
|-----------|----------|
| [AGENTS.md](AGENTS.md) | Cómo se trabaja: issues, ramas, commits, PRs |
| [docs/project-structure.md](docs/project-structure.md) | Dónde está y dónde va cada cosa |
| [docs/architecture.md](docs/architecture.md) | Cómo funciona por dentro |
| [docs/versioning.md](docs/versioning.md) | Versiones y releases |
| [docs/adr/](docs/adr/) | Decisiones de arquitectura |

## Licencia

[MIT](LICENSE). Si el proyecto necesita otra, cambia `LICENSE` y el campo `license` de `pyproject.toml`.
