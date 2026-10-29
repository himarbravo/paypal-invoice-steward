"""Convierte la semilla en un proyecto con nombre propio.

Sustituye el nombre provisional `my-project` en todos los archivos, renombra el
paquete `src/my_project/`, borra del README la sección de uso de la semilla,
borra el workflow que prueba la semilla y se borra a sí mismo.

Uso (desde la raíz del repositorio, una sola vez):

    python3 scripts/init_project.py mi-proyecto --owner usuario --author "Nombre" \
        --description "Qué hace el proyecto"
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
SEED_SECTION = re.compile(r"<!-- seed:start -->.*?<!-- seed:end -->\n\n?", re.DOTALL)


def text_files() -> list[Path]:
    this_script = Path(__file__).resolve()
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path == this_script:
            continue
        if SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicializa un proyecto desde la semilla.")
    parser.add_argument("name", help="nombre del proyecto en kebab-case, p. ej. mi-proyecto")
    parser.add_argument("--owner", help="usuario u organización de GitHub")
    parser.add_argument("--author", help="autor que figura en pyproject.toml")
    parser.add_argument("--description", help="descripción corta del proyecto")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", args.name):
        sys.exit("El nombre debe estar en kebab-case: minúsculas, cifras y guiones.")
    if not (ROOT / "src" / "my_project").is_dir():
        sys.exit("No existe src/my_project/: este proyecto ya está inicializado.")

    package = args.name.replace("-", "_")
    year = date.today().year
    replacements = {
        "(c) YEAR": f"(c) {year}",
        "my-project": args.name,
        "my_project": package,
        "My Project": args.name.replace("-", " ").title(),
    }
    if args.owner:
        replacements["github.com/OWNER/"] = f"github.com/{args.owner}/"
    if args.author:
        replacements['name = "AUTHOR"'] = f'name = "{args.author}"'
        replacements[f"(c) {year} AUTHOR"] = f"(c) {year} {args.author}"
    if args.description:
        replacements["Descripción corta del proyecto."] = args.description

    for path in text_files():
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = original
        if path == ROOT / "README.md":
            text = SEED_SECTION.sub("", text)
        for old, new in replacements.items():
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8")

    (ROOT / "src" / "my_project").rename(ROOT / "src" / package)
    (ROOT / ".github" / "workflows" / "seed.yml").unlink(missing_ok=True)
    Path(__file__).unlink()
    print(f"Proyecto inicializado como {args.name} (paquete {package}).")


if __name__ == "__main__":
    main()
