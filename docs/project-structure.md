# Mapa del proyecto: dónde está y dónde va cada cosa

Antes de crear un archivo, consulta esta guía. Si algo no encaja en ningún sitio, **no inventes una carpeta**: abre un issue y propón el cambio con un ADR (ver [adr/](adr/)).

---

## 1. Vista general

```
paypal-invoice-steward/
├── AGENTS.md                  # Protocolo de trabajo (GitHub, ramas, commits, PRs)
├── CLAUDE.md                  # Importa AGENTS.md para Claude Code
├── GEMINI.md                  # Importa AGENTS.md para Gemini CLI
├── LICENSE                    # Licencia del proyecto (MIT por defecto)
├── README.md                  # Qué es el proyecto y cómo arrancarlo
├── CHANGELOG.md               # Historial de cambios por versión
├── pyproject.toml             # Metadatos, VERSIÓN, dependencias y config de herramientas
├── .editorconfig              # Estilo básico común a todos los editores
├── .gitignore                 # Lo que Git nunca debe guardar
│
├── .github/
│   ├── workflows/             # CI: lint, tipos y tests (ci.yml); convenciones del PR (pr.yml)
│   ├── dependabot.yml         # Actualización automática de dependencias y acciones
│   ├── ISSUE_TEMPLATE/        # Plantillas de issues (feature, bug, tarea)
│   ├── copilot-instructions.md  # Dirige a Copilot a AGENTS.md
│   └── pull_request_template.md
│
├── docs/
│   ├── project-structure.md   # ← este archivo
│   ├── architecture.md        # Cómo funciona el sistema por dentro
│   ├── versioning.md          # Cómo se versiona y se publica una release
│   └── adr/                   # Registro de decisiones de arquitectura
│
├── src/paypal_invoice_steward/            # CÓDIGO DEL PROYECTO (el paquete Python)
│   ├── __init__.py            # Expone __version__
│   ├── __main__.py            # Punto de entrada (python -m paypal_invoice_steward)
│   ├── core/                  # Núcleo del dominio: conceptos, reglas e interfaces
│   ├── persistence/           # Entrada/salida: archivos, red, bases de datos, APIs
│   └── ui/                    # CLI y visualización
│
├── tests/                     # Pruebas: misma estructura que src/paypal_invoice_steward/
│   ├── core/  persistence/  ui/
│   ├── test_architecture.py   # Hace cumplir las reglas de dependencia
│   └── test_package.py
│
└── scripts/                   # Utilidades de desarrollo (no forman parte del paquete)
```

---

## 2. Qué va en cada carpeta

### `src/paypal_invoice_steward/`: el producto
Todo el código que se instala con el paquete. Usamos el *src layout*: así los tests se ejecutan siempre contra el paquete instalado, nunca contra archivos sueltos.

Cada subpaquete describe en su `__init__.py` su responsabilidad y de qué puede depender. **Léelo antes de añadir código ahí.**

| Subpaquete    | Contiene                                              | Ejemplos de archivos           |
|---------------|-------------------------------------------------------|--------------------------------|
| `core`        | Conceptos y reglas del dominio, interfaces base       | `models.py`, `rules.py`        |
| `persistence` | Leer/escribir datos fuera del programa                | `loader.py`, `export.py`       |
| `ui`          | Lo que ve o usa el usuario                            | `cli.py`, `render.py`          |

Son las tres capas mínimas. Un proyecto pequeño puede borrar la que no use; uno grande añadirá subpaquetes de dominio entre `core` y `persistence` (con issue + ADR).

### `tests/`: las pruebas
- **Espejo de `src/`**: el test de `src/paypal_invoice_steward/core/rules.py` va en `tests/core/test_rules.py`.
- Archivos `test_<modulo>.py`, funciones `test_<comportamiento>()`.
- Fixtures compartidas en `conftest.py`, en la carpeta del nivel más bajo donde se usen.
- Si un test necesita aleatoriedad, **fija la semilla**.

### `docs/`: documentación para humanos
- `architecture.md`: visión técnica general. Se actualiza cuando cambia un módulo o una relación entre módulos.
- `adr/`: una decisión importante = un archivo numerado. Ver [adr/0000-template.md](adr/0000-template.md).
- `versioning.md`: proceso de versiones y releases.

### `scripts/`: herramientas auxiliares
Scripts de desarrollo: generar datos de prueba, perfilar rendimiento, etc. **No** se importan desde `src/`. Si un script se vuelve útil para el usuario final, se convierte en un comando del paquete.

### `.github/`: automatización del proceso
CI y plantillas. Se modifica solo con un PR de tipo `ci:` o `chore:`.

---

## 3. Reglas de dependencia entre módulos

Las dependencias entre subpaquetes van en **una sola dirección**: lo más estable abajo, lo más cambiante arriba. Nunca en círculo.

```
          ┌──────┐
          │  ui  │  (nadie depende de ui)
          └──┬───┘
             │
      ┌──────▼──────┐
      │ persistence │  (el dominio nunca la importa)
      └──────┬──────┘
             │
        ┌────▼────┐
        │  core   │  (no depende de nadie)
        └─────────┘
```

Las flechas apuntan hacia lo que se puede importar. **Nunca hacia arriba.** Si `core` necesita algo de fuera (leer un archivo, por ejemplo), define una interfaz y `persistence` la implementa.

Estas reglas las comprueba [tests/test_architecture.py](../tests/test_architecture.py). Si el test falla, se corrige el import; la tabla de dependencias del test solo se cambia junto con un ADR.

---

## 4. Decidir dónde va algo nuevo

| Si vas a…                                  | Va en                                   |
|--------------------------------------------|-----------------------------------------|
| Añadir un concepto o regla del dominio     | `src/paypal_invoice_steward/core/`                  |
| Leer o guardar un nuevo formato de datos   | `src/paypal_invoice_steward/persistence/`           |
| Añadir un comando o una vista              | `src/paypal_invoice_steward/ui/`                    |
| Añadir un test                             | `tests/`, en la ruta espejo             |
| Añadir un script de desarrollo             | `scripts/`                              |
| Añadir una dependencia                     | `pyproject.toml` (justifícalo en el PR) |
| Tomar una decisión de diseño no trivial    | `docs/adr/NNNN-titulo.md`               |
| Crear un subpaquete nuevo de primer nivel  | Issue + ADR **antes** de crearlo        |

**Cuándo dividir un archivo:** si un módulo supera unas 300-400 líneas o mezcla dos responsabilidades, se convierte en un subpaquete (`rules.py` → `rules/__init__.py`, `rules/pricing.py`...).

---

## 5. Convenciones de nombres

| Elemento         | Convención              | Ejemplo                     |
|------------------|-------------------------|-----------------------------|
| Paquetes/módulos | `snake_case`, singular  | `core/rules.py`             |
| Clases           | `PascalCase`            | `class Report`              |
| Funciones/vars   | `snake_case`            | `compute_total()`           |
| Constantes       | `UPPER_SNAKE_CASE`      | `MAX_RETRIES`               |
| Privado          | prefijo `_`             | `_update_cache()`           |
| Tests            | `test_<qué>.py`         | `tests/core/test_rules.py`  |
| ADRs             | `NNNN-titulo-kebab.md`  | `0003-formato-de-datos.md`  |

El código (identificadores) se escribe en **inglés**. Docstrings, comentarios y documentación, en **español**.
