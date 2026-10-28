# Inventory Activities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar seguimiento de recepciones, entregas y transferencias reales, sin sustituir el control de stock.

**Architecture:** Política por empresa y reglas por tipo de operación explícito; ciclo privado por picking y ejecuciones de actividad con identidad propia. Los eventos nativos de picking/movimientos disparan la observación; el cierre depende de done/cancel, con vencimiento heredado para documentos restantes. Reutilizar el cálculo laboral existente y los filtros del Centro.

**Tech Stack:** Odoo19, Python/pytz, PostgreSQL, XML/OWL existente, TransactionCase y HOOT; wrappers PowerShell/SSH para STAGING.

**Spec:** `docs/superpowers/specs/2026-10-28-design-inventory-activities-design.md`, aprobado2026-10-28.

## Global Constraints

- Tres días laborables, excluyendo el día del anclaje, con calendario operativo explícito.
- Anclaje inicial: mayor entre confirmación y scheduled_date inicial; un date_deadline anterior conserva el compromiso más exigente.
- No recalcular silenciosamente por ediciones posteriores; parciales heredan vencimiento vigente.
- Solo tipos de operación seleccionados, código incoming/outgoing/internal y empresa coherente; incluir equipos/repuestos/componentes.
- No validar stock, crear compras, aplicar conteos, activar cron ni generar tareas por cada faltante.
- Políticas/destinatarios reales no se crean ni activan. Control general no cambia mecanismos nativos.
- Derechos del actor y destinatario en su propio contexto; historial privado y actividades solo sobre picking persistente autorizado.
- Comenzar tras terminar Ingeniería; rama nueva `feature/inventory-activities` desde main actualizado, preservando trabajo ajeno.

## Review Focus

1. Recepción programada después de la confirmación y luego reprogramada nativamente: capturar ancla una vez, Task1/3.
2. Fines de semana, excepciones, DST y límite nativo anterior: fecha local consistente, Task1.
3. Autoconfirmación, creación en estado listo y parciales anidados: una identidad por documento, Task2.
4. Tipos de otra empresa, usuario sin almacén y regla sin responsable: no ampliar acceso, Task1/3.
5. Devolución nueva frente a reapertura inexistente del documento terminado; cantidades y reservas normales permitidas, Task2/3.

## Archivos e interfaces compartidas

Nuevos: `models/mc_rov_inventory_activity_policy.py` (política y reglas),
`models/mc_rov_inventory_activity_cycle.py`, `models/mc_rov_inventory_activity_run.py`,
`models/inventory_activity_automation.py`, `models/inventory_activity_lifecycle.py`,
`models/inventory_activity_source.py`, `views/mc_rov_inventory_activity_views.xml`,
`data/inventory_activity_data.xml`, `security/inventory_activity_policy_rules.xml`.

Modificar imports/manifest/ACL, `models/mc_rov_work_assignment.py` y pruebas
indicadas abajo. No otro botón principal ni rediseño de las cinco secciones.

Pruebas y herramientas: `.tmp/inventory-activity-pilot/`, wrappers
`.tmp/staging-inventory-activity-{policy,events,boundaries}-{red,green}.ps1`.
Usar el mismo protocolo seguro de la entrega de Ingeniería: hashes, respaldo,
restauración de pruebas, recuperación de GREEN fallido y SSH manual; no reutilizar
recibos antiguos. Los nombres exactos del payload final definen la cantidad esperada.

### Task1: Política logística y fecha capturada

**Files:** nuevos policy/cycle/run/vista/data/reglas; integración de imports,
manifest/ACL; `tests/inventory_activity_common.py`, `tests/test_inventory_activity_policy.py`.

**Interfaces:**
- `InventoryActivityCommon._picking(code, **values) -> stock.picking`,
  `_policy(**values) -> policy`, `_rule(picking_type, **values) -> rule`:
  fixtures nativos propios de entradas/salidas/internos y movimientos reales.
- `mc.rov.inventory.activity.policy`: empresa única, enabled(defaultFalse),
  calendar_id, lead_days(default3, entero1..365), rule_ids.
- `mc.rov.inventory.activity.rule`: policy_id, picking_type_id único dentro de
  política, user_id, employee_id opcional; tipo debe pertenecer a la misma empresa.
- `_rule_for(picking) -> rule|False`, `_configuration_error(picking) -> str|False`.
- `_deadline(confirmed_at, scheduled_at=False, explicit_deadline=False) -> date`:
  fecha laboral desde max de instantes y límite nativo anterior en zona del calendario.
- Ciclo `mc.rov.inventory.activity.cycle`: picking/empresa, confirmed_at, ancla
  original, fecha programada capturada, límite original/vigente, padre si parcial,
  tipo/code y estado; UNIQUE(picking_id).
- Run `mc.rov.inventory.activity.run`: ciclo/evento, actividad, resultado/motivo,
  fechas; unicidad por ciclo/evento, sin ACL pública.

- [ ] Escribir `TestInventoryActivityPolicy`: default3/desactivado; bool/fracción,
  cero y366 rechazados; calendario/empresa/usuario/tipo/empleado inválidos;
  política/regla única; ACL coordinador y privacidad de ciclo/run.
  Con calendario QA lunes-viernes en America/Santiago, sin festivos iniciales:
  ```python
  # Viernes30oct2026→lunes2, martes3, miércoles4nov.
  self.assertEqual(policy._deadline(datetime(2026, 10, 30, 15)), date(2026, 11, 4))
  # Fecha prevista futura jueves5nov→viernes6, lunes9, martes10.
  self.assertEqual(policy._deadline(datetime(2026, 10, 30, 15), datetime(2026, 11, 5, 15)), date(2026, 11, 10))
  ```
  Otro caso añade excepción laboral2nov y exige5nov; añadir DST, zona diferente
  del actor y explicit_deadline anterior que no se alarga por los3días.
- [ ] Ejecutar RED policy con selectores `/mc_rov:TestInventoryActivityPolicy`:
  contratos nuevos ausentes; escenarios nativos/factores de calendario previos pasan.
- [ ] Implementar interfaces, vista/reglas por tipo y tipos de actividad propios
  `inventory_receipt/delivery/transfer`. Usar `mc.rov.work.deadline._working_date`
  sin modificar su contrato. La regla se valida bajo la cuenta destinataria sin
  heredar empresas del actor; cuenta vacía no se sustituye por Dev/administrador.
- [ ] GREEN policy y comprobación de configuraciones/PDFs ajenos intactos; no
  instalar reglas reales ni invocar acciones de reabastecimiento/conteo.
- [ ] Commit: `feat: configurar seguimiento laboral de operaciones de inventario`.

### Task2: Eventos nativos y operaciones parciales

**Files:** crear automation/lifecycle; ampliar common y
`tests/test_inventory_activity_events.py`; integración de imports.

**Interfaces:**
- `mc.rov.inventory.activity.automation._start(picking, occurred_at, parent=False) -> run|False`.
- `mc.rov.inventory.activity.lifecycle._capture(pickings, access='write') -> dict[id, snapshot]`;
  `_sync(pickings, before, occurred_at) -> None`;
  `_inherit_remaining(parent, remaining, occurred_at) -> None`.
- Snapshot: state, tipo y pertenencia persistente. La confirmación se registra por
  evento real; una edición de la fecha no se interpreta como confirmación nueva.

- [ ] Escribir `TestInventoryActivityEvents`: draft sin actividad; confirmación de
  entrada/salida/interno crea tipo correcto; waiting/confirmed/assigned no generan
  tres actividades. Hecho real cierra y cancelación real cancela; reserva no cierra.
  Probar autoconfirmación de movimientos, creación ya confirmada y botón normal.
  Parcial nativo: originaldone sin pendiente, restanteconfirmado con uno y límite
  original; segunda división conserva ese límite; devolución usa nuevo ciclo si su
  tipo está seleccionado. Sin política/al desactivar tipo no crear nada.
- [ ] RED events mediante pickings/moves y asistentes nativos de validación parcial;
  corregir primero fixtures si cantidad/series impiden llegar al evento.
- [ ] Implementar observación en `stock.picking` create/write/action_confirm,
  `_action_done`/action_cancel y `_create_backorder`, más `stock.move._action_confirm`
  donde se necesite para autoconfirmación. Consolidar hooks anidados y considerar
  movimientos devueltos/agrupados por el método, no solo self. No forzar estados.
  Capturar parent antes de cerrar original y establecer herencia del restante sin
  una ventana que permita asignarle un plazo nuevo. Bloqueo/identidad transaccional
  por picking; estados calculados flush/invalidación según patrones existentes.
- [ ] GREEN events: ninguna actividad huérfana, identidad única por documento,
  fechas capturadas consistentes y resultado nativo de métodos conservado.
- [ ] Commit: `feat: seguir confirmaciones y parciales logísticos reales`.

### Task3: Decisiones manuales y fronteras de origen

**Files:** crear source y `tests/test_inventory_activity_boundaries.py`;
extender lifecycle para mail.activity, patrón de Ingeniería/Calidad.

**Interfaces:** `_runs(pickings, pending=False, access='write') -> runs`,
`_check_source_changes(pickings, values) -> None`, `_check_source_deletion(pickings) -> None`.
Registrar resultados propios mediante callbacks nativos de feedback/unlink/write.

- [ ] Escribir `TestInventoryActivityBoundaries`: actor multicompañía no amplía
  destinatario; picking restringido/portal/tipo ajeno no accesible; no ACL a historial.
  Hecho/cancelación manual no valida/cancela picking ni recrea actividad al reservar
  o editar scheduled_date. Reparto/reprogramación con motivo conserva auditoría y
  el nuevo límite vigente se hereda en parciales. Cambio posterior de fecha prevista
  no renueva plazo; activar política nueva no reconstruye confirmaciones antiguas.
  Con pendiente, proteger empresa/tipo/location_id/location_dest_id; permitir
  cantidades, líneas, series y reservas legítimas de Odoo. Borrado explica historial;
  NewId/temporales no crean persistencia. Pausa admite cierres sin nuevas etapas.
- [ ] RED boundaries preserva todos los casos nativos Task2 y documenta fallos nuevos.
- [ ] Implementar checks y callbacks solo sobre actividades propias. No congelar
  productos de un picking multicomponente ni modificar las actividades nativas de
  excepción. Consultar historial con sudo solo tras autorizar el origen y empresa.
- [ ] GREEN boundaries y regresión focalizada de mail.activity compartido, Ingeniería
  y parciales. No repetir la suite completa antes del cierre integrado salvo fallo.
- [ ] Commit: `fix: proteger identidad y decisiones de actividades logísticas`.

### Task4: Inventario en Trabajo asignado

**Files:** modificar `models/mc_rov_work_assignment.py`,
`tests/test_work_assignment_process.py`, `static/tests/work_center.test.js` y
`static/tests/embedded_work.test.js` solo donde lo requiera la navegación nueva.

**Interfaces:** `_PROCESS_MODELS['inventory'] = ('stock.picking',)`;
`get_processes(kind='activities')` añade clave inventory/etiqueta Inventario,
disponible con acceso de lectura a picking y actividades. Tareas/proyectos siguen
sin integración nueva. La clasificación usa origen inmediato y no títulos.

- [ ] Escribir backend: filtro Inventario devuelve actividades de picking solamente,
  conserva empresa/alcance/empleado; Sin proceso vinculado ya no incluye picking.
  Añadir HOOT de selección, conservación al volver y cuenta sin acceso. Retener
  separación de Aceptación y su clasificación por tipos.
- [ ] RED backend y navegador con solo pruebas temporales, producto intacto.
- [ ] Implementar registro/etiqueta/dominio en el servicio existente. No cambiar
  otro botón ni las cinco secciones operativas; usar el bridge actual.
- [ ] GREEN focalizado y HOOT exacto por nombres; comprobar ambos temas y retirar
  pruebas temporales con recibo antes de la regresión final.
- [ ] Commit: `feat: filtrar actividades de inventario en trabajo asignado`.

### Task5: Concurrencia, prueba integrada y entrega

**Files:** pruebas anteriores, manifest, documentación y herramientas aisladas
`.tmp/inventory-activity-pilot/`.

**Interfaces:** versión prevista19.0.25.6.0 si Ingeniería entregó5.0;
revalidar main antes de fijar versión. Baseline exacto viene del recibo de esa
entrega, nunca de una suposición sobre el checkout primario.

- [ ] Preparar y ejecutar dos transacciones concurrentes por confirmación,
  validación/cancelación y parcial. Una identidad por documento/evento, reintentos
  nativos, plazo heredado y cero huérfanas; copia aislada sin cron/correo.
- [ ] Suite backend completa por descubrimiento exacto después de integrar cambios;
  no afirmar870 si hay contratos nuevos. Guardar cada nombre/resultado y restauración.
- [ ] QA manual temporal con recepción/entrega/interno, caso futuro3días, parcial,
  devolución, pausa, reparto/reprogramación y cierre manual sin validar stock.
  Retirar escenario por IDs propios sin borrar historial ni tocar configuraciones ajenas.
- [ ] Revisión independiente, hooks/versionado, PR/CI/merge/main y paquete revisado;
  autorización concreta antes de producción. Backups BD/filestore/código, recuperación
  antes de liberar servicio y verificación de stock/permisos/config/PDFs intactos.
- [ ] Cierre documentado; destinatarios reales, scheduler y Compras permanecen sin activar.

## Self-review del plan

Task1 cubre plazos/configuración y Review Focus1/2/4; Task2 cubre eventos/parciales
y Focus3/5; Task3 cubre privacidad/identidad/manuales; Task4 cubre el Centro; Task5
cubre concurrencia/QA/entrega. Interfaces y modelos se usan con el mismo nombre;
no dependencia funcional de los servicios privados de Ingeniería, solo su baseline.
No hay código de producto o tests nuevos escritos todavía para este plan.
