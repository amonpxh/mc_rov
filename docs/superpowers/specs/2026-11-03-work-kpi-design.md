# KPI de seguimiento: primer incremento

## Evidencia instalada

Auditoría `installed-20261103-162622-901.json`, STAGING, READ ONLY y rollback;
33 modelos, fuentes137 intactas y PID sin cambios. La versión nominal de STAGING
es19.0.25.2.0; sus fuentes corresponden al baseline funcional verificado de la entrega6.0.
No extrapolar sus conteos a producción: contiene datos históricos de ensayos.

Los seis modelos `mc.rov.<flujo>.activity.run` tienen `started_at`, `original_deadline`,
`outcome` y `finished_at`. Cinco tienen `current_deadline`; Reparación no lo conserva.
En Reparación no se reconstruye el plazo final desde el chatter ni desde una actividad
archivada editable. Los otros cinco usan el valor capturado por su cierre real.
Ingeniería e Inventario conservan zona del ciclo; los otros cuatro, `calendar_tz`.
No hay atribución histórica homogénea por empleado; `finished_by_id` identifica la
cuenta autora del cierre, que puede ser compartida. No producir rankings personales.

## Decisiones del primer corte

Elección de implementación de Codex: comenzar por métricas de etapas/eventos por
proceso y empresa. No equivalen al número de órdenes completas ni a productividad
individual. Metas y umbrales de colores quedan sin fijar hasta acordarlos.

Separar un núcleo de cálculo puro de la lectura autorizada en Odoo y de la interfaz.
El núcleo recibe filas ya autorizadas y normalizadas; no consulta BD ni concede permisos.
El servicio posterior no abrirá ACL de los historiales privados. Sus consultas de
presentación tampoco usarán gateways de cierre que bloquean filas o exigen escritura.

### Poblaciones y fórmulas

1. **Etapas pendientes actuales:** `outcome=pending`, una por identidad de run autorizada.
   Si falta la actividad activa, conservar la obligación y señalar la inconsistencia.
2. **Pendientes vencidas:** pendiente con plazo vigente conocido anterior a la fecha
   local de corte. El vencimiento de hoy no está vencido. Sin plazo conocido se cuenta
   como cobertura incompleta, no como puntual ni vencida.
3. **Etapas terminadas en el período:** solo `business_done` con cierre dentro del
   período seleccionado. Cuenta cada run/evento, incluidos cierres de distintas etapas
   de una misma orden. Cancelaciones y `manual_done` no son terminaciones reales.
4. **Cumplimiento del plazo original:** terminadas con fecha local de cierre menor o
   igual a `original_deadline` / terminadas con ambas fechas conocidas. Mostrar numerador,
   denominador y casos sin datos. Sin denominador, porcentaje desconocido (`None`).
5. **Cumplimiento del plazo vigente capturado:** fórmula anterior con `current_deadline`
   histórico. No sustituir un valor ausente por el original; mostrar cobertura incompleta.
6. **Mediana de duración de etapa:** horas corridas entre inicio y cierre UTC, para
   terminaciones reales con instantes válidos. No llamar días laborables a horas/24.
   Duración negativa o incompleta se excluye y se informa; duración cero es válida.

El período filtra los cierres, no el backlog actual. La normalización aporta la fecha
local del corte y del cierre de cada fila, derivada de la zona capturada del seguimiento.
Los plazos pendientes provienen de la actividad actual cuando está autorizada; las
fechas originales se conservan para el indicador original. Un cambio de plazo puede
mejorar el cumplimiento vigente y no el original; ambos deben seguir visibles.

Se muestran cancelaciones y cierres manuales históricos del período como contexto,
separados de las terminaciones. Rechazos y reaperturas se especificarán por proceso
en un siguiente incremento: un nuevo run/ciclo no demuestra por sí solo una reapertura
y un rechazo no significa lo mismo en los seis flujos.

### Contrato del núcleo

`models/work_kpi_metrics.py::build_metrics(rows)` recibe iterable de diccionarios con:
`outcome`, `in_period` (para cierres), `started_at`/`finished_at` UTC naive normalizados,
`finished_date` local, `original_deadline`, `current_deadline`, `as_of_date` local,
`activity_active` y `pending_deadline` actual. Devuelve contadores y métricas con
`value`, `known`, `unknown`; cumplimiento añade `on_time`. No redondear porcentajes
en el núcleo; la interfaz decidirá su presentación. No alterar las filas recibidas.

### Autorización e interfaz siguientes

Primer tablero de equipo para usuarios con consulta de equipo y lectura nativa del
origen, limitado a sus empresas activas; el detalle reutiliza acciones nativas sobre
documentos autorizados. Flujos sin permiso se muestran no disponibles, no con cero.
No introducir filtros por empleado para cumplimiento histórico sin evidencia suficiente.
El diseño del servicio y de las vistas se concretará después del núcleo probado y de
sus contratos de permiso. No instalar un tablero parcialmente autorizado.

## Otros hallazgos de la auditoría

Compras y `purchase_stock` instalados; confirmación, doble aprobación y creación de
recepción nativas disponibles. `purchase_requisition` no está instalado; no confundirlo
con una solicitud interna del taller ni instalarlo por el nombre.
No aparecen modelos `ai.*` o `llm.*`. Solo `ai_auto_install` figura instalado entre las
extensiones listadas; auditar el módulo exacto `ai`, manifiestos y dependencias disponibles
antes de escoger motor o instalar. La consulta inicial por prefijo no cierra esa cuestión.
En STAGING hay15 series ROV sin puesta en servicio y24 productos sin categoría, campo
opcional en esta instalación. Son candidatos de revisión, no errores confirmados ni
motivo para inventar fechas o categorías.
