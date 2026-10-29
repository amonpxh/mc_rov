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
