# Versiones y releases

## 1. Principio: las versiones viven en Git, no en carpetas

- **Prohibido** crear carpetas o copias como `v1/`, `v2/`, `old/`, `proyecto_final.py`, `backup/`.
- Una versión es un **tag de Git** sobre un commit de `main`. Para ver cualquier versión antigua:
  ```bash
  git checkout v0.3.0       # inspeccionar
  git switch main           # volver
  ```
- Para recuperar código borrado se usa el historial (`git log -- ruta`, `git show <commit>:ruta`), no copias.

---

## 2. Esquema: Semantic Versioning (SemVer)

Formato `MAJOR.MINOR.PATCH`, por ejemplo `1.4.2`.

| Sube…   | Cuándo                                                                 | Ejemplo en este proyecto                                  |
|---------|------------------------------------------------------------------------|-----------------------------------------------------------|
| `MAJOR` | Cambio **incompatible**: datos guardados o API pública antiguos dejan de funcionar | Cambiar el formato de un archivo de configuración |
| `MINOR` | Funcionalidad **nueva y compatible**                                    | Añadir un comando nuevo                                   |
| `PATCH` | **Corrección** de bugs, sin cambiar comportamiento previsto             | Arreglar un cálculo erróneo                               |

Al subir una cifra, las de la derecha vuelven a 0: `0.4.3` → `0.5.0`.

### Fase `0.x` (fase actual)
Mientras `MAJOR` sea `0`, el proyecto está en desarrollo inicial:
- Lo incompatible sube `MINOR` (`0.4.0` → `0.5.0`).
- Lo compatible o los fixes suben `PATCH`.
- La `1.0.0` se publica cuando la API pública y los formatos de datos se consideren estables. Esa decisión se registra con un ADR.

### Pre-releases (opcional)
Para probar antes de publicar: `0.5.0rc1`, `0.5.0rc2` → `0.5.0` (formato PEP 440, compatible con pip).

---

## 3. De commits a versión

El tipo de los Conventional Commits (ver [AGENTS.md](../AGENTS.md)) determina el salto:

| Commits desde la última versión         | Salto (en 1.x+) | Salto (en 0.x) |
|-----------------------------------------|-----------------|----------------|
| Alguno con `!` o `BREAKING CHANGE:`     | MAJOR           | MINOR          |
| Algún `feat:`                           | MINOR           | MINOR o PATCH  |
| Solo `fix:`, `perf:`                    | PATCH           | PATCH          |
| Solo `docs:`, `test:`, `chore:`, `ci:`… | no hace falta release | no hace falta release |

---

## 4. Dónde está la versión

**Única fuente de verdad: `version` en [pyproject.toml](../pyproject.toml).**

- `paypal_invoice_steward.__version__` la lee automáticamente del paquete instalado. **Nunca** se escribe la versión a mano en otro sitio.
- El tag de Git debe coincidir: `version = "0.2.0"` ↔ tag `v0.2.0`.

---

## 5. CHANGELOG.md

Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

- Cada PR que cambia comportamiento añade una línea en la sección **`[Unreleased]`**, en la categoría que corresponda:
  `Added` · `Changed` · `Deprecated` · `Removed` · `Fixed` · `Security`
- Se escribe para usuarios: qué cambia para ellos, no detalles internos.
- Los PRs de solo `docs`/`test`/`chore`/`ci` no necesitan entrada.

---

## 6. Procedimiento de release (paso a paso)

Se hace en una rama propia y pasa por PR, igual que cualquier otro cambio.

```bash
# 1. Partir de main actualizado
git switch main && git pull --ff-only
git switch -c chore/release-v0.2.0

# 2. Subir la versión en pyproject.toml
#    version = "0.2.0"

# 3. En CHANGELOG.md:
#    - Renombrar [Unreleased] a [0.2.0] - AAAA-MM-DD
#    - Crear una sección [Unreleased] vacía encima
#    - Actualizar los enlaces de comparación del final

# 4. Verificar
ruff check . && ruff format --check . && pytest

# 5. Commit y PR
git commit -am "chore(release): v0.2.0"
git push -u origin HEAD
gh pr create --title "chore(release): v0.2.0" --body "Release v0.2.0. Ver CHANGELOG."

# 6. Tras el merge (squash), etiquetar el commit resultante en main
git switch main && git pull --ff-only
git tag -a v0.2.0 -m "v0.2.0"
git push origin v0.2.0

# 7. Publicar la release en GitHub con las notas del CHANGELOG
gh release create v0.2.0 --title "v0.2.0" --notes-file <(sed -n '/^## \[0.2.0\]/,/^## \[/p' CHANGELOG.md | sed '$d')
```

**Los tags no se mueven ni se borran** una vez publicados. Si una release sale mal, se publica una nueva versión PATCH con el arreglo.

---

## 7. Hotfix sobre una versión publicada

Mientras solo se mantenga la última versión (situación actual), un hotfix es un `fix/` normal seguido de una release PATCH.

Si en el futuro hay que mantener una versión antigua (p. ej. `0.4.x` mientras `main` va por `0.6`):

```bash
git switch -c release/0.4 v0.4.2      # rama de mantenimiento desde el tag
git switch -c fix/88-crash-guardado
# ... arreglo + PR contra release/0.4 ...
# release v0.4.3 desde release/0.4; luego llevar el fix a main con cherry-pick
```

Las ramas `release/X.Y` solo se crean cuando hacen falta, y se documenta en un ADR.

---

## 8. Compatibilidad de datos

Los archivos que el usuario crea o guarda con el proyecto (configuración, datos exportados, estados guardados) son contratos con el usuario:
- Incluyen un campo `schema_version`.
- Cambiar su formato de forma incompatible = salto incompatible (MINOR en `0.x`, MAJOR en `1.x+`).
- Si es razonable, el proyecto debe migrar automáticamente los formatos antiguos.
