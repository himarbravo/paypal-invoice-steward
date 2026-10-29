# scripts/

Utilidades de desarrollo: generar datos, perfilar, tareas de mantenimiento.

- No forman parte del paquete instalado.
- `src/` nunca importa nada de aquí.
- Cada script empieza con un docstring o comentario que explica qué hace y cómo se ejecuta.

| Script | Para qué |
|--------|----------|
| `check.sh` | Ejecuta los mismos checks que la CI |
| `setup_github.sh` | Configura labels, squash merge y protección de `main` (lo ejecuta una persona) |
