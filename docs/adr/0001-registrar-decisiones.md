# 0001. Registrar las decisiones de arquitectura con ADRs

- **Estado:** Aceptada
- **Fecha:** 2026-10-02

## Contexto

El proyecto irá acumulando código y lo trabajarán varias personas y agentes. Sin registro, el motivo de cada decisión se pierde y se vuelven a discutir cuestiones ya resueltas.

## Decisión

Cada decisión de diseño no trivial se documenta en `docs/adr/NNNN-titulo.md` a partir de [0000-template.md](0000-template.md). Los ADR son inmutables: si una decisión cambia, se crea uno nuevo y el antiguo pasa a "Reemplazada por".

## Consecuencias

- Hay que escribir un ADR antes de crear un módulo de primer nivel, añadir una dependencia importante o cambiar un formato de datos.
- El historial de razonamiento queda en el repositorio, junto al código.
