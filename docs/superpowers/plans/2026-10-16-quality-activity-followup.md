# Seguimiento de alertas de Calidad — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Ejecución propuesta en este chat, sin delegación no autorizada.

**Goal:** Mantener un pendiente nativo para resolver cada alerta ROV abierta, con plazo de1día laborable y reapertura auditada.

**Architecture:** Política por empresa y servicio/historial privados propios de Calidad; eventos reales create/write de alerta reconcilian stage_id.done. Compartir solo `mc.rov.work.deadline` y control general; no hacer depender alertas de la existencia de un ciclo de aceptación.

**Tech Stack:** Odoo19 Enterprise, PostgreSQL, Python/XML, TransactionCase y QA manual STAGING con SSH.

**Spec:** `docs/superpowers/specs/2026-10-16-acceptance-quality-activities-design.md`, aprobado.

## Global Constraints

- Plan independiente en funcionalidad, segunda parte de la entrega conjunta19.0.25.2.0. Depende del cálculo laboral de Task1 del plan `2026-10-16-acceptance-activities.md`, no de sus ciclos o de FEN.
- Plazo inicial1día laborable desde creación de alerta abierta o transición real done→abierta; no reiniciar plazo por editar ni mover entre etapas abiertas.
- Alcance inicial alertas con producto o serie ROV. Un componente sin vínculo explícito al equipo no se clasifica por nombre; no ampliar por inferencia a todos los componentes.
- Mantener `_mc_registrar_alerta_de_fallo` existente, no duplicar alertas/chequeos o crear tareas espejo. `quality.check.user_id` registra ejecutor, no destinatario inferido.
- Cierre por stage_id.done, no etiqueta de etapa. No exigir nuevos campos correctivos/preventivos para cerrar.
- Cuenta, empleado y calendario explícitos; no Dev ni configuración operativa por upgrade. Pausas no impiden cierres ni producen backfill al reactivar.
- Mantener origen/permisos originales, políticas empresa, ciclo único, historial privado, auditoría manual y PDFs intactos.

## Review Focus

1. El cierre de una etapa configurada como done afecta todas las alertas actualmente en esa etapa: Task2 debe reconciliar también cambios de quality.alert.stage.done, sin depender de que se escriba alerta.stage_id.
2. Reabrir una alerta dos veces simultáneamente deja un solo nuevo pendiente y ciclo; Task3 verifica concurrencia.
3. Borrar actividad o marcarla hecha manualmente no cierra alerta ni la regenera por editar; Task2 cubre ambas decisiones.
4. Alerta sin lote durante fabricación puede obtener después el alcance de series: Task2 conserva el seguimiento si ya era ROV por producto, sin nuevo pendiente por completar lot_ids.
5. Cambiar producto/empresa/series mientras hay seguimiento no permite trasladar un pendiente a origen inaccesible; Task3 prueba cambios reales y copias temporales.

## Interfaces y archivos

Crear `models/mc_rov_quality_activity_policy.py`, `models/mc_rov_quality_activity_run.py`,
`models/quality_activity_automation.py`, `models/quality_activity_lifecycle.py`,
`data/quality_activity_types.xml`, `views/mc_rov_quality_activity_policy_views.xml`,
`security/quality_activity_policy_rules.xml` y pruebas focalizadas.
Modificar imports/manifest/ACL, sin cambiar el contenido de `models/quality_alert.py`
cuando una herencia separada preserve correctamente su MRO.

```python
# mc.rov.quality.activity.automation
def _in_scope(self, alert):  # -> bool
    """Producto/serie y raíz ROV, no cadenas del nombre ni autor del control."""
def _start(self, alert, started_at):  # -> run vacío o singleton privado
    """Autoriza origen y destinatario y crea un ciclo pendiente idempotente."""
# mc.rov.quality.activity.lifecycle
def _reconcile(self, alerts, previously_closed, occurred_at):  # -> None
    """Cierra por done o inicia por transición de reapertura real."""
```

`previously_closed` es un mapa id→bool capturado bajo bloqueo antes de mutar;
no se confunde con el estado calculado después. Los IDs temporales no generan efectos.

### Task1: Configuración, alcance e historial

**Files:** política/run/XML/seguridad anteriores, `tests/test_quality_activity_policy.py`; modificar imports, manifest y ACL de política (no ledger).

- [x] Escribir RED del modelo, default enabled=True y lead_days=1, entero1..365/no bool, calendario válido y destinatario autorizado; política única por empresa. ACL Coordinar y regla de empresa, sin lectura del historial por usuarios normales.

```python
def test_quality_policy_defaults(self):
    self.assertIn('mc.rov.quality.activity.policy', self.env.registry.models)
    policy = self.env['mc.rov.quality.activity.policy']
    self.assertEqual(policy.default_get(['enabled', 'lead_days']),
                     {'enabled': True, 'lead_days': 1})
```

- [x] Ejecutar RED nativo, separando fallos esperados de errores de entorno/fixtures. Reutilizar política preexistente solo dentro de la transacción de test, sin borrar ni cambiar configuración real.
- [x] Implementar política con `_configuration_error(alert=False)` y `_deadline(started_at)` adaptador a `_working_date`. Ledger con alert_id restrict, company_id, cycle unique(alert_id,cycle), activity_id setnull, estado, fechas, calendario/tz, actor y motivo. Actividad «Resolver alerta de Calidad» res_model quality.alert.
- [x] Probar `_in_scope`: producto ROV, serie ROV, equipo por fabricación/reparación explícita si alerta carece de producto propio, y exclusión de componente sin enlace inequívoco. Empresas incompatibles se rechazan; nunca seguir producto de otra empresa vía sudo.
- [x] GREEN política/calendario y configuración por upgrade vacía; commit `feat: configurar seguimiento de alertas de Calidad`.

### Task2: Creación, cierre, reapertura y decisiones manuales

**Files:** `models/quality_activity_automation.py`, `models/quality_activity_lifecycle.py`, `tests/test_quality_activity_lifecycle.py`; herencias quality.alert, quality.alert.stage y mail.activity en archivos separados de lógica existente.

- [x] Crear fixture propia con etapas abierta/done y producto/serie ROV, usuario TallerQA con grupos nativos de Calidad y política explícita. Sin depender de nombres de etapas o productos de ejemplo instalados.
- [x] RED: crear alerta abierta inicia1pendiente; crear cerrada0; mover abierta→abierta0extra; done cierra; reabrir genera1nuevo ciclo; pausa conserva cierre y evita creación/reapertura; reactivar/editar no reconstruye; actividad manual homónima no intervenida.
- [x] RED adicional: un chequeo fallido produce la misma única alerta nativa/del módulo y un solo pendiente; cambiar a pass no cierra la alerta. Completar lot_ids de una alerta ya seguida no reinicia fecha ni duplica.
- [x] Implementar create/write con bloqueo de filas ordenado, estado previo real y actor original; `_start` valida política/empresa/acceso antes de escritura privada. Capturar el cierre antes de feedback/unlink y preservar fecha reprogramada/actor.
- [x] En quality.alert.stage.write, si cambia done, capturar alertas afectadas y estados previos bajo bloqueo, ejecutar super y reconciliar estado efectivo. No usar nombre de etapa ni date_close como única verdad; no arreglar otros comportamientos nativos fuera de alcance.
- [x] Registrar hecho/cancelación/archivo/unlink manuales sin cerrar alerta. La siguiente edición abierta no recrea; done→abierta genuino crea nuevo ciclo si está permitido.
- [x] GREEN de eventos, fallos de chequeo y decisiones manuales, conservando retornos nativos; commit `feat: seguir resolución y reapertura de alertas`.

### Task3: Permisos, integración y validación de entrega

**Files:** `tests/test_quality_activity_boundaries.py`, `scripts/qa/quality_activity_concurrency.py`; actualizar runbook conjunto y `docs/pendientes.md`.

- [x] RED+GREEN: origen sin acceso, empresas múltiples, destinatario solo otra empresa, consulta/exportación del ledger, nombres restringidos, NewId/copias sin efectos, cuenta/empleado independientes y reprogramación con motivo. Cambio real de empresa/producto/series seguido se rechaza con explicación o conserva alcance por operación explícita validada; no puede trasladar historial.
- [x] Verificar Centro proceso Calidad ya nativo: pendientes se encuentran por calidad/empleado/alcance sin nueva pestaña, y cierre/reparto mantienen las mismas ACL. Confirmar que lecciones con acción preventiva siguen consultándose sin nuevos criterios.
- [x] Dos transacciones reales aisladas: creación/inicio repetido, reapertura y cierre contra stage.done. Exigir identidad única, un pendiente por ciclo, cero huérfanos y retry transaccional entero. No crear fixtures en producción/STAGING fuera del escenario QA registrado.
- [ ] Revisión integral una vez junto a aceptación, suite exacta completa594base+nuevas y lint. QA manual alerta automática/manual, cierre/reapertura, cambio de etapa.done, pausa y reparto; retirar escenario sin borrar historial.
- [ ] Entregar con Task6 del plan de aceptación: PR adjunto/CI, autorización para merge y despliegue, respaldo/recuperación y verificación de cero retrospectividad. No activar destinatarios reales ni modificar calendarios durante upgrade.

## Autocomprobación del plan

Scope/política(Task1), eventos y alertas ya existentes(Task2), fronteras/centro y
concurrencia(Task3); todos los Review Focus tienen prueba. Ningún cierre depende de
FEN ni de una prueba RND/TRN; no se crea un pendiente por cada control de fabricación.
