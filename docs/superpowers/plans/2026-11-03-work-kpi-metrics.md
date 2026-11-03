# Núcleo de cálculo de KPI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline task-by-task. El usuario autorizó el programa completo; no volver a pedir aprobación del alcance general.

**Goal:** Calcular indicadores verificables sin inventar datos, independientemente de Odoo.

**Architecture:** Núcleo puro sobre filas autorizadas/normalizadas. Adaptador Odoo y tablero
tendrán un plan posterior con pruebas nativas de permisos y orígenes; el núcleo no expone RPC.

**Tech Stack:** Python estándar, unittest para cálculos, CI existente más una fase de pruebas puras.

**Spec:** docs/superpowers/specs/2026-11-03-work-kpi-design.md

## Global Constraints

- No consultas, escrituras, ACL, credenciales, metas ni configuración real en este corte.
- Una fila representa una etapa/evento, no una orden o persona.
- `None` para métricas sin denominador; cobertura conocida/desconocida explícita.
- Plazo original y vigente separados; no reparar datos históricos desde actividades/chatter.
- CI de integración Odoo existente se conserva; no sustituir1246 pruebas por las puras.

## Review Focus

1. Hoy frente a vencido, igualdad de fecha y valores ausentes.
2. Cancelación/manual_done confundidas con business_done y período aplicado al backlog.
3. Reprogramación que oculte el incumplimiento original.
4. Datos temporales incompletos/negativos y duración cero legítima.
5. Filas alteradas por el cálculo o denominadores que excluyan silenciosamente datos incompletos.

### Task1: Cálculo puro con RED/GREEN local

**Files:** Create `tests/unit/test_work_kpi_metrics.py`, `models/work_kpi_metrics.py`.
**Interfaces:** `build_metrics(rows: Iterable[dict]) -> dict`, según contrato del diseño.

- [x] Escribir pruebas: vacío; pendientes de hoy/vencidas; plazo faltante; actividad faltante;
  cierres reales y exclusiones; período/backlog; original frente a vigente; fecha cierre
  ausente; mediana impar/par; duración cero/negativa/ausente; datos originales inmutables.
- [x] Ejecutar `python -m unittest discover -s tests/unit -v` con `PYTHONPATH=models`:
  debe fallar por núcleo ausente antes de escribir implementación.
- [x] Implementar contadores, porcentajes con cobertura y mediana de horas corridas.
- [x] Repetir las pruebas hasta GREEN, sin debilitar sus aserciones:16/16, tras14 fallos y dos controles.

### Task2: Incorporar la verificación a CI y guardar el corte

**Files:** Modify `.github/workflows/test.yml`; Update `docs/pendientes.md`.
**Interfaces:** Nueva fase unittest pura previa a la suite Odoo ya existente.

- [x] Añadir fase `PYTHONPATH=ci-addons/mc_rov/models python3 -m unittest discover -s ci-addons/mc_rov/tests/unit -v`.
- [x] Comprobar sintaxis/formato/lint: Black99 y pylint10/10; ejecución Odoo original conservada.
- [x] Guardar commit local8af81cf; núcleo probado localmente, no tablero instalado.
- [x] Siguiente corte especificado en `2026-11-03-work-kpi-service.md`; RED36 preparado, aún no ejecutado.
