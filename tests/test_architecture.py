"""Hace cumplir las reglas de dependencia entre subpaquetes.

Las reglas están descritas en docs/project-structure.md, sección 3.
"""

import ast
from collections.abc import Iterator
from pathlib import Path

import my_project

PACKAGE = my_project.__name__
ROOT = Path(my_project.__file__).parent

# Subpaquete -> subpaquetes que puede importar.
# Añadir un subpaquete de primer nivel requiere un ADR y una línea aquí.
ALLOWED: dict[str, set[str]] = {
    "core": set(),
    "persistence": {"core"},
    "ui": {"core", "persistence"},
}


def imported_modules(path: Path) -> Iterator[str]:
    """Nombres absolutos de todo lo que importa un archivo."""
    package = (PACKAGE, *path.relative_to(ROOT).parts[:-1])
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = list(package[: len(package) - node.level + 1]) if node.level else []
            module = ".".join([*base, *([node.module] if node.module else [])])
            yield module
            yield from (f"{module}.{alias.name}" for alias in node.names)


def test_every_subpackage_declares_its_dependencies():
    subpackages = {p.parent.name for p in ROOT.glob("*/__init__.py")}
    assert subpackages == set(ALLOWED)


def test_subpackages_only_import_what_they_are_allowed():
    violations = []
    for subpackage, allowed in ALLOWED.items():
        for path in (ROOT / subpackage).rglob("*.py"):
            for module in imported_modules(path):
                parts = module.split(".")
                if parts[0] != PACKAGE or len(parts) < 2 or parts[1] not in ALLOWED:
                    continue
                if parts[1] != subpackage and parts[1] not in allowed:
                    violations.append(f"{path.relative_to(ROOT)} importa {parts[1]}")
    assert not violations, "Dependencias no permitidas: " + "; ".join(sorted(set(violations)))
