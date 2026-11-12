# Implementación de volumen y Pareto

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.
> Ejecución nativa en esta sesión y CI, conforme al recorrido autorizado.

**Goal:** completar F4, F5 y Q4 con fuentes autorizadas, evidencia histórica y filtros.
**Architecture:** eventos privados transaccionales; agregación pura; adaptadores de
fuente y tablero OWL existente. Reutilizar aceptación formal, BoM/ECO y stock nativos.
**Tech Stack:** Odoo19, PostgreSQL, Python estándar, OWL, HOOT y CI existente.
**Spec:** ../specs/2026-11-12-kpi-volumen-pareto-design.md, aprobado para implementar.

## Global Constraints

- Hora de Santiago; semanas lunes–domingo, meses/años calendario.
- Sin backfill, prototipos, activación real, instalación en servidores ni despliegue.
- Capturas privadas sin ACL general; fuente/empresa/serie autorizadas antes de leer.
- Solo Ficha de Equipo Nuevo como documento de liberación; valida Supervisor.
- Revisión significa diseño/configuración, con histórico sellado y desconocidos visibles.

## Review Focus

1. Reapertura no duplica primer cierre: contrato en captura de reparación.
2. Parciales y mismo serial no duplican unidad: contrato en captura de fabricación.
3. Contexto RPC no habilita escritura de evidencia: contrato de frontera común.
4. Cambio posterior de BoM/producto no reetiqueta historia: contrato de versión sellada.
5. Pareto truncado no cambia denominador: contrato puro y visual de Otros.

## Tarea 1: contratos y agregaciones

Archivos: tests/unit/test_production_kpi_metrics.py, models/production_kpi_metrics.py.
Interfaz: summarize_events(events, date_from, date_to, revision) -> dict;
pareto(observations, dimension, unit, limit) -> dict. Fechas ISO y dimensiones selladas.

- [ ] Escribir RED de deduplicación, intervalo Santiago, desconocidos y Pareto.
- [ ] Ejecutar unittest focalizado y observar fallos por función ausente.
- [ ] Implementar agregaciones sin Odoo ni mutación de entradas.
- [ ] Ejecutar los mismos contratos y pruebas puras anteriores; guardar evidencia.
- [ ] Commit del incremento.

## Tarea 2: evidencia y captura de negocio

Archivos: models/production_kpi_event.py, production_kpi_capture.py,
production_kpi_findings.py; tests/test_production_kpi_capture.py; imports respectivos.
Interfaz privada: _record_event(kind, source, lot, payload, event_at); capacidad Python
opaca para escritura. Unicidad por identidad de hecho, no por clic ni fecha editable.

- [ ] Añadir RED nativo de cierre, importación done sin evidencia, rollback,
  historial inmutable, fabricación serializada/parcial, hallazgos y contexto falsificado.
- [ ] Publicar pruebas en PR124 y comprobar RED preciso en odoo_test por CI.
- [ ] Capturar primer cierre nativo después de super; fabricación desde salida done;
  snapshot de BoM/revisión acreditada; detección explícita y observación confirmada.
- [ ] Verificar mismos casos GREEN, fuente restringida, empresas y dos conexiones.
- [ ] Commit de captura validada; no backfill.

## Tarea 3: hitos y servicio autorizado

Archivos: models/production_kpi_service.py, production_kpi_release.py;
wizard/new_unit_release_wizard.py, views/new_unit_release_views.xml,
security/ir.model.access.csv; tests/test_production_kpi_service.py.
Interfaz: mc.rov.production.kpi.get_summary(date_from=False,date_to=False,
model_id=False,revision="latest") -> {repair,manufacturing,findings,coverage,filters}.

- [ ] RED de selección completa autorizada, revisión vigente/concreta/Todas,
  ausencia de fecha, denominadores, liberación y salida/reverso.
- [ ] Servicio verifica permisos de equipo, fuentes y empresa antes de evidencia;
  no expone claves privadas. Aceptación usa intentos conjuntos existentes.
- [ ] Asistente de Supervisor elige serie/FEN, revisa NC y sella liberación explícita;
  valida FEN emitida y pruebas acreditadas. No crea ni valida movimientos.
- [ ] Salida/reverso vincula movimiento real con unidad; saldos al corte sin restas
  ciegas. Revisión ambigua y datos antiguos permanecen desconocidos.
- [ ] GREEN focalizado y commit.

## Tarea 4: tablero y entrega revisable

Archivos: models/kpi_dashboard.py, kpi_dashboard_catalog.py,
static/src/kpi_dashboard/kpi_dashboard.{js,xml,scss}, tests/test_kpi_dashboard.py,
static/tests/kpi_dashboard.test.js, tests/test_kpi_dashboard_browser.py.

- [ ] RED de secciones Producción/Hallazgos, filtros y navegación autorizada.
- [ ] Conectar servicio; mostrar cantidades/cobertura/unidad/fecha, Pareto y Otros;
  mantener secciones actuales. Sin objetivos inventados ni ceros por falta de acceso.
- [ ] GREEN nativo, HOOT poblado, capturas escritorio/móvil y regresión completa exacta.
- [ ] Revisión independiente de rama completa, corregir hallazgos con RED/GREEN.
- [ ] Actualizar PR124 y continuidad; solicitar integración solo con HEAD validado.

## Registro de decisiones

- El usuario autorizó explícitamente continuar la implementación; no pedir otra
  aprobación del mismo diseño o del método ya establecido después de cada tarea.
- La publicación es en rama de tarea y PR borrador ya autorizados; merge separado.
- No confundir etapa aceptada/liberada/salida; evidencia incompleta se indica, no se inventa.
