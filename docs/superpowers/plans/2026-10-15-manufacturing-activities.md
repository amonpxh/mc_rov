# Automatismos de fabricación y configuración — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Ejecutar en este chat, sin delegar salvo autorización explícita posterior.

**Goal:** Crear un pendiente nativo por fabricación ROV y administrar generación/plazos desde una ubicación común por empresa.

**Architecture:** Control general de creación compartido con reparación; política y seguimiento privados propios de fabricación. Eventos de MRP y movimientos reconcilian estados persistidos sin efectos desde campos compute. Actividades y reparto nativos; ninguna tarea de Proyecto espejo.

**Tech Stack:** Odoo 19 Enterprise, PostgreSQL, Python, XML, TransactionCase; PowerShell/Bash para QA STAGING con SSH manual.

**Spec:** `docs/superpowers/specs/2026-10-15-manufacturing-activities-design.md`.

## Global Constraints

- Plazo máximo inicial 4 semanas = 28 días corridos desde confirmación; fecha límite explícita anterior prevalece. MO restante de una seguida conserva vencimiento vigente.
- Cuenta y empleado distintos; usuario interno y calendario elegidos explícitamente por empresa, sin heredar empresas del actor.
- Solo productos bajo raíz ROV del Centro; no inferir aplicabilidad por nombre o serie.
- Desactivar creación no borra ni completa pendientes; tampoco impide cierre por negocio. Reactivar no hace backfill.
- No duplicar operaciones, controles de Calidad, aceptación, inventario ni tareas de Proyecto. No modificar PDFs/calendarios/cuentas reales.
- Pruebas temporales se restauran. Sin producción hasta QA y autorización específica de esta entrega.
- Base `3d799d3467fe9b59315e59f68443f188b6665a54`: 489 pruebas y CI de main aprobados. No repetir esa suite hasta modificar producto.
- Versión de esta ampliación `19.0.25.1.0`, compatible y sin reconstrucción de datos históricos.

## Review Focus

1. Desactivar general entre etapas: impedir creaciones nuevas en reparación/fabricación, seguir cerrando pendientes de ambos. Task 1/3.
2. Asistente y movimientos completan una MO por caminos distintos: nunca cerrar por clicar antes del resultado real ni depender solo de write(state). Task 3.
3. Retropedido con fecha anterior o actividad reprogramada: conservar límite vigente de original sin copiar resultado/empleado ni iniciar otras cuatro semanas. Task 2/3.
4. NewId, origen oculto y actor multiempresa: ninguna copia temporal altera una corrida real y no ampliar contexto del destinatario. Task 3/4.
5. Cambio horario y medianoche UTC: contar 28 fechas locales, no 28 jornadas ni 672 horas UTC. Task 2.

## Archivos e interfaces

- `models/mc_rov_automation_control.py`: configuración general única por empresa, chatter y `_creation_enabled(company) -> bool` privado, sin selección implícita de cuentas.
- `views/mc_rov_automation_control_views.xml`, `security/automation_control_rules.xml`: menú padre Automatizaciones, acción/formulario general, regla company_ids y ACL Coordinación read/write/create, no unlink.
- `models/mc_rov_manufacturing_activity_policy.py`: política única por empresa; enabled, user_id, employee_id público, calendar_id, lead_days=28. `_configuration_error(production=False) -> str|False`, `_deadline(started_at, explicit_deadline=False) -> date`.
- `models/mc_rov_manufacturing_activity_run.py`: identidad privada MO/ciclo, relación al seguimiento original si retropedido, actividad, inicio, límite original, calendario/zona, resultado/actor/motivo; unicidad MO+ciclo. Sin ACL pública.
- `models/manufacturing_activity_automation.py`: servicio privado `_after_confirmation(productions, started_at)`, `_reconcile(productions)`, `_finish(run, outcome, reason)` y extensión de MO para hooks/identidad.
- `models/manufacturing_activity_stock.py`: hooks de movimientos si el camino nativo de movimientos termina/cancela MO fuera de sus botones. `_action_done(*args, **kwargs)` y `_action_cancel(*args, **kwargs)` conservan retorno y solo reconcilian MO relacionadas ya seguidas.
- `models/manufacturing_activity_lifecycle.py`: decisiones manuales de mail.activity, defensa del origen y borrado de MO con historia; no tocar los resultados de reparación.
- `views/mc_rov_manufacturing_activity_policy_views.xml`, `security/manufacturing_activity_policy_rules.xml`, `data/manufacturing_activity_types.xml`: política de Coordinación y tipo nativo no encadenado.
- Modificaciones de integración: `models/__init__.py`, `tests/__init__.py`, `security/ir.model.access.csv`, `__manifest__.py`; reparentar menú existente de reparación sin cambiar su XML ID.
- `tests/test_automation_control.py`, `tests/manufacturing_activity_common.py`, `tests/test_manufacturing_activity_policy.py`, `tests/test_manufacturing_activity_generation.py`, `tests/test_manufacturing_activity_lifecycle.py`, `tests/test_manufacturing_activity_access.py`.
- `scripts/qa/manufacturing_activity_concurrency.py`, `docs/runbooks/manufacturing-activities.md`, `docs/pendientes.md` y actualización del runbook de reparación para nueva ubicación.

## Task 1: Control general y ubicación única

- [ ] Crear `TestAutomationControl(TransactionCase)`, tagged post_install/-at_install. RED de modelo/menú ausentes; default True, ausencia de registro equivale a True, unicidad por empresa, Coordinación solo empresas permitidas y usuario operativo sin escritura. Prueba visible del formulario y reparentado de reparación.

```python
def test_general_default_and_pause(self):
    self.assertIn('mc.rov.automation.control', self.env.registry.models)
    control = self.env['mc.rov.automation.control']
    self.assertTrue(control._creation_enabled(self.env.company))
    row = control.create({'company_id': self.env.company.id})
    self.assertTrue(row.enabled)
    row.enabled = False
    self.assertFalse(control._creation_enabled(self.env.company))
```

- [ ] Registrar RED focalizado sin errores de fixture, instalación temporal de pruebas y restauración, servicio activo. Antes de esperar un fallo del nuevo guard, probar reparación ya existente con su fixture válida.
- [ ] Implementar `mc.rov.automation.control` con mail.thread, company_id requerido, enabled default=True tracking=True, SQL UNIQUE(company_id); regla global company_ids, ACL solo Coordinación. Consulta privada con sudo limitada a company_id, sin método RPC público que cambie configuración.

```python
def _creation_enabled(self, company):
    company.ensure_one()
    row = self.sudo().search([('company_id', '=', company.id)], limit=1)
    return not row or row.enabled
```

- [ ] Añadir menú Seguimiento automático y submenú Control general con nombre visible «Crear actividades automáticas». Reparentar menu_repair_activity_policy al nuevo padre conservando acción e identidad. Mostrar ayuda: no afecta pendientes existentes ni automatismos nativos de Odoo.
- [ ] En reparación `_start_stage`, después de `order.check_access('write')` y validación de etapa, retornar False si control general está apagado. No añadir el guard al cierre del ledger. Nuevas pruebas que usan helpers de generación/lifecycle existentes cubren: general apagado no crea, política apagada no crea, general reactivado no reconstruye y REV exacta sigue cerrando un pendiente previo.
- [ ] GREEN focalizado + 66 contratos existentes de reparación; validar vista/ACL con usuario no administrador. Commit `feat: centralizar control de actividades automáticas`.

## Task 2: Política, fechas e identidad de fabricación

- [ ] Crear helper `ManufacturingActivityCommon(RevisionCommon)` sin métodos test heredados, con usuario Taller MRP, calendario explícito Santiago y método `_production(**values)` que crea MO de `self.product`, cantidad 1, UoM del producto. `_policy(**values)` debe comprobar modelo presente antes de crearlo. `_runs(production)` consulta ledger privado desde entorno de test.

```python
def _production(self, **values):
    return self.env['mrp.production'].create({
        'product_id': self.product.id,
        'product_qty': 1.0,
        'product_uom_id': self.product.uom_id.id,
        'company_id': self.env.company.id,
        **values,
    })
```

- [ ] RED de política/cálculo faltantes. Casos: default28, configurable1..365, bool y valores fuera de rango rechazados; confirmar viernes incluye sábados/domingos; UTC 01:00 corresponde al día anterior local; cambio DST suma fechas; fecha explícita anterior/igual/posterior; fecha explícita vencida no se mueve a hoy; calendario otra empresa y cuenta archivada/portal rechazados.

```python
def test_twenty_eight_calendar_days(self):
    policy = self._policy()
    started = datetime(2026, 10, 16, 15)
    self.assertEqual(policy._deadline(started), date(2026, 11, 13))
    self.assertEqual(policy._deadline(started, datetime(2026, 10, 30, 15)),
                     date(2026, 10, 30))
```

- [ ] Implementar política con validación ORM antes de flush, UNIQUE empresa y rango SQL. Cuenta válida exige acceso MRP de lectura/escritura con allowed_company_ids=[company.id], empleado hr.employee.public legible y perteneciente a empresa. Calendario aporta zona; no exigir asistencia laboral ni excluir festivos para días corridos.

```python
local_start = fields.Datetime.context_timestamp(
    self.with_context(tz=self.calendar_id.tz), started_at).date()
deadline = local_start + timedelta(days=self.lead_days)
if explicit_deadline:
    explicit = fields.Datetime.context_timestamp(
        self.with_context(tz=self.calendar_id.tz), explicit_deadline).date()
    deadline = min(deadline, explicit)
return deadline
```

- [ ] Crear ledger privado sin ACL pública. Campos: company_id, production_id (restrict), cycle, parent_run_id (restrict), activity_id (set null), started_at, original_deadline, calendar_id/tz, outcome pending/business_done/manual_done/cancelled, finished_at/by/reason; UNIQUE(production_id,cycle), CHECK(cycle>0).
- [ ] Política visible en Seguimiento automático → Fabricación; etiquetas «Plazo máximo (días corridos)» y ayuda «28 días equivalen a cuatro semanas». Sin crear política por upgrade. GREEN y commit `feat: configurar seguimiento de fabricación en cuatro semanas`.

## Task 3: Eventos reales, retropedidos y decisiones manuales

- [ ] RED sobre fixture MO: confirmar crea1; confirmar repetido crea0 adicionales; general/política apagados o producto no ROV crean0; falta configuración avisa sin inventar destinatario; fallo inesperado posterior revierte actividad+ledger+evento juntos; MO existente no se reconstruye al editarla.
- [ ] Implementar `_after_confirmation` con registros persistidos, acceso write y pertenencia real a raíz ROV, bloqueo SQL parametrizado de filas ordenadas, captura del estado previo y condición de transición nativa real desde draft. Identidad interna no falsificable por create/write/context público; cambios privados mediante método interno explícito.
- [ ] Crear tipo `activity_type_manufacturing_complete`, título «Completar fabricación», res_model mrp.production, cuenta/empleado explícitos y nota con enlace escapado al origen. Consultar control general y política antes de crear; guardar actividad/ledger en misma transacción. No usar encadenamiento, cron ni base.automation para duplicar la lógica.
- [ ] Cubrir confirmación de retropedidos por `_action_confirm_mo_backorders` además de `action_confirm`, comprobando MRO real de installed.json. Una copia normal no hereda ledger/actividad/ciclo; un retropedido derivado de MO seguida recibe identidad nueva y límite vigente de actividad original (aunque ya esté archivada), con fecha explícita anterior como tope. Conservar el valor al cerrar la original para que unlink nativo no pierda el límite reprogramado. No copiar empleado/resultado.
- [ ] RED de lifecycle: asistente antes de done conserva pendiente, finalizar tras validar lo cierra; cancelación real cancela; `_action_cancel` que deja MO done no se acredita como cancel si realmente quedó terminada; retropedido parcial deja actividad nueva y solo cierra original terminada; operaciones terminadas/to_close no equivalen a done. Prueba terminar desde Shop Floor y movimientos nativos relacionados; reconciliar estado efectivo fuera de compute.

```python
def test_start_is_not_completion(self):
    self._policy()
    mo = self._production()
    mo.action_confirm()
    run = self._runs(mo)
    self.assertEqual(run.outcome, 'pending')
    self.assertTrue(run.activity_id.active)
    self.assertNotEqual(mo.state, 'done')
```

- [ ] Implementar hooks de confirmación/cierre/inventario/cancelación conservando retorno y argumentos de super. Para movimientos, recopilar MO por production_id/raw_material_production_id antes/después de operación; filtrar solo seguidas y reconciliar estado efectivo. Nada de side effects en _compute_state ni sudo sobre el negocio de quien inicia el evento.
- [ ] `_finish` fija resultado/actor/motivo antes de action_feedback/action_cancel nativos para que archivado interno no degrade business_done a manual_done. Archivo/unlink/hecho manual registran decisiones propias sin cambiar MO ni afectar ledger de reparación. No recrear en siguiente edición ni al reactivar política/general.
- [ ] RED/GREEN de reparto solo empleado/usuario/fecha y conservación de campos no seleccionados; los cambios de política no reprograman existentes. Proteger referencias pendientes de actividad/MO; MO con historial no se borra, con mensaje comprensible. No crear un botón de reapertura; solo detectar nueva confirmación si el ciclo nativo la permite tras cancelación real.
- [ ] Focalizados de generación+lifecycle y reparación previa, commit `feat: seguir fabricación hasta su cierre real sin duplicados`.

## Task 4: Fronteras, concurrencia y entrega STAGING

- [ ] RED/GREEN de usuario sin acceso al origen, otra empresa, contexto receptor limitado, actividad temporal con origen/editada, MO NewId sin origen, identidad falsificada RPC, historial no exportable y reprogramación auditada. Pruebas de eventos mezclados en recordsets y atomicidad si uno falla. Control general apagado debe afectar generación de ambos procesos y conservar sus cierres.
- [ ] Verificar menú Seguimiento automático restringido a Coordinación; Taller solo gestiona trabajo permitido. Un administrador con grupo técnico no implica elegirlo como destinatario. Consultas nativas y filtro Fabricación deben incluir únicamente actividades cuyo origen sigue siendo accesible, sin lista congelada de IDs.
- [ ] Completar imports/ACL/reglas/XML y versión19.0.25.1.0, runbook con ubicación, 28 corridos vs reparación2 laborables, interruptor general/proceso, efecto futuro y motivos. Actualizar docs/pendientes distinguiendo local/STAGING/CI/producción y configuración real todavía aplazada.
- [ ] Scripts del workspace `.tmp/staging-manufacturing-activity-*-red.ps1` y `*-green.ps1`, payload de archivo UTF8/LF, sin exportar código grande por entorno; solo STAGING marcado, lock y backup, tests temporales restaurados y servicio activo. Recuperación si falla sobre BD nueva verificada, preservando la fallida y código anterior; no clean sobre base viva. Validar sintaxis antes de SSH manual.
- [ ] Ejecutar suite completa `/mc_rov` con descubrimiento por AST y coincidencia exacta de nombres; no fijar arbitrariamente un conteo objetivo ni aceptar suite vacía. Hooks nativos, revisión de diff y dos transacciones PostgreSQL reales por confirmación/cierre en copia con prefijo `mc_rov_manufacturing_ci_`, sin correo/cron y conexiones bloqueadas al terminar. Reintentar transacción completa por serialización, comprobar1run/1actividad y0huérfanos.
- [ ] QA operativa STAGING con autorización de escenario nuevo: cuenta Taller/Supervisor, MO normal y parcial, plazo anterior28, reparto/fecha con motivo, general/proceso desactivados y vuelta a activar sin backfill, cancelación/cierre independientes, retorno al Centro. Archivar escenario conservando auditoría tras aprobación del usuario. No crear fixtures en producción.
- [ ] Revisión final, commit de entrega, PR adjunto al chat y CI en checkout aislado. No merge/despliegue de esta ampliación hasta aprobación de entrega. Preparar instalador concreto con backup/chequeo de esquema/no backfill cuando corresponda.

## Self-review

- Spec cubierta: objetivo/alternativas → Task1/3; política/plazos → Task2; eventos/retropedidos/manuales → Task3; privacidad/concurrencia/entrega → Task4.
- Review Focus tiene pruebas asignadas a Task1..4. Los hooks computados no se suponen cubiertos por write: se verifican caminos de movimientos/operaciones.
- Funciones privadas están declaradas en Archivos e interfaces; los fixtures reutilizan RevisionCommon sin heredar clases con tests que inflen descubrimiento.
- Control general solo frena creación de nuestros pendientes; no se presenta como apagado de toda automatización de Odoo. Configuración real sigue pendiente de cuenta Taller/calendario.
- Plan y diseño para revisión antes de escribir código de producto.
