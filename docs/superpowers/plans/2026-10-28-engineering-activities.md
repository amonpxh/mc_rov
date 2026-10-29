# Engineering Activities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir pendientes propios de preparar/aplicar ECO ROV, conservando aprobaciones nativas y un límite anual total.

**Architecture:** Políticas por empresa, ciclo privado por ECO y ejecuciones privadas por evento/etapa, siguiendo la separación ya usada en Calidad. Los hooks observan eventos nativos después de que ocurren; el servicio no aprueba ni aplica cambios. La actividad nativa y su historial se mantienen separados del seguimiento propio.

**Tech Stack:** Odoo19, Python/dateutil/pytz, PostgreSQL, XML, TransactionCase y herramientas PowerShell/SSH existentes para STAGING.

**Spec:** `docs/superpowers/specs/2026-10-28-design-inventory-activities-design.md`, aprobado2026-10-28.

## Global Constraints

- Un año calendario TOTAL desde creación del ECO, sin reinicio por etapa/reapertura;29feb→28feb cuando corresponda.
- Ámbito: jerarquía ROV existente, empresa explícita, tipos ECO producto/BoM.
- Reutilizar aprobaciones nativas, sus destinatarios, fechas y decisiones; no crear otro pendiente de aprobar.
- Configuración en Seguimiento automático; ninguna política/destinatario/cron real se crea al instalar.
- Control general pausa nuevos pendientes propios, permite cierres y no reconstruye eventos pasados al reactivar.
- Privacidad y acceso se evalúan bajo actor y destinatario, sin ampliar empresas; historial privado.
- Baseline productivo4.1/main d6f5efe; STAGING nominal2.0 según auditoría, con código posterior instalado: exigir hashes reales, no equivalencia por versión.
- Solo escribir en el worktree aislado. Preservar primario y `.superpowers`. Nunca pedir claves en chat.

## Review Focus

1. ECO compartido/sin empresa o destinatario de otra empresa: no seguimiento ni filtración; Task1/3.
2. Bisiesto, medianoche UTC y usuario con otra zona: aniversario de la fecha local de la política; Task1.
3. Rechazo/retroceso/aprobación obligatoria pendiente: no confundir `allow_apply_change` con aprobación; Task2.
4. Aprobaciones nativas creadas entre hooks: no cambiar IDs, vencimientos ni cierres nativos; Task2/3.
5. Edición ordinaria tras pausa o «Hecho» manual: no reconstruir el evento antiguo; Task2/3.

## Entrega y archivos

Primera entrega funcional de las dos del diseño. Mantener esta rama
`feature/design-inventory-activities` para Ingeniería; logística tendrá otra rama
desde el main que contenga esta entrega. Documentos de ambos planes pueden viajar
con este PR; solo el producto de Ingeniería se entrega aquí.

Nuevos: `models/mc_rov_engineering_activity_policy.py`,
`models/mc_rov_engineering_activity_cycle.py`, `models/mc_rov_engineering_activity_run.py`,
`models/engineering_activity_automation.py`, `models/engineering_activity_lifecycle.py`,
`models/engineering_activity_source.py`, `views/mc_rov_engineering_activity_views.xml`,
`data/engineering_activity_data.xml` y pruebas indicadas por tarea.

Integración: `models/__init__.py`, `tests/__init__.py`, `__manifest__.py`,
`security/ir.model.access.csv`; crear `security/engineering_activity_policy_rules.xml`
según patrón actual de `security/quality_activity_policy_rules.xml`.
Usar herencias en archivos nuevos; no reescribir los puentes de `models/mrp_eco.py`.

## Ejecución verificable en STAGING

Cada tarea lleva RED antes de producto y GREEN focalizado. Los instaladores locales
en `.tmp/engineering-activity-pilot/` y wrappers
`.tmp/staging-engineering-activity-{policy,events,boundaries}-{red,green}.ps1`
se preparan/revisan antes de pedir al usuario ejecutarlos. RED solo cambia pruebas;
GREEN respalda BD/archivos y restaura en base nueva si falla; ambos retiran pruebas
temporales y reinician solo STAGING. Mantener configuraciones/PDFs existentes.

Selector nativo por tarea: `--test-tags /mc_rov:TestEngineeringActivityPolicy`,
`/mc_rov:TestEngineeringActivityEvents`, `/mc_rov:TestEngineeringActivityBoundaries`.
Descubrir nombres exactos mediante AST de los tests finales; no inventar un total.
Guardar código de retorno, cada nombre ejecutado, errores reales y resultado de
restauración. El usuario ejecuta SSH únicamente en su terminal.

### Task 1: Configuración y aniversario con contratos nativos

**Files:** crear política/ciclo/run/vista/data anteriores y
`tests/engineering_activity_common.py`, `tests/test_engineering_activity_policy.py`;
modificar integración/seguridad arriba.

**Interfaces:**
- `EngineeringActivityCommon._eco(**values) -> mrp.eco`, `_policy(**values) -> policy`:
  fixtures propios ROV/otra categoría, dos empresas y cuentas internas/portal.
- Política `mc.rov.engineering.activity.policy`: company, enabled(defaultFalse),
  `prepare_user_id`, `apply_user_id`, empleados opcionales por etapa,
  `lead_years`(entero positivo, default1), `tz` explícita, indicador de configuración.
- `_deadline(created_at: datetime) -> date`; `_configuration_error(eco, stage) -> str|False`.
- Ciclo `mc.rov.engineering.activity.cycle`: ECO/empresa, límite original/vigente,
  etapa observada, contador de evento y estado; unicidad por ECO.
- Run `mc.rov.engineering.activity.run`: ciclo/evento/etapa, actividad, fechas,
  resultado/motivo; unicidad ciclo/evento/etapa, sin ACL pública.

- [x] Escribir `TestEngineeringActivityPolicy`: defaults desactivados/1año;
  bool/fracción/cero rechazados antes de conversión; unicidad empresa; solo
  coordinador configura; usuario sin acceso al origen no recibe; empresa vacía
  no seguida; historial no legible por usuario normal.
  Aserciones calendario exactas:
  ```python
  self.assertEqual(policy._deadline(datetime(2024, 2, 29, 15)), date(2025, 2, 28))
  # tz America/Santiago: fecha local27oct aunque el instante UTC sea28oct.
  self.assertEqual(policy._deadline(datetime(2026, 10, 28, 1)), date(2027, 10, 27))
  ```
  Añadir controles nativos de ECO con aprobación pendiente/satisfecha para fijar
  reglas reales de avance y aplicación, sin sustituir métodos por mocks.
- [x] Ejecutar RED policy: faltan modelos/contratos nuevos; fixtures nativos y
  contratos previos pertinentes deben pasar. Corregir primero fixtures si fallan.
- [x] Implementar interfaces y restricciones mínimas. Reutilizar validación de
  destinatario/empleado público de Calidad, con contexto SOLO de su empresa;
  `relativedelta(years=lead_years)` sobre fecha local, sin usar365días fijos.
  Preparar menú/vista de política, tipos propios `engineering_prepare/apply` y
  reglas de configuración por empresa; no ACL para ciclo/run.
- [x] Ejecutar GREEN policy y verificar ninguna configuración real creada, hashes
  de PDFs/configuración intactos y restauración de pruebas.
- [x] Commit explícito de estos archivos: `feat: configurar seguimiento anual de ingeniería`.

### Task 2: Preparación y aplicación por eventos reales

**Files:** crear automation/lifecycle; ampliar common y
`tests/test_engineering_activity_events.py`; importar en init.

**Interfaces:**
- Servicio `mc.rov.engineering.activity.automation`:
  `_in_scope(eco) -> bool`, `_applicable(eco) -> bool`,
  `_start(eco, stage, occurred_at) -> run|False`.
- Servicio `mc.rov.engineering.activity.lifecycle`:
  `_capture(ecos, access='write') -> dict[id, snapshot]`,
  `_sync(ecos, before: dict, occurred_at) -> None`.
- Snapshot mínimo: activo, state y aplicabilidad nativa. Run conserva evento
  incluso al cerrar manualmente; reactivar política no aumenta ese contador.

- [x] Escribir `TestEngineeringActivityEvents`: creación→preparar; iniciar revisión
  NO cierra preparación; aprobación obligatoria pendiente/rechazada NO crea
  aplicar; aprobación/etapa realmente aplicable completa preparar y crea aplicar;
  aplicación nativa real completa aplicar. Verificar native approval IDs/due dates
  sin cambios por nuestro servicio. Crear ECO done/ajeno/sin política: cero tareas.
  Añadir retroceso/rechazo→retirar aplicar y volver a preparar conservando límite,
  archivo/desarchivo, política activada después de creación sin backfill y nueva
  transición futura sin seguimiento padre calculada desde `create_date` original.
- [x] Ejecutar RED events con fixtures de `action_new_revision`, `approve`, `reject`
  y `action_apply` nativos; registrar nombres y fallos esperados.
- [x] Implementar captura/transición mediante herencias de ECO create/write y
  métodos nativos necesarios. `_applicable` combina estado/etapa, restricciones
  nativas de aprobación/avance y bloqueo; nunca solo `allow_apply_change`.
  Consolidar llamadas anidadas para observar eventos estables, con identidad y
  bloqueo transaccional del origen; preservar resultados/excepciones nativos.
  Cerrar solo actividades propias. Validar política ANTES de escrituras técnicas
  en orígenes nuevos sin seguimiento; pausa no impide cierre de historial existente.
- [x] GREEN events: cada recorrido nativo produce sus tareas exactas, sin duplicar
  aprobación ni renovar el aniversario. Repetir pruebas Task1 solo por integración.
- [x] Commit: `feat: seguir preparación y aplicación real de cambios de ingeniería`.

### Task 3: Decisiones manuales, privacidad e identidad

**Files:** crear source y `tests/test_engineering_activity_boundaries.py`;
extender lifecycle como herencia de mail.activity, patrón de Calidad.

**Interfaces:** `_runs(ecos, pending=False, access='write') -> runs`,
`_check_source_changes(ecos, values) -> None`, `_check_source_deletion(ecos) -> None`.
Callbacks manuales de feedback/unlink/write se integran con los existentes mediante
`super`, sin cambiar el ciclo de reparación/fabricación/aceptación/Calidad.

- [x] Escribir `TestEngineeringActivityBoundaries`: actor multiempresa no amplía
  destinatario; usuario/empleado de otra empresa/archivado falla sin exposición;
  portal y equipo restringido denegados. Hecho manual no aprueba/aplica ECO ni
  regenera tarea por edición ordinaria. Cancelación manual conserva motivo;
  reparto/reprogramación conserva historial y límite original. Preservar company,
  producto, BoM/tipo de ECO seguidos; impedir borrado con explicación. Permitir
  cambios normales en la revisión y registrar temporales sin efectos persistentes.
  Pausa cierra tareas existentes pero no crea etapas nuevas; reactivar sin backfill.
- [x] RED boundaries conserva los recorridos Task2; fallos nuevos deben ser los
  límites de acceso/identidad/manuales que todavía no están implementados.
- [x] Implementar interfaces, callbacks propios y auditoría de plazos/reparto.
  No identificar por título, creador o cuenta administrador. Respetar `NewId` y
  origen persistente; bloquear identidad semántica, no el contenido editable de
  la nueva versión. Permitir cierre de historial al actor autorizado bajo pausa.
- [x] GREEN boundaries y revisión focalizada de regresiones de mail.activity.
- [x] Commit: `fix: proteger identidad y decisiones del seguimiento de ingeniería`.

### Task 4: Validación integrada y entrega de Ingeniería

**Files:** tests finales anteriores, `__manifest__.py`, `docs/pendientes.md`;
herramientas `.tmp/engineering-activity-pilot/` sin incorporar secretos/backups.

**Interfaces:** UI utiliza filtro Diseño existente; no nueva navegación frontend.
Versión prevista19.0.25.5.0; revalidar main antes de fijarla si hubo otra entrega.

- [x] Preparar carreras aisladas de creación, aprobación/entrada aplicable,
  aplicación y archivo/desarchivo. Dos transacciones, reintentos nativos, una
  identidad por evento y cero actividades huérfanas; probar límites del año.
- [x] Ejecutar regresión exacta completa UNA VEZ tras cambios integrados y guardar
  todos los nombres; incorporar cualquier fallo nuevo antes de declarar GREEN.
- [ ] QA con cuentas/empresa/calendario temporales registrados, aprobaciones
  nativas configuradas SOLO para el escenario y fases del ECO. Retirar datos QA
  con propiedad comprobada y preservar historial; verificar políticas ajenas.
- [ ] Revisión independiente de rama, hooks/lint/versionado; PR y CI, merge tras
  autorización, main validado, paquete productivo revisado con respaldo/recuperación.
  Pedir autorización solo sobre una entrega concreta; no activar cuentas reales.
- [ ] Commit de cierre y evidencia precisa. No repetir suites sin cambios nuevos.

## Self-review del plan

Cobertura: política/plazo en Task1; disparadores y aprobaciones en Task2;
manuales/pausa/permisos/identidad en Task3; concurrencia/QA/entrega en Task4.
Las cinco clases de Review Focus tienen contratos en esas tareas. Interfaces
consistentes; no dependencia de logística. Las aprobaciones nativas quedan fuera
del año de nuestras tareas en cuanto a reprogramación automática, según el diseño.
La implementación y cada verificación se registran en docs/pendientes.md y en el ledger del plan.
