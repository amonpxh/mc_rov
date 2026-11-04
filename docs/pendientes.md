## Programa de preparación del uso real autorizado — 2026-11-03

Usuario autorizó KPI, Compras/abastecimiento, agente IA Odoo/Telegram, datos maestros,
roles/permisos, procedimientos/capacitación, operación técnica, ensayo general y arranque.
Diseño: `docs/superpowers/specs/2026-11-03-preparacion-uso-real-design.md`.
Plan por proyectos: `docs/superpowers/plans/2026-11-03-preparacion-uso-real.md`.
Rama local `feature/preparacion-uso-real`, en el checkout ya aislado; baseline40ce2fe
y notas de cierre5ad4a9a conservadas. Producción no cambia.

Auditoría ejecutada y verificada: `installed-20261103-162622-901.json`,33 modelos,
READ ONLY/rollback,137 fuentes y PID intactos. Compras/purchase_stock instalados;
agentes IA ausentes entre los modelos registrados. Suplemento20261103-165902-021:
`ai` y `ai_app` disponibles pero sin instalar, manifiestos OEEL-1, ningún secreto leído.

Primer incremento KPI: núcleo puro local con16 pruebas GREEN tras RED14 fallos/2 controles,
sin consultas BD desde el núcleo. Plazo original/vigente separados y cobertura explícita;
Reparación no conserva plazo final histórico y no se reconstruye desde chatter.
Diseño: `docs/superpowers/specs/2026-11-03-work-kpi-design.md`.
RED36 confirmado, intento20261103-165902-021:30 fallos esperados y seis controles
nativos verdes, cero errores. STAGING activo; fuentes, datos y pruebas conservados.
Servicio KPI instalado en STAGING, sin nuevas ACL; filtra empresa/documento antes
de consultar historial privado, conserva fuentes archivadas autorizadas y cobertura.
GREEN36/36 verificado20261103-173705-971, cero fallos/errores; respaldo
`/var/tmp/mc-rov-kpi-service-green-QC9PNr`.139 fuentes exactas tras instalación;
pruebas temporales restauradas, datos/configuraciones/stock/historial/PDFs intactos.
La preparación corrigió UTF-8 del manifiesto y auxiliares QA (entorno, ValidationError,
dominio nativo id=0); conservó casos, aserciones y producto. Intentos fallidos y sus
recuperaciones se conservan en `.tmp/preparacion-uso-real-pilot`.

Regresión completa1282/1282 verificada20261104-091932-672,1246 anteriores más36 KPI,
cero fallos/errores y descubrimiento exacto por nombre. Respaldo
`/var/tmp/mc-rov-kpi-regression-gPJAxl`, producto/datos intactos, pruebas restauradas,
STAGING activo. El tablero visual, revisión final e integración siguen pendientes.
Producción6.0 intacta; no activar responsables reales ni reabrir la copia QA cerrada.

**Revisión de alcance2026-11-04:** el usuario señaló que no se había acordado el
catálogo de KPI empresarial y pidió investigar Odoo, métricas típicas y giro ROV antes
de continuar. Investigación terminada y añadida a
`docs/superpowers/specs/2026-11-03-work-kpi-design.md`, sección Revisión del catálogo.
Odoo19 sí trae análisis de reparaciones; necesita fecha/población correcta para
terminadas por período. Reutilizar producción, compras, inventario y PLM donde sirvan;
adaptar cliente/series/hallazgos y capturar primer veredicto/bloqueos para tasas históricas.
MTBF de Mantenimiento Odoo no equivale a fiabilidad de la flota ROV por horas de uso.
Prioridades/fórmulas/metas finales siguen como propuesta, no aprobación del usuario.
No continuar implementación de la interfaz como si ese catálogo ya estuviera acordado.
Propuesta externa recibida y contrastada:23 candidatos,11 iniciales y panel de
cobertura; no se suman a la lista anterior. Revisión guardada al final del diseño.
Conservar cohortes maduras, compromiso original y cobertura; precisar primer intento
por episodio, deduplicación de incidentes, poblaciones de cobertura, bloqueos efectivos
y significado de fechas reales. Auditar datos ya existentes antes de crear13 capturas.
La clasificación/prioridades/fórmulas corregidas siguen pendientes de acuerdo; sin
cambios de producto ni despliegue por la recepción de la propuesta externa.

Consolidación autorizada2026-11-04: catálogo único en
`docs/superpowers/specs/2026-11-04-kpi-catalogo-consolidado.md`,22 familias,
11 fichas iniciales (F1–F6/Q1–Q4/A1), D1 y paneles P-NC/P-PRE/P-ET aparte.
Revisión independiente de conteos, fórmulas y casos aplicada: compromisos únicos,
reapertura/recierre, intentos inválidos, cohortes con dictamen pendiente y reversos.
Definiciones de negocio siguen propuestas; sin metas ni ventanas adoptadas.
F3 acordado2026-11-04: promesa original en Odoo al aceptar el cliente trabajo y
fecha; cambios con motivo/autor y comparación con salida validada del taller.
Sin fecha acordada, sin compromiso definido. Salida registrada no equivale a
recepción en destino, cierre técnico o FEN. Documento/vínculo y roles pendientes.

Auditoría complementaria **ejecutada y revalidada**, intento20261104-115911-124:
34 modelos, READ ONLY/rollback,139 fuentes y PID intactos, STAGING activo;
sin instalar/reiniciar ni tocar copia QA o producción. Recibo coincide exactamente
con JSON guardado. Evidencia workspaceCode `.tmp/preparacion-uso-real-pilot/`
`catalog-source-installed-20261104-115911-124.json`; trabajo remoto
`/var/tmp/mc-rov-kpi-catalog-source-fkOLHT`. Mapa y brechas añadidos al catálogo.
Reutilizar órdenes/series/movimientos, HH/empleado/causas, revisiones/chequeos y
catálogos; no duplicar su captura. Quedan historia de promesa original/primer
veredicto, bloqueos efectivos y relaciones de retorno/retrabajo por especificar.
En esta copia no hay salida interna→cliente done ni compras; conteos incluyen QA
y productos no ROV, sin rendimiento real ni inferencia sobre producción. Campos
editables y métodos delegados no prueban historia inmutable ni cadena nativa completa.
Revisión independiente Q1–Q4 confirma brechas y reutilización; sin cambios de producto.
El usuario aceptó el circuito propuesto de promesa original/cambios/salida; hoy no
se formaliza así. Reutilizar commitment_date donde corresponda, sin crear ventas
ficticias para medir reparación ni equiparar fecha interna a compromiso. Acuerdo
de negocio documentado; circuito aún no implementado. Q2 acordado2026-11-04:
180 días de observación desde salida del taller, independiente de garantía comercial;
interpretación de especificación: días corridos, sin equipararlos a seis meses.
Tasa solo con cohortes que completan180 días y cobertura efectiva; visitas recientes
en seguimiento y retornos conocidos visibles aparte, sin contarlos como cero fallas.
Caso de control:10 visitas maduras/2 afectadas/3 retornos más4 recientes =2/10.
Q1 acordado: cuenta primer pase aprobado con observaciones solo informativas si
cumple todas las pruebas obligatorias y no requiere corrección/reensayo.
Liberación acordada: pruebas obligatorias aprobadas, documentación requerida
completa y ninguna NC bloqueante pendiente; separada de salida física registrada.
F2 acordado: detención real, no solo alerta material; causas repuestos/materiales,
cliente (autorización/información), ingeniería, documentación, personal/equipo de
prueba, servicio externo y Otro con explicación. Unión de intervalos para tiempo
total; propuesta de diseño conserva duración por causa no aditiva, sin reparto
arbitrario de solapes. Calendario del tablero acordado: Santiago, lunes–domingo y
meses/años calendario; plazos laborales mantienen calendario operativo.
No repetir auditoría ni suite1282 sin cambio relevante; sus pruebas no aprueban
automáticamente las once definiciones empresariales ni un tablero nuevo.

Primer incremento empresarial local, aún sin instalar: plan
`docs/superpowers/plans/2026-11-04-business-kpi-quality-foundation.md`, nuevo núcleo
puro `models/business_kpi_metrics.py`, sin import Odoo/__init__, ACL ni vistas.
Reglas de retornos180, primer pase y liberación implementadas;50/50 unitarias
(34 nuevas/16 anteriores), Black99 y pylint10. Revisión independiente corrigió tres
P2 con RED34/9 fallos/0 errores antes de GREEN: fallo real no se vuelve desconocido
por invalidación, retornos sin fecha conservan relación/existencia y cualquier
retorno se cuenta aparte del relacionado. Flags mal tipados rechazados.
Faltan captura durable, adaptadores autorizados, cálculos de flujo/proveedores,
tablero y QA instalado; la suite nativa1282 no se declara reejecutada por este paso.
Configuración real quality.point/mc.rov.chequeo sigue sin consultar; semillas no
son perfiles vigentes. Divergencia continuo/terreno local por verificar antes de
usar el confirmador como protocolo KPI; no corregida ni tratada como norma nueva.
Siguiente consulta preparada, NO ejecutada:
`.tmp/staging-work-kpi-profiles-source.ps1` en workspaceCode. Solo configuración
técnica/IDs de chequeos y quality.point, metadatos de tipos y políticas; sin resultados
de ensayos ni documentos de negocio. READ ONLY/rollback, fuente instalada139 y PID
intactos, sin instalar/reiniciar ni tocar QA/producción. Verificador2 válidos/24 rechazos,
PowerShell real1válido/1hash rechazado y Bash aprobados. No asumir perfiles desde XML
noupdate ni instalar nuevos antes de recibir esta evidencia mediante SSH privado.

Propuesta inicial de KPI: pendientes/vencidos, cumplimiento de plazos, tiempos de
resolución y rechazos/reaperturas. Núcleo y servicio tienen fórmulas especificadas;
rechazos y reaperturas se definirán por flujo en otro incremento, sin contarlos por run;
no inferir personas desde cuentas compartidas ni medir QA como rendimiento real.
Compras/IA requieren planes específicos según las funciones instaladas. Credenciales,
responsables, umbrales y activaciones reales siguen sin fijarse; no suponerlos.
Defontana/SII permanece fuera de este programa.

## Producción instalada: Inventario y cierre real de actividades — 2026-11-03

**19.0.25.6.0 instalada y verificada**, commit `40ce2fe`, [PR #113](https://github.com/amonpxh/mc_rov/pull/113).
CI del PR y de main: 1246 casos exactos, cero fallos y errores; formato aprobado.
STAGING: 94 pruebas de navegador, carreras aisladas 6+4, QA Taller/Supervisor y
calendario en ambos temas y cambios de ancho aprobados. Revisión independiente aprobada.
Copia `mc_rov_inventory_qa_wamR0o` cerrada, con historial conservado y conexiones bloqueadas.

Recibo productivo `INVENTORY_PRODUCTION_DEPLOY=PASSED`; Odoo activo desde
2026-11-03 19:03:58 UTC. Respaldo: `/var/backups/mc-rov-prod-inventory-activities-yu8541`.
Verificados esquema, permisos, protección de cierre manual en los seis flujos y vistas
nativas. Existencias, operaciones, políticas, calendarios, historial y PDFs emitidos
conservados; cero cuentas, actividades, políticas e historial de Inventario nuevos.
Solo se renovó `write_date` de las series 3 y 5, diferencia previamente diagnosticada.
Evidencia local del paquete: `.tmp/prod-inventory-activities` en el workspace Code.

Queda preparar el uso real: definir responsables, calendarios y tipos de operación,
acordar los KPI mínimos y activar las políticas elegidas. La instalación no activó
automatismos reales ni reconstruyó pendientes antiguos. No repetir el instalador.

## Inventario: Task3 guardada; RED315 del filtro en Trabajo asignado preparado — 2026-10-30

Protecciones296nativas guardadas`b76b10a`, hooks aprobados y task-done3 revalidado8b6..b76. Task4BASEb76/brief leído; solo pruebas nuevas en test_work_assignment_process.py:11contratos de opciónInventario/stockacceso/solo picking/títuloindependiente/ninguno/empleado/mío-equipo/empresa/origenrestringido/dominiodinámico/sinProyectos/tiposmanualesypropios, más2controlesnativos. Seis casos anteriores de procesos idénticos porAST.296anteriores+6procesos+2controles+11nuevos=**315total**.

`.tmp/staging-inventory-activity-process-red.ps1`, marcador `picking-process-scope-and-capabilities-red-v1`:solo pruebas temporales/respaldo/restaura/reiniciaSTAGING y protege133fuentes/snapshotcompleto stock/permisos/calendarios/Ingeniería/PDFs. Exige11fallos nuevos concretos (10MissingInventoryProcess y uno exclusión de Sin proceso vinculado),304verdes y0errores/descubrimiento315exacto. Black99/pylint10/hooks/AST/PS/Bash/hashgate real/replaypayload/lector7casos aprobados. **RED315 aún NO ejecutado; mc_rov_work_assignment.py NO modificado**. Antes de productoTask4 faltaRED. Interfazactual carga opciones dinámicamente;63HOOTlocales existentes y3controles nuevos de selección/retorno/sinacceso pendientes de preparar/ejecutar, sin forzar fallos donde UI ya soporte opciones genéricas. Luego Task5suiteintegrada/concurrencia/QA/retiro/revisiónindependientefinal/entrega; producción5.0 y destinatarios reales intactos.

## Inventario: protecciones y auditoría instaladas en STAGING296/296 — 2026-10-30

GREEN intento `20261030-153503-969`:296/296exactos,0fallos/errores;19controles nuevos y253previos incluidos40regresionesIngeniería verdes. Postchecks APIprivada/menú/ACL/no configreal/historialreal/hash133 y snapshotstock/permisos/calendarios/Ingeniería/PDF intactos; pruebasrestauradas/STAGING activo. Respaldo `/var/tmp/mc-rov-inventory-boundaries-green-j4OVOZ`. Recibo/log/nombres/todos hashesProducto+pruebas revalidados con verify-task3-receipt.py. Datosproductivos/activaciónreal sin cambios, producciónIngeniería19.0.25.5.0 main6b.

Task3 completa: guardar y seguir Task4 filtroInventario enTrabajoasignado, manteniendo alcance/empresa/empleado/permisos y sin agregar vínculo aProyecto. Luego Task5 concurrenciaaislada/suitecompleta/QAmanual/retirada/revisiónindependientefinal/PR/CI/entregaautorizada. Todavía no activar destinatariosreales ni scheduler/Compras.

## Inventario: RED296 confirmado; protecciones y auditoría GREEN preparados — 2026-10-30

REDv2 intento `20261030-151650-738`:24fallos nuevos concretos/272verdes/0errores/296exactos;253anteriores y19controles nuevos pasan, incluido cambioempresa ya protegido. Respaldo `/var/tmp/mc-rov-inventory-boundaries-red-BQhUos`, pruebasrestauradas,132fuentes/config/stock/PDFs intactos y STAGING activo. Lectorexacto revalidado contra log deesteintento.

Task3 **local, aún sin instalar**: nuevo inventory_activity_source.py, ampliaciónLifecycle y unimport (3archivos). APIprivada _runs exige lectura/permiso solicitado/empresa delactor antes deconsultahistorialsudo. Picking protegido enempresa/tipo/src/dst conpendiente, cantidades/componentes/reservaspermitidos. Borradosdocumento/ciclo/run explicanhistorial. Mailcallbacks limitados atipospropios y vinculación real, temporalesignorados; hecho/cancelación/archivo/unlink guardanactor/fecha/motivo sin validar stock. Repartovalida destinatarioactivo/interno/empresa/derechos sobre documento en su propio contexto, sinexpandirempresas. Fecha soloasistente con coordinación/motivo/capacidadenmemoria; lógica deautorización ASTidéntica aIngeniería revisada. Conservaplazoactual/original y captura fechafinal aunque mismo writearchive; pausa noimpideauditardecisiones. Actividadesnativas/homónimas quedanindependientes.

`.tmp/staging-inventory-activity-boundaries-green.ps1`, marcador `source-privacy-and-manual-history-green-v1`, **296mismoscasos**: respaldoBD/fuentes y recuperaciónenbasenueva si falla, preservando política y eventosTask2/bloqueandofallida. Postchecks fuentes133/APIprivada/ACL/tipos/0configreal/0historialreal y snapshotcompletoStock/Ingeniería/PDF; restaura pruebas y reiniciaSTAGING. No cambiaACL/vistas/calendarios/recipientes reales ni producción. Black99/pylint10/AST/PS/Bash/hashgate real/replaypayload/lector6casos aprobados. GREEN nativo NO ejecutado, Task3abierta y producto sincommit; después seguirTrabajoasignado/regresiónintegrada/concurrencia/revisiónindependientefinal/QA/entrega.

## Inventario: RED296 v1 diagnosticado; fixture y clasificación corregidos en v2 — 2026-10-30

Intento `20261030-125437-927`:296exactos,24fallosnuevos/1error/271verdes;253anteriores pasan. Errorúnico: al agregar componente, producto copiado llega sinproduct_id al movimiento. Fixture ahora crea otro product.product almacenable con campos nativos explícitos y exige variante persistente; conserva las tres aserciones de negocio (2componentes/mismorun/pendiente) y todos296nombres. Cambioempresa ya estaba protegido en Task2 y pasó; pasa a controlverde obligatorio. Reasignación sin acceso sí falló; pasa a fallo requerido. Puerta sigue24fallos concretos y ahora19controles nuevos verdes, sinerrores/regresiones. Producto132hashes y snapshot idénticos; ningún callback/SourceTask3 implementado. Respaldo `/var/tmp/mc-rov-inventory-boundaries-red-3qRcYS`, pruebas restauradas/STAGING activo, producción intacta.

Paquetes/logs v1 archivados y diagnóstico guardado. ASTsolo1métodofixturemodificado, asercionesfinalesintactas. Verificacioneslocales inicialmente bloqueadas por falta de créditos de revisión automática; reanudadas y aprobadas después del go: Black99/pylint10, AST/PS/Bash/hashgate/replay/lector9casos. **REDv2 nativo pendiente**. Ejecutar `.tmp/staging-inventory-activity-boundaries-red.ps1`, marcador `explicit-component-and-existing-company-control-red-v2`, exigir24FAIL/272PASS/0ERROR/296exactos. No escribir productoTask3 hasta confirmación.

## Inventario: Task2 guardada; RED296 de fronteras preparado — 2026-10-30

Eventos/partiales213nativos guardados en`8b6a282`, hooks aprobados; task-done2 revalida recibo actual y BASEb8..8b6, Task3 iniciada BASE8b6 y brief cotejado con plan. Pruebas nuevas guardadas`4f0bf06`:43fronteras de decisionesmanuales/identidad/privacidad. Incluye hecho/cancelación/archivo/unlink con actor/motivo sin validar stock, captura e herencia de plazo reprogramado, autorización no falsificable con motivo/coordinación, reparto/empleado, protección empresa/tipo/ubicaciones/origenactividad, historialprivado, contextoempresa/restricciones/portal, pausas y temporales. Se permite cantidades/componentes/reservas. Caso combinado reprogramar+archivar usa asistente real y delegado write completo, misma regresión anteriormente encontrada en Ingeniería.

Retiene213casos anteriores+40regresiones de fronteras/revisión final Ingeniería: **296total**. `.tmp/staging-inventory-activity-boundaries-red.ps1`, marcador `source-privacy-and-manual-decisions-red-v1`; solo pruebas temporales/respaldoBD/restauración/reinicioSTAGING. Exige24fallos nuevos concretos y18controlesnuevos verdes,253anteriores todosverdes,0errores y descubrimientoexacto296. El caso restante de asignación a cuenta sin acceso puede revelar una protección nativa ya existente.132fuentes/snapshotcompleto ACL/reglas/stock/calendarios/Ingeniería/PDF intactos. Black99/pylint10/hooks/AST/PS/Bash/hashgate real/replaypayload/lector9casos aprobados. **RED296 nativo NO ejecutado, productoTask3 NO implementado**: inventory_activity_source.py ausente y callbacksInventorymanuales pendientes. No tocar producción/realactivation; una revisión independiente final al terminarTask4/QA.

## Inventario: eventos y parciales instalados en STAGING213/213 — 2026-10-30

GREENv2 intento `20261030-123343-996`:213/213 exactos,0fallos/errores; snapshotcompleto de permisos/stock/config/Ingeniería/PDF intacto, menú/servicios/0configreal/0historialreal/hash132 aprobados, pruebasrestauradas/STAGINGactivo. Respaldo `/var/tmp/mc-rov-inventory-events-green-KKR4p1`. Recibo actual/log/nombres/hasheslocales revalidados. Generación por confirmación nativa, cierre real, reservas sin cierre, parcialesanidados con compromiso heredado y devoluciones en ciclo nuevo aprobados; realactivationoff/noProdchange. Task2 completa; guardar y seguir Task3pruebas de decisionesmanuales/identidad/privacidad con213anteriores, sin implementarantesRED. ProducciónIngeniería19.0.25.5.0 intacta, una revisiónindependientefinal al cerrarInventario.

## Inventario: GREEN213v1 recuperado; firma nativa y prefijos QA corregidos en v2 — 2026-10-30

Intento `20261030-122129-653`:213casos exactos,196verdes/0fallos/17errores.16errores tienen la misma causa: StockMove._action_confirm exige create_proc, usado por _create_backorder, y el observador nuevo lo omitía; el17 es fixture con prefijoQAII compartido por incoming/internal, descubierto al hacer flush nativo. Recuperación comprobada, respaldo `/var/tmp/mc-rov-inventory-events-green-taDOHH`, fallida `odoo_staging_failed_inv_evt_taDOHH` conservada bloqueada, pruebas restauradas/STAGING activo. Producción intacta.

Corrección mínima: solo firma/passthrough InventoryMoveEvents._action_confirm(merge=True,merge_into=False,create_proc=True), reenviando create_proc literal a super; único método de producto cambiado (AST). Fixture solo cambia sequence_code de QAI+primera letra a QAI+code completo para distinguir3tipos, sin tocar aserciones/nombres213. Todos los demás hashes de producto/pruebas iguales av1. Fuente nativa auditada de5overrides coincide exactamente; reproducción localv1 TypeError y regresiónv2 con create_proc=False/True pasa, prefijos únicos3 comprobados. Paquetev1 archivado, builder exige únicamente esa sustitución de fixture respectoREDoriginal. Black99/pylint10/AST/PS/Bash/hashgate/replay/checker6aprobados. **GREEN nativo sigue pendiente**: repetir `.tmp/staging-inventory-activity-events-green.ps1`, marcador `native-confirmation-signature-unique-qa-sequences-green-v2`, mismos213casos. No commitear producto/avanzarTask3 antes deGREEN.

## Inventario: RED213 nativo confirmado; generación/cierre GREEN preparados — 2026-10-30

RED de eventos intento `20261030-115455-377`:32fallos nuevosMissingEvent y181verdes/0errores/213exactos; controles nativos6 y175anteriores pasan. Respaldo `/var/tmp/mc-rov-inventory-events-red-kuOqr7`, pruebas restauradas,130fuentes/stock/config/PDF intactos y STAGING activo. Pruebas guardadas`d861e79`, Task1guardada`b8deb0d`.

Implementación **local, todavía sin instalar** de Task2:2servicios y modelos/__init__ (3archivos), sin cambios a política/calendario/ACL/vistas ni otras fuentes. Hooks de picking create/write/confirm/assign/done/cancel/backorder y move create/write/confirm/assign/done/cancel conservan resultados nativos, capturan estados calculados y documentos resultantes tras merges; consolidan eventos anidados con identidad no falsificable por RPC. Cicloúnico/runúnico, bloqueoSQL ordenado/noop para retries REPEATABLE READ, solo después de derechos sobre picking. Restantes heredan límiteoriginal/vigente del padre desde su backorder_id nativo aunque el enlace de movimientos llegue antes de retornar _create_backorder; devoluciones generan ciclo nuevo. Solo propiasactividades cierran, reserva no valida/cierra; pausa permitecierres. Configincompleta se explica sininventarDev.

`.tmp/staging-inventory-activity-events-green.ps1`, marcador `native-stock-events-partials-green-v1`:213casos mismosnombres/aserciones/payloadtests, respaldoBD/fuentes, recuperación en base nueva preservando política instalada y bloqueando fallida, testsrestore/reinicio. Snapshot completo incluye todasACL/reglas/4tablasInventario, serviciosdeclarados y políticaoff/0historial/cuentas reales;132fuentesesperadas. Black99/pylint10/AST/PS/Bash/hashgate real/replaypayload/lector6casos aprobados. **GREEN213 nativo NO ejecutado**, Task2abierta, no commitear producto hasta resultado. ProducciónIngeniería5.0 y activaciónreal intactas; siguen después fronteras/decisiones/Trabajoasignado/concurrencia/revisiónindependientefinal/QA/entrega.

## Inventario: Task1 guardada; RED213 de eventos preparado — 2026-10-30

Task1 configuración instalada/175nativos aprobados y guardada commit`b8deb0d`, hooks aprobados; ledger task-done1 registra6b..b8, Task2brief extraído BASEb8. Nuevas pruebas de Task2:32contratos de creación/confirmación/reserva/cierre/cancelación/parciales/devoluciones/plazos heredados/pausas/tipos elegidos y6controles de stock nativo. Conserva175anteriores, **213total**. Helpers ejercen quantity/picked nativos, asistentes stock.backorder.confirmation/process y stock.return.picking/action_create_returns, sin estados forzados ni mocks de stock; solo reloj de confirmación fijado y cantidadesQA transaccionales. Fuentes del inventario instalado y APIs oficialesOdoo19 consultadas; controles nativos deben confirmar compatibilidad de la instancia.

`.tmp/staging-inventory-activity-events-red.ps1`, marcador `native-stock-events-and-partial-wizards-red-v1`: solo pruebas temporales, respaldoBD, restaura pruebas/reinicia STAGING, verifica130fuentes/snapshot completo incl4modelosInventario y todosACL/reglas/stock/calendarios/Ingeniería/PDFs. Espera32fallos nuevosMissingEvent/181verdes/0errores/213exactos; no acepta regresiones previas ni errores de fixtures. Formato99/pylint10/hooks/PS/Bash/AST/hashgate real/replaypayload/lector7casos aprobados. **RED213 nativo aún NO ejecutado; generación/cierre NO implementados**. Producción5.0 y destinatarios reales intactos. Siguienteacción ejecutar wrapper en terminalusuario, antes de escribir productoTask2.

## Inventario: configuración instalada en STAGING175/175; siguen eventos nativos — 2026-10-30

GREENv3 intento `20261030-114547-015`:175/175 exactos,0fallos/errores; configuración/stock/PDF/Ingeniería anteriores intactos, menú/ACL/reglas/defaults/historialvacío/hash130 aprobados, tests restaurados y STAGING activo. Respaldo `/var/tmp/mc-rov-inventory-policy-green-VjJKV9`. Recibo revalidado con log actual y hashes locales. Política desactivada/default3laborables y selección explícita por tipo instaladas; ningún destinatario/regla real o pendiente generado. Producción continúa Ingeniería19.0.25.5.0 main6b. Task1completa, sigueTask2 RED de confirmación/cierre/parciales nativos con los175casos previos; todavía no implementar generación antes del RED. Una revisión independiente final al terminar Inventario.

## Inventario:175/175 verdes; verificador de rol corregido, instalación aún recuperada — 2026-10-30

Intento `20261030-113527-741`:175/175 exactos,0fallos/0errores y snapshot de configuraciones intacto. Falló solo postcheck del instalador: seleccionaba primerusuario interno como coordinador y get_view denegó su acceso correctamente. Se corrigió únicamente selector del verificador a miembros reales de Coordinar asignaciones; si no existen, se informa explícitamente, sin conceder grupos ni inventar cuentas. Producto9archivos y todos los módulos de175pruebas conservan hashes de v2. Reproducción local del selector con primerusuario no autorizado/segundo autorizado y ninguno autorizado pasa; paquete/AST/PS/Bash/hashgate/replay/checker pasan. Recuperación nativa comprobada: fallida `odoo_staging_failed_inv_HuBzqT` conservada bloqueada, backup `/var/tmp/mc-rov-inventory-policy-green-HuBzqT`, pruebas restauradas/STAGING activo. **Instalación GREEN completa todavía pendiente**, Task1 abierto. Repetir mismo wrapper con marcador `verified-coordinator-view-postcheck-green-v3`. Producción intacta.

## Inventario: GREEN v1 recuperado; tres expectativas nativas corregidas en v2 — 2026-10-30

Intento `20261030-112942-838`:175 casos exactos,172verdes/0fallos/3errores. Las tres protecciones entre empresas sí rechazaron calendario/empleado/tipo extranjeros mediante `odoo.exceptions.UserError` de `_check_company`; las pruebas esperaban la subclase `ValidationError`. Misma convención nativa ya usada en Aceptación/Calidad. Solo se cambió esa expectativa en tres casos y se añadió import UserError; nombres175 y demás aserciones intactos. Producto9archivos/hashset130 exactamente igual a v1. Recuperación comprobada en log, base fallida `odoo_staging_failed_inv_e2Oywl` conservada bloqueada, respaldo `/var/tmp/mc-rov-inventory-policy-green-e2Oywl`, pruebas restauradas y STAGING activo. Producción intacta. Paquetev1 archivado; builder exige diff textual exacto autorizado para las3pruebas y conserva REDv2original. Black99/pylint10/PS/Bash/AST/hashgate/replay/lector6casos aprobados. Repetir mismo `.tmp/staging-inventory-activity-policy-green.ps1`, marcador `native-company-exception-contracts-green-v2`. **GREEN todavía pendiente**; no avanzar Task2 hasta175/175 y verificaciones nativas.

## Inventario: RED175 confirmado; configuración GREEN preparada — 2026-10-30

- RED nativo v2 intento `20261030-111305-206`: exactamente43 fallos nuevos esperados,132casos verdes y0errores; nombres/multiplicidad validados. Respaldo `/var/tmp/mc-rov-inventory-policy-red-M7Fctt`; pruebas restauradas, fuentes/configuraciones/stock intactos y STAGING activo.
- Rama `feature/inventory-activities`, base main6b08308. Implementación **local, todavía sin instalar**: política por empresa desactivada/default3díaslaborables, reglas por tipo incoming/outgoing/internal explícito, destinatario en contexto propio, calendario compartido existente y límite nativo anterior; historial privado sin ACL pública. Solo configuración/esquema/tipos/vista, sin generación ni cierres todavía. Ingeniería producción5.0 entregada sigue intacta.
- GREEN175 preparado: `.tmp/staging-inventory-activity-policy-green.ps1`. Respalda BD/fuentes, recuperación en base nueva si falla, restaura pruebas/reinicia STAGING. Protege124fuentes previas salvo3integraciones y añade6archivos; valida2ACL/2reglas nuevas exactas, historial/configuración nuevos vacíos, stock/calendarios/Ingeniería/PDFs previos intactos. Conserva versión nominal STAGING2.0, local5.0; no crea cuentas/políticas reales ni toca producción.
- Formato99/pylint10, XML/AST/PS/Bash, hashgate real PowerShell, replay de payload y6casos positivos/negativos del lector exacto aprobados. **GREEN nativo no ejecutado**. Task1 queda abierto hasta175/175 y verificación nativa; no solicitar nuevo go ni revisión parcial. Luego eventos/generación/cierre y revisión independiente final de Inventario.

## Ingeniería: validación cerrada; entrega19.0.25.5.0 preparada en rama — 2026-10-29

- Implementación y tres hallazgos de revisión corregidos (commit `67622aa`): **979/979** nativos, seis carreras simultáneas y QA práctico de Supervisor/Taller aprobados. Evidencia en [validación de Ingeniería](qa/2026-10-29-engineering-activities.md); logs completos en `.tmp/engineering-activity-pilot/`.
- Copia QA1PdSGX cerrada: servidor detenido, historial respaldado y conexiones bloqueadas. STAGING activo; producción sigue **19.0.25.4.1**, sin Ingeniería ni activación de cuentas reales.
- Versión local **19.0.25.5.0**. `origin/main` consultado, permanece en `d6f5efe`; el cambio de versión es solo metadato. Rama `feature/design-inventory-activities`, entrega funcional solo Ingeniería. Automatismos de Inventario siguen en plan separado.
- Pendientes: decisión de integración, publicación/PR/CI, merge autorizado y despliegue con respaldo. Cuentas, roles y zona horaria reales se configuran después. Plan Task4 permanece abierto hasta cerrar las puertas de entrega.

## Ingeniería: suite974 y seis carreras nativas aprobadas, 2026-10-29

- Evidencia automatizada actual revalidada: **974/974 exactos**, cero fallos/errores; seis carreras de concurrencia completas con dos PIDs por caso, cero huérfanas incluidas actividades inactivas, aniversario conservado y actividades nativas de aprobación intactas. Prueba de permiso nativo sin/con escritura de producto aprobada dentro de la copia.
- Concurrencia v3 intento20261029-103154-118: copia `mc_rov_engineering_ci_On5wwK` y respaldo `/var/tmp/mc-rov-engineering-concurrency-On5wwK` conservados; conexiones bloqueadas, fuentesSTAGING intactas y servicio activo. El enlace histórico corregido está validado por974 y por la carrera que encontró el defecto.
- Cierre de implementación automatizada: guardar corrección, dos regresiones y probador; revisión independiente del conjunto antes de QA operativa. Todavía faltan escenario manual/retirada y entrega PR/CI/release con autorizaciones correspondientes. No activar automatismos ni cuentas reales; producción19.0.25.4.1 intacta.

## Ingeniería: aprobaciones concurrentes verdes; fixture de aplicación corregido en v3, 2026-10-29

- Intento nativo v2 `20261029-100621-756`: creación, entrega repetida y **aprobaciones concurrentes pasan**, con un pendiente de aplicación, dos actividades enlazadas, cero huérfanas (incluidas inactivas), aniversario y actividades nativas preservados. El defecto del enlace quedó cubierto en la carrera que lo encontró. No se completaron las seis carreras: aplicación se detuvo por AccessError nativo al escribir product.template.version.
- Diagnóstico: las dos cuentas QA de la copia tenían PLM pero no `product.group_product_manager` (Productos/Crear), permiso exigido por action_apply nativo. ACL/XMLID confirmados contra auditoría instalada; no corresponde elevar permisos desde la automatización. Copia `mc_rov_engineering_ci_0vvDqx` conservada y bloqueada; STAGING activo y fuentes intactas. v2wire/prepared/log/diagnóstico preservados.
- Preparado `.tmp/staging-engineering-activity-concurrency.ps1`, marcador **isolated-six-native-events-native-product-rights-v3**. Único ajuste del probador: antes de aplicar y solo en la copia, cada actor debe tener acceso a ECO pero carecer de escritura de producto; exige AccessError nativo y que ECO/versión/historial no cambien. Después habilita el grupo nativo a esas dos cuentas ficticias, comprueba escritura y ejecuta la misma carrera con ambos actores, sin sudo en los eventos.
- Comparación AST prueba que carreras y aserciones originales permanecen iguales al retirar ese helper/import/llamada. El lector también conserva sus comprobaciones previas y añade el marcador obligatorio de permisos verificados. Black99/pylint10/PS/Bash/Python embebido/pins y lector de9casos sintéticos aprobados. **v3 nativo NO ejecutado**.
- Repetir solo concurrencia v3; no hace falta repetir974 porque producto y suite no han cambiado. Los permisos de STAGING y producción no se modifican; el ajuste está limitado a las cuentas de la copia neutralizada.
- Preparación real pendiente: quien aplique ECO de producto necesitará el permiso nativo Productos/Crear además de PLM; decidir esa cuenta/rol en la preparación operativa, no concedido ahora. Task4 sigue en curso, sin release; tras seis carreras verdes quedan revisión independiente y QA operativa.

## Ingeniería: corrección validada con974; concurrencia v2 preparada, 2026-10-29

- Recibo nativo del intento `20261029-095319-181` revalidado por cada nombre: **974/974 exactos**, cero fallos/errores. Incluye los972anteriores y las dos regresiones de enlaces archivados. Fuente instalada de lifecycle coincide con el archivo local corregido. Configuraciones/stock/calendarios/aprobaciones/PDF intactos, cero política/historial real nuevo, pruebas restauradas y STAGING activo. Respaldo `/var/tmp/mc-rov-engineering-history-fix-green-06SLOh`.
- Preparado de nuevo `.tmp/staging-engineering-activity-concurrency.ps1`, marcador **isolated-six-native-events-after-history-fix-v2**. Ahora exige el recibo974 de la corrección y los124hashes instalados actualizados; solo cambia el hash de lifecycle respecto de v1.
- Comparación literal de los paquetes v1/v2 tras extraer el mapa de hashes: todo el probador, sus seis carreras y aserciones son exactamente iguales. El hash del probador también coincide. No se relajó la comprobación de cero huérfanas ni se excluyeron actividades inactivas. Copia anterior pDJ91Z permanece bloqueada y conservada; v2 creará otra copia neutralizada.
- PS/Bash/Python embebido/pins y fuenteprobadoridéntica verificados localmente. **Concurrencia v2 NO ejecutada**. Repetir el comando de concurrencia y revisar el log nuevo, sin usar v1 como resultado. No repetir974sinotroscambios.
- La corrección funcional está validada en STAGING pero aún sin commit separado, a la espera de confirmar la carrera que encontró el defecto. Task4 sigue incompleto: concurrencia, revisión independiente y QA operativa/retirada del escenario antes de release. Producción19.0.25.4.1 y automatismos reales intactos.

## Ingeniería: defecto de historial detectado en concurrencia; corrección y GREEN974 listos, 2026-10-29

- Concurrencia del intento20261029-094046-795: creación y entrega repetida pasan; se detiene tras aprobaciones en `AssertionError: Orphan engineering activity: approvals`. No se completaron las seis carreras. Copia `mc_rov_engineering_ci_pDJ91Z` bloqueada y conservada, trabajo `/var/tmp/mc-rov-engineering-concurrency-pDJ91Z`; fuentesSTAGING intactas y servicio activo. No es un fallo de fixture ni un duplicado aceptado.
- Causa real: `_finish` completaba la actividad nativamente y después vaciaba `run.activity_id`. Odoo conserva esa actividad archivada; quedaba sin enlace a su historial. Corrección LOCAL mínima: retirar solo esa limpieza explícita. Se conserva el vínculo cuando se archiva; si Odoo borra de verdad, el campo ya tiene `ondelete=set null`. Comparación AST contra el payload instalado prueba que el único cambio ejecutable es retirar esa llamada.
- Añadidas dos regresiones nativas de enlace en cierre de preparación y aplicación; la comprobación de cero huérfanas incluye actividades inactivas. El probador de seis carreras y sus aserciones permanecen iguales. RED observado es el fallo nativo de concurrencia, no se afirma que las dos unitarias nuevas hayan sido ejecutadas en RED.
- Preparado `.tmp/staging-engineering-activity-history-fix.ps1`, marcador **preserve-archived-links-full974-v1**. Instala **un archivo de producto** y ejecuta toda la suite **974** (972 anteriores más dos regresiones). Respalda BD/archivos, restaura pruebas; si falla recupera BD en base nueva y conserva la fallida bloqueada. No activa destinatarios, no crea QA persistente y no toca producción.
- Black99/pylint10/ASTdiff/PS/Bash/Python embebido, instalación del payload en carpeta temporal con comparación byte por byte y lector de5casos sintéticos aprobados localmente. **GREEN974 NO ejecutado**. Ejecutar el nuevo comando antes de repetir concurrencia; no reusar su paquete anterior con fuente972 tras instalar la corrección.
- Suite972 fue verde antes de este cambio y sigue como evidencia histórica. Ahora falta validar974 y reconstruir paquete de concurrencia con su nuevo recibo/hash. Task4 sigue incompleto; sin commit de corrección ni release. Producción19.0.25.4.1, cuentas y automatismos reales intactos.

## Ingeniería: suite972 aprobada; concurrencia aislada preparada, 2026-10-29

- Suite nativa completa del intento `20261029-091946-975` releída y revalidada por Counter: **972/972 exactos**, cero fallos/errores. Conserva 870 casos anteriores y 102 nuevos de Ingeniería. Producto124archivos y configuraciones/stock/calendarios/aprobaciones/PDF intactos, pruebas restauradas y STAGING activo. Respaldo `/var/tmp/mc-rov-engineering-regression-2x4P0M`.
- Preparado `.tmp/staging-engineering-activity-concurrency.ps1`, marcador **isolated-six-native-events-strict-v1**, y probador local `scripts/qa/engineering_activity_concurrency.py`. Seis carreras: creación nativa de dos ECO, entrega inicial repetida sobre el mismo ECO, dos aprobadores distintos sobre dos plantillas obligatorias distintas, aplicación simultánea, archivo y desarchivo simultáneos. Usuarios PLM reales solo en la copia, empresas acotadas y distintas zonas de usuario; valida aniversario de política Santiago y bisiesto.
- La copia se crea CONNECTION LIMIT0, se restauran datos y se neutralizan cron/correo/baseURL antes de habilitar conexiones al probador; se bloquea y desconecta al terminar. No instala/reinicia ni crea QA en STAGING o producción. Conserva dump y copia. Verifica los124hashes antes/después contra el recibo972; exige servicioSTAGINGactivo y bloqueo final de copia confirmado.
- Cada carrera exige dos PIDs distintos, reintento completo solo en SerializationFailure/DeadlockDetected, identidad única, cantidades exactas, plazos preservados y cero actividades propias huérfanas, incluyendo inactivas. Compara IDs/usuarios/vencimientos/active de las actividades nativas de aprobación antes/después de aprobar/aplicar; no las cierra nuestro servicio. Falla en cualquier excepción o fase faltante.
- Black99/pylint10/AST/PS/Bash/Python embebido/hashes y lector de8casos sintéticos aprobados localmente. **Concurrencia nativa NO ejecutada**. Ejecutar nuevo comando y revisar log actual. No repetir la suite972 sin cambios funcionales nuevos o un fallo que lo justifique.
- Task4 sigue en curso: concurrencia, revisión independiente y QA operativa/retirada de escenario antes de preparar PR/release. No cambiar versión ni activar cuentas reales todavía. Producción19.0.25.4.1 intacta; Inventario sigue luego según el plan.

## Ingeniería: Task3 cerrado; suite integrada972 preparada, 2026-10-29

- GREEN198 nativo confirmado y releído: **198/198 exactos**, cero fallos/errores, fuentes locales coinciden con instaladas. Configuraciones/stock/calendarios/aprobaciones/PDF intactos, sin configuración o historial real nuevo, pruebas restauradas y STAGING activo. Respaldo `/var/tmp/mc-rov-engineering-boundaries-green-Bx1vk2`.
- Commit `be19075` guarda identidad/historial y decisiones manuales; hooks del repositorio aprobados. Task3 completado con task-done revalidando recibo nativo y hashes actuales. Task4 en curso, BASEbe19075721ab84ca5ea807abfcfbbe387d6c8edb.
- Preparado `.tmp/staging-engineering-activity-regression.ps1`, marcador **full972-exact-installed-product-v1**. Descubrimiento local: **972 casos únicos**, mantiene cada uno de los 870 anteriores y añade 102 de Ingeniería (32 política/nativos,35 eventos/nativos,35 fronteras). Sin casos heredados omitidos o duplicados.
- Paquete fija 124 archivos instalados mediante base completa auditada de Inventario, auditoría de Ingeniería y recibos GREEN sucesivos. Verifica los 49 aliases de formato aún necesarios contra evidencia con hash, sin admitir cambios semánticos. Conserva versión nominal STAGING19.0.25.2.0; versión local4.1 no implica despliegue nuevo.
- Solo instala temporalmente toda la suite de pruebas, respalda BD, exige nombres/resultados exactos y restaura todos sus archivos; verifica producto y snapshot completos, reinicia solo STAGING. No instala lógica nueva, no configura destinatarios reales, no toca producción. PS/Bash/Python embebido, hashes/payload/inventario de restauración y lector con 5 casos sintéticos aprobados localmente.
- **Suite972 nativa NO ejecutada**. Ejecutar nuevo comando por SSH manual y revisar su salida/log actuales. Después siguen concurrencia aislada, revisión independiente y QA con escenario temporal antes de PR/release. No repetir GREEN198 ya cerrado. Ingeniería todavía no está lista para producción; Inventario sigue en el plan posterior.

## Ingeniería: protecciones GREEN198 confirmado, 2026-10-29

- Recibo nativo del intento20261029-091003-629 verificado: **198/198 nombres exactos, cero fallos y errores**, código instalado idéntico a los tres archivos locales preparados. Configuraciones/stock/calendarios/aprobaciones/PDF intactos, cero configuración/historial real creado, pruebas restauradas y STAGING activo.
- Respaldo `/var/tmp/mc-rov-engineering-boundaries-green-Bx1vk2`. Task3 funcional validado; decisiones manuales conservan resultado/autor/plazo sin aprobar ECO; referencias e historial privados protegidos. Falta validación integrada, concurrencia, revisión independiente y QA; no declarar Ingeniería lista para producción todavía.
- Task4 comienza con suite completa exacta y carreras aisladas. Sin cambios productivos ni destinatarios/calendarios/cron reales.

## Ingeniería: RED198 confirmado; protecciones GREEN198 preparadas, 2026-10-29

- Recibo RED v2 del intento `20261028-131846-337` releído: **19 fallos nuevos esperados, 179 pasan, 198 nombres exactos y cero errores**. Pruebas restauradas, producto/configuración intactos, STAGING activo. Respaldo `/var/tmp/mc-rov-engineering-boundaries-red-b52Xgm`. El error de exportación del v1 quedó resuelto sin cambiar producto ni debilitar contratos.
- Implementación LOCAL de Task3: servicio privado `_runs` exige acceso al ECO antes de leer historial; protege empresa/producto/BoM/tipo; permite editar la revisión nueva. Historial de ciclo/run no se borra por ORM y el borrado del ECO explica cómo conservarlo. Decisiones de actividad hechas/canceladas/archivadas registran actor, fecha, motivo y plazo sin aprobar/aplicar ECO. Reprogramación mantiene fecha original y conserva la actual para la siguiente etapa aunque la actividad se retire. Protege origen/tipo de actividad; ignora NewId sin tocar el origen persistente.
- Preparado `.tmp/staging-engineering-activity-boundaries-green.ps1`, marcador **source-privacy-manual-history-green-v1**. Instala tres archivos: models init, lifecycle y source; **mismos 198 contratos del RED**. Exige base/políticas/historial reales sin cambios; conserva aprobaciones nativas, stock/calendarios/PDF y permisos. No configura cuentas ni activa automatismos reales, no toca producción.
- Recuperación si falla: archivos originales y BD restaurada en base nueva, comparación exacta del snapshot y failedDB bloqueada conservada. Verifica volver a los servicios de eventos de Task2 sin el servicio source de Task3. En éxito restaura solo pruebas y conserva producto.
- Black99/pylint10/diffcheck, PS/Bash/Python embebido, hashes/payload/198 nombres y lector de resultados (5 casos sintéticos) aprobados localmente. **GREEN198 nativo NO ejecutado**; Task3 no está completo ni se ha hecho commit funcional. Ejecutar el nuevo comando por SSH manual y revisar su log actual antes de avanzar a integración/concurrencia/revisión/QA.
- Producción19.0.25.4.1 y destinatarios reales intactos. Ingeniería sigue antes de Inventario según planes aprobados.

## Ingeniería: RED198 detenido por fixture de exportación; v2 listo, 2026-10-28

- Intento nativo `20261028-131156-618`: **19 fallos nuevos esperados y 1 error de prueba entre 198 casos exactos**. Los 163 contratos anteriores pasan y no hay casos omitidos/duplicados. RED no confirmado; no implementar Task3 aún.
- Error único: la prueba de exportación esperaba AccessError del modelo privado, pero la cuenta QA no tenía `base.group_allow_export`; Odoo lanzó UserError antes de llegar a esa ACL. Corregida la preparación de esa cuenta solo dentro de su prueba transaccional. Se conservan las dos comprobaciones de AccessError, sin abrir permisos reales ni tocar producto.
- Fuentes/configuración/stock/PDF intactos, pruebas restauradas, STAGING activo. Respaldo `/var/tmp/mc-rov-engineering-boundaries-red-yciika`. Evidencia y paquete v1 conservados en `.tmp/engineering-activity-pilot/`; diagnóstico actual en `boundaries-red-v1-diagnose.json`.
- Repreparado `.tmp/staging-engineering-activity-boundaries-red.ps1`, marcador **export-enabled-account-red-v2**. Mismos 35 nuevos + 163 previos = 198. Diferencia de payload comprobada: solo dos líneas en la prueba de exportación; baseline de producto y todas las demás pruebas iguales. Lint10/Black99/PS/Bash/Python embebido y hashes aprobados.
- Pendiente repetir ese RED y revisar el log del nuevo intento. V2 no ejecutado. Task2 sigue cerrado en bc45036/GREEN163; Task3 no tiene implementación funcional nueva. Producción y automatismos reales intactos.

## Ingeniería: eventos GREEN163 cerrado; fronteras RED198 preparado, 2026-10-28

- GREEN nativo de generación/cierre/reapertura confirmado y releído: **163/163 exactos**, cero fallos/errores. Configuraciones/stock/calendarios/aprobaciones/PDF intactos, menú y fuentes verificadas, cero políticas/historiales reales nuevos, pruebas restauradas y STAGING activo. Respaldo `/var/tmp/mc-rov-engineering-events-green-b1A6oV`.
- Task2 guardado en `bc45036` y marcado completo con recibo nativo. Única diferencia local respecto del archivo instalado: pragma de lint compatible con entornos sin plugin; AST idéntico comprobado contra payload original con hash verificado. Sin cambios funcionales después del GREEN.
- Task3: 35 pruebas nuevas de decisiones manuales, reprogramación/reparto, protección de producto/BoM/tipo/empresa, historial privado, destinatarios y registros temporales. Conserva los 163 anteriores: **198 total**. No se ha implementado source ni callbacks manuales de Ingeniería todavía.
- Preparado `.tmp/staging-engineering-activity-boundaries-red.ps1`: solo pruebas temporales, respaldo de BD, producto y snapshot exactos, restauración de pruebas y reinicio STAGING. Deben fallar al menos 12 contratos nuevos concretos; nueve controles nuevos y todos los anteriores deben pasar. Cero errores y ningún caso omitido o duplicado. Se informa cada fallo real nuevo; otros contratos pueden estar cubiertos ya por controles compartidos.
- Black99/pylint10/PS/Bash/Python embebido y lector con 5 casos sintéticos comprobados localmente. **RED198 NO ejecutado todavía**; esperar la salida y su log actuales antes de implementar Task3. No repetir events-green ni policy-green.
- Ingeniería todavía no está lista para producción: faltan Task3, regresión/concurrencia/revisión independiente y QA. Producción19.0.25.4.1, cuentas/calendarios/destinatarios/cron reales intactos. Inventario sigue después según el plan aprobado.

## Ingeniería: eventos RED confirmado; GREEN163 preparado, 2026-10-28

- RED nativo de eventos confirmado: 32 fallos esperados por automatización ausente, 3 controles nativos y 128 contratos anteriores pasan; 163 nombres exactos y cero errores. Respaldo `/var/tmp/mc-rov-engineering-events-red-SSZeR0`; pruebas restauradas, producto/configuración intactos, STAGING activo.
- Implementación LOCAL de generación, cierre y reapertura de ECO: un aniversario desde su creación, preparación/aplicación por estados y aprobaciones reales, archivo/retroceso con identidad conservada. Solo cierra actividades propias; aprobaciones nativas intactas. Hooks anidados y feedback se consolidan como un evento.
- Preparado `.tmp/staging-engineering-activity-events-green.ps1`: 163 contratos, 3 archivos de producto, mismos tests del RED, hashes exactos antes/después y snapshot con ACL completas, stock/calendarios/aprobadores/PDF protegidos. Exige cero políticas/historiales reales antes de instalar. Si falla, restaura código y BD en base nueva y conserva la fallida bloqueada; vuelve a la política ya validada de Task1.
- Black99/pylint10/diffcheck, sintaxis PS/Bash/Python embebido, hashes/payload y lector de resultados (5 casos sintéticos) aprobados. Esto NO confirma GREEN nativo. Pendiente ejecutar el nuevo comando en terminal y leer su salida/log actuales; no repetir RED ni policy-green.
- Task2 sigue en curso, sin commit funcional ni publicación/despliegue. Task1 está completo en 1d82538. Task3 (decisiones manuales y fronteras), revisión integral, concurrencia y QA siguen después. Inventario va en el plan posterior. Producción19.0.25.4.1 y destinatarios reales sin cambios.

## Centro de trabajo: icono Diseño/BoM diferenciado, 2026-10-27

- Corrección visual 19.0.25.4.1: Diseño/BoM usa `fa-sitemap`; Inventario conserva `fa-cubes`. Solo cambia el icono, sin tocar permisos, navegación ni datos.
- STAGING instalado con comprobación del único literal y hashes antes/después, respaldo `/var/tmp/mc-rov-center-design-icon-qhaVk2`, servicio activo y hash JS productivo intacto. Usuario confirmó visualmente «todo ok».
- Producción 19.0.25.4.0/main3588 está instalada y verificada; el icono nuevo todavía no está publicado ni desplegado. Preparar PR y CI de esta corrección antes de integrarla.

## Inventario: STAGING837 y navegador39 aprobados; entrega local19.0.25.3.0, 2026-10-27

- Cierre nativo completado: pruebas HOOT temporales restauradas; suite backend **837/837 exactos**, cero fallos/errores. Auditoría independiente de nombres del log contra payload837 aprobada. Los mensajes SQL duplicate-key pertenecen a seis pruebas negativas de unicidad; no son fallos de suite. Producto/configuraciones/stock y snapshot intactos, pruebas Python restauradas, STAGING activo. Respaldo `/var/tmp/mc-rov-center-inventory-regression-t9UBvQ`.
- Navegador39/39, permisos backend30/30, apertura/retorno nativos, menú claro/oscuro y panelestrecho verificados. Tema claro original restituido. Revisión independiente sin bloqueantes; geometría2/4/8 comprobada en HOOT. Mejora visual de contraste seleccionado en oscuro es preexistente y no bloquea este cambio; comprobación amplia/foco manual opcional no se afirma como realizada.
- Release LOCAL preparada **19.0.25.3.0**. STAGING probado permanece19.0.25.2.0 con implementación instalada. Tras837 solo se subió versión del manifiesto y aplicó Black99 al backend; AST idéntico al código probado, verificación explícita guardada en `release-validation.json`. Black99/pylint10/diffcheck aprobados. CI del commit final todavía pendiente.
- Rama `feature/work-center-inventory`, base `f5fd59f`, PR aún no publicado. Preparar commit local y descripción revisable; publicación de esta rama necesita autorización específica. No asumir autorización anterior de PR108 ni del issue QA rechazado. Merge/producción requieren decisión posterior. No repetir los instaladores ya completados.

## Inventario: navegador39 aprobado; cierre y regresión837 preparados, 2026-10-27

- Instalación de interfaz confirmada, respaldo `/var/tmp/mc-rov-center-inventory-ui-60KSmV`, snapshot y resto del producto intactos, STAGING activo. Log bundle39 leído. Navegador real suite @mc_rov: **39/39 aprobados**; geometría320/480/1000/1600 y panelestrecho incluida. `browser-green-result.json` y recibo `ui-install.json` actualizados solo tras observar el resultado.
- QA real: desde Trabajo asignado se abrió Inventario → Ubicaciones, con filtro nativo Ubicaciones Internas, columnas stock/ubicación/serie; regreso por breadcrumb conserva el Centro. Capturas inspeccionadas en claro4columnas y claro/oscuro2columnas. Tema claro original restaurado y confirmado visualmente. No se editaron existencias ni actividades. El API de viewport perdió las pestañas; se recuperó abriendo pestaña nueva, sin afirmar comprobación visual amplia que no se realizó.
- Revisión independiente de código terminada: cero hallazgos bloqueantes; permisos/empresas, estado y grid correctos. Nota no bloqueante preexistente: texto de botón seleccionado usa color de marca con contraste débil en oscuro. Pendiente opcional comprobación visual8columnas/foco; geometry8 ya pasó HOOT.
- Siguiente `.tmp/staging-center-inventory-final-check.ps1`: retira dos archivos HOOT temporales aprobados y ejecuta toda la suite **837** (828base+9Inventario), exacta por nombres. SSH en cada paso. Fuente instalada se exige idéntica al backend/UI validados; 53 aliases de formato heredados se verifican contra evidencia previa, cuatro archivos nuevos usan recibos exactos. Snapshot ampliado incluye quants/calendarios/políticas/PDFs; respaldo y restauración de pruebas. PS/Bash expandido, Python embebido, payload/restoreinventory y837nombres comprobados localmente. **NO ejecutado todavía**.
- No repetir instaladores antiguos ni GREEN actuales. Versión STAGING continúa19.0.25.2.0; nueva release/CI/PR/merge/despliegue pendientes. Producción sin cambios.

## Inventario: RED navegador confirmado; interfaz GREEN preparada, 2026-10-27

- Túnel recuperado. Navegador IAB con suite @mc_rov seleccionada explícitamente: **32 pasan / 7 fallan**, total39. Se expandieron los siete fallos: etiquetas/entrada ausentes y seis «Falta el botón Inventario autorizado». Ningún fallo previo. Evidencia `.tmp/work-center-inventory-pilot/browser-red-result.json`; URL real `http://localhost:8070/web/tests?id=f92f0bf0`. No usar parámetro filter como prueba de selección: al principio ejecutó suite global y se detuvo; ese resultado se excluye.
- Implementación LOCAL de tres archivos de interfaz: Inventario con capacidad explícita, acción nativa conservando filtros/área, guard de edición y doble apertura, aviso de fallo visible también desde Trabajo asignado; etiquetas cortas y grid por contenedor2/4/8. Títulos de área conservados, sin ACL nuevas ni producto en producción.
- Preparado `.tmp/staging-center-inventory-ui-green.ps1`: exige hashes previos de los tres archivos + backend GREEN y pruebas temporales conocidas, respalda BD/código, instala solo JS/XML/SCSS, verifica bundle39 y snapshot de datos, restaura archivos si falla y reinicia STAGING. PS/Bash expandido/JS/XML/Python/payloads/diffcheck aprobados. **NO ejecutado**: falta SSH del usuario; luego recargar navegador y exigir39/39 + temas/responsive/retorno real.
- Conservar pruebas temporales hasta comprobar GREEN; restaurador `.tmp/staging-center-inventory-browser-restore.ps1`. No repetir RED/backendGREEN ya completados. PR/merge/producción pendientes posteriores.

## Inventario: GREEN de acceso aprobado; RED de navegador preparado, 2026-10-27

- Evidencia nativa revisada: 30/30, cero fallos/errores, sin ERROR/CRITICAL. Permisos de Inventario, llamada sin acceso técnico de Administrador y empresas autorizadas validados. Respaldo `/var/tmp/mc-rov-center-inventory-green-nVkZo8`; pruebas restauradas, resto del producto/datos intactos, STAGING activo.
- Backend instalado en STAGING; interfaz todavía sin modificar. Rama `feature/work-center-inventory`, base main `f5fd59f`, producción sin cambios. No repetir instaladores antiguos de aceptación ni el GREEN ya aplicado.
- Ocho pruebas HOOT nuevas preparadas: orden/etiquetas, ocultación sin permiso, acción nativa/filtros, protección de edición, errores RPC y carga de vista, doble apertura y distribución real 2/4/8 por ancho de contenedor. Base 31 + nuevas 8 = 39. RED esperado: siete nuevas fallan, una nueva y 31 anteriores pasan. **Todavía no ejecutadas**.
- Siguiente comando `.tmp/staging-center-inventory-browser-red.ps1`: solo carga pruebas temporales, respalda BD/archivos y verifica bundle/producto/datos. Después ejecutar filtro mc_rov en navegador y revisar fallos exactos antes de implementar interfaz. Restaurador preparado `.tmp/staging-center-inventory-browser-restore.ps1`, con guard de archivos QA conocidos y del producto vigente. PS/Bash expandido, Python embebido, JS y payloads39 validados localmente.
- Incidencia QA del instalador antiguo sigue en borrador: publicación rechazada por revisión automática, sin autorización posterior. No reintentar ni crear issue sin ella.

## Fabricación automática — QA manual verificada, 2026-10-16

- Usuario confirma generación, reparto solo de empleado y cierre de la normal WH/MO/00779. En la parcial WH/MO/00780, la parte001 quedó hecha y solo002 conserva el pendiente y el vencimiento reprogramado (2026-10-17). Cancelar00781 retiró su pendiente.
- Pausa general verificada: confirmar00782 con control apagado no generó actividad;00780-002 siguió pendiente. Reactivar y editar00782 tampoco creó actividad retroactiva.
- Escenario STAGING registrado: cuentas2081/2082, empleados1212/1213, producto2498, series13244..13247, órdenes854..857 y parcial derivada, política554, calendarioQA2255, control171. Creación respaldada en `/var/tmp/mc-rov-manufacturing-operational-qa-b31ACW`.
- **Retiro QA confirmado:** `.tmp/staging-manufacturing-activity-qa-close.ps1`. Respalda BD y valida propiedad; cancela solo órdenesQA pendientes y archiva cuentas/empleados/producto. Conserva órdenes, series dadas de baja, calendario e historial; deja política sin destinatario y control en su conducta previa conservando auditoría.
- Validación automática previa:594/594 y concurrencia aislada aprobadas; no hay cambios de producto posteriores. RetiroQA respaldado en `/var/tmp/mc-rov-manufacturing-qa-close-p2hK8Y`: cuentas/empleados/producto archivados, cuatro series dadas de baja, cinco órdenes conservadas (dos hechas y tres canceladas), cuatro seguimientos sin pendientes; STAGING activo. Pendiente cierre documental y PR/CI. Sin merge/despliegue de fabricación autorizado; producción conserva reparación19.0.25.0.0 sin destinatario operativo real.

## Fabricación automática — validación automática completa, 2026-10-16

- Implementación de fabricación y control general en `feature/manufacturing-activities`, producto hasta `c972adc`, versión19.0.25.1.0. Revisión independiente: único hallazgo importante corregido por RED/GREEN; sin otros críticos/importantes.
- **STAGING:594/594**, cero fallos/errores, nombres exactos sin omisiones/duplicados y16 archivos instalados coincidentes con el candidato. Configuraciones y PDFs intactos, pruebas temporales retiradas y servicio activo. Respaldo `/var/tmp/mc-rov-manufacturing-regression-nFRdU2`.
- **Concurrencia real aprobada desde Taller:** dos conexiones por confirmación/cierre, reintento completo por serialización; un seguimiento, una actividad pendiente al confirmar y cero pendientes al terminar; cero huérfanos. El segundo cierre recibió la validación nativa de serie ya fabricada. Copia `mc_rov_manufacturing_ci_t0JTV0` conservada con conexiones bloqueadas; respaldo `/var/tmp/mc-rov-manufacturing-concurrency-t0JTV0`.
- **Pendiente QA manual:** creador preparado `.tmp/staging-manufacturing-activity-qa-users.ps1`, todavía no ejecutado. Dos cuentas nuevas `mcqa.manufacturing.taller`/`mcqa.manufacturing.supervisor`, dos empleados, producto/series ficticios y cuatro órdenes borrador (normal/parcial/cancelación/pausa). Política28corridos desactivada; calendarioQA Santiago propio. Control general nuevo solo si ausente, activado como su conducta previa y registrado para retirarlo. No sustituye políticas ajenas ni cambia cuentas/calendarios existentes; contraseña solo en terminal.
- Después: prueba operativa guiada, archivo de datos QA conservando órdenes/historial, cierre documental y PR/CI. No merge/despliegue de fabricación autorizado todavía. Producción sigue con reparación19.0.25.0.0; cuenta real de Taller y calendario operativo siguen pendientes para activar automatismos reales.

# Trabajo pendiente

## Piloto de actividades automáticas — 2026-10-15

- **STAGING validado:** 66 contratos focalizados y suite completa **489/489**, cero fallos/errores y descubrimiento de todos los casos. Concurrencia real: dos conexiones por etapa, reintento de serialización, una actividad por etapa y cero huérfanas.
- **QA manual aprobada:** generación por etapa, reparto solo de empleado, confirmación de REV cierra diagnóstico, terminar orden cierra reparación, cancelar retira pendientes y reabrir genera un nuevo ciclo sin duplicados. Dos hallazgos de revisión independiente corregidos tras RED/GREEN (multiempresa y registros temporales).
- **Escenario QA retirado:** usuarios635/636 y empleados1068/1069 archivados; producto2273 archivado y series11315/11316 dadas de baja como ficticias. Orden4348 terminada y4349 cancelada; REV10324/10325 e historial conservados. Seis seguimientos: dos terminados por negocio, cuatro cancelados. Política529 sin destinatario QA; no hay cuenta operativa elegida automáticamente.
- Evidencia local en `.tmp/repair-activity-pilot/`: regression-tests.log, concurrency-probe.log y qa-closed.json. Respaldos finales `/var/tmp/mc-rov-repair-regression-zPWHT6`, `/var/tmp/mc-rov-repair-concurrency-EyIE0z` y limpieza `/var/tmp/mc-rov-repair-qa-close-zr9BsS`. Copias aisladas conservadas con conexiones bloqueadas; PDFs intactos, servicio activo.
- Rama `feature/repair-activities`, base b9bbd63, implementación hasta ab43229. Runbook: [Actividades automáticas](runbooks/repair-activity-pilot.md). Cierre documental y PR/CI pendientes; producción continúa con la versión anterior. Falta elegir destinatario/calendario de producción y autorizar despliegue antes de activar trabajo real.
- CI heredado modificaba el checkout de producción. Se prepara aislamiento en el workspace del runner antes de abrir el PR: solo BD odoo_test, comprobación de ruta y todos los casos descubiertos. Revisión/CI de ese ajuste pendientes; no tocar ni cambiar ramas del checkout operativo.

## Entrega Trabajo asignado — estado de cierre

- Usuario autoriza revisión, merge de PR #102, despliegue y retirada del QA temporal.
- STAGING: 42 contratos de asignación, privacidad, procesos y onchange aprobados; QA manual Supervisor/Taller aprobado (reparto, empleado, fecha con motivo y auditoría, permisos).
- Interfaz aprobada: vistas nativas integradas, una zona de contenido, botones iguales de ancho y altura ocupando la fila; temas claro/oscuro y PNG transparente verificados.
- Revisión final: corregida la lista de IDs congelada en la acción de actividades. Regresión RED en CI: único fallo de 423 pruebas; la consulta conserva filtros dinámicos y ACL del origen por ORM. Pendiente GREEN completo.
- Pendiente CI del paquete completo final, merge/deploy y archivo del escenario mcqa.taller/mcqa.supervisor en STAGING. No se agregan actividades automáticas ni permisos reales de producción.
- PR: https://github.com/amonpxh/mc_rov/pull/102. Evidencia y respaldos detallados en `.tmp/work-assignment-source/progress.md`.

### Integración de Trabajo asignado — 2026-10-13

- **QA manual bloquea cierre:** Supervisor 194 ve actividades QA, pero al abrir Repartir devuelve AccessError read mail.activity 311. No ampliar permisos ni usar sudo para ocultarlo. Primera sonda ejecutada: origen, búsqueda/read de actividades, accesos write, servicio, acción nativa y default_get pasan. Segunda sonda reprodujo exactamente el AccessError en activity_origin_copy y wizard_onchange; etiquetas/formulario guardado sí pasan. Causa: diferencia entre NewId(origin=311) y IDs persistidos al trasladar el permiso SQL. Corrección local preparada: comprobar origen persistido y volver a asociar el resultado a su copia; validar también cualquier referencia temporal modificada. Cuatro regresiones añadidas (copia legítima/onchange y dos denegaciones de origen). Black y pylint 10/10. Script `staging-work-assignment-onchange-green.ps1` listo para instalar solo backend y ejecutar 42 contratos; pendiente GREEN, sin cambios de permisos.
- **Tema oscuro pendiente corregir:** screenshot muestra marco claro y textos oscuros sobre vistas nativas oscuras. CSS actual fija blancos/grises y color raíz. Tokens instalados confirmados; CSS cambiado localmente a variables Odoo (fondos/texto/bordes/selección), todavía no instalado ni validado en ambos temas. Preflight SCSS del script deberá usar contexto de variables nativas antes de la siguiente instalación. Icono ya es PNG, pero SVG/PNG tienen fondo blanco incorporado; preparar variante de mismo dibujo con fondo exterior transparente y comprobar ambos temas. No cerrado ni listo para producción.

- QA manual con perfiles: usuario autorizó preparar creación de cuentas temporales STAGING. Creación **ejecutada y confirmada en STAGING**: mcqa.taller ID 193, mcqa.supervisor ID 194, empleados 896/897, reparación WH/RO/03451 ID 3460 y actividades 311/312. Evidencia `qa-users-created.json`. Prueba manual del usuario pendiente; archivado todavía no ejecutado. Scripts `staging-work-assignment-qa-users.ps1` y `staging-work-assignment-qa-users-cleanup.ps1` preparados. Crean mcqa.taller/mcqa.supervisor, dos empleados ficticios, una reparación y dos actividades; solo Supervisor recibe consulta/reparto, sin RRHH privado. Clave QA la introduce el usuario, no queda en archivos de evidencia. Creación transaccional y reutilización sin resetear claves; archivado posterior limitado a IDs registrados. Sin cuentas/datos de producción ni cambios a usuarios existentes.

- Último ajuste visual **instalado y verificado en STAGING**, respaldo `/var/tmp/mc-rov-work-embedded-frontend-green-SbtfEd`: cabecera duplicada y explicación permanente retiradas; ayuda contextual en filtros, Actualizar dentro del contenido activo, sin máximo de 1280 px. A 1280 px los siete accesos ocupan la fila (último borde a 3 px del borde del panel); a 432 px permanecen en una fila desplazable y el último acceso es alcanzable. Una sola acción Actualizar en ambos contextos. XML/libsass OK, sin repetición de suites lógicas por cambio de layout. Evidencia `integrated-layout-final.jpg`.

- Corrección visual **instalada y comprobada en STAGING**, respaldo `/var/tmp/mc-rov-work-embedded-frontend-green-oD2mfK`: ROV/título/descripcion restaurados; título 20 px y Actualizar agrupado en su misma fila, a 12 px del título. Siete accesos caben a 1280 px (1209 px de navegación, sin overflow). XML/libsass OK; sin cambios de lógica ni nueva repetición de suites.

- Ajuste visual **instalado y comprobado en STAGING**, respaldo `/var/tmp/mc-rov-work-embedded-frontend-green-Ct75aL`: cabecera compacta sin ROV/frase introductoria. A 1280 px los siete accesos caben en una sola fila (1209 px disponibles, sin desbordamiento); a 432 px siguen en una fila y el desplazamiento permite alcanzar el séptimo. Nombres conservados. XML/libsass OK; no se repitieron suites de lógica por este cambio de estilo. Evidencia `compact-center-desktop.jpg` y `compact-navigation-qa.json`.

- Backend del filtro cruzado instalado en STAGING: **38/38 contratos GREEN**, respaldo `/var/tmp/mc-rov-work-process-green-HGmpAR`.
- Frontend RED confirmado en navegador: **6/6 fallos esperados**, todos por ausencia de la integración, sin errores inesperados.
- Primera implementación instalada en STAGING el 2026-10-09 (respaldo `/var/tmp/mc-rov-work-embedded-frontend-green-m10cTs`); HOOT focalizado: **4/6 pasaron**, 2 fallaron por conversión `Number()` dentro de la plantilla. También se detectó fallo de SCSS por `min(680px, 70vh)`.
- Correcciones del selector/SCSS **reinstaladas en STAGING**, respaldo `/var/tmp/mc-rov-work-embedded-frontend-green-2EywQ3`. **27/27 HOOT aprobadas** (13 Centro, 5 asignación, 6 integración, 3 puente); no errores de estilos. Lista/Kanban/calendario nativos, tareas/proyectos, búsqueda NAS, apertura del origen y retorno conservando filtro/lista comprobados sin editar registros. Evidencia `.tmp/work-assignment-source/embedded-browser-qa.json` y `embedded-native-qa.jpg`.
- Actualizar habilitado y **6/6 contratos revalidados** en STAGING, respaldo `/var/tmp/mc-rov-work-embedded-frontend-green-GAZvQu`. Comprobación real detectó que borraba la búsqueda nativa (NAS: 2 → 5 registros).
- Corrección **instalada y validada en STAGING**, respaldo `/var/tmp/mc-rov-work-embedded-frontend-green-6HIUmF`: Actualizar conserva globalState (búsqueda/agrupación) y descarta únicamente los datos cacheados. **7/7 contratos de integración GREEN**; búsqueda real NAS conserva faceta y 2 registros tras Actualizar, sin errores de consola. Total frontend: 28 casos (21 previamente aprobados + 7 revalidados). Evidencia `embedded-refresh-final.json` / `embedded-refresh-final.jpg`.
- Pendiente cerrar revisión del diff y checks de rama/PR, validación final de empaquetado y QA del usuario con permisos reales de consulta/reparto. PR #102 continúa draft; no se autorizó producción para esta entrega.
- Correcciones anteriores verificadas: conversión del empleado en método JS; `height` + `max-height`, equivalentes y compatibles con libsass. SCSS reproducido RED y compilación local GREEN con libsass 0.23.0; evidencia `.tmp/work-assignment-source/embedded-style-check.json`.
- Implementación: una zona de contenido, navegación compacta, actividades/tareas/proyectos con `View` nativa, filtros independientes de las listas operativas, estado de búsqueda y protección de cambios sin guardar mediante callbacks separados.
- Preparado `C:/Users/MC/Desktop/Trabajo/Proyectos/Code/.tmp/staging-work-assignment-embedded-frontend-green.ps1`: instala solo manifest/assets y pruebas; conserva respaldos y restaura si falla la actualización. **27 pruebas HOOT** por ejecutar (18 anteriores adaptadas, 6 de integración del contenedor y 3 del puente).
- Validación local: sintaxis JS/PowerShell/Bash, XML y manifest correctos. Esto **no confirma GREEN**: falta HOOT y comprobar búsqueda/menú Repartir/retorno/scroll en vistas nativas reales.
- Aceptación no ofrece actividades específicas de REV/FEN; Tareas/Proyectos no infieren procesos por título. No se añadieron automatismos, permisos reales, registros ni cambios PDF.
- PR #102 sigue draft; sin merge ni despliegue de esta entrega a producción.


> Fuente de continuidad. Actualizar al cerrar cada sesión y distinguir código local,
> pruebas, merge y despliegue. Las propuestas no aprobadas no son tareas de implementación.

## Estado vigente — 2026-10-13
- **Integración visual de Trabajo asignado aprobada:** una sola zona alterna tablero
  y listas del proceso. Maqueta `http://localhost:8081/` aprobada; nombre confirmado.
  Filtro por origen inmediato implementado localmente; RED 5/5 confirmado.
  GREEN de 38 contratos aprobado; respaldo `/var/tmp/mc-rov-work-process-green-HGmpAR`.
  Composición de vistas nativas implementada e instalada; seis pruebas RED confirmadas. Primera pasada 4/6; selector/SCSS corregidos y 27 HOOT GREEN; falta ajuste local de Actualizar. Fuentes instaladas verificadas.
  PR #102 mantiene la primera entrega como borrador, CI aprobado; no hacer merge/deploy
  antes de completar esta integración y QA. Producción sigue en 19.0.24.4.0.

- **Trabajo asignado manual en STAGING 19.0.24.5.0:** suite completa **415/415**
  aprobada, HOOT **18/18** aprobado; QWeb conservados y servicio activo.
  Respaldo final `/var/tmp/mc-rov-work-assignment-privacy-green-PA4bdI`.
  Consulta personal/equipo, empleado, reparto y vistas nativas implementados.
  Revisión independiente sin hallazgos importantes pendientes. Exportación con
  nombre restringido y permiso del origen verificada: prueba focalizada 1/1
  aprobada el 2026-10-09 19:10 UTC; pruebas temporales restauradas.
  PR borrador [#102](https://github.com/amonpxh/mc_rov/pull/102) abierto; hooks aprobados.
  Faltan CI, QA visual del usuario con roles reales y aprobación para producción.
  No hay automatizaciones ni asignación de empleado en tareas de Proyecto.

- Ajuste aprobado e integrado en `main` mediante `439d013`
  ([PR #101](https://github.com/amonpxh/mc_rov/pull/101)): icono ampliado
  y brazos más anchos instalados en STAGING y producción; render a escala de referencia verificado
  en 126 × 126 px, sin desplazamiento ni rotación. Seis contratos nuevos de responsables
  escritos antes del cambio de backend. Auditoría y RED verificados en STAGING:
  16 contratos anteriores pasan; cinco pruebas nuevas producen ocho aserciones
  fallidas esperadas (subcasos REV/RND/TRN/FEN), sin errores. Backend e icono instalados
  en STAGING 19.0.24.4.0: suite 383/383 aprobada, servicio activo y hashes QWeb
  conservados. RED frontend observado: 10 pruebas anteriores pasan y 3 nuevas fallan por
  columnas ausentes. Columnas instaladas en STAGING y HOOT GREEN 13/13 comprobado en navegador.
  QA visual: REV, órdenes, fabricación y alertas muestran sus responsables;
  Equipos no muestra columna. Black/pylint y hooks aprobados. CI del PR 380/380
  y lint aprobados. Merge y CI de main aprobados: 380/380, lint verde. Producción 19.0.24.4.0
  instalada y verificada el 2026-10-09: nombres/etiquetas y referencias comprobados,
  conteos sin cambios y sonda revertida. Icono instalado coincide con el PNG aprobado.
  Evidencia: `../.tmp/prod-center-responsibles/verification.json` y `deployment.txt`.
  Comprobación visual de icono y responsables en producción aprobada por el usuario.
  No repetir el deploy; entrega cerrada.
  Evidencia: `../.tmp/center-work-qa/responsibles-green-tests.log`.

- **Centro de trabajo desplegado en producción.** STAGING 19.0.24.3.0
  pasó la suite final 378/378; servicio activo. Nombre e icono morado verificados
  en el lanzador de Odoo, sin logo MC dentro de la pantalla. Black y pylint-odoo
  pasan; PDFs conservados. [PR #100](https://github.com/amonpxh/mc_rov/pull/100)
  integrado en `main` mediante `b9410ba`, con checks del PR y del merge aprobados
  (CI del merge: 375 pruebas). Instalación de producción verificada con lectura y rollback.
- Producción: `mc_rov 19.0.24.4.0`, código funcional `439d013` (PR #101).
  Upgrade y reinicio completos verificados; servicio activo desde
  2026-10-09 12:48:36 UTC, PID 1073901. Menú, acción e icono verificados;
  conteos y referencias de las áreas comprobados sin crear datos.
  Ambos reportes QWeb conservan sus hashes. Comprobación visual en producción aprobada.
- Navegación FEN terminada y aprobada manualmente: historial en **Fichas**, sin título
  interior adicional. **Pruebas** conserva revisiones y creación RND/TRN.
  **Imprimir ficha** aparece en cabecera y Fichas, no en Pruebas; ambos accesos
  abren el mismo asistente. Fichas y sus accesos se ocultan para no-ROV.
- **Retomar / Abrir** abre la FEN elegida, sin crear otra. Sus botones inteligentes
  **Equipo / Rendimiento / Terreno** abren las referencias guardadas, cuando existen;
  no sustituyen la evidencia por pruebas posteriores. Emisión y PDFs sin cambios.
- Verificación: STAGING pasó la suite completa de **359 pruebas, cero fallos/errores**;
  después de retirar el botón de Pruebas pasó el contrato del formulario (1/1).
  CI del PR y del merge funcional: **356 pruebas, cero fallos/errores**, lint aprobado.
  QA manual: FEN/00878 â†’ TRN/00003 y equipo 26-02; retorno por breadcrumb comprobado.
  Emitidas, varias fichas, referencias antiguas y permisos cubiertos por pruebas
  transaccionales; no confundirlas con muestras reales emitidas.
- Producción confirmó pestaña Fichas y ubicación final de Imprimir ficha mediante
  vista instalada. Contiene **cero FEN**: no se certificó apertura de una FEN real
  allí. La sonda se revirtió, sin emitir documentos ni consumir correlativos.
  Ambos reportes QWeb conservaron sus hashes antes/después del despliegue.
- Respaldo de producción:
  `/var/backups/mc-rov-prod-center-responsibles-0dLZNQ/odoo_prod.dump`.
  Evidencia del último despliegue: `../.tmp/prod-center-responsibles`; evidencia FEN
  anterior: `../.tmp/prod-fen-navigation` y `../.tmp/fen-navigation-qa`.
  No publicar archivos `.tmp`. No queda despliegue pendiente para esta entrega.
- Mapa de relaciones aprobado: recorridos abiertos y ramas por escenario, no una
  secuencia obligatoria. Auditoría y límites en diseño § 12–13. Equipo → Trazabilidad
  → fabricación de origen funciona; alerta → reparación abre la orden exacta.
  Reparaciones/alertas del equipo son botones inteligentes nativos, no pestañas.
  Calidad → fabricación: corte directo confirmado en la vista instalada; la alerta
  guardaba la MO sin ofrecer acceso a ella. Botón Fabricación implementado e
  instalado en STAGING `19.0.24.2.0`, tres contratos y suite 362/362 aprobados.
  Desplegado en producción; tests y lint del PR y del merge aprobados. Las tres
  alertas reales no tienen MO: caso positivo cubierto por pruebas transaccionales.

## Próximos pasos acordados, en orden

### Ajustes posteriores al despliegue del Centro

- Icono aprobado por el usuario: sin desplazamiento ni rotación, brazos más anchos
  (32 → 40), círculo blanco limpio; rectángulo cromático recalculado a 126 × 126 px
  en la maqueta, igual que Contactos/Ventas. Maqueta:
  `../.tmp/center-work-qa/icon-measured/wide-comparison.png`. PNG/SVG actualizados
  localmente y render del PNG comprobado a 126 × 126 px; instalado en STAGING y producción.
- Responsables en el Centro: propuesta y nombres de columnas aprobados por el usuario;
  backend aprobado en STAGING (383/383), interfaz instalada y HOOT 13/13 aprobado; desplegado en producción. REV/RND/TRN: «Técnico responsable», con ayuda
  «Persona registrada como responsable de realizar la prueba». Evitar «Realizado por»
  en borradores, porque aún podrían no haberse ejecutado. Órdenes: «Responsable».
  Reutilizar responsables existentes; separar responsable del registro de asignado
  de una actividad nativa. REV/RND/TRN y FEN usan empleados; las órdenes nativas
  usan usuarios. No inferir asignación desde autor, propietario o último editor.
  Campos de Fabricación/Calidad/ECO auditados: usuario nativo responsable.
  Empleados se consultan mediante `hr.employee.public`, respetando permisos.
  Sin persona registrada: «Sin responsable»; nombre restringido: «Sin acceso al nombre».
  Modelos/BoM/equipos sin columna; responsable logístico de producto excluido. No crear obligaciones
  ni asignar automáticamente tareas a partir de los conteos del Centro.
- Actividades programadas: fuera del alcance actual. El usuario quiere conversar
  su incorporación después; no implementar ahora. Si se incorporan, distinguir
  «Asignado a» del responsable del registro o del técnico de una revisión.

### Entrega del Centro de trabajo

Piloto aprobado por el usuario. Nombre «Centro de trabajo», icono morado de
conexiones y sin logo MC dentro de la pantalla. Bordes y scroll corregidos.
Suite final del árbol actual: **378/378**, cero fallos/errores, servicio STAGING
activo. Nombre/icono instalados y verificados en el lanzador nativo. Contratos
backend y HOOT (16 y 10) aprobados; preservación de filtros y referencias comprobada.
Los reportes FEN/REV conservan sus hashes y las sondas se revirtieron.

Evidencia: `../.tmp/center-work-qa/final-release-tests.log`,
`final-release-response.txt` y `final-icon-installed.png`.
Respaldo: `/var/tmp/mc-rov-center-work-final-release-Ic3VQH`.
Black y pylint-odoo locales aprobados. PR #100 integrado (`b9410ba`), checks del PR
y del merge aprobados. Producción 19.0.24.3.0 instalada y reiniciada; sonda de lectura
aprobada, sin cambios de conteos y con rollback. Menú/acción 1018 e icono verificados.
Evidencia: `../.tmp/prod-center-work/verification.json` y `deployment.txt`.
Falta comprobación visual en producción; no repetir despliegue para hacerla.

El runner PowerShell tenía un prefijo BOM convertido en texto; produjo un error
en la primera línea pero continuó y completó el despliegue. Generador y script
corregidos; primera línea y sintaxis comprobadas localmente sin ejecutar SSH.
Los avisos de deprecación de `odoo.osv` y del compute de ficha técnica no bloquearon
el upgrade. Su limpieza técnica queda para una pasada separada, sin alterar esta entrega.

El runner final excedía el límite Linux por variable de entorno; ahora transporta
el paquete mediante archivo temporal. Reejecución verificada. Issue QA preparado
localmente; publicación GitHub pendiente de autorización explícita tras rechazo
por revisión automática. No bloquea la entrega funcional.

Diseño vigente: [Centro de trabajo](designs/centro-trabajo-rov.md).
Plan: [Implementación](superpowers/plans/2026-10-08-centro-trabajo-rov.md).
[Historial de ensayos](pendientes-centro-historial-2026-10-08.md): no tratar los
pendientes intermedios de ese archivo como estado actual.

### 1. Muestras adicionales de FEN cuando existan

La implementación y el despliegue de navegación están cerrados. La ruta actual es
**Equipo â†’ Fichas â†’ Retomar / Abrir**, con acceso a la evidencia exacta seleccionada.
La muestra manual de STAGING contiene una FEN en borrador; producción aún no tiene FEN.

Cuando existan documentos reales emitidos o varias fichas de una unidad, completar
la comprobación manual de esos escenarios. Ya tienen cobertura automatizada; no
bloquean esta entrega. No emitir fichas de clientes ni consumir correlativos solo
para probar navegación. No existe un menú general de FEN en las vistas actuales.

### 2. Completar la auditoría de fabricación

La MO WH/MO/00010 → botón nativo Números de serie → equipo 0000008 ya fue comprobada.
WH/MO/00011 no tiene serie: el botón se oculta y aparece el campo de asignación.
El inventario de 11 MO no contiene varias series ni controles de calidad asociados.
Contrastar los casos restantes con Odoo y taller:

- Fabricación con cero, una o varias series; dónde se asignan y cómo se elige la unidad.
- Diseño/BoM vigente frente a cambio de diseño: actualizar BoM o usar PLM es condicional,
  no un paso obligatorio para cada fabricación.
- Controles de calidad según producto y operación configurados; no añadir una batería universal.
- Configuración técnica incompleta, pruebas repetidas/rechazadas y aceptación todavía incompleta.
- Equipo → RND/TRN → FEN: conservar revisiones independientes y selección explícita de evidencia.
- Confirmar qué corresponde a fabricación, aceptación y entrega comercial; no trasladar
  requisitos de emisión FEN al cierre de MO o a la entrega sin una decisión de negocio.

Entregable: matriz de conexiones existentes, cortes demostrados y aplicabilidad de
cada paso. Proponer cambios solo donde haya una dificultad real, antes de implementarlos.

Sonda focalizada completada con rollback sobre `19.0.24.1.0`; matriz en diseño § 14.
Confirmado: la alerta guarda `production_id`, pero no ofrece acceso directo a MO;
existe ruta indirecta por control cuando está vinculado y visible. Fabricación ya
ofrece conexiones nativas a alertas e ingeniería. Muestra: 11 MO, una BoM, tres
alertas; cero puntos/controles/ECO y ninguna MO con varias series. Lectura heredada
completada: Reparación → fabricaciones consulta `reference_ids.production_ids`, no
la serie; BoM se propone por compatibilidad y prioridad, no por fecha más reciente.
Botón **Fabricación** aprobado e implementado en `feature/quality-production-navigation`,
versión `19.0.24.2.0`. RED observado: tres fallos esperados. GREEN instalado en
STAGING: tres contratos y suite completa **362 pruebas, cero fallos/errores**.
Sonda de la vista instalada aprobada, rollback confirmado y Odoo activo. Reportes
QWeb FEN/REV con hashes conservados. Hooks locales aprobados.

La muestra real sigue siendo QA00002/3/4 sin `production_id`; el caso con MO se
verificó con pruebas transaccionales, no mediante un clic sobre una alerta real.
Se mantiene pendiente la comprobación de pantalla con una muestra vinculada cuando
exista. No se crearon alertas de QA persistentes ni se tocaron controles o PDFs.
Respaldo STAGING: `/var/tmp/mc-rov-quality-navigation-z394km`.
Evidencia: `../.tmp/quality-navigation-qa` (GREEN y vista instalada) y
`../.tmp/process-navigation-audit/manufacturing.json` (auditoría).
PR #98 integrado en main (`54c177d`), con tests y lint aprobados en PR y merge.
Producción desplegada en `19.0.24.2.0`: upgrade/reinicio completos, servicio activo,
vista instalada y acciones de tres alertas reales comprobadas con rollback, hashes
QWeb FEN/REV conservados. La base contiene tres alertas y ninguna tiene MO vinculada;
no se certificó un clic sobre un caso positivo real ni se crearon alertas persistentes
para probar. Respaldo `/var/backups/mc-rov-prod-quality-navigation-KvN70P/odoo_prod.dump`.
Evidencia `../.tmp/prod-quality-navigation`. No queda merge ni despliegue pendiente
para este acceso. La primera sonda GREEN falló por conversión ASCII de la tilde en
Windows PowerShell; corregida con escape Unicode, sin cambiar el botón.

### 3. Coordinación de tareas: propuesta para evaluar

El Centro de trabajo ya está desplegado en producción 19.0.24.4.0; no queda
pendiente construirlo. Reúne accesos y registros operativos, no una lista personal
de tareas asignadas. Los responsables mostrados reutilizan datos del registro.

El usuario plantea evaluar Kanban para actividades/tareas, con preocupación por
su conexión con reparación, fabricación y diseño. Acuerdo posterior: Usuario asignado
es la cuenta (Taller/Dev/Supervisor), Empleado asignado es la persona ejecutora.
Diseño base y respaldo de fechas aprobados; plan de primera entrega manual pendiente
de revisión antes de implementación.
Distinguir seguimiento nativo de un registro de una
tarea de Proyecto con vida propia. Evaluar vínculos explícitos al origen y destino,
asignación real, criterios de terminación y pasos condicionales. No duplicar estados
operativos, generar todos los pasos para todos los casos ni equiparar tarea realizada
con orden cerrada, revisión aprobada o FEN emitida. Mi trabajo identifica la cuenta
conectada; un filtro por empleado no identifica quién usa una cuenta compartida.

Diseño para revisión:
[Trabajo asignado](superpowers/specs/2026-10-09-trabajo-asignado-design.md).
Propone actividades nativas con empleado opcional, permisos separados para consultar
equipo y coordinar, y acceso desde el Centro. Primer piloto: Completar revisión técnica
de la primera REV creada al entrar la orden ROV al taller, no «Diagnóstico» porque
ese hito no tiene estado propio. Tareas/Proyectos mediante accesos nativos; integración
por empleado de tareas y automatizaciones de fabricación quedan para siguientes fases.
Política de fecha aprobada: plazo por actividad, luego fecha prevista de la orden,
y plazo general configurable como respaldo; sin autoalargar. Reprogramación explícita
con motivo. Cantidades concretas se definen al configurar; ninguna regla habilitada.
Ejemplos aportados son contexto, no instrucciones de crear datos: avances parciales,
reingresos, componentes/cables, entregas inciertas, compras, coordinación y desarrollo.
Trabajo asignado no arrastra filtros ROV de las seis áreas; completar actividad no
entrega, recibe, reserva material, firma ni confirma un registro operativo.
Plan preparado: [Primera entrega manual](superpowers/plans/2026-10-09-trabajo-asignado-manual.md).
Plan aprobado para ejecución directa. Tarea 1 terminada: fuentes instaladas
recuperadas (14 archivos), con rollback. Compras, transferencias, Ventas y Documentos
admiten actividades; CRM no instalado. Sin usuarios activos no HR/no administrador;
ese caso se verifica con fixtures transaccionales, no cuentas reales.
Checkout aislado: `../.tmp/worktrees/trabajo-asignado`, rama
`feature/trabajo-asignado-manual`. RED observado el 2026-10-09: seis fallos esperados
por ausencia de `mc_employee_id`, cero errores. El runner lo clasificó incorrectamente
al buscar una frase con tilde transmitida por PowerShell; corregido a seis aserciones
ASCII exactas más el resumen de Odoo. No hace falta repetir ese RED.
Campo y validaciones implementados localmente: empleado opcional, selección pública,
empresa del origen, rechazo de nueva asignación a archivados y conservación posterior.
Relación privada con FK nativa; token interno de HR de Odoo 19 limitado a la escritura
de relación tras validar el directorio público, sin ampliar ACL ni devolver ese contexto.
Black y pylint locales aprobados. GREEN focalizado preparado en
`../.tmp/staging-work-assignment-green.ps1`. Primer intento: cinco casos pasan;
el de otra empresa falla al preparar su fixture porque Partes de horas crea un
proyecto interno y la BD de STAGING exige `project_project.billing_type`. La validación
de empleado no llegó a ejecutarse en ese caso. Código restaurado, servicio activo.
Fixture corregida para aislar únicamente `_create_internal_project_task`; empresa y
empleado siguen siendo reales y transaccionales. Segundo GREEN verificado: 6/6,
cero fallos/errores; campo instalado en STAGING y servicio activo. Respaldo:
`/var/tmp/mc-rov-work-assignment-green-pOHgBe`. Hashes de ambos reportes conservados.
No hay cambio de pantalla. Ocho contratos nuevos de consulta y seguridad: RED
confirmado en STAGING, 8 fallos esperados y cero errores; pruebas restauradas.
Servicio y dos permisos independientes implementados localmente; consulta personal
incluye futuras y no ROV, filtra empleado/empresa y usa acciones nativas. Proyectos
personales son los que contienen tareas asignadas a la cuenta, no los creados por ella.
Lectura directa de actividades comprueba origen y empresa; las referencias se
inspeccionan internamente sin nombres ni elevación y el documento usa permisos ORM.
Black/pylint y parsers aprobados. GREEN de 14 contratos (6 + 8) en
`../.tmp/staging-work-assignment-query-green.ps1`; verificación vigente: 14/14 pasan.
Consulta y protección instaladas en STAGING, no hay pantalla nueva. Wizard y Centro
pendientes; automatización y ampliación de tareas de Proyecto en planes posteriores.
Primer GREEN de consulta: 12/14 pasan; fixture multiempresa hereda ubicaciones de
inventario de empresa original y lectura directa restringida no bloquea. Código y
grupos nuevos restaurados, servicio activo. Correcciones locales: fixture usa
`with_company(company)` y `read` comprueba explícitamente acceso, incluso con datos
prefetched; la prueba verifica además `has_access('read') == False`. Segundo GREEN
aprobado: 14/14, cero fallos/errores. Servicio activo, hashes QWeb conservados.
Respaldo: `/var/tmp/mc-rov-work-assignment-query-green-DBiEgD`.
Ocho contratos de wizard escritos antes del producto: permisos independientes,
selección prohibida, cambios explícitos, quitar empleado, reprogramar con motivo,
autoría de cuenta, atomicidad y orden/repuestos intactos. RED preparado en
`../.tmp/staging-work-assignment-wizard-red.ps1`: RED confirmado, 8 fallos esperados,
cero errores; pruebas restauradas y STAGING activo. Asistente, ACL y acción nativa
implementados localmente. Cambios explícitos por campo, validación completa al
guardar, savepoint para evitar cambios parciales, motivo de reprogramación y nota
en origen con autoría de la cuenta; sin modificar cierre, entrega ni repuestos.
Para actividades libres, conserva la auditoría en su nota. Black/pylint y parsers
aprobados. Primer GREEN: 17 contratos pasan y 5 producen errores de acceso a
`ir.model` durante la validación de empresa. Código y metadatos restaurados;
STAGING activo. Corregido localmente: usar la referencia de origen de la actividad
y resolver referencias técnicas explícitas sin conceder acceso al catálogo de
administración; el documento mantiene sus controles ORM. La prueba verifica que
Taller no recibe permisos de lectura de `ir.model`. Segundo GREEN aprobado en STAGING: **22/22 contratos, cero fallos/errores**;
asistente y accion nativa instalados, servicio activo y hashes QWeb conservados.
Respaldo: `/var/tmp/mc-rov-work-assignment-wizard-green-z0kJp1`.
HOOT RED observado: 13 pruebas previas pasan y las cinco nuevas fallan solo
por la entrada Trabajo asignado ausente. Accesos instalados en STAGING
(respaldo `ikjeoA`). HOOT GREEN confirmado: **18/18** (13 existentes y 5 nuevas).
Las correcciones del helper de seleccion y espera de render solo afectaron pruebas.
Abrir actividades llega a la lista nativa con Kanban/calendario, sin filtros Hoy/Vencidas
heredados. Tres contratos de vistas nativas escritos: lista/formulario/calendario,
Kanban con estado vacio y busqueda/agrupacion por empleado. RED confirmado en STAGING: tres fallos esperados, cero errores, pruebas restauradas
y servicio activo. Vistas nativas implementadas localmente. Etiqueta de empleado
calculada sin sudo desde el directorio publico: sin asignacion y nombre restringido
se distinguen. Tres contratos cubren esas vistas y lectura sin RRHH privado.
GREEN confirmado en STAGING: **25/25 contratos, cero fallos/errores**;
respaldo `/var/tmp/mc-rov-work-assignment-activity-views-green-3qDpIy`,
servicio activo y QWeb conservados. QA visual: Kanban nativo conserva usuario,
fecha y acciones, y muestra «Sin empleado asignado». En lista se detectó una
columna técnica duplicada: corregida localmente con `column_invisible` y
comprobación de regresión instalada y verificada. Entrega local versionada
`19.0.24.5.0`. Runner de suite completa preparado:
`../.tmp/staging-work-assignment-final-qa.ps1`.
Suite completa aprobada: **408/408**, cero fallos/errores; respaldo
`/var/tmp/mc-rov-work-assignment-final-qa-hmIU67`, STAGING activo y QWeb conservados.
Columna duplicada corregida y verificada en navegador tras recargar.
Revisión independiente encontró dos fronteras pendientes: consultas nativas
(search/count/group) de actividades con origen prohibido y serialización/auditoría
de un empleado cuyo nombre público queda restringido. Seis contratos nuevos
preparados en `../.tmp/staging-work-assignment-privacy-red.ps1`; RED confirmado por log: **6 fallos esperados, cero errores**; el runner
marcó inesperado por contar una frase parcial, no por otro fallo del producto.
Corregido localmente: búsquedas antes de paginar y etiquetas públicas en read,
web_read, agrupaciones, exportación y auditoría. Séptimo contrato añade paginación; GREEN
aprobado en STAGING: **415/415**, cero fallos/errores; respaldo
`/var/tmp/mc-rov-work-assignment-privacy-green-PA4bdI`. La prueba añadida de exportación
queda para ejecución focalizada en `../.tmp/staging-work-assignment-export-check.ps1`;
no repite la suite ni modifica producto.
QA de roles y cierre de PR pendientes.
Automatizaciones fuera de esta entrega.
Producción continúa sin cambios y no se crearon los ejemplos del usuario.

Diseño y auditoría: [Recorridos guiados](designs/flujo-guiado.md).
Auditoría inicial de funciones existentes (2026-10-09): «Actividades pendientes»
en STAGING ya ofrece Kanban, personas asignadas, fecha límite y «Convertir a tarea».
Su ayuda nativa explica la conexión con Proyecto → Mis tareas. No confundir esa
aplicación con las actividades del reloj/chatter. El código local de mc_rov no
declara integración con project.task/mail.activity; REV hereda mail.thread sin
mail.activity.mixin. Auditoría de módulos instalados completada con rollback:
`../.tmp/task-activity-audit/installed.json`. Actividades pendientes usa project.task
sin proyecto; Proyecto → Mis tareas reúne tareas asignadas con y sin proyecto.
«Mis actividades» es otra acción nativa (124), con lista/Kanban/calendario y vínculo
al documento mediante res_model/res_id; lista y tarjetas verificadas en navegador.
Su filtro inicial muestra actividades propias vencidas o de hoy, no todas las futuras.
Reparación, fabricación, equipo, BoM, ECO, alerta y control de calidad admiten
actividades nativas. REV/RND/TRN y FEN no las admiten actualmente; tampoco mrp.workorder.
project_mrp está instalado: fabricación y BoM tienen project_id, y la fabricación
ofrece action_open_project. Es vínculo al proyecto, no a una tarea concreta.
No se encontraron relaciones directas entre project.task y los registros operativos
auditados. No inferir tareas automáticas ni sincronización de estados de esos vínculos.
Las actividades y tareas se asignan a res.users; técnico empleado sin login sigue
siendo un caso distinto. En la muestra hay cinco actividades sobre tareas y ninguna
sobre los otros modelos operativos que admiten actividades.
Sugerencia aún sin aprobación de implementación: probar primero seguimiento nativo
ligado al registro; reservar Proyecto para trabajos que requieran etapas/subtareas,
y diseñar vínculos explícitos si se necesita una tarea para una orden/REV/FEN/ECO.
No se crearon tareas ni se convirtió ningún registro durante la inspección.
Guía de procesos: [Flujo de trabajo](flujo-de-trabajo.md).
Los apartados del diseño sobre Guía + chatter son antecedentes descartados.

## Cerrado: no volver a implementar

| Trabajo | Estado confirmado |
| --- | --- |
| PDF de equipo reparado (REV) y ficha consolidada de equipo nuevo (FEN) | Aprobados y desplegados; no quedan ajustes visuales abiertos. RND/TRN son evidencia de FEN, no revisiones de reparación. |
| Borradores FEN para vista previa | Desplegado en `19.0.23.7.0`; emisión final conserva requisitos de aprobación. |
| Selección de RND/TRN y botón Imprimir ficha | Corregidos y desplegados. No sugerir REV de reparación como evidencia FEN. |
| Separar Electrónica / Software | Desplegado en `19.0.23.7.0`; componentes Electrónica y Software / Configuración para Hallazgos y Trabajos. |
| Aviso compacto de cierre de reparación | Desplegado en `19.0.23.8.0`; carencias comprobables, sin enlaces ni requisitos nuevos. |
| Equipo / Orden de reparación desde revisiones | Desplegado en `19.0.24.0.0`; destinos exactos, sin sudo ni cambios de datos; orden oculta sin vínculo. |
| STAGING y pruebas de despliegue | Operativos; no es una tarea pendiente montar STAGING. |

Conservar composición de ambos PDFs, lógica adaptativa de Hallazgos, firmas y footer.
La temperatura continúa interna. Los últimos cambios de navegación no modificaron
los hashes QWeb PDF. No repetir suites o despliegues sin cambios relevantes.

## Para la preparación final del sistema

Pospuestos por el usuario hasta completar el sistema:

- Carga/revisión de productos y equipos: categorías ROV, propietario, puesta en
  servicio y faltantes técnicos. No asumir que producción sigue vacía por una nota antigua.
- Permisos por perfiles y validación con usuarios reales. Respetar mientras tanto
  los permisos actuales; navegación no implica autorización adicional.
- Reorganización administrativa, traspaso a la empresa e infraestructura del pipeline.
  El roadmap anterior es referencia, no un plan de ejecución vigente.
- Revisión del workspace de CI separado de los addons de producción: el runbook
  todavía documenta el directorio compartido; comprobar el entorno antes de cambiarlo.
- Comprobar si se resolvió la rotación de `admin_passwd` anotada en agosto. Su estado
  actual no fue verificado; no copiar contraseñas a documentación o logs.

Después de comenzar el uso real: medir llenado de `hallazgo_origen_id` y utilidad de
`analisis_causa`, definir indicadores de desempeño con datos representativos.
No hay un calendario de seis meses ni una automatización activa para esas evaluaciones.

## Revisión técnica separada y propuestas sin aprobación actual

- Advertencias existentes de `compute_sudo/store` mezclados: `stock.lot.mc_ficha_*`
  y `mc.rov.revision.software_difiere/software_diferencias`. Reproducir y delimitar
  antes de corregir; no son fallos del despliegue ni cambios hechos en esta entrega.
- Catálogos editables de motores/periféricos: propuesta histórica; el código actual
  conserva una Selection de motores y textos de brazo/dispositivos. Revalidar necesidad
  con taller antes de convertirlos en catálogos. No bloquea los recorridos actuales.
- Tolerancias por modelo, trazabilidad de piezas y vínculo cotización/configuración:
  propuestas históricas a revisar al definir operación y carga; no implementar por inercia.
- Fotos de Hallazgos: aplazadas, sin petición actual de implementación.

## Descartado o sin necesidad actual

- Panel Guía + chatter: retirado con su código y pruebas; duplicaba las pestañas.
- Chequeos por luz/cámara individual: no hay necesidad actual confirmada. Mantener
  luces internas/externas y chequeos generales; no abrir esta ampliación automáticamente.
- Historial adicional de ficha técnica y batería duplicada de armado: no reintroducir
  propuestas descartadas ni copiar las mediciones de RND/TRN a controles de MO.

## Historial y referencias

Las notas anteriores, ensayos, decisiones y estados intermedios se conservaron en
[Historial hasta 2026-10-07](pendientes-historial-2026-10-07.md). Sus casillas antiguas
no son tareas vigentes. Ante contradicción prevalecen este estado confirmado, el código
actual y las decisiones más recientes del usuario.

Procedimientos: [Pruebas](runbooks/testing.md), [STAGING](runbooks/staging.md) y
[Despliegue](runbooks/deploy.md).


## Pendiente nuevo: agente IA en Odoo y Telegram — 2026-10-15

- [ ] Analizar y diseñar un agente que ayude a ejecutar tareas sobre registros reales de Odoo, accesible desde el chat de Odoo (Discuss) y Telegram. Solicitud del usuario: registrar el pendiente y evaluar viabilidad; todavía no implementar ni instalar.
- Auditar primero módulos IA nativos disponibles en la instalación Odoo 19, edición/licencia y herramientas extensibles antes de elegir desarrollo propio. Referencia: https://www.odoo.com/documentation/19.0/applications/productivity/ai/agents.html
- Propuesta inicial, pendiente de diseño: un agente con dos canales, mismas reglas y permisos; comenzar con consultas/resúmenes de trabajo y luego creación/reparto/reprogramación de actividades ligadas al origen. Mantener validadores existentes, auditoría y confirmación explícita de cambios sensibles.
- No requiere por principio una BD de negocio aparte. Odoo conserva órdenes, actividades, tareas y proyectos como fuente de verdad; evaluar tablas de conversación/vinculación/auditoría en su BD. Servicio externo opcional para procesar mensajes/colas/modelo; almacenamiento separado solo si la arquitectura lo justifica, sin duplicar datos operativos.
- Telegram exige vincular identidad Telegram con cuenta Odoo y persona/empleado autorizado, especialmente por las cuentas compartidas de Taller/Dev/Supervisor. No deducir identidad por nombre visible ni conceder al bot permisos globales de administrador. Prevenir que reintentos de mensajes dupliquen acciones.
- Definir acciones permitidas, proveedor/modelo y coste, privacidad de los datos enviados, retención de conversaciones y acceso por empresa. Distinguir propuesta del agente de cambio aplicado y revisión confirmada por persona responsable.
- Integración Telegram mediante Bot API oficial: https://core.telegram.org/bots/api . Primer piloto en STAGING. Estimación preliminar: consulta/resumen dificultad media; ejecución fiable de tareas entre módulos y ambos canales dificultad media-alta. No hay plazo ni arquitectura cerrados.
- Este pendiente no sustituye el cierre del piloto de actividades automáticas: suite general, concurrencia aislada, revisión y QA operativa siguen pendientes.


## Pendiente nuevo: Inventario desde Centro de trabajo — 2026-10-15

- [ ] Diseñar acceso a Inventario desde el Centro de trabajo, reutilizando acciones/vistas nativas y permisos existentes. Usuario solicita registrarlo y evaluar otros faltantes; no implementar todavía.
- Alcance candidato: consultar existencias/disponibilidad por producto y ubicación, componentes/repuestos además de equipos ROV, recepciones, entregas y transferencias internas. Distinguir existencia física de disponibilidad para uso; no aplicar filtro exclusivo de vehículos.
- Mantener relación de materiales/movimientos con órdenes de reparación y fabricación cuando ya exista. Consultar un equipo sigue dedicado a serie/configuración/historial, no sustituye inventario.
- Auditar fuentes y permisos instalados antes de cerrar el alcance. Elegir presentación sin romper los siete accesos iguales aprobados: posible octavo acceso con adaptación de ancho; propuesta visual pendiente.
- Revisar como candidatos posteriores Compras/reabastecimiento (por materiales faltantes) y entregas/retiros (preferentemente dentro de Inventario). KPIs ya son pendiente independiente; documentos/informes mediante sus procesos salvo necesidad transversal confirmada. Estos candidatos son recomendaciones para discutir, no funcionalidades aprobadas para implementar.
- Conservar la prioridad del cierre del piloto de actividades automáticas y tratar IA/Telegram posteriormente.


### Compras en Odoo y futuro reemplazo de Defontana — alcance corregido

- Aclaración posterior del usuario: Defontana se usa actualmente solo para cotizaciones comerciales y facturación con el SII; NO para compras/abastecimiento. Esta aclaración sustituye la propuesta anterior de sincronizar compras con Defontana.
- [ ] Auditar y diseñar Compras y abastecimiento en Odoo, conectados con necesidades de reparación/fabricación e Inventario: solicitudes de cotización a proveedores, órdenes de compra y recepciones. No duplicar inventarios ni confundir compra aprobada con material disponible.
- [ ] Como última etapa de la hoja de ruta, evaluar reemplazar también cotizaciones comerciales y facturación de Defontana por Odoo. No iniciar migración ni retirar Defontana antes de estabilizar procesos operativos y verificar requisitos tributarios, localización chilena, DTE, certificados/folios y habilitación aplicables con fuentes oficiales y responsables de la empresa.
- Referencia aportada por el usuario para esa etapa: https://facele.cl/integracion-erp-con-la-facturacion-electronica-sii-en-chile-guia-tecnica-para-empresas/ . Guardada como recurso de proveedor; acceso directo no disponible en la consulta actual, contenido no verificado. No supone elección de Facele ni aprobación de contratación.
- Prioridad actual: terminar piloto de actividades automáticas. GREEN focalizado55 aprobado; suite general preparada y todavía sin salida recibida. Luego concurrencia aislada, revisión y QA operativa antes de entrega. Inventario/Compras, KPIs e IA siguen como pendientes separados; sustitución comercial/tributaria de Defontana al final.

### Inventario: filtro de actividades GREEN315; navegador66 preparado (2026-10-30)
STAGING confirmó 315/315, sin cambios de configuración/existencias/PDFs; pruebas temporales retiradas y servicio activo. Intento 20261030-160430-943, respaldo f2Ugyc. Preparado `.tmp/staging-inventory-activity-process-browser-tests.ps1`: carga 3 controles del filtro Inventario más los 63 anteriores; falta ejecución real en navegador y revisión claro/oscuro. No hay cambios visuales nuevos ni activación real. Task4 sigue pendiente de navegador/restauración; Task5 conserva suite integral, concurrencia, QA aislado, revisión independiente y entrega. Producción sigue 19.0.25.5.0.

Inventario 2026-10-30: navegador66/66 aprobado por Codex, filtro revisado claro/oscuro y tema oscuro original restaurado. Evidencia process-browser-green66.png; respaldo de pruebas sZu3d5. Siguiente retirar pruebas con staging-inventory-activity-process-browser-restore.ps1; Task4 no cerrado hasta confirmarlo. Task5 integral/QA/revisión/entrega aún pendiente.

Inventario: retirada nativa HOOT confirmada (dos hashes OK, sZu3d5 restored=true, STAGING activo). Filtro listo: backend315/315 + navegador66/66 + temas. Preparada suite integral1120 por nombre (979 previos y141 nuevos); todavía NO ejecutada. Sigue staging-inventory-activity-regression.ps1 y después concurrencia/QA aislado/revisión final. Producción sin cambios.

Inventario 2026-10-30: suite completa1120/1120 confirmada, intento20261030-162819-515, respaldomFRLuB, pruebas restauradas/fuentes y snapshot intactos/STAGING activo. Preparada concurrencia6 nativa aislada con confirmación/repetición/validación/cancelación/parcial/restante; falta ejecutarla con staging-inventory-activity-concurrency.ps1. QA operativo/revisión independiente/entrega pendientes; producción sigue5.0 sin activación real.

Inventario 2026-10-30: concurrencia6 nativa aprobada, intento20261030-164035-599, copiafTWDqQ bloqueada, fuentes intactas/STAGING activo, cero huérfanas y plazos conservados. QA operativo aislado preparado (empresa propia, dos cuentas, 8 operaciones, política apagada3días laborables); aún NO creado. Ejecutar staging-inventory-activity-qa-users.ps1, luego QA/cierre/revisión independiente final/entrega. Producción no modificada.

### Prioridad: corregir cierre de TODOS los pendientes automáticos — 2026-11-02
Usuario aprobó «Abrir trabajo» y cierre solo por resultado real para Reparación/Fabricación/Aceptación/Calidad/Ingeniería/Inventario. Hecho manual de actividad no debe hacer desaparecer trabajo abierto. Actividades manuales generales y aprobaciones nativas no son los recordatorios propios. Retirada excepcional solo coordinación, motivo obligatorio, actor/fecha/historia y etiqueta distinta de trabajo terminado. Protección también servidor/RPC/archivo/borrado y paneles nativos, no solo Centro.
Diseño: docs/superpowers/specs/2026-11-02-automatic-activity-real-completion-design.md. Builder independiente completion_builder_check: sin dudas importantes ni contradicciones. Solo auditoría/diseño escritos; producto aún NO corregido. Consulta instalada preparada: staging-automatic-activity-completion-source.ps1 (READ ONLY, sin reinicio). Inventario sigue sin entrega a producción; versión de producción19.0.25.5.0. No recrear escenario QA wamR0o ni reescribir manual_done históricos.
QA Inventario confirmado por usuario: recepción normal completada con cierre automático; entrega cancelada ausente del Centro (aparición previa solo panel de orden); transferencia original apareció en Centro, parcial dejó una restante, completar restante retiró pendiente; comparación de fecha original del parcial pendiente lectura técnica. FUTURO previsto06-11-2026 16:46:49 vence11-11-2026 confirmado. Pausa y reactivación conservan FUTURO sin reconstruir PAUSA/retroactivos. Caso MANUAL se detuvo para corregir confusión Hecho; no afirmarlo aprobado. REPARTO/devolución/cierre QA pendientes.

Cierre real todos los flujos: consulta nativa de35 métodos y49 assets Mail confirmada READ ONLY. Preparado RED1180 (1120 anteriores+60 nuevos;42fallos esperados,1138verdes,0errores). Script staging-automatic-activity-completion-red.ps1. Producto aún intacto; no afirmar corregido ni usar1120 como prueba de nueva semántica. Diseño/plan2026-11-02 guardan alcance y adaptación explícita de pruebas manuales anteriores.

Cierre real todos los flujos: RED1180 confirmado (42fallos previstos/1138verdes/0errores), intento20261102-094833-883/respaldoBOQx1b/STAGING activo. Guard común implementado solo localmente en2archivos; GREEN104 preparado con60nuevos+44cierres/eventos reales. Ejecutar staging-automatic-activity-completion-green.ps1. Todavía no corregido en servidor ni terminado: faltan retiro excepcional, interfaz y adaptación explícita de contratos antiguos/manuales, suite integral, QA y revisión. Producción sin cambios.

Cierre real: protección común104/104 nativa y MRO confirmados, intento20261102-101504-439/respaldoKmXV9A, guard guardadoac7f620. Retirada excepcional preparada en RED176 (104previos+72nuevos,60fallos esperados/116verdes). Script staging-automatic-activity-withdrawal-red.ps1. No existe asistente nuevo todavía; no cambios adicionales de producto. Resultado previsto exception_withdrawn para preservar withdrawn anterior de Ingeniería/Inventario. Interfaz, adaptación contratos antiguos, suite integral, QA y revisión pendientes.

### Retirada excepcional: RED176 confirmado; GREEN preparado (2026-11-02)

RED nativo exacto176 confirmado (60 ausencias esperadas,116 verdes,0 errores), intento20261102-103532-002. Preparado el asistente de retirada con motivo, reconocimiento de trabajo abierto e historial para los seis flujos. Paquete GREEN176 revisado localmente, pendiente de SSH/STAGING; no se declara instalado ni terminado. Respalda y pausa la copia QA existente wamR0o antes del cambio de esquema, conservando su escenario para actualizarlo después. Producción intacta; interfaz, adaptación de contratos antiguos y verificación integral pendientes.

### Alcance confirmado: sin retirada ni botones redundantes (2026-11-02)

El usuario descartó la retirada excepcional y aprobó automáticas sin Hecho/Cancelar/Abrir redundante. Tarjeta/referencia abre la operación; el resultado real cierra el pendiente. Manuales/aprobaciones nativas intactas. Restaurados solo12paths locales propios del asistente nunca instalado; eliminados72 contratos del alcance sustituido. Instaladores antiguos de retirada bloqueados antes de SSH. Evidencia RED176 conservada como histórica, no requisito vigente.

Preparado RED158:54 contratos nuevos de presentación/identidad/store/navegación (42 ausencias esperadas y12 controles nativos), conserva104 comprobados. Descubrimiento local1234; selección exacta158. Producto STAGING sigue134/guard104 sin cambios; no se ejecutó GREEN de retirada ni se pausó QA. Pendiente SSH de presentación, luego indicador/interfaz y adaptación explícita de los contratos antiguos. Producción intacta.

### Presentación automática: RED158 confirmado y GREEN preparado (2026-11-02)

Intento nativo20261102-112101-823: exact158,42ausencias esperadas/116verdes/0errores. Incluye104anteriores+54nuevos; doce controles de apertura real sin cierre y ausencia de retirada incluso para administrador pasaron. Fuentes134 e historial/stock/permisos/config intactos, pruebas restauradas, backup31ylsE, STAGING activo.

Implementado localmente solo models/automatic_activity_completion.py: mc_automatic_pending readonly/no almacenado/sin compute sudo, identifica runs pendientes por vínculo, origen legible y empresa autorizada. Lectura sin bloqueos de cierre ni ACL privadas. Store nativo comprueba acceso actual e invalida caché de identidad antes de serializar. Conserva guard aprobado y prohíbe asistente/gateway/outcome excepcional. Preparado staging-automatic-activity-presentation-green.ps1 para158; pendiente ejecución SSH. Recupera preindicador134 en base nueva si falla, conserva guard y DBfallida. No modifica interfaz ni producción; QA aislado se conserva para actualización posterior.

### Presentación GREEN v1: corregido fixture nativo de temporales (2026-11-02)

Intento20261102-113412-631 exact158:0fallos/6errores, exclusivamente test_temporary_record_never_borrows_persistent_origin en los seis flujos. Stack nativo models.py:6454 espera origin.id; la prueba pasaba un entero. Los152otros casos pasaron. Recuperación verificada, STAGING activo; base fallida preservada odoo_staging_failed_auto_prs_AJXKxt, backupAJXKxt. No GREEN confirmado.

Corrección única de prueba: origin=activity.id → origin=activity. Mismos158 nombres/aserciones, producto byte por byte intacto respecto al intento. Conservados log/paquete/prueba v1; alias revisado en presentation-native-fixture-fix.json con hashes antes/después, excepción del constructor limitada a ese único cambio. Paquete actualizado native-new-origin-record-fixture158-v2; Black99/pylint10/replay158/clasificador7/AST/Bash/PS/hash gates pasan localmente. Pendiente nueva ejecución SSH; interfaz y producción sin cambios.

### Presentación nativa GREEN158 verificada (2026-11-02)

Intento20261102-114104-319:158exactos,0fallos/0errores; READ ONLY de store/MRO/sin retirada y hashes134 actuales verificados. Historial/permisos/stock/config intactos, pruebas restauradas, STAGING activo, backupc0pSgQ. Incluye corrección nativa origin=registro sin relajar comprobaciones; producto un archivo. Pendiente interfaz en todas las superficies, adaptación de contratos viejos, suite completa/concurrencia/QA/revisión final. Producción intacta.

### Vistas automáticas: RED170 preparado (2026-11-02)

Indicador/guard158 guardados en20723ab con todos los hooks. Nuevos12contratos sobre vistas combinadas con cuenta Taller: cinco cargas de identidad, cuatro condiciones sobre botones y controlador de lista que depende de selección; dos controles verdes conservan apertura nativa sin botón duplicado. Selección exacta170 (158 anteriores+12), esperan10fallos concretos/160verdes/0errores; descubrimiento local1246. No cambia producto todavía.

Paquete staging-automatic-activity-ui-red.ps1 también recoge fuentes instaladas de listas/calendario y ejemplos de pruebas Mail, solo lectura+rollback, para basar la integración en las firmas reales. Solo pruebas Python temporales; restablece sus archivos y reinicia STAGING, snapshot ampliado de historial/ACL sin exclusiones. Conserva copia QA y producción. Black99/pylint10, replay170, ocho verificaciones del clasificador, AST, Bash/PowerShell y hash gates locales aprobados. Pendiente SSH nativo; después código visual y HOOT de superficies.

### Interfaz: RED170 confirmado; navegador RED94 preparado (2026-11-02)

Intento nativo20261102-115407-635:10fallos de vista esperados/160verdes/0errores exact170. Producto134/historial/permisos/stock/config intactos, pruebas restauradas, STAGING activo, backupMbSnbU. Fuentes de listas/calendario/Mail obtenidas en solo lectura y rollback. Navegación nativa confirmada sin botón adicional.

Preparadas28pruebas HOOT nuevas en embedded_work.test.js, conservando los66anteriores byte a byte (work_center50+embedded16). Total94; esperan22fallos específicos y72verdes. Cubren selección manual/automática/mixta/dominio, modificadores de cabecera y menú Eliminar, chatter/popover/Hecho-y-siguiente/calendario y callbacks que no deben retirar automáticas. Se montan componentes nativos de Mail con su arranque de pruebas oficial; controles mantienen manuales y apertura anual. No hay código visual de producto escrito aún.

Cargador staging-automatic-activity-ui-browser-red.ps1 solo cambia dos archivos de pruebas, preserva respaldo original incluso en reintentos, verifica134fuentes y snapshot completo y reinicia STAGING. Restaurador preparado con coincidencia exacta de archivos instalados y recuperación idempotente; sin exigir ficticiamente GREEN para retirar pruebas. Se corrigió localmente la coincidencia de prefijos de respaldo antes de ejecutar. Node/AST/replay94/nombres únicos/Bash/PS/recibos y hashes actuales aprobados. Pendiente SSH y RED real en navegador. Túnel8070 confirmado por usuario; copia QA y producción intactas.

### RED94 real confirmado; interfaz GREEN170 preparada (2026-11-02)

En Edge, host127.0.0.1:8070 y suite conocida id=f92f0bf0:94completadas/72verdes/22fallos previstos, sin errores de preparación. Primer/último fallo2026-11-02T18:28:02.154Z/.909Z; DOM y mensajes de consola comparados por nombre exacto con la lista preparada. Los66anteriores y seis controles manuales/navegación pasaron. Recibo ui-browser-red-result.json y captura ui-browser-red-proof.jpg. Dos ejecuciones de búsqueda aproximada previas incluyeron otros módulos y se abortaron; no se usan como evidencia del producto. El identificador de suite evita esa ambigüedad.

Producto local5paths: vistas de actividad +manifest y3assets nuevos. Condiciones del indicador en kanban/lista/formulario/calendario; controlador derivado del nativo sin archivar limita cierres/Eliminar a selección manual visible. Contexto del modificador solo de presentación, no autorización RPC. Dominio con registros no cargados se trata de forma conservadora. Chatter/popover enlazan el resumen, calendario día/semana/mes enlaza referencia del cuerpo (incluido móvil); anual conserva su apertura nativa. Sin botón Abrir adicional ni asistente/retirada. Callbackguards impiden cierres/encadenado y el unlink manual espera RPC antes de retirar de pantalla. Store registra atributo reactivo; no se bloquea remove nativo de resultados reales.

Preparado staging-automatic-activity-ui-green.ps1: exige170nativos, conserva los94HOOT y su respaldo35ucjV, respaldo de BD/código y recuperación fresca preUI134 si falla. Antes de cambiar assets compartidos respalda y pausa solo QA wamR0o, bloquea conexiones y conserva límite previo/unidad/DB/historia/filestore original, sin recrear escenario. QA no se reinicia con registro viejo; se actualizará después. Código postUI137, sin activar destinatarios ni tocar producción.

Node, XML,12targets exactos de herencia cliente y9servidor contra fuentes instaladas, replay170,7mutaciones de clasificador, AST/Bash/PS/hashes y protección de HOOT94 aprobados localmente. Se corrigió antes de instalar el nombre del callback de borrado al nativo onDeleteSelectedRecords, obtenido de su fuente. GREEN170 nativo pendiente; después GREEN94 de navegador, contratos antiguos/suite completa/concurrencia/QA y revisión independiente. No producto marcado terminado ni cometido como aprobado todavía.


### 2026-11-02 — GREEN170 v1 recuperado; herencia de botones corregida
Intento 20261102-155600-770: 1 fallo/0 errores de 170, test_list_rows_hide_done_and_cancel_for_automatics. Recuperacion RC0, STAGING activo, QA wamR0o pausada con respaldo /var/tmp/mc-rov-auto-ui-green-I7KNxs/qa-database.dump. Causa reproducida localmente: cada XPath de herencia nativa modifica solo el primer nodo coincidente; separar action_done/unlink de fila y action_done/action_cancel de cabecera protege 2/2 y 2/2 frente a 1/2 y 1/2. Mismos 170 tests intactos. Paquete v2 regenerado: replay170, 7 controles del verificador, sintaxis Bash/PowerShell y diff-check verdes. Native GREEN y HOOT94 pendientes; sin cambios a produccion.


### 2026-11-02 — Interfaz nativa GREEN170 y navegador independiente GREEN94
Intento nativo 20261102-160229-020: 170/170 exactos, fuentes instaladas verificadas, configuraciones intactas, pruebas Python restauradas, STAGING activo. Respaldo /var/tmp/mc-rov-auto-ui-green-e32F75; QA wamR0o respaldada/pausada sin recreacion. Banner mostrado v1 desactualizado: se verifica contenido por hashes y coincide exactamente con XML corregido y resto de los cinco archivos (manifiesto normalizado a runtime2.0). HOOT en navegador integrado de Codex, sesion independiente de Edge: 94/94 en4s, sin errores/advertencias; recibo ui-browser-green-result.json y captura ui-browser-green-proof.jpg. Pasada Edge minimizada descartada por throttling; preferencia del usuario: usar exclusivamente navegador propio/integrado, nunca tocar Edge/pestanas personales. Se usa API tabs.get de IAB porque wrapper cua.getTab llama user no disponible. Falta retirar dos archivos HOOT temporales mediante restaurador registrado, adaptar expectativas antiguas de cierre manual con mapa explicito, suite completa, concurrencia, retomar mismo QA y revision independiente final. Ningun cambio de produccion.


### 2026-11-02 — Pruebas HOOT retiradas; regresion1246 preparada
Restaurador verificado: ambos archivos originales OK, AUTOMATIC_UI_BROWSER_TESTS_RESTORED=True, STAGING activo; QA propia continua pausada. Mapeo explicito35 contratos antiguos uno-a-uno en10 archivos, sin eliminar tests ni cambiar producto. Sustituye cierres manuales exitosos por UserError exacto (no acepta AccessError), pendiente/enlace/actor/plazo/historial/fuente intactos; mantiene controles de cambios de etapa, cierre real, parciales, pausas y reprogramacion atomica. Mapa revisionable docs/qa/automatic-activity-legacy-contract-map.json. Suite1246=1120 previos con35 reemplazos+126 nuevos. Paquete staging-automatic-activity-regression.ps1 preparado, NO ejecutado: replay1246 exactos,6 pruebas positivas/negativas del verificador, AST,Bash,PowerShell y gates locales verdes,137 fuentes exactas con47 alias de formato previamente auditados. Snapshot completo sin exclusiones ACL; protege archivos HOOT originales; exige QA DB bloqueada y servidor apagado. Black pasa11archivos; pylint solo reporta2 C8107 ya existentes en tests de rollback Repair/Manufacturing, pendientes de comprobacion respecto a baseline antes de commit. Sin produccion/cuentas reales. Siguiente: usuario ejecuta regresion1246 porSSH; diagnosticar evidencia del intento antes de cualquier reintento.


### 2026-11-02 — Diagnostico regresion1246 v1; correccion solo de pruebas v2
Intento 20261102-165431-119: descubrimiento1246 exacto,1238 pasan,8 fallan,0 errores. Snapshot/configuraciones/producto intactos, pruebas restauradas, STAGING activo; respaldo /var/tmp/mc-rov-automatic-completion-regression-PNflvT. Siete fallos comparaban message_ids antes de materializar tracking diferido de fixtures; el savepoint del rechazo vaciaba tracking previo. Se conserva la igualdad estricta del historial, pero se ejecuta env.flush_all + cr.precommit.run antes del snapshot, patron nativo ya usado en test_automation_control.test_pause_is_recorded_in_native_chatter. Octavo: Calidad esperaba que unlink capturara plazo editado; ahora unlink es rechazado, por tanto run conserva compromiso capturado y actividad su fecha editada; se agregan cierre real de alerta y aserciones business_done/plazo actualizado, sin quitar controles de fecha ni historial. Solo tests/automatic_completion_assertions.py y test_quality_activity_lifecycle.py modificados; los137 archivos de producto iguales. Mismos1246 casos/35 mapeos. V1 wire/prepared/logs conservados; v2 native-tracking-baseline-real-deadline-full1246-v2 regenerado/replay1246/6 verificadores/sintaxis Bash-PS/gates locales verdes. Black y pylint10/10 en los dos archivos corregidos. Native v2 NO ejecutado; QA continua pausada; sin produccion.


### 2026-11-02 — Suite completa1246 GREEN; revalidacion stock preparada
Intento 20261102-171010-454:1246/1246 exactos,0 fallos/errores; producto137/configuraciones intactos, pruebas temporales restauradas, STAGING activo; respaldo /var/tmp/mc-rov-automatic-completion-regression-Y5vAJB. Verificador independiente ejecutado contra log timestamped. Siguen pendientes carreras especificas cierre generico/cierre real/reprogramacion/rollback y QA copia existente/revision independiente final; NO declarar correccion integral terminada. Primero revalidar los seis eventos nativos de Inventario bajo guard/interfaz nuevos: paquete staging-automatic-activity-inventory-concurrency.ps1 desde este recibo1246 y137 hashes. Probador original sin modificaciones; checker8 controles positivos/negativos,AST,Bash,PowerShell y gates locales pasan; ejecucion nativa pendiente. Copia nueva sin cron/correo, conexiones bloqueadas al finalizar; no reinicia STAGING ni toca wamR0o/produccion.


### 2026-11-02 — Stock6 revalidado; cuatro carreras especificas listas
Concurrencia stock6 intento20261102-174030-725 PASSED: confirm/duplicate_confirm/validate/cancel/partial/remaining,0 huerfanas,plazos conservados,conexiones copia mc_rov_inventory_ci_p6pfaG bloqueadas,STAGING activo/producto intacto. Respaldo/work /var/tmp/mc-rov-inventory-concurrency-p6pfaG. Nuevo probador scripts/qa/automatic_activity_completion_concurrency.py conserva fixture/validacion nativos exactos mediante bundle de funciones fijado por hash, sin alterar modelos ni los seis casos anteriores. Cuatro carreras nuevas sobre Inventario para el guard compartido: generic_pair (dos conexiones del titular: feedback/cancel), generic_vs_real (titular frente a otro operador que valida), reprogram_vs_real (solo cuenta ficticia recibe coordinacion en copia), rollback_vs_real (cierre real revertido tras mutacion y otro iniciado; gana otro actor). Verifica run/ciclo unico, pendientes/actividades equivalentes,cero huerfanas,original inmutable,fecha final/ciclo coherente,autor real,estado y cantidades nativas. Caso generic_pair exige UserError exacto y conserva estado/cantidades; rollback exige resultado rolled_back, no acepta un supuesto cierre idempotente. Paquete staging-automatic-activity-completion-concurrency.ps1 listo desde1246+stock6; checker11 positivos/negativos,AST,Bash,PS/gates locales,Black/pylint10 pasan. NO ejecutado nativamente aun. Nueva copia sin cron/correo,exige wamR0o pausada,al terminar bloquea conexiones. No instala/reinicia ni toca produccion. Restan QA misma copia, auditoria historica/manual_done,revision independiente,integracion y entrega.


### 2026-11-03 — Cuatro carreras GREEN y reanudacion misma QA preparada
Recibo nativo20261102-175247-493 confirmado por verify-completion-races.py:4/4, dos cierres genericos bloqueados mantienen pending; cierre real prevalece ante feedback/reprogramacion; rollback explicito revertido seguido de cierre del otro actor,0 huerfanas,original preservado/fecha final coherente. Copia mc_rov_auto_close_ci_SLIXN2 bloqueada; producto/STAGING intactos. Se retoma preparacion que quedo entre turnos, sin repetir pruebas ya aprobadas ni usar Edge. Paquete staging-automatic-activity-qa-resume.ps1 listo (same-owned-copy-preserved-history-readonly-audit-v1), todavia NO ejecutado. Exclusivo mc_rov_inventory_qa_wamR0o/compania1157/cuentas11428-11429/unidadmc-rov-inventory-qa-wamR0o.service, sin reseed ni cambios de clave. Respalda BD antes de abrir conexiones; actualiza solo DB QA con cron/correo apagados y red solo localhost; compara snapshots completos de datos/historial,usuarios incluidos hashes de clave,empleados,grupos/empresas,stock/permisos/PDFmetadatos y bytes emitidos. Permite solo write_date de series como en baseline auditada anterior. Conserva scenario.json exacto y filestore original; no copia STAGING de nuevo. Verificacion READ ONLY prueba cinco vistas con ambos roles, indicador/origen autorizado,audita parcial/restante,MANUAL/REPARTO y manual_done historicos sin reapertura. Mantiene QA bloqueada/detenida si falla incluso en controles finales. Comparacion de PID/snapshot de STAGING y137 hashes; no toca produccion. AST,Bash,PS,gates locales y checker de alcance/payload/fallo pasan; falta ejecucion SSH y revision visual QA antes de revision independiente final/commits/integracion.


### 2026-11-03 — Misma QA reanudada; extractor local reparado sin repetir SSH
Intento20261103-094703-719 termino remoto RC0 (Exit status0 del logSSH comprobado),READY/VERIFY/PDF/usuarios-datos-historial/STAGING/producto intactos todosPASSED,work /var/tmp/mc-rov-automatic-qa-resume-qvuRix. Wrapper local v1 perdio backslashes de regexLOG/REPORT y no extraia JSON, por eso dio QA no confirmado0. Solo se corrige Pythonbuilder/PSlocal, se demuestra wire remoto byte-identico SHA antes/despues, y se revalida respuesta original sin nuevas conexiones ni otra actualizacion. qa-resume-result.json confirmado y audit/logs originales decodificados. Regresion real PowerShell14casos reproduce extractor roto y rechaza SSHerror/marcadores ausentes/informes con DB incorrecta/readonlyfalse/reapertura. Mismas cuentas/claves/operaciones/permisos y PDFs preservados. Auditoria parcial865/restante871,runs513-514, ambos current_deadline2026-11-04 (same_deadlineTrue). MANUAL868 sigue assigned con run516 manual_done archivado heredado, no se reabre; REPARTO869 draft sin run; FUTURO866 assigned/pendingactivo. Otro manual_done copiado de Calidad run461 alerta1484 requiere revision, no implica datos reales de produccion ni se altera. QAvisual pendiente. Usuario reconecto tunel8071; IABtab5 quedo paginaerror dataURI y politica no permite recargar ese contexto, se uso pestana nueva6 al destino autorizado localhost8071/web/login. Login disponible; usuario mcqa.inventory.taller prellenado, solicitar solo clave temporal en pagina/botonUsuario (noSuperusuario). Perfil QA localhost separado de sesionSTAGING127.0.0.1. Handler qaLoginTab id6, isolatedBrowser IAB; no tocar Edge ni pestanas personales. Captura qa-taller-login.jpg,tab marcadaHandoff; esperando usuario. No repetir instalador. Despues probar lectura FUTURO866 enCentro/chatter/lista/calendario sinHecho/Cancelar y crear pendiente confirmando REPARTO869 existente; completar por operacion real. Verificar recordatorio manual conserva acciones; luegoSupervisor/reparto/reprogramacion/temas y cierreQA/finalreview/commits.

### 2026-11-03 — QA Taller: cierre real y manuales comprobados; calendario movil pendiente
En IAB propio (sin Edge), misma copia wamR0o y cuenta mcqa.inventory.taller. FUTURO866 mantiene Preparado/pending, vencimiento11-11-2026. Kanban sin Hecho/Cancelar; lista con Reagendar; chatter automatico solo Editar y resumen/referencia que abre el origen. Se creo/completo recordatorio manual QA — recordatorio manual de control por flujo nativo (Listo/comentario), manteniendo recepcion866 pendiente y Preparado. Evidencia qa-manual-versus-automatic.jpg y qa-manual-completed-automatic-pending.jpg.
REPARTO869 se confirmo nativamente a las10:33:47: Preparado, una Gestionar recepcion paraTaller/vencimiento06-11-2026. Aparecio como segunda tarjeta; tarjeta abrio fuente869; Validar10:34:43 produjo Realizado y cierre business con autorTaller. Al regresarCentro solo quedo866 (1/1). Evidencia qa-real-reception-before.jpg, qa-real-reception-done.jpg, qa-real-reception-after-center.jpg. No cambios a STAGING/produccion/cuentas/permisos ni resiembra.
Calendario escritorio1280: cuadrice visible al crear pestaña nueva; popover automatico sin Hecho/Cancelar y referencia abrio866 sin cerrarla (qa-calendar-automatic-popover.jpg). La observacion anterior de escritorio vacio no se reproduce en nueva pestaña; no declararla defecto confirmado escritorio. En435x800 SI reproduce: widget/ActionSwiper altura0, renderer/wrapper0.8px, contenedor82.5px, controlador559.2px dentro wrapper560px. o_view_controller display:block y o_content sin altura definida, flex no aplica a sus hijos; investigar contrato de layout nativo antes de corregir. Captura qa-calendar-mobile-zero-height.jpg. Overrideviewport restaurado. Sin cambio de producto/test todavia; no aprobar QA calendario movil.
SesionTaller cerrada; IABtab7 deja login mcqa.inventory.supervisor prellenado, esperando clave privada del usuario. No restablecer claves ni usar superusuario. Faltan Supervisor/reprogramacion/reparto/temas, corregir calendario movil con prueba, cierreQA/revision independiente final/commits/integracion. Full1246/stock6/races4 previos siguen validos para producto actual, no repetir sin cambios.

### 2026-11-03 — Supervisor QA GREEN; calendario movil corregido localmente, instalador pendiente
Usuario inicio sesion Supervisor privadamente en IABtab7. AlcanceTrabajo del equipo/ProcesoInventario/lista: una automatica866 sinDone/Cancel. Reagendar nativo -> Mañana rechazo con UserError humano Use Repartir actividades e indique el motivo para reprogramar; vencimiento11-11 intacto. Escritorio1280 permite checkbox, seleccion automatica noofreceHecho/Cancelar/Eliminar, Acciones soloDuplicar/Repartir. WizardRepartir cambia cuentaTaller->Supervisor y fecha11->12nov con motivoQA; mantuvo mismo pendiente/empleadoTaller. Segundo wizard restituyo cuentaTaller/plazo11nov con motivo. Fuente866 siguePreparado; chatter registra autorSupervisor,ambas cuentas/fechas/motivos. Capturas qa-supervisor-reprogrammed.jpg y qa-supervisor-restored-audit.jpg. No completar/cancelar866.
Calendario movil: CSS nativo cargado se exporto por capacidadpageAssets a archivo temporal, sin fetch alternativo. Confirma ActionSwiper ya tieneheight100%; causa en host incrustado: controlador displayblock y main.o_content sin alto/resolucionflex. SCSSlocal agrega solo .mc_assignment_native > .o_calendar_view displayflex/column, hijo.o_content flex1/minheight0. ReproduccionRED real435x800 guardada antes; no nuevotest espejodelCSS ni cambiosbackend. NativeGREENvisual aunpendiente.
Paquete .tmp/staging-automatic-activity-calendar-layout.ps1 y Q/build-calendar-layout.py listos. Antes137hash exactos desde qa-resume; despues soloSCSS, hash02d6dfd7e19e4537a13f40e2442b73a52c85580d90485333146dfcaa29ab98fb. Respalda ambasBD y SCSS, pausa/reinicia odoo-staging y mismaunidadQA; no upgradeesquema/reseed/conexiones/permisos. Compara snapshot completoREADONLY offline en ambasBD, conserva2tests yscenarioexactos,4archivosprodSHA; falla->restaurasoloSCSS/reiniciaservicios. Bash/PowerShell/4ASTPython/gatesalcance/diffcheckPASS; REMOTE_EXECUTED=False. FaltaejecucionuserSSH, verificarcalendario435y1280/eventos/lista/kanban y temas. Overrideviewportreset, IABtab7HandoffconSupervisorautenticado. No repetir1246/races porCSSsinriesgonuevo; nueva revisionfinal independiente aunpendiente. Produccionintacta.

### 2026-11-03 — Preflight calendario reparado: bytes Windows frente a payload Linux
Primer intento local aborto antesSSH en hashSCSS. Causa: builderread_text normalizabaCRLF->LF y wrappercomparaba Get-FileHash bytesWindows con hashpayloadLinux. Se agrega local_source_sha256 de read_bytes; after conserva hashLF que verificara servidor. Misma hojaSCSS sin editar; wireSHAantes/despues identico, sin actividadremota. Guardrealextraido delwrapper probado con bytescorrectosPASS, hashLFincorrectoparaarchivoCRLFREJECT (reproduccion), hashcerosREJECT; sintaxisPSPASS. Builderregenerado y preflightlocalPASS. No quitarni relajarcontroldehashes; solo distinguir los dosartefactos. Usuario puede repetir staging-automatic-activity-calendar-layout.ps1; nativeGREENvisual pendiente.

### 2026-11-03 — Calendario intento110608 recuperoSCSS pero detuvoQA; arranque temporal corregido
Respuesta20261103-110608-726: baseline137/exact-single-file/snapshotambasBDPASSED; systemctlstartQA fallo Unitnotfound. TraprestauroSCSS original,STAGINGactive,QAinactive;backup /var/tmp/mc-rov-calendar-layout-eyX8nc, historial/BDsin cambios. Causa: unidad systemd-run transitoria se descargaal detenerse; wrappernuevo habiausadosystemctlstart asumiendo persistencia. Errornuestro, no cambiodatos. Wire/preparedfallidos preservados con sufijo-failed-20261103-110608-726.
Recuperacionv2 preparada en mismo staging-automatic-activity-calendar-layout.ps1. SiQAesta inactiva, exige backupdump previo,hashSCSSoriginal,prod/test/scenarioSHAprevios,QA snapshotbefore=after=actualREADONLY y8071libre; no aceptacopiaajena/modificada. Helperstart-owned-qa-calendar.sh derivado delqa-resume nativoyaaprobado: validapropiedades siunidadexiste, siunidadseperdio systemd-run con mismaDB/unit/usuarioodoo/config,loopback8071,cron0,nodatabaselist,IPAddressDenyany/Allowlocalhost/MemoryMax1200M. No cambia claves/cuentas/BD/conexionlimite ni debilita aislamiento. Usado tambientraprecuperacionarchivo; sin modulo-upgrade. Cinco regresiones Bashconcomandosmock (sinservidor) reproducenmissingunit y pruebanrecrear/reusarcargada/rechazarredampliada/falloarranque/puertoocupado. Bash/PS/5ASTPython/hashwire/scopePASS. PendienteejecucionSSHuser yGREENvisual; nocontarintentoanteriorcomoinstalado. QAseencuentradetenidahastarecuperacion;produccionintacta.

### 2026-11-03 — Calendario movil/temas GREEN; review independiente y ultimo ajuste de resize
Nativev2 intento20261103-111612-291: previouscopy/baseline137/exactsinglefile/snapshotambasBDPASSED, STAGINGyQAactive, backup /var/tmp/mc-rov-calendar-layout-krDmoy. Reciboprepared/wire preservados calendar-layout-installed-v2.*. UI en IABnuevo8 (handlerqaWorkTab) misma sesionSupervisor:435x800 widget419.3px (antes0),event14420 abre modal con referencia866 yfecha11nov,sinDone/Cancel; desktop1280x900 freshCalendar522.4px/eventopens. Claro yOscuro ambosvalidos, capturas qa-calendar-mobile-green.jpg,qa-calendar-desktop-green.jpg,qa-calendar-desktop-light.jpg,qa-calendar-mobile-light.jpg. TemaSupervisor originalSistema restaurado yviewportreset. QAdatos operativos conservados.
HallazgoP2enresizeenmismaCalendar: mobile->desktop conservaActionSwiper, regladealtura nativaesmobile-only, wrappers0 aunque renderer522.4. Remontarvista funcionaba pero no basta. Revisionindependiente automatic_completion_final_review contra mergebase6b08308 incluyendoWIPconfirmoP2, sinotros hallazgosproducto/seguridad/negocio. Fixlocal4lineasSCSSscope mc_assignment_native.o_calendar_renderer da100% a3wrappers entodosanchos; reviewerloaprobocomo minimo. FaltaGREENnativo resize435->1280->435 manteniendomismavista/event. Scriptmismo nombre ahora reviewed-live-mobile-desktop-resize-v3 usa baseline137exacto delrecibov2instalado, exigeQAactive, nofallbackbackupeyXobsoleto; helpertransientunit probado5casos y utilizado rollback. Bash/PS/preflightlocal/hashPASS;v3NOejecutado. No repetirSuite1246/racesporCSSsolo salvo nueva evidencia. DosC8107baselinetests verificarp antesclaimsCIclean. Faltan nativevisualv3, cierreQAconhistorial, hooks/commits/integracion. Produccionno tocada.

### 2026-11-03 — QA visual final aprobado e integracion local limpia; cerrar copia pendiente
CalendarioV3 nativo intento20261103-112505-085 PASSED: baseline/exactsinglefile/businessdataunchanged,STAGINGyQAactivos,backup /var/tmp/mc-rov-calendar-layout-4MKCOH. IABtab9/sessionSupervisor: mismavistaCalendar435x800->1280x900->435x800 sinremontar; widget419.3->522.4->419.3px,un evento14420 enlostres. Eventoabreenescritorioymovil con866/Taller/vencimiento11nov/sinDoneCancel. qa-calendar-resize-proof.json y qa-calendar-resize-final.jpg. P2reviewindependiente cerrado conprueba real; nootros hallazgosproducto. TemaSistema yviewportreset. CierreTallerreal869/manualreminder y repartoSupervisor/reprogramacion/restauracion866 yaaprobados, sin repetir.
Integracionprecommit sobre todoslosarchivosWIP PASSED (whitespace/EOF/XML/largefiles/conflicts/case/pylint_odoo/Black). ConfirmadosdosC8107enHEADpreexistente: testsrepair/manufacturing tenianValidationErrorQA literal; ahora _() sin cambiar tipodeerror niaserciones/casos. ScriptQAraces comenta unknown-option-value comoprobadorstockexistente paracompatibilidad entrepylints; sinlogicachanges. EOFmapjson corregido; mismos35mapeos y1246casos, noseborra ninguntest. Full1246/HOOT94/stock6/races4nativosprevios se conservan; desdeellos solocambiosproductoCSSvalidadosvisualmente, traduccionliteralQA/comentariolint/EOFtestsinsemanticanueva. No seafirma suitesremotasejecutadasdenuevo sobrebytesdistintos deesosartefactostest.
Falta cerrar mismaQA sinborrarhistorial con .tmp/staging-inventory-activity-qa-close.ps1 (registroconfirmadoworkwamR0o/dbmc_rov_inventory_qa_wamR0o),detenerunidad ybloquearconexiones. Despuesprepararversion/PR/CI/entrega; no merge ni produccionactualizadospor esta correccion. Noactivarpoliticasreales.
