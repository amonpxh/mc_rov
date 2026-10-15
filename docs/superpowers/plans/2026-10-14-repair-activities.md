# Actividades automáticas de diagnóstico y reparación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Método propuesto: implementación directa y revisión final independiente; confirmar con el usuario antes de ejecutar.

**Goal:** Generar y cerrar dos actividades nativas independientes, con 2 días laborables desde el inicio de cada etapa y sin duplicados ni cambios a la asignación manual.

**Architecture:** Una política por empresa elige destinatario/calendario; un servicio privado procesa transiciones reales de orden/REV. Un registro técnico sin acceso RPC público conserva cada etapa/ciclo aunque la actividad se archive o elimine. Reutilizar Centro, reparto y vistas nativas existentes.

**Tech Stack:** Odoo 19 ORM, PostgreSQL, resource.calendar, mail.activity, pruebas TransactionCase, scripts PowerShell/SSH de STAGING.

**Spec:** `docs/superpowers/specs/2026-10-14-revision-activity-pilot-design.md`.

## Global Constraints

- Dos actividades nativas, cada una con 2 días laborables desde el inicio de su etapa; regla activada por defecto.
- No implementado ni instalado: este documento no es evidencia de pruebas.
- No duplicar tareas, construir Kanban, modificar PDFs o confirmar documentos desde una actividad.
- Sin retroactivos, extensiones automáticas ni concesión de permisos a cuentas reales.
- Cuenta/empleado/calendario explícitos y compatibles con empresa/origen; configuración incompleta avisa sin bloquear la orden.
- No sobrescribir cuenta, empleado ni fecha después del reparto manual.
- Una sola herramienta escribe en el checkout. Partir de main verificado en un worktree nuevo; conservar documentos locales no versionados.

## Evidencia instalada

Auditoría revertida `.tmp/repair-activity-pilot/installed.json` (ruta relativa al workspace,
fuera del repositorio), 10 fuentes y ninguna ausente. Estado nativo:
`draft → confirmed → under_repair → done`; cancelación `cancel` y retorno a `draft`.
`action_repair_start` confirma si hace falta y escribe `under_repair`;
`action_repair_end` valida ese estado y llama `action_repair_done`.
Por ello observar cambios efectivos, incluidos los producidos por importación/write,
después del `super().write` y la creación actual de primera REV.
`mail.activity._action_done` archiva, `action_cancel` elimina mediante `unlink`.
`resource.calendar._work_intervals_batch(start_dt, end_dt, resources=None,
domain=None, tz=None, compute_leaves=True)` acepta fechas conscientes de zona;
la clave `False` representa el calendario sin recurso individual.
Calendario empresa 1: UTC, lunes-viernes 08–12 / 13–17, sin ausencias globales.
Decisión posterior: reutilizar calendario de empresa configurado America/Santiago,
no crear paralelo por defecto. Auditoría adicional confirmó cuatro hr.version,
cuatro estructuras de nómina, un centro de fabricación y cuatro recursos vinculados;
una cuenta activa ya usa Santiago. Cambio STAGING confirmado: calendario 1 y
recurso activo 3 en Santiago, jornadas/ausencias intactas y tres vencimientos
verificados. Respaldo `/var/tmp/mc-calendar-santiago-zDs8HQ`; evidencia
`.tmp/repair-activity-pilot/calendar-santiago.json`. Producción sin cambios.
No alterar calendarios por upgrade.

## Review Focus

1. Doble clic/concurrencia: una etapa por ciclo; bloqueo de orden antes de leer estado previo.
2. Transiciones terminales/importadas: cerrar directo no inventa actividades; reabrir conserva historia.
3. Cuenta pierde permisos o se cambia origen de actividad: no filtrar información ni operar sobre un origen distinto.
4. Calendario UTC/DST/festivos parciales: contar fechas locales con trabajo efectivo, no franjas ni 48 horas.
5. Actividad hecha/cancelada manualmente: guardar decisión; no duplicar ni afirmar cierre del proceso.

## Task 1: Política y vencimientos con calendario nativo

**Files:** Create `models/mc_rov_repair_activity_policy.py`, `views/mc_rov_repair_activity_policy_views.xml`, `security/repair_activity_policy_rules.xml`, `tests/test_repair_activity_calendar.py`. Modify `models/__init__.py`, `tests/__init__.py`, `security/ir.model.access.csv`, `__manifest__.py`.

**Interfaces:** modelo `mc.rov.repair.activity.policy`; campos `company_id` requerido/único,
`enabled=True`, `user_id`, `employee_id` opcional (hr.employee.public), `calendar_id`,
`diagnosis_days=2`, `repair_days=2` (enteros positivos). Método privado
`_deadline(started_at: datetime, days: int) -> date` devuelve vencimiento o lanza
`ValidationError` por calendario inválido. `_configuration_error(order) -> str|False`
verifica destinatario activo, compañías, employee y acceso read/write al origen.

- [ ] Escribir RED de lunes→miércoles, viernes→martes, ausencia global de lunes→miércoles, dos franjas→un día, ausencia parcial, semana alterna, evento UTC que cae el día anterior en Santiago, calendario vacío/flexible sin jornada explícita y destino archivado/otra empresa. Fixtures crean calendario y ausencias transaccionales; no editar calendario instalado.

```python
from datetime import datetime, date
from odoo.tests.common import TransactionCase

class TestRepairActivityCalendar(TransactionCase):
    def test_two_business_days_exclude_event_day(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'QA lunes viernes', 'tz': 'America/Santiago',
            'attendance_ids': [(0, 0, {
                'name': str(day), 'dayofweek': str(day),
                'hour_from': 8, 'hour_to': 17, 'day_period': 'morning',
            }) for day in range(5)],
        })
        policy = self.env['mc.rov.repair.activity.policy'].create({
            'company_id': self.env.company.id, 'calendar_id': calendar.id,
            'user_id': self.env.user.id,
        })
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15), 2),
                         date(2026, 10, 20))
```

- [ ] Ejecutar `/mc_rov:TestRepairActivityCalendar` y comprobar fallo esperado por ausencia de modelo/método, sin aceptar errores de carga como RED válido.
- [ ] Implementar cálculo: convertir instante UTC a calendar.tz, comenzar medianoche del día siguiente; consultar intervalos efectivos sin resource ni employee_timezone heredada. Recorrer intervalos y añadir cada fecha local con duración positiva a un conjunto ordenado. Consultar ventanas de 35 días hasta alcanzar days, límite de 366 días; si no se alcanza, error de configuración, nunca fecha inventada.

```python
tz = pytz.timezone(self.calendar_id.tz)
event_day = pytz.utc.localize(started_at).astimezone(tz).date()
start_day = event_day + timedelta(days=1)
# Cada límite se localiza por separado para no sumar 24h a través de DST.
start = tz.localize(datetime.combine(start_day, time.min))
end = tz.localize(datetime.combine(start_day + timedelta(days=35), time.min))
intervals = self.calendar_id.with_context(employee_timezone=False)._work_intervals_batch(
    start, end, resources=None, tz=tz, compute_leaves=True,
)[False]
```

- [ ] Dividir también intervalos que cruzan medianoche; excluir segmento de duración cero en límite final. Usar `resource_id=False` y empresa correspondiente para ausencias globales. Dos franjas y almuerzo no cuentan como tres días.
- [ ] ACL: Coordinación (`mc_rov.group_work_assignment_coordinate`) crea/edita política solo de empresas permitidas; regla company_id in company_ids. Sin permisos a RRHH privado. Formulario/action menú «Seguimiento de reparaciones» bajo `menu_mc_rov_root`, restringido a Coordinación; mostrar activado, días, cuenta y calendario. Ausencia de fila equivale a habilitado pero incompleto, sin crear pendientes. Nunca autoseleccionar administrador.
- [ ] GREEN focalizado, XML/lint y commit `feat: configurar plazos del seguimiento de reparaciones`.

## Task 2: Identidad, ciclos y creación atómica

**Files:** Create `models/mc_rov_repair_activity_run.py`, `models/repair_activity_automation.py`, `tests/test_repair_activity_automation.py`. Modify `models/__init__.py`, `tests/__init__.py`, `models/repair_order.py`.

**Interfaces:** modelo privado `mc.rov.repair.activity.run`, campos `company_id`,
`repair_id`, `cycle`, `stage` (diagnosis/repair), `revision_id`, `activity_id`
(ondelete set null), `started_at`, `original_deadline`, `calendar_id`, `calendar_tz`,
`outcome` (pending/business_done/manual_done/cancelled), `finished_at`.
Unicidad SQL `(repair_id, cycle, stage)`; ninguna ACL pública ni menú de runs.
En orden: `mc_activity_cycle` Integer readonly, copy=False, y
`mc_activity_cycle_closed` Boolean readonly, copy=False. Evitar escritura RPC
de estos campos; gestionarlos solo desde helper privado validado, sin confiar
en un flag de contexto que un cliente puede falsificar.
Servicio AbstractModel `mc.rov.repair.activity.automation`:
`_after_order_transition(order, old_state, started_at) -> None`,
`_start_stage(order, stage, started_at, revision=False) -> run|False`.

- [ ] Crear fixture sobre `RevisionCommon` de `tests/test_mc_rov_revision.py` (producto/serie ROV), destinatario de taller y política de Task 1. Crear orden con product_id, lot_id, company_id. Testear confirmación repetida, inicio repetido y componente no ROV.

```python
order.action_repair_start()
runs = self.env['mc.rov.repair.activity.run'].sudo().search([
    ('repair_id', '=', order.id), ('outcome', '=', 'pending')])
self.assertEqual(set(runs.mapped('stage')), {'diagnosis', 'repair'})
order.write({'state': 'under_repair'})
self.assertEqual(len(runs), self.env['mc.rov.repair.activity.run'].sudo().search_count([
    ('repair_id', '=', order.id), ('outcome', '=', 'pending')]))
```

- [ ] RED de creación única, primera REV existente confirmada (sin diagnóstico), primera REV borrador reutilizada, RND/TRN/REV posterior no seleccionadas, ausencia de política/cuenta/calendario, directo draft→done sin creación, install/upgrade sin backfill, lote añadido después del evento sin reconstrucción retroactiva.
- [ ] En `repair_order.write`, si hay registros y se solicita state, antes de super bloquear filas ordenadas y leer estados actuales; después de super y `_crear_revision`, procesar transición por registro. Mantener validadores y retorno existentes. Si vals no cambia estado real, no procesar. Evitar SQL IN vacío. Usar SQL parametrizado y tabla ORM para bloqueo.

```python
from odoo.tools import SQL
locked = self.sorted('id')
self.env.cr.execute(SQL('SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE',
                       SQL.identifier(self._table), tuple(locked.ids)))
locked.invalidate_recordset(['state'])
previous = {order.id: order.state for order in locked}
```

- [ ] Primer evento abierto inicia cycle=1; reapertura terminal o reentrada desde draft con ciclo cerrado aumenta una sola vez. cancel→draft no genera, confirmed→under_repair mantiene ciclo. Orden antigua confirmed→under_repair genera solo reparación nueva, sin diagnóstico retroactivo.
- [ ] Antes de elevación técnica verificar operación write del actor y acceso del destinatario al origen bajo su empresa; solo servicio privado eleva para ledger y actividad del evento autorizado. Crear mail.activity sobre repair.order con tipo propio no encadenado, título por stage, usuario explícito y empleado opcional. Nota usa enlaces `/odoo/repair.order/ID` y `/odoo/mc.rov.revision/ID` escapados por Markup/format, no HTML concatenado de nombres.
- [ ] Error esperado de configuración: registrar aviso de origen con causa accionable y log; no inventar cuenta/fecha ni bloquear orden. Error inesperado de creación: abortar transacción completa, no ocultarlo con except Exception. Fecha/identidad y actividad se guardan juntas.
- [ ] Testear rollback con excepción posterior a super y prueba de dos transacciones coordinadas sobre orden fixture confirmada: solo un run por stage, ninguna actividad huérfana. El test concurrente usa BD CI desechable y limpia registros de prueba en finally; no commits de fixtures en STAGING real.
- [ ] GREEN focalizado y commit `feat: generar actividades por etapa sin duplicados`.

## Task 3: Cierre de negocio, decisiones manuales y reapertura

**Files:** Modify `models/repair_activity_automation.py`, `models/mail_activity.py`, `models/mc_rov_revision.py`, `tests/test_repair_activity_automation.py`. Create `data/repair_activity_types.xml`; load in `__manifest__.py`.

**Interfaces:** `_after_revision_confirmation(revision) -> None`,
`_finish_run(run, outcome, feedback) -> None`. Tipo diagnóstico y tipo reparación
sin sucesor automático: no usar encadenamiento nativo para crear segunda etapa.

- [ ] RED: confirmar REV exacta termina diagnóstico y deja reparación abierta; confirmar otra no termina; finalizar orden termina solo reparación; validación fallida no cierra; cancelación guarda cancelled y conserva auditoría; confirmar diagnóstico no inicia reparación.

```python
self._corrida_completa(revision)
self._responder_todo(revision)
self._responder_sellos(revision)
revision.action_confirmar()
self.assertFalse(diagnosis.activity_id.active)
self.assertEqual(diagnosis.outcome, 'business_done')
self.assertTrue(repair.activity_id.active)
self.assertEqual(order.state, 'under_repair')
```

- [ ] Integrar confirmación por transición de `estado` en `mc_rov_revision.write`, después de super; seleccionar run por revision_id exacta, pendiente y orden abierta. No crear por reabrir documento. No marcar otra REV ni cambiar técnicos.
- [ ] En done, `_finish_run` fija business_done y luego llama `activity.action_feedback(feedback=...)`; cancel registra outcome antes de `action_cancel` y postea motivo de orden. Nunca marcar cancelación como hecho. Cierre de ciclo al llegar a done/cancel, sin completar diagnóstico por sustitución.
- [ ] `mail.activity._action_done` valida acceso/origen actual antes de super; tras éxito cambia solo runs pending a manual_done. `unlink` y `write(active=False)` registran cancelled si siguen pending; outcome business_done ya fijado no se degrada por archivado interno. Guardar evento antes de unlink para mantener identidad al borrar relación. Mismo transaction rollback protege toda operación.
- [ ] Testear títulos manuales iguales intactos, cierre manual sin modificar fuente, borrado/cancelación sin recreación al editar, cuenta/empleado/fecha modificados se mantienen, copia de actividad no hereda run, actividad movida a otro origen es rechazada si está seguida. Comprobar exportación/lectura no revela ledger ni empleado privado.
- [ ] Reapertura: ciclo anterior conserva resultado; nuevo diagnóstico solo si REV aplicable sigue sin confirmar; reparación al volver a under_repair. Desactivar política impide creación pero no impide cerrar runs existentes.
- [ ] GREEN y commit `feat: cerrar seguimientos con eventos reales y conservar historia`.

## Task 4: Permisos, integración y entrega verificable

**Files:** Create `tests/test_repair_activity_access.py`, `docs/runbooks/repair-activity-pilot.md`. Modify `__manifest__.py`, `docs/pendientes.md`, spec. Scripts del workspace `.tmp/staging-repair-activity-red.ps1` y `.tmp/staging-repair-activity-green.ps1` con payloads en `.tmp/repair-activity-pilot/`.

- [ ] RED/green de destino sin acceso a orden, coordinador fuera de empresa, campos internos falsificados por RPC, lectura privada de ledger, origen de actividad cambiado, cuenta archivada, empresa cambiada tras generar, REV seguida borrada. Bloquear borrado/cambio de empresa/origen que rompa run pendiente con mensaje explicativo; no impedir archivado de actividad concluida ni borrar historia.
- [ ] La instalación no crea políticas activas con cuentas elegidas automáticamente: valores por defecto enabled=True, cuenta/calendario sin selección forzada. Configurar fixture piloto explícita. Elegir calendario de empresa tras validar cambio Santiago en STAGING y confirmar cuenta antes de activar escenario; nunca modificar calendario por upgrade, importar festivos no verificados ni reactivar QA anterior silenciosamente.
- [ ] Versionar funcionalidad compatible como `19.0.25.0.0`; importar tests por archivo real. Scripts verifican número de tests descubierto y marcadores, LF/UTF-8 sin BOM, backup BD/código, lock exclusivo, restauración código/vistas si falla y servicio active. RED solo pruebas temporales; green instala código/configuración de prueba autorizada, no producción. Conservar hashes de PDFs y no modificar pendientes reales.
- [ ] Ejecutar clases focalizadas y luego suite completa `/mc_rov` en CI/BD desechable. Una suite vacía no cuenta como GREEN. Precommit XML/Black/pylint y revisión final de diff contra spec.
- [ ] QA manual: iniciar visita, dos vencimientos según cada inicio, repartir solo empleado, confirmar REV y comprobar cierre independiente, terminar orden, cancelar/reabrir escenario, permisos Taller/Supervisor y retorno Centro/orden/REV. Usar fechas controladas para fines de semana en tests, sin esperar dos días reales.
- [ ] Runbook incluye configuración, festivos registrados, aviso por configuración incompleta, diferencia cierre manual/de negocio, desactivación y rollback. PR explica trigger/antes-después y evidencia; adjuntar PR a chat. Actualizar pendientes distinguiendo local, STAGING, CI, merge y producción. No desplegar producción hasta QA y autorización de entrega.

## Self-review del plan

- Cobertura de spec: Task 1 plazos/configuración; Task 2 identidad/transacciones; Task 3 ciclos/eventos; Task 4 permisos/despliegue y no retroactivos.
- Review Focus: concurrencia Task 2; terminales Task 2/3; pérdida de acceso Task 4; calendario/zona Task 1; manuales Task 3.
- Interfaces coherentes: servicio único; ledger privado; política accesible solo a Coordinación; no contexto RPC usado como autorización.
- No producto implementado. Antes de ejecutar: revisión del usuario del plan y método; selección de calendario/cuenta antes de QA instalada.
