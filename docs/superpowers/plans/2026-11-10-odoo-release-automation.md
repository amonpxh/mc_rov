# Versionado automático Odoo — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Ejecución inline; una revisión independiente al final.

**Goal:** proponer versiones y CHANGELOG sin cambiar Odoo ni requerir GitHub Pro, PAT o servicios pagados.

**Architecture:** motor Python estándar que lee commits de primera línea desde una base explícita y propone `19.0.X.Y.Z`. Un workflow de GitHub, tras comprobar CI de main, mantiene un PR de entrega; al integrar ese PR prepara una release borrador. La integración humana y el despliegue siguen separados.

**Tech Stack:** Python estándar, Git, GitHub CLI y Actions con acciones fijadas a SHA.

**Spec:** autorización del usuario de los puntos 1, 2 y 3 en esta sesión; reglas de `AGENTS.md` y `docs/agents/releases.md`.

## Global Constraints

- GitHub gratuito y repositorio privado; no exigir protección de pago ni previews 3D.
- Versión `19.0.X.Y.Z`: feat incrementa Y, correcciones compatibles Z, ruptura explícita X.
- Base acreditada `40ce2feebe93b89c71b0b653704307b1fd5bef46`, versión `19.0.25.6.0`.
- Clasificación explícita de PR114 como feat porque su título histórico no es Conventional Commits.
- No cambiar datos de negocio, producto instalado, secretos, cuentas o servidores.
- PR automático de entrega sin auto-merge; release borrador sin publicar tag ni desplegar.
- CI confiable del SHA de main antes de escribir; permisos de escritura solo en el job de automatización.

## Review Focus

- Commit de producto sin clasificación: rechazar, no omitir silenciosamente.
- Main adelantado o CI incompleto: no generar ni publicar una entrega obsoleta.
- PR de entrega editado por una persona: no sobrescribir su HEAD.
- Repetición del workflow: no duplicar PR, entrada de CHANGELOG o release.
- Estado/versiones/changelog divergentes y base no ancestro: rechazar con diagnóstico.

## Task 1 — Motor de planificación y pruebas

**Files:** `scripts/ci/odoo_release.py`, `scripts/ci/test_odoo_release.py`, `.odoo-release.json`.

- [x] Escribir pruebas fallidas: cinco segmentos, prioridades feat/fix/ruptura, docs sin entrega,
  clasificación ausente, manifiesto divergente, base inválida, historial y conservación de CHANGELOG.
- [x] Ejecutar y confirmar RED por motor ausente.
- [x] Implementar `plan_release(root, today)` y aplicación limitada a manifiesto, changelog y estado.
- [x] Pasar los mismos casos y probar la planificación real contra main sin escribir.

## Task 2 — Orquestación y workflow

**Files:** `scripts/ci/release_bot.py`, `scripts/ci/test_release_bot.py`, `.github/workflows/releases.yml`.

- [x] Probar permisos y decisiones de bot: CI completo, SHA actual, idempotencia, PR protegido,
  release con padre correcto y versión concordante; API simulada donde requiere red.
- [x] Implementar creación/actualización de PR bot con lease y release borrador del SHA real.
- [x] Agregar pruebas del motor en runner de GitHub y automation solo para main tras CI exitoso.
- [x] Validar YAML, hooks y escaneo; documentar aprobación de workflows si GitHub la exige para PR del bot.

## Task 3 — Cierre y ramas conservadas

- [x] Registrar exclusión de pago y PR115 integrado; actualizar instrucciones y procedimiento de entrega.
- [x] Respaldar refs y cambios locales de tres worktrees; demostrar equivalencia funcional del PR81.
- [x] Eliminar solo referencias remotas revisadas con lease; no borrar carpetas ni ramas locales.
- [x] Revisión independiente del conjunto; dos hallazgos corregidos con regresiones RED→GREEN.
- [ ] Publicar PR borrador y comprobar CI del commit final.


## Evidencia local de cierre

38 pruebas en verde, hooks completos aprobados y simulación real sin escrituras:
19.0.25.7.0, un commit de producto pendiente (PR114), tres archivos generables.
Revisión independiente cerrada sin hallazgos pendientes tras corregir:
(1) entrega cuyo CI termina después de avanzar main y (2) tag existente con código
distinto, incluida resolución de tags anotados. No se aplicó la propuesta ni se cambió
el producto instalado. La automatización se revisa e integra mediante su propio PR.
