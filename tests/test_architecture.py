"""Enforces the dependency rules between subpackages.

The rules are described in docs/project-structure.md, section 3.
"""

import ast
from collections.abc import Iterator
from pathlib import Path

import paypal_invoice_steward

PACKAGE = paypal_invoice_steward.__name__
ROOT = Path(paypal_invoice_steward.__file__).parent

# Subpackage -> subpackages it may import.
# Adding a top-level subpackage requires an ADR and a line here.
ALLOWED: dict[str, set[str]] = {
    "core": set(),
    "persistence": {"core"},
    "ui": {"core", "persistence"},
}


def imported_modules(path: Path) -> Iterator[str]:
    """Absolute names of everything a file imports."""
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
                    violations.append(f"{path.relative_to(ROOT)} imports {parts[1]}")
    assert not violations, "Dependencies not allowed: " + "; ".join(sorted(set(violations)))
