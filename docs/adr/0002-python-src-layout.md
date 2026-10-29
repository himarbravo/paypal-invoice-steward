# 0002. Python 3.11+ con src layout, pip y pyproject.toml

- **Estado:** Aceptada
- **Fecha:** 2026-10-02

## Contexto

Hay que elegir lenguaje y forma de empaquetar el proyecto. Importan la claridad del código, un ecosistema amplio de librerías y la facilidad para testear.

## Decisión

- **Python ≥ 3.11.**
- **src layout** (`src/my_project/`) empaquetado con `pyproject.toml` y backend `hatchling`.
- Entorno con `venv` + `pip install -e ".[dev]"`.
- **ruff** para lint y formato, y **pytest** para tests.
- La versión se define solo en `pyproject.toml` (ver [versioning.md](../versioning.md)).

## Alternativas consideradas

- **Flat layout** (`my_project/` en la raíz): más simple, pero permite que los tests pasen importando archivos sin instalar el paquete.
- **uv / poetry:** más rápidos y con lockfile integrado; se pueden adoptar más adelante con un nuevo ADR sin cambiar la estructura.

## Consecuencias

- Hay que instalar el paquete en modo editable para desarrollar.
- Sin lockfile por ahora: las dependencias se declaran con versión mínima. Revisar al añadir dependencias de ejecución.
