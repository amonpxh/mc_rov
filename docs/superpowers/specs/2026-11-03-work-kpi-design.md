# KPI de seguimiento: primer incremento

**Estado2026-11-04:** el servicio provisional de etapas está probado en STAGING;
el usuario pidió revisar el catálogo de KPI con funciones nativas, referencias de
gestión y necesidades ROV antes de continuar el tablero. Las fórmulas de este primer
incremento fueron propuestas por Codex y no constituyen un catálogo empresarial
acordado. Véase la revisión de catálogo al final. No se continúa la interfaz en esta revisión.

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
Suplemento20261103-165902-021 confirmó archivos de `ai` y `ai_app` disponibles,
ambos sin instalar, licencia declarada OEEL-1. `ai_auto_install` instalado; no se
leyeron configuraciones, agentes, prompts ni credenciales. Disponibilidad de archivos
no implica proveedor configurado ni autorización para contratar o activar IA.
En STAGING hay15 series ROV sin puesta en servicio y24 productos sin categoría, campo
opcional en esta instalación. Son candidatos de revisión, no errores confirmados ni
motivo para inventar fechas o categorías.

## Revisión del catálogo para fabricación diseño y reparación de ROV

Investigación2026-11-04. Propuesta para decidir con el usuario; no fija metas ni
autoriza cambios de producto adicionales. Se compararon documentación/código oficial
Odoo19, referencias NIST/Lean/ASQ, fuentes de fabricantes ROV y metadatos instalados.

### Qué reutilizar de Odoo

Nativo significa una capacidad documentada o presente en el código oficial de Odoo19;
no garantiza que todos sus menús estén disponibles para cada cuenta de esta instalación.
La auditoría STAGING confirma `mrp`, `mrp_workorder`, `mrp_plm`, `quality_control`,
`purchase` y `purchase_stock` instalados. El modelo Reparación está verificado.
Los módulos concretos de Dashboards y sus vistas no estaban incluidos en esa auditoría.
No se concede un rol de administrador para mostrar indicadores.
En Production Analysis, Yield Percentage compara cantidad producida y demandada;
no es aceptación al primer intento ni tasa de equipos sin defectos [O1].

| Función Odoo19 | Utilidad para Marine Connection | Decisión propuesta |
|---|---|---|
| Production Analysis: unidades producidas, órdenes, demanda, rendimiento, costos y duración de operaciones | Base para producción y costos por familia/modelo; Count es cantidad de MO, no unidades | Reutilizar; filtrar producto final ROV y período de terminación; conciliar series, cantidades y parciales [O1] |
| Repair Orders Analysis: gráfico/pivote y filtros por cliente, producto y estado | Conteos de órdenes y pendientes sin crear otro registro de reparaciones | Reutilizar y adaptar fecha/población. Creación del mes + estado reparado no equivale a reparaciones terminadas ese mes. Menú nativo reservado a Stock Manager [O2] |
| Work Orders y centros: duración real/prevista, carga, pérdidas y OEE | Útil en operaciones y bancos repetibles con tiempo registrado y capacidad definida | Condicional; no convertir número de órdenes distintas en productividad equivalente [O3] |
| Forecast y componentes de fabricación | Prevención de faltantes y decisión de qué puede comenzar | Reutilizar; pronóstico no equivale a stock reservado físicamente ni RFQ a compra confirmada [O4] |
| Purchase and Vendor Analysis | Órdenes, recepciones, cumplimiento y comparación de proveedores | Reutilizar donde exista Dashboards/acceso. Contrastar fecha prometida y recibida para cada métrica; no llamar a todo plazo mostrado lead time realizado [O5] |
| Warehouse Metrics y Operation Analysis | Envejecimiento de stock, transferencias y tiempos logísticos | Reutilizar cuando estén disponibles; material crítico y obsolescencia necesitan clasificación [O6] |
| Conteos y ajustes de inventario | Base para exactitud entre cantidad física y registrada | Adaptar el porcentaje: líneas contadas sin diferencia / líneas contadas, con tolerancia acordada. Cantidad ajustada no es exactitud [O7] |
| PLM ECO y controles/alertas de calidad | Etapas, revisiones, responsables y resultados nativos | Reutilizar los registros. ECO terminados no mide por sí solo calidad de diseño; resultados actuales no prueban primer pase [O8, O9] |
| Maintenance: MTBF, MTTR, próxima falla estimada | Puede ayudar a mantener equipamiento propio del taller | Condicional al objeto correcto. Sus días de solicitudes correctivas no son horas de funcionamiento de ROV de clientes [O10] |

### KPI típicos y elección para el giro

NIST distingue productividad, calidad y mantenimiento y estudia relaciones entre
indicadores; no hay que sumar KPI como si fueran independientes [G1]. Separar tiempo
de proceso, plazo total de recorrido y tiempo que espera el cliente [G2]. ASQ define
primer pase excluyendo retrabajo/repetición, y Pareto permite ordenar frecuencia,
tiempo o costo [G3, G4]. Estas referencias justifican las definiciones, no metas universales.

| Prioridad de negocio | Indicador candidato | Unidad y criterio de medida | Reutilización y dato necesario |
|---|---|---|---|
| Inicial | No conformidades críticas abiertas y antigüedad | Casos abiertos con severidad y decisión de bloqueo | Calidad nativa/catálogo local; acordar severidad, estado y qué impide liberar |
| Inicial | Entregas completas y a tiempo | Compromisos vencidos del período cumplidos con totalidad y requisitos | Operaciones nativas; fijar compromiso original con cliente, cantidades y requisitos; cubrir entregas pendientes vencidas |
| Inicial | Fabricación terminada por semana/mes/año | Cantidades y series únicas de producto final ROV realmente terminado | Production Analysis + salida fabricada; no contar subensambles, creación de serie o MO como unidades |
| Inicial | Reparaciones terminadas por período y cliente | Órdenes/visitas distintas cerradas; series distintas como otra medida | Reporte nativo + fecha de cierre/entrega validada; limitar a ROV; no confundir cliente de la visita con dueño actual |
| Inicial | Entrada frente a salida y pendientes actuales | Órdenes recibidas y terminadas; backlog por estado y antigüedad administrativa | Registros de órdenes; distinguir ingreso del equipo de creación de cotización; explicitar fechas desconocidas |
| Inicial | Bloqueos y tiempo por causa | Órdenes bloqueadas y duración de cada intervalo de espera | Registrar causa/inicio/fin y resolver esperas simultáneas; estado actual no reconstruye días pasados |
| Inicial | Pareto de hallazgos y visitas afectadas | Observaciones registradas y visitas/series afectadas por categoría/componente; Pareto por frecuencia | Catálogo local estructurado; evitar multiplicación por chequeos/revisiones. Incidentes únicos requieren identidad/deduplicación definida |
| Inicial, iniciar captura | Aceptación completa al primer intento | Equipos que aprueban protocolo completo en primera presentación / equipos con primera presentación evaluada | Pruebas nativas/locales + evento inmutable del primer veredicto. Separar fabricación/reparación y observaciones según criterio acordado |
| Inicial | Preparación para iniciar trabajo | Órdenes próximas con materiales, documentación y recursos requeridos disponibles | Forecast/BoM/PLM; definir fecha de corte, faltante y reserva. No basta que el producto tenga stock global |
| Inicial | Expediente de liberación completo por serie | Entregas con identificación, configuración, pruebas y aprobación aplicables / entregas | Evidencia ROV y PDFs emitidos; fijar qué documentos exige cada tipo de trabajo |
| Siguiente | Plazo total y etapas de reparación/fabricación | Mediana, distribución y casos, con límites de inicio/fin acordados | Fechas reales; separar HH, horas de prueba, espera, duración de orden y duración de seguimiento |
| Siguiente | Carga/capacidad por especialidad y programa semanal | Horas comprometidas frente a disponibles; trabajos planificados terminados | Calendarios, competencias y estimaciones; bancos/centros no equivalen automáticamente a personas |
| Siguiente, requiere seguimiento | Retorno por la misma falla | Visitas que vuelven por el mismo modo de falla / cohorte con seguimiento suficiente | Enlace a reparación previa, causa y ventana acordada; evitar comparar recientes sin igual seguimiento |
| Siguiente | Retrabajo, HH reales frente a previstas y costo de mala calidad | Horas/materiales adicionales y desvío de presupuesto | Líneas HH locales + imputación de retrabajo y tarifas históricas; inspeccionar no es necesariamente retrabajar |
| Siguiente | Proveedor, exactitud de inventario y componentes críticos | Cumplimiento de recepciones; líneas contadas; faltantes de artículos críticos | Reportes nativos y definiciones de promesa, tolerancia y criticidad; conteos físicos necesarios |
| Siguiente | Hitos de diseño y cambios tras liberación | Hitos cumplidos, cambios posteriores, motivo e impacto | PLM nativo + baseline/hitos. Separar mejora solicitada, cambio de alcance y corrección de defecto |
| Siguiente | Costo real, desvío y margen por trabajo | Materiales, HH, servicios, devoluciones e ingreso conciliados | Datos de costos/finanzas completos; costo actual de producto no sustituye costo histórico de reparación |
| Condicional | OEE, tiempos de cambio, rendimiento de puesto | Tiempo y capacidad del centro/operación repetible | Útil con Work Orders y captura consistente; no indicador general del negocio heterogéneo |
| Posterior, datos del operador | MTBF por horas, disponibilidad y éxito de misión | Fallas / exposición operacional; tiempo requerido y disponible; misiones y causas | Bitácoras/telemetría/uso del cliente. No inferir estos denominadores de órdenes recibidas |
| No inicial | DPMO, nivel sigma o Cp/Cpk globales | Exigen oportunidades y procesos/especificaciones comparables y datos adecuados | Podrían servir a un proceso repetitivo concreto, no mezclar diseños y reparaciones heterogéneos |

Cliente, modelo, serie, período, familia/componente y tipo de intervención son
dimensiones, no KPI nuevos por cada combinación. Los filtros necesitan atribución
histórica y permisos por origen/empresa. No evaluar personas desde cuentas compartidas.

### Adecuación específica a ROV

La fabricación de robótica marina aporta evidencia a favor de controles de entrada,
proceso y ensayo final por número de serie: Blue Robotics publica ese recorrido [R1].
Su guía de vacío trata ensayos posteriores a ensamblaje o mantenimiento de sellos [R2].
La ficha pública IMCA R006 cubre inspección/reporte/cierre y prueba funcional húmeda
[R3]; no se atribuyen requisitos del documento íntegro restringido. VideoRay recomienda
registros de mantenimiento/reparación y bitácoras operacionales [R4].

De ahí se propone priorizar expediente por serie, aceptación completa, repetición
de fallas y desglose por componente/configuración. No se adopta ningún límite de
presión/voltaje ni obligación de certificación de otra fuente. Un ensayo de vacío
no demuestra por sí solo calificación a profundidad. MTBF/éxito de misión de flota
requieren exposición que el taller puede no recibir; clima, logística y cambio de
alcance deben separarse de avería propia.

### Fuentes y cobertura de nuestros registros

Auditoría existente de STAGING:33 modelos y campos de Reparación, MO, Calidad,
series, ECO y producto. Verifica `repair.order.partner_id`, `lot_id`, `state`,
`fecha_entrega_real` y `mc_total_horas`; MO incluye fechas, cantidades y vínculos
a series/salida/línea de venta. No verifica todavía todos los campos de hallazgos,
chequeos, stock.move.line, workorder/workcenter, ventas e historial de propiedad.
No auditado no significa ausente. Los datos de ensayo no representan desempeño real.

- Reparación: `models/repair_order.py` completa fecha_entrega_real al pasar a done
  si estaba vacía; es fecha editable de entrega, no timestamp inmutable. Importados
  nacidos cerrados pueden carecer de ella. HH son suma de líneas de trabajo manuales.
- Fabricación: `models/mrp_production.py` soporta varias series por orden; conciliar
  cantidades, parciales y subproductos antes de fijar el contador final.
- Hallazgos: `models/mc_rov_revision_linea.py` y `models/mc_rov_hallazgo.py` ofrecen
  categorías, componente, severidad y prueba detectora en fuente local. Varias
  revisiones pueden repetir observaciones de la misma visita; no presumir incidente único.
- Primer pase: `models/mc_rov_revision.py` permite volver a borrador/corregir resultado.
  La primera aprobación real no se demuestra por el resultado final actual ni por
  una alerta por problema abierto. Conservar eventos de primer veredicto desde el arranque.
- Atribución: reparación usa cliente de esa visita; fabricación puede tener vínculo
  comercial o producir para stock sin cliente conocido. Dueño actual no es cliente histórico.

### Criterios antes del tablero

1. Cerrar con el usuario catálogo, prioridad y decisión de cada indicador. Todavía
   no están aprobadas las metas, el orden final ni todas las fórmulas empresariales.
2. Definir orden/visita, unidad serializada y etapa como poblaciones distintas;
   indicar fecha, numerador, denominador, exclusiones y cobertura sin datos.
3. Verificar el reporte nativo y sus permisos en la instalación antes de extenderlo;
   ampliar auditoría solo donde falte información necesaria para el KPI elegido.
4. Registrar desde uso real los eventos que no se pueden reconstruir: compromiso
   original, primer veredicto, bloqueos e identidad de recurrencias.
5. No crear tablero con métricas desconocidas presentadas como cero. Mostrar N,
   tasas y conteos juntos; explicar muestras pequeñas y cortes por modelo/protocolo.
6. Servicio de etapas actual queda como seguimiento interno auxiliar. Su duración
   no es HH ni plazo completo del cliente; sus cierres no son órdenes/ROV terminados.

### Referencias primarias consultadas

- [O1 Producción Odoo19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/manufacturing/reporting/production_analysis.html)
- [O2 Análisis nativo de reparaciones y permisos Odoo19](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/repair/views/repair_views.xml)
- [O3 Centros de trabajo Odoo19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/manufacturing/advanced_configuration/using_work_centers.html)
- [O3b Definición OEE Odoo19](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/inventory_and_mrp/manufacturing/reporting/oee.rst): tiempo productivo/activo del centro; no asumir fórmula ASQ disponibilidad×rendimiento×calidad.
- [O4 Pronóstico Odoo19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/reporting/forecast.html)
- [O5 Compras y proveedores Odoo19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/purchase/advanced/purchase_dashboard.html)
- [O6 Tableros de inventario Odoo19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/reporting/dashboards.html)
- [O7 Conteos Odoo19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/inventory_management/count_products.html)
- [O8 ECO Odoo19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/plm/manage_changes/engineering_change_orders.html)
- [O9 Funciones oficiales de Calidad](https://www.odoo.com/app/quality-features): página de producto actual, no documentación fijada a versión19.
- [O10 Fórmulas de Mantenimiento Odoo19](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/maintenance/models/maintenance.py): solicitudes correctivas completadas; MTTR media de días solicitud/cierre y MTBF derivado de fecha efectiva/última falla/cantidad. No son horas de operación del ROV cliente.
- [G1 NIST sobre jerarquía y relaciones de KPI de producción](https://www.nist.gov/publications/hierarchical-structure-key-performance-indicators-operation-improvement-production)
- [G2 Lean Enterprise Institute sobre tiempos](https://www.lean.org/lexicon-terms/cycle-time/)
- [G3 ASQ sobre primer pase](https://asq.org/quality-resources/quality-glossary/)
- [G4 ASQ sobre Pareto](https://asq.org/quality-resources/pareto)
- [G5 ASQ sobre costo de calidad](https://asq.org/quality-resources/cost-of-quality)
- [R1 Calidad y trazabilidad Blue Robotics](https://bluerobotics.com/quality/)
- [R2 Ensayo de vacío Blue Robotics](https://bluerobotics.com/learn/using-the-vacuum-test-plug/)
- [R3 Ficha pública IMCA R006](https://www.imca-int.com/resources/technical-library/document/aed42e5e-c55b-ee11-8def-6045bdf1ea43/)
- [R4 Manual VideoRay Pro4](https://download.videoray.com/documentation/pro_4/pdf/videoray_doc_pro_4.pdf)

## Contraste con la propuesta externa recibida el 4 de noviembre de 2026

El usuario aportó una propuesta independiente con23 candidatos,11 indicadores de
primer tablero y D1 como panel de cobertura. Se revisó el texto completo y sus
fichas. Sigue siendo una propuesta, no una aprobación de KPI, parámetros ni capturas.
No se suman sus11 a nuestros10; son alternativas sobre poblaciones similares.

### Aportes que conviene conservar

- Separar importancia de negocio de facilidad actual; capturar información antes
  de pretender reportar historia que no existe.
- F1/F2/F3: cartera/antigüedad, intervalos de bloqueo, promesa original y recompromisos.
  Su ficha F3 sí incluye abiertas vencidas; no atribuirle su omisión.
- Q2: cohortes maduras para retorno relacionado, casos por confirmar y retorno por
  cualquier causa como medida diferente. Sí controla seguimiento suficiente.
- F4/F5: visitas, equipos distintos y series por hito separados, sin medir órdenes
  como unidades. Cliente histórico y desconocido separado de cero.
- D1: visibilidad de cobertura; corregir población/denominador según el dato.
- Lista operativa de etapas vencidas aparte del resultado empresarial; OEE global,
  fiabilidad de flota sin exposición y rankings personales siguen fuera del tablero inicial.

### Correcciones y decisiones antes de fusionar fichas

1. **Q1 primer pase:** serie+protocolo no basta para visitas sucesivas. Identidad por
   episodio de aceptación, serie, visita/orden y protocolo/versión. Fallo real que
   obliga a interrumpir el protocolo debe cerrar el primer intento como fallo, aunque
   no se ejecuten todos los ensayos. Distinguir pendiente e inválido por instrumentación
   con motivo autorizado. La expresión primera ejecución completa era ambigua también
   en nuestra propuesta y se precisa para ambas; no se atribuye un conteo errado ya existente.
2. **Q4 hallazgo único:** visita+componente+modo de falla es una agrupación candidata,
   no identidad segura. Puede haber dos componentes físicos iguales o reincidencia
   durante la misma visita. Separar incidente, instancia/posición de componente y
   observaciones que lo documentan. Mientras falte identidad, mostrar observaciones
   registradas y visitas/series afectadas, sin presentar incidentes únicos inventados.
3. **D1 cobertura:** medir por dato/unidad/población elegible, con faltante, inválido
   y no aplicable separados. La causa solo aplica a hallazgos y la recepción física
   del equipo a visitas elegibles. Incluir abiertas para promesas/bloqueos; todas las
   órdenes cerradas no es un denominador universal válido.
4. **F2 detención:** material esperado/atrasado y BoM desactualizada son señales de
   riesgo; no demuestran que ninguna operación pueda avanzar. Registrar detención
   efectiva y sus intervalos. Tiempo total detenido = unión de intervalos; evitar
   sumar dos veces causas simultáneas y fijar reparto/causa principal para el Pareto.
5. **F3 puntualidad:** entregadas en período mide comportamiento de lo que salió;
   compromisos que vencían en período mide cumplimiento del plan, incluyendo lo
   todavía no entregado. Ambas vistas son válidas con nombres/denominadores distintos.
   No usar primera entrega parcial de una venta como cumplimiento completo.
6. **F1 coherencia:** reconciliar primero saldo inicial + entradas − salidas −
   cancelaciones/ajustes = saldo final por unidad/población. No mezclar visitas,
   órdenes y series. Cierre técnico y entrega definen carteras distintas. La ley
   de Little requiere igual límite, unidad y promedios compatibles; no valida
   automáticamente semanas ni usa la mediana recepción–entrega para WIP hasta cierre.
7. **Historia:** cancelaciones, desmontajes y reversos posteriores no borran que una
   fabricación ocurrió. Conservar fecha efectiva y fecha de registro/corrección;
   acordar tratamiento histórico. Snapshots deben cubrir los cortes requeridos,
   no prometer saldo mensual exacto desde fotografías semanales incompletas.
8. **Severidad/Pareto:** estratificar criticidad; no sumar números ordinales de
   severidad como costo sin pesos/interpretación acordados. Mantener vistas por
   frecuencia, horas o costo real y una alerta separada de casos críticos.
9. **A1 proveedor:** tasa nativa por unidades/fecha vigente y tasa propuesta por
   líneas completas/promesa original son métricas distintas. Versionar/nombrar;
   no comparar series antes/después de cambiar fórmula como si fueran homogéneas.
10. Ventanas90 días,13 semanas,12 meses, mínimo10 y tramos de antigüedad fueron
    marcados como propuestas por la otra IA. Siguen sin acordarse; no son valores
    adoptados automáticamente ni estándares obligatorios para MC.

### Aplicación a mc_rov y fuentes nativas

La revisión externa estudió Odoo estándar sin acceder al código local ni a sus
datos. Clasificar sus13 datos como nuevos requeriría antes el siguiente inventario:
existente utilizable / existente con semántica o cobertura pendiente / realmente faltante.

- Reparación: el core crea/valida un movimiento al cerrar [O11], pero eso no demuestra
  fecha física completa para todas nuestras órdenes e importaciones. Ya existe
  fecha_entrega_real editable y autollenada al cerrar (`models/repair_order.py`),
  que no equivale a timestamp de cierre ni retiro efectivo certificado.
- Tipos/HH: ya hay tipos de intervención múltiples, empleado, fecha, horas, acción,
  origen y análisis de causa (`models/repair_order.py`, `models/mc_rov_componente.py`).
  Verificar cobertura y evitar duplicar visitas en tipos que se superponen.
- Ensayos/configuración: ya existen revisiones/pases, motivos y snapshots de
  software/controlador/umbilical al confirmar (`models/mc_rov_revision.py`). Falta
  demostrar conservación del primer veredicto y cobertura completa de configuración.
- FEN ya conserva fecha/responsable, pruebas aprobadas y PDF emitido protegido
  (`models/mc_rov_ficha_equipo_nuevo.py`). Verificar si su emisión es la liberación
  empresarial deseada; no extenderla a reparaciones ni equipararla a despacho.
- La auditoría STAGING sí verifica quality_repair instalado y quality_check_ids en
  repair.order. Queda comprobar configuración de puntos, intentos y cobertura; no
  crear otra integración por asumir que Calidad en Reparación está ausente.
- La fuente local y auditoría soportan varias series por MO (lot_producing_ids).
  La división obligatoria una-MO/una-serie no es un contrato aplicable a todos
  nuestros recorridos. Conciliar parciales/backorders/subproductos/cantidades.

### Resultado de la comparación

Conservar la estructura por flujo/calidad/abastecimiento/ingeniería/capacidad y la
captura anticipada. Mantener no conformidades críticas y preparación de materiales/
documentación visibles, aunque no sean tarjetas del resumen de11. Retornos, retrabajo
y proveedores tienen valor; su puesto en el primer resumen requiere prioridad y
cobertura acordadas. D1 es apoyo, no KPI de productividad del taller.
Se prepara una sola selección consolidada y fichas corregidas antes de programar.
No hay cambio de producto ni autorización inferida de este informe externo.

Referencias contrastadas:
- [O11 Cierre estándar de reparación Odoo19](https://github.com/odoo/odoo/blob/19.0/addons/repair/models/repair.py)
- [Límites de Little y promedios compatibles](https://projectproduction.org/journal/littles-law-a-practical-approach-to-understanding-production-system-performance/)
- La copia aportada enumera fuentes pero perdió sus hipervínculos. IMCA R006 citada
  como rev2.1 ya tiene [rev3 octubre2026 en su ficha pública](https://www.imca-int.com/resources/technical-library/document/aed42e5e-c55b-ee11-8def-6045bdf1ea43/).
  No se verificaron íntegramente las normas de pago ni se deduce obligatoriedad.
