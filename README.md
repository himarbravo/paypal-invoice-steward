# My Project

Descripción corta del proyecto.

> Estado: desarrollo inicial (`0.x`). Ver [CHANGELOG.md](CHANGELOG.md).

<!-- seed:start -->
## Cómo usar esta semilla

Este repositorio es una plantilla: un proyecto Python vacío con el protocolo de trabajo, la documentación base y la CI ya montados. El nombre `my-project` es provisional.

1. Crea tu repositorio a partir de la plantilla y clónalo:
   ```bash
   gh repo create <usuario>/<nombre> --private --template himarbravo/project-seed --clone
   cd <nombre>
   ```
2. Renombra el proyecto. El script sustituye el nombre en todos los archivos, renombra el paquete, borra esta sección y se borra a sí mismo:
   ```bash
   python3 scripts/init_project.py <nombre> --owner <usuario> --author "<Tu nombre>" \
       --description "<Qué hace el proyecto>"
   ```
3. Instala, comprueba y sube el primer commit:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ./scripts/check.sh
   git add -A && git commit -m "chore: inicializar proyecto desde la semilla" && git push
   ```
4. Configura el repositorio: crea los labels que usa [AGENTS.md](AGENTS.md), deja solo squash merge y protege `main`. Va después del primer push, porque a partir de aquí ya no se puede empujar directo a `main`:
   ```bash
   ./scripts/setup_github.sh
   ```
5. Adapta lo que es propio de cada proyecto: [docs/architecture.md](docs/architecture.md), [docs/project-structure.md](docs/project-structure.md) y la sección 4 de [AGENTS.md](AGENTS.md).
<!-- seed:end -->

## Requisitos

- Python 3.11 o superior

## Instalación para desarrollo

```bash
git clone https://github.com/OWNER/my-project.git
cd my-project
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Uso

```bash
my-project              # o: python -m my_project
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
