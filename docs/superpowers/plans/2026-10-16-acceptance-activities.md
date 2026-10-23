# Seguimiento de aceptación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Propuesta: ejecución en este chat; no delegar salvo autorización posterior.

**Goal:** Generar y resolver pendientes de aceptación por equipo efectivamente fabricado, con evidencia explícita y un día laborable por actividad.

**Architecture:** Actividades nativas sobre stock.lot, con ciclo privado fabricación/serie, evidencia seleccionada mediante asistente y eventos de negocio que reconcilian resultados. Servicios separados para calendario, generación, evidencia y cierre. Calidad tiene su propio plan; comparte solo calendario y controles existentes.

**Tech Stack:** Odoo19 Enterprise, PostgreSQL, Python/XML, TransactionCase, HOOT para integración del Centro; scripts PowerShell/Bash de STAGING con SSH manual.

**Spec:** `docs/superpowers/specs/2026-10-16-acceptance-quality-activities-design.md`, aprobado por el usuario el2026-10-16.

## Global Constraints

- Base main `b25d15fe90dbb99bf28be90989da53ed5e1f3dde`,594pruebas aprobadas. Rama `feature/acceptance-quality-activities`; worktree reutilizado `.tmp/worktrees/repair-activities` limpio antes de este diseño.
- Entrega conjunta con el plan de Calidad, versión19.0.25.2.0. Cambiar manifest al introducir los modelos; no crear configuración ni datos operativos mediante XML/upgrade.
- **Cada actividad tiene1día laborable**, incluido resolver un rechazo. Contar desde su propio evento y excluir el día de inicio como el cálculo de reparación existente. Jornadas/ausencias globales del calendario elegido; fechas locales, no sumas de24horas.
- Inicio solo por equipos serializados ROV efectivamente fabricados. No usar lot_producing_ids como prueba única de fabricación; comprobar movimientos terminados. Nada desde compute, inventario histórico, creación de un lote o edición ordinaria.
- Cuenta y empleado independientes. No inferir destinatario desde responsable técnico, creador, editor ni Dev; comprobar destinatario y empresa sin heredar empresas del actor.
- No crear borradores RND/TRN/FEN automáticamente, tareas espejo, nuevos Kanban, correcciones de PDF ni aprobación automática.
- Pausa bloquea creación y permite cierres. Reanudar no reconstruye eventos. Decisiones manuales sobre actividades conservan auditoría y no sustituyen resultados técnicos.
- Implementación primero STAGING/TDD; restaurar pruebas temporales y conservar respaldos. Producción requiere nueva aprobación después de QA/PR/CI.

## Review Focus

1. Una MO con dos series y producción parcial solo inicia aceptación para las unidades realmente producidas; Task2 prueba movimientos y cantidades.
2. Prueba nueva del mismo lote pero no vinculada no cierra el pendiente; Task3 prueba asociación explícita y contexto falso.
3. Rechazo, vuelta a borrador y sustitución de evidencia no pierden auditoría ni reescriben FEN emitida; Task4 prueba ambos lados de la emisión.
4. Hook nativo con sudo no amplía acceso del operario ni empresas del destinatario; Task5 prueba MRO, permisos y copias temporales.
5. Filtrar aceptación en el Centro no congela IDs ni clasifica toda actividad de equipo como aceptación; Task5 prueba dominio dinámico.

## Archivos y contratos

Crear modelos `mc.rov.work.deadline` (abstracto), `mc.rov.acceptance.activity.policy`,
`mc.rov.acceptance.activity.cycle`, `mc.rov.acceptance.activity.run` y servicios
`mc.rov.acceptance.activity.automation` y `mc.rov.acceptance.activity.lifecycle`.
Los historiales privados carecen de ACL pública. El asistente usa resúmenes y
acciones que revalidan acceso al equipo; no accede directamente a modelos privados.

Interfaces privadas compartidas entre tareas:

```python
# mc.rov.work.deadline
def _working_date(self, calendar, company, started_at, days):  # -> datetime.date
    """Misma semántica que repair.activity.policy._deadline; sin escribir datos."""

# mc.rov.acceptance.activity.automation
def _produced_lots(self, production):  # -> stock.lot recordset en entorno del actor
    """Solo series realmente producidas por movimientos terminados de esta MO."""
def _start(self, production, lot, started_at):  # -> cycle vacío o singleton privado
    """Autoriza origen/destinatario, bloquea y crea ciclo + dos pendientes atómicos."""
def _start_stage(self, cycle, stage, started_at):  # -> run vacío o singleton privado
    """Idempotente por ciclo, etapa y evento de elegibilidad."""

# mc.rov.acceptance.activity.lifecycle
def _select_evidence(self, lot, rnd=None, trn=None, reason=False):  # -> None
    """None conserva, False desvincula; cambiar evidencia exige motivo y auditoría."""
def _reconcile(self, lots, occurred_at):  # -> None
    """Cierra realización, sigue rechazos y reconcilia elegibilidad de emisión."""
def _after_fen_emission(self, ficha):  # -> None
    """Cierra solo ciclo con lote y evidencia explícita coincidentes."""
```

Los hooks pasan instantes capturados una sola vez y registros persistidos. Los
métodos públicos sobre lote/autorización no devuelven ledger ni tokens Python.

### Task1: Política y cálculo laboral compartido

**Files:** crear `models/work_activity_deadline.py`, `models/mc_rov_acceptance_activity_policy.py`, `views/mc_rov_acceptance_activity_policy_views.xml`, `security/acceptance_activity_policy_rules.xml`, `tests/test_acceptance_activity_policy.py`; modificar `models/mc_rov_repair_activity_policy.py`, `models/__init__.py`, `__manifest__.py`, `security/ir.model.access.csv`, `tests/__init__.py`.

**Consumes:** calendario y control general existentes. **Produces:** `_working_date` y política por empresa con enabled, user_id, employee_id(public), calendar_id y días separados performance_days, field_days, rejection_days, fen_days.

- [x] Escribir RED de existencia/defaults, duración1..365 rechazando bool antes de conversión, cuenta interna activa, calendario laboral con zona válida/no flexible y acceso por empresa. Ejemplo directo:

```python
def test_policy_defaults(self):
    self.assertIn('mc.rov.acceptance.activity.policy', self.env.registry.models)
    policy = self.env['mc.rov.acceptance.activity.policy']
    self.assertEqual(policy.default_get(['enabled', 'performance_days', 'field_days',
                                        'rejection_days', 'fen_days']),
                     {'enabled': True, 'performance_days': 1, 'field_days': 1,
                      'rejection_days': 1, 'fen_days': 1})
```

- [x] Ejecutar RED STAGING con pruebas temporales. Aceptar solo fallos nuevos previstos y cero errores de carga; todas las pruebas anteriores focalizadas deben seguir pasando.
- [x] Extraer literalmente el algoritmo de `_deadline` de reparación a `_working_date(calendar, company, started_at, days)`; conservar el método anterior como adaptador. No instanciar una política de reparación para calcular aceptación.

```python
def _deadline(self, started_at, days):
    self.ensure_one()
    return self.env['mc.rov.work.deadline']._working_date(
        self.calendar_id, self.company_id, started_at, days)
```

- [x] Implementar política/menú bajo Seguimiento automático con permiso Coordinar, regla de empresa y ausencia de políticas por upgrade. Copiar restricciones semánticas, no empresas del actor.
- [x] GREEN de política y14contratos originales de calendario: viernes→lunes, festivo registrado, domingo, Chile frente a medianoche UTC, DST, calendario vacío/sin jornada futura. Verificar también políticas reparación/fabricación intactas.
- [x] Black/pylint/hooks y commit `feat: configurar plazos laborales de aceptación` solo después de GREEN nativo.

### Task2: Ciclo por unidad producida y generación inicial

**Files:** crear `models/mc_rov_acceptance_activity_cycle.py`, `models/mc_rov_acceptance_activity_run.py`, `models/acceptance_activity_automation.py`, `data/acceptance_activity_types.xml`, `tests/acceptance_activity_common.py`, `tests/test_acceptance_activity_generation.py`; modificar imports/manifest. No ACL pública para cycle/run.

**Consumes:** Task1. **Produces:** `_produced_lots`, `_start`, `_start_stage` y hooks MRP/movimientos.

- [x] Crear fixture `AcceptanceActivityCommon(ManufacturingActivityCommon)`: política aceptación explícita en calendario lun-vie Santiago, cuenta TallerQA con permisos mínimos, series únicas y movimientos nativos. Reutilizar la fixture existente solo para producción/revisiones; no su calendario vacío de días corridos.
- [x] En esa fixture definir `_acceptance_policy(**values)` (create/reuse transaccional sin borrar política), `_finished_production(quantity=1)` (confirmar/producir series mediante MRP nativo y devolver MO) y `_acceptance_activities(lot)` (buscar tipos XML de aceptación sobre stock.lot). Todas las pruebas posteriores importan esta clase; no duplicar cuentas/fixtures.
- [x] RED: MO confirmada/asistente sin done crea0; done con una serie crea1ciclo/2actividades; done repetido crea0extra; dos series terminadas crean2ciclos/4actividades; parcial inicia solo serie producida; componente/noROV, sin serie, pausa y configuración incompleta crean0 sin inventar destinatario. Una excepción posterior revierte cierre/ledger/actividades juntos.

```python
def test_done_creates_two_pending_activities_per_produced_lot(self):
    self._acceptance_policy()
    production = self._finished_production()
    lots = self.env['mc.rov.acceptance.activity.automation']._produced_lots(production)
    self.assertEqual(len(lots), 1)
    self.assertEqual(len(self._acceptance_activities(lots)), 2)
    self.assertTrue(all(a.res_model == 'stock.lot' for a in self._acceptance_activities(lots)))
```

- [x] Ejecutar RED; después implementar ledger con unicidad MO/lote y etapa/evento, calendario/tz, vencimientos original/vigente y resultado/actor/motivo. Bloquear filas de MO y lotes en orden; no considerar sudo como actor autorizado.
- [x] Implementar hooks reales de reconciliación MRP/stock conservando retornos de super. `_produced_lots` lee movimientos terminados/producto/serie, excluye componentes y series no producidas. Para MO bajo reparación/fabricación sin política aceptación no cambiar su comportamiento anterior.
- [x] GREEN con ciclo real/partial/movimiento directo y controles anteriores; verificar que upgrade no crea actividades o documentos técnicos; commit `feat: generar aceptación al fabricar cada equipo`.

### Task3: Selección explícita de evidencia y navegación nativa

**Files:** crear `models/mc_rov_acceptance_evidence_history.py` (modelo privado mc.rov.acceptance.evidence.history que conserva revision_id/previous_revision_id restrict, ciclo, etapa, actor, instante y motivo), `wizards/mc_rov_acceptance_evidence_wizard.py`, `views/mc_rov_acceptance_evidence_wizard_views.xml`, `models/acceptance_activity_evidence.py`, `tests/test_acceptance_activity_evidence.py`; modificar imports, ACL del asistente, manifest y vista heredada de equipo en `views/stock_lot_views.xml` (confirmar ID nativo mediante auditoría antes de heredar).

**Consumes:** ciclo y `_start_stage`. **Produces:** `_select_evidence` y acción pública `stock.lot.action_mc_acceptance_evidence`.

- [x] RED: seleccionar RND/TRN registra solo esas evidencias (la reconciliación de realización se verifica en Task4); revisar otro registro del mismo lote no hace nada. Rechazar otro equipo/tipo, repair_id presente, otra empresa, ciclo incompatible y origen sin permiso. Selección de evidencia ya confirmada requiere acción explícita y queda auditada.
- [x] Definir asistente con lot_id, rnd_id, trn_id, reason; `action_apply` llama `_select_evidence` tras permisos de lote/ambas pruebas. El formulario muestra solo resumen autorizado del ciclo y abre pruebas por acciones nativas. No publicar IDs/columnas privadas del ledger.
- [x] Crear prueba desde el asistente usa los formularios existentes y vincula explícitamente el registro creado, sin pasar tokens privados por context JSON. Fuera del asistente, los botones manuales existentes conservan su semántica.
- [x] Reemplazar evidencia rechazada exige motivo, conserva selección previa en historial y referencias restrict; impedir asociaciones ambiguas. El responsable_id técnico no modifica el empleado de la actividad.
- [x] GREEN de asistente/default_get/onchange con caché fría y selección con usuario Taller sin grupo técnico; verificar acciones serializables y lectura del origen; commit `feat: vincular pruebas al ciclo de aceptación`.

### Task4: Rechazo, corrección y emisión de FEN

**Files:** crear `models/acceptance_activity_lifecycle.py`, `tests/test_acceptance_activity_lifecycle.py`; modificar imports. Heredar revisión/FEN desde este archivo y mail.activity para decisiones manuales, conservando métodos/firmas existentes.

**Consumes:** `_select_evidence`. **Produces:** `_reconcile`, `_after_fen_emission`, auditoría manual y cierres efectivos.

- [ ] RED: confirmar aprobada cierra realización; rechazada cierra realización y crea1resolución; repetir confirmación no duplica; corrección borrador deja resolución abierta; repetición explícita aceptada cierra rechazo. Ambas rechazadas generan2resoluciones independientes.
- [ ] RED de FEN: una prueba aprobada no crea emisión; ambas aceptadas crean1; documento de otra selección no cierra; acción de previsualizar/guardar borrador no cierra; emisión real sí. Corregir prueba antes de emitir retira elegibilidad; después de emitir no modifica PDF ni reabre ciclo cerrado.

```python
def test_unrelated_revision_does_not_finish_stage(self):
    self._acceptance_policy()
    production = self._finished_production()
    lot = self.env['mc.rov.acceptance.activity.automation']._produced_lots(production)
    pending = self._acceptance_activities(lot)
    self._revision(lot_id=lot.id, tipo='rendimiento')
    self.assertEqual(self._acceptance_activities(lot), pending)
```

- [ ] Implementar reconciliación por evidencia persistida y estado/resultado actuales; capturar resultados antes/después del evento. Registrar cierre de negocio antes de feedback/unlink nativo para que hooks manuales no lo sobrescriban.
- [ ] Registrar generaciones distintas de elegibilidad cuando una corrección real retire/restituya requisitos. Cada nuevo pendiente usa su evento propio, no la fecha original del equipo. Una edición que no cambie elegibilidad no recrea pendientes cancelados manualmente.
- [ ] GREEN: pausas permiten cierre, impiden etapas nuevas; reactivar/editar no reconstruye, cancelación manual no aprueba prueba/FEN; correcciones preservan PDFs y registros previos; commit `feat: resolver aceptación y rechazos por evidencia`.

### Task5: Centro, privacidad y fronteras

**Files:** crear `tests/test_acceptance_activity_boundaries.py`; modificar `models/mc_rov_work_assignment.py`, `tests/test_work_assignment.py`, `static/tests/embedded_work.test.js` solo si hay cambio de capacidad/frontend; guardas de origen en servicio de evidencia/lifecycle.

- [ ] RED de filtro Aceptación con actividades sobre lote. Dominio dinámico por res_model=stock.lot y tipos XML explícitos de aceptación (RND/TRN/rechazos/emisión). No lista de activity IDs congelada, ni lectura de ledger privado desde cliente.
- [ ] Habilitar opción acceptance para actividades; tareas/proyectos continúan sin vínculo inventado. Mantener Equipo como origen stock.lot; actividades manuales de mantenimiento con otro tipo no entran en Aceptación. Publicar capacidad según acceso, conservar permisos personales/equipo.
- [ ] RED+GREEN de nombres restringidos/exportación, coordinador sin consulta global, usuario externo, múltiples empresas, destinatario con solo otra empresa, contexto JSON falsificado, NewId sin efecto persistente, copias/referencias cambiadas, selección atómica en lote y cambio/borrado de evidencia seguida con explicación humana.
- [ ] HOOT de vista embebida conserva búsqueda/empleado/alcance y muestra filtro Aceptación disponible. Backend filtra cuenta/empleado/proceso en consulta nativa; no conceder RRHH privado ni grupos a usuarios reales.
- [ ] Hooks nativos Black/pylint y commit `feat: integrar aceptación con trabajo asignado` tras GREEN.

### Task6: Validación conjunta y entrega

**Files:** crear `scripts/qa/acceptance_activity_concurrency.py`, `docs/runbooks/acceptance-quality-activity-pilot.md`; actualizar `docs/pendientes.md`. Scripts de ejecución temporal bajo `.tmp/acceptance-quality-activity-pilot/` fuera de Git.

- [ ] Completar también el plan `2026-10-16-quality-activity-followup.md` antes de entrega conjunta; su historial/política es independiente del ciclo de aceptación.
- [ ] Revisión integral una vez al terminar ambos bloques; corregir hallazgos reales con RED/GREEN. No desplegar cambios no revisados a producción ni repetir revisiones por rutina en cada commit.
- [ ] Ejecutar suite completa por descubrimiento AST exacto, incluyendo594base y todos los nuevos casos/imports de soporte. Exigir cero fallos/errores y ningún nombre omitido/duplicado. Comparar hashes instalados y conservar políticas/calendarios/PDFs; restaurar tests temporales.
- [ ] Concurrencia real en base aislada sin cron/correo: dos cierres MRP sobre misma serie, dos selecciones/cierres de etapa y FEN; una identidad/actividad por evento, transacciones con retry completo, cero huérfanos. Bloquear conexiones a copia al finalizar.
- [ ] Crear QA temporal propia con política apagada y contraseña solo terminal. Usuario prueba generación, reparto, rechazo/corrección, selección explícita, emisión, parcial, pausa y alertas. Retirar solo escenario registrado conservando documentos, auditoría y series dadas de baja.
- [ ] PR adjunto al chat, CI aislado aprobado, nueva aprobación para merge/producción; respaldo de BD/filestore/código y recuperación fresca antes de liberar tráfico. Verificar esquema y cero pendientes/configuraciones retrospectivos. Registrar activación real aplazada hasta cuenta Taller/calendario.

## Autocomprobación del plan

Cobertura: generaciónporunidad(Task2), evidencia(Task3), rechazo/FEN(Task4), Centro y
seguridad(Task5), plazos/controles(Task1), QA/entrega(Task6), alertas(plan separado).
Los casos Review Focus están asignados. No hay cambio de negocio adicional ni
dependencia en una política de reparación creada artificialmente.
