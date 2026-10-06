# Trabajo pendiente

> Actualizar esta sección al cerrar cada sesión de trabajo.

**Aviso de cierre desplegado — 2026-10-06.** Implementado y validado en STAGING y producción:
franja ámbar nativa antes de las pestañas, sin enlaces ni botones. Anticipa únicamente
Tipo de intervención vacío, trabajos sin Origen y acciones que consumen repuestos
sin movimientos registrados en la orden. No añade requisitos ni certifica que los
repuestos estén completos; conserva los validadores actuales. Se oculta en órdenes
terminadas/canceladas y cuando no hay carencias comprobables. Respeta permisos sin sudo.

- Piloto Guía + chatter descartado y retirado, incluidas sus pruebas y assets:
  duplicaba las pestañas sin orientar claramente el siguiente trabajo.
- Se conservan la auditoría de procesos y el diseño en `docs/designs/flujo-guiado.md`.
  La navegación entre procesos y el futuro centro de trabajo siguen pendientes.
- Seis pruebas nuevas del aviso: RED confirmado; suite completa GREEN en STAGING,
  **349 pruebas, cero fallos y errores**. Separación título/texto verificada con
  seis pruebas y QA visual. Chatter nativo, validadores y fuentes PDF intactos.
- Corregida una prueba de Calidad que confundía etiquetas iniciales del catálogo
  con etiquetas editables de la base. Se comprueba la semilla sin modificar datos.
- PR #90 fusionado: commit funcional `1b3d7dd`, merge `d6e6e5c`. Lint y 349 pruebas
  sin fallos/errores en CI del PR y de main. Producción en `19.0.23.8.0`.
- Respaldo `/var/backups/mc-rov-prod-closing-notice-jy7lqh/odoo_prod.dump`:
  22.058.983 bytes. Upgrade terminado sin ERROR/CRITICAL; servicio activo, PID 1020875,
  reiniciado el 2026-10-06 a las 20:14:17 UTC. HTTP y checkout main limpio verificados.
- Verificación final PASSED sobre 13 órdenes reales: texto acorde a datos, aviso ausente
  en cerradas/canceladas, campo no almacenado sin sudo, chatter nativo y cero enlaces.
  Consulta con rollback; sin datos QA creados. Hashes de ambos QWeb PDF sin cambios.
- Incidencias del runner resueltas fuera del repo: cierre SSH inicial sin ejecución;
  PowerShell trató warnings nativos como error; comparación con tilde dañada por el pipe.
  El upgrade ya había terminado: se completó solo la verificación, sin reinstalar.
- Advertencias existentes de métodos compute compartidos en stock.lot (mc_ficha_*) y
  mc.rov.revision (software_difiere/software_diferencias), por store/compute_sudo mixtos:
  registrar para revisión técnica separada; no modificados durante este cierre.
- Evidencia en `.tmp/repair-guide-source` y `.tmp/prod-closing-notice` (fuera del repo).
  No repetir la suite completa sin cambios relevantes. No publicar archivos `.tmp`.

**Despliegue cerrado - 2026-10-05:** PR #88 fusionado en main como
`028af90f84074018e67308a2414f9a7d45b906b8`. CI: 343 pruebas, 0 fallos y 0 errores;
lint aprobado. Produccion actualizada a `19.0.23.7.0` desde ese commit, con respaldo
`/var/backups/mc-rov-prod-028af90-IoPH6H/odoo_prod.dump`. Upgrade sin ERROR/CRITICAL,
registro cargado y servicio reiniciado: PID 1000443, activo desde 14:53:09 UTC.
HTTP local verificado. Catalogo Electronica / Software separado; migracion de
Parametros ejecutada, 0 filas por reclasificar en Hallazgos y Trabajos.
Boton superior Imprimir ficha y seleccion FEN por tipo/equipo verificados.
PDF real REV/00023: Letter, 1 pagina, footer completo, sin texto fuera de pagina;
reserva hasta la caja de texto inferior 21,05 pt. FEN de QA transaccional:
Letter, 1 pagina, footer completo, sin texto fuera de pagina, reserva 15,94 pt.
Inspeccion visual de ambos sin clipping. FEN QA revertida; nombre explicito
QA-PROD-028af90 no consume correlativo. Sin alteraciones del diseno aprobado.
Evidencia local en `.tmp/prod-release-028af90/`: PDFs, PNGs, verification.json,
pdf-inspection.json y upgrade.log, excluidos de Git. Esta entrada cierra los
pendientes de commit/PR/merge/despliegue de las iteraciones anteriores.
La actualizacion documental posterior no requiere otro upgrade ni reinicio.
**Cierre de entrega - 2026-10-05:** QA manual aprobada: PDF FEN y acciones
Vista previa / Emitir ficha correctas. La secuencia FEN es global por documento y
se asigna al crear, incluso en borrador; no depende del numero de serie ROV.
Se cierra el diff en `fix/rev-letter-footer-y-acciones-rov`, incluyendo la separacion
Electronica/Software previamente probada. Hooks completos aprobados y 56 pruebas
focalizadas STAGING sin fallos. No se incluyen artefactos `.tmp`.
Siguiente etapa: PR contra main, suite completa CI, merge y despliegue controlado
con upgrade/reinicio de produccion. Produccion aun no actualizada en esta etapa.
Las entradas anteriores son evidencia historica; esta aprobacion resuelve el QA
manual pendiente y la preferencia de borradores para vista previa.
**Vista previa FEN con borradores - 2026-10-05:** usuario aprobo permitir
borradores para vista previa y mantener bloqueo de emision final. Implementado
localmente: propuesta mas reciente por tipo/equipo entre borradores y confirmadas
aprobadas, sin aceptar reparaciones, otros equipos ni confirmadas rechazadas.
Dominios del wizard y de la ficha alineados, aviso de requisitos de emision en el
wizard. Boton superior Imprimir ficha. La regla action_emitir permanece intacta.
Ampliadas pruebas de propuesta reciente, dominios reales, guardado de borrador y
bloqueo final. Hooks/sintaxis/diff aprobados. STAGING instalado: 56 pruebas, 0 fallos
y 0 errores; servicio activo. Equipo 26-02 propone TRN/00003 (borrador), RND vacia
porque no existe; emision final bloqueada. PDF verificado: Letter 612 x 792 pt,
una pagina, sin texto fuera de pagina, footer completo y sin clipping visual.
QWeb FEN/REV mantiene ambos hashes. La fixture se revirtio con SAVEPOINT/rollback.
Evidencia en `.tmp/fen-draft-preview-qa/`: PDF, PNG, verification.json y tests.log.
El fallo anterior de revision automatica por creditos impidio la comprobacion del
02-10; se retomo y los checks locales pasaron. Sin commit ni produccion.
Tras QA final: revisar diff conjunto, commit/PR y despliegue controlado posterior.

**QA manual del selector FEN - 2026-10-02:** usuario aprobo color RND/TRN,
controles ocultos en no-ROV y flujo REV. Etiqueta superior Imprimir ficha cambiada
localmente junto con asercion de vista; hooks aprobados, no instalada aun.
Sonda READ ONLY confirmo dominios correctos por equipo/tipo/sin repair_id/confirmado
/aprobado. Equipo 26-02 (lot id 3) no tiene RND: solo TRN/00002 y TRN/00003, ambas
borrador sin resultado, mas REV/00004 de reparacion. Ninguna es elegible para emision.
En 0000008 se propone REV/00008 (id 8), una prueba real de rendimiento confirmada y
aprobada con prefijo historico; no se propone ninguna reparacion. La ultima aprobada
se elige por fecha desc, id desc. No hay dos fallos de filtrado: hay ambiguedad del
nombre historico y ausencia de pruebas elegibles. Pendiente preferencia del usuario
sobre permitir borradores en seleccion/vista previa, sin relajar emision final.
No se renumeraron pruebas ni se cambiaron reglas de negocio. Evidencia local:
`.tmp/fen-selector-diagnosis.json`. No modifica PDF ni produccion.

**Auditoria de evidencia FEN - 2026-10-02:** completada, sin cambios funcionales
ni visuales adicionales. REV/00014 es mc.rov.revision id 14, tipo rendimiento,
equipo id 5, sin repair_id, confirmado, rechazado y documento_emitido=True.
Clasificacion: fixture QA inadecuada + numero historico conservado por la migracion
19.0.19.0.0; no es una reparacion ni un fallback. El generador antiguo de paleta
filtraba por tipo/equipo/sin repair_id/documento emitido, sin exigir aprobacion.
El selector normal propone id 8 y excluye id 14 por resultado. El modelo FEN valida
el tipo/equipo/sin reparacion y la emision exige ambas pruebas aprobadas.
No se renumeraron revisiones historicas: una RND antigua puede conservar REV en su
nombre; la validacion funcional es por tipo, no por prefijo textual.
Ampliadas pruebas de slots ausentes, rechazo de reparaciones en ambos slots y
exclusion de reparaciones de las propuestas. STAGING: 53 pruebas focalizadas,
0 fallos y 0 errores. Los tests remotos se restauraron y Odoo quedo activo.
Nueva fixture independiente con RND/TRN aprobadas: cinco PDFs FEN (ambas, RND
pendiente, TRN pendiente, ambas pendientes y equipo con REV pero sin RND), todos
Letter 612 x 792 pt, una pagina, footer completo, reserva 10,10 pt y sin texto
fuera de pagina. Texto extraido sin identificadores REV en las validaciones.
REV regression es identica pixel a pixel a REV antes. QWeb FEN/REV conserva sus
hashes; sin cambios de estilo/Python funcional. Fixtures revertidas por SAVEPOINT
y rollback. Evidencia en `.tmp/fen-evidence-qa/`: audit.json, PDFs, HTML, texto,
crops, pdf-verification.json y tests.log. Sustituye la muestra de paleta rechazada
como QA de evidencia; no reutilizar esa muestra antigua para validar aceptacion.
Sin commit ni produccion. Cambios anteriores de vista/geometria quedan intactos.

**REV/00023 y acciones ROV - 2026-10-02:** trabajo sin commit en
`fix/rev-letter-footer-y-acciones-rov`, basado en el commit de catalogo.
La captura real reproduce las dos paginas Letter del PDF adjunto. El diagnostico
controlado confirmo que `padding-bottom:8px` del cuerpo genera la pagina vacia;
quitarlo deja una pagina sin reducir Hallazgos/Observaciones.
Localmente se elimino ese padding, se igualaron las tarjetas superiores con reserva
minima para cinco sellos y se reutiliza un footer corporativo unico en FEN/REV.
Se ajusto la banda de firmas/footer de REV a la referencia FEN; pendiente medir los
renders finales. FEN conserva el resto de su composicion.
FEN tiene un unico boton de cabecera para imprimir la ficha de equipo nuevo, con
el selector existente; Rendimiento y Terreno tienen igual color. La cinta y campos
de baja quedan ocultos en no-ROV, ademas de las pestanas ya protegidas.
STAGING instalado y validado: 53 pruebas, 0 fallos y 0 errores; servicio activo.
PDFs REV full, FEN antes/despues y replay de la captura real REV/00023 con cinco/cuatro
sellos: todos Letter 612 x 792 pt, una pagina, sin texto fuera de pagina. REV/00023
no existe en STAGING: el replay usa su captura real con el QWeb instalado.
Tarjetas superiores: 103,73 pt en ambos lados y ambos casos. Footer REV/00023 y FEN
con baseline 780,27 pt, reserva 10,10 pt; REV full baseline 780,85 pt, reserva 9,52 pt.
Zona util de firma REV: 38,03 pt. FEN antes/despues identico pixel a pixel.
REV full: 8 hallazgos, 7 visibles y resumen de uno adicional; observaciones y nota
visibles. Fixtures revertidas por rollback. Evidencia en `.tmp/rev23-final-qa/`,
incluidos PDFs, crops superiores/inferiores, medidas y log de pruebas.
Sin commit, publicacion ni despliegue a produccion. Pendiente aprobacion visual.

**Separación Electrónica / Software — 2026-10-01:** implementación local en
`feature/separar-electronica-software`, versión `19.0.23.7.0`. Electrónica conserva
los subtipos físicos; Software / Configuración contiene Software de superficie,
Firmware y Parámetros / Configuración. El upgrade reclasifica los hallazgos y trabajos
del subtipo Parámetros que todavía usan Electrónica; sin subtipo permanecen en
Electrónica porque no se puede inferir su naturaleza. No se conserva una categoría
mixta histórica. Chequeos y diseño PDF permanecen intactos. Validación local del XML
y SQL de migración y hooks de pre-commit aprobados. STAGING instaló `19.0.23.7.0`:
20 pruebas, 0 fallos y 0 errores; catálogo verificado, sin hallazgos ni trabajos de
Parámetros todavía asociados a Electrónica; servicio activo. Evidencia recibida del
runner el 2026-10-01. Los avisos existentes de campos calculados quedaron fuera de alcance.
Pendientes publicación del commit, PR, merge y despliegue a producción.

**Cierre FEN/REV — 2026-10-01:** PR #87 se fusionó en `main` como
`1fad9963f4fbe7f064e7f44e3e2889e523c5c2fa`; checks de `pre-commit` y de la suite Odoo
pasaron. La versión `19.0.23.6.0` se actualizó en producción y `odoo` quedó activo.
Se verificaron el reporte FEN, su paperformat y la fuente Noto Sans; HTTP local respondió
correctamente. La última validación FEN de STAGING pasó 15 pruebas y generó PDFs Letter de
una página; sus datos auxiliares se revirtieron. Las entradas fechadas que siguen son
registros históricos; `.tmp` contiene evidencia local y no forma parte del PR.

**Radio y gap vertical de subcubos Chequeos FEN - 2026-10-01:** radio de 2 pt y `border-spacing:4pt 2.75pt` (horizontal sigue en 4 pt; gap vertical sube 0,75 pt). Padding, tipografia, contenido, anchos, REV y geometria general no cambiaron. TDD RED se confirmo; `TestFichaEquipoNuevo` paso: 15 pruebas, 0 fallos y 0 errores. Los PDFs FEN con contenido y pendiente son Letter de una pagina (612 x 792 pt); los fixtures se revirtieron y Odoo quedo activo. Los crops RND/TRN antes/despues y las paginas completas se revisaron; el pie y las firmas siguen intactos. QWeb REV mantuvo el mismo hash. Evidencia final en `.tmp/report-final-qa-rounding/`; los artefactos QA anteriores se conservaron. Sin commit ni despliegue a produccion.

**Microajuste de gaps en Chequeos FEN — 2026-10-01:** la grilla de subcubos
blancos usa `border-spacing:4pt 2pt`; padding, columnas, contenidos, semántica y QWeb
REV permanecen intactos. La aserción TDD falló primero contra el QWeb anterior; en STAGING
pasaron las 15 pruebas FEN. Las muestras completa y pendiente son Letter (612 × 792 pt),
una página, con footer y firmas visibles; se revisaron los crops de Chequeos antes/después
y el espacio entre subcubos es visible sin contornos. La observación de QA conserva sus
acentos. Las fixtures se revirtieron, Odoo quedó activo y el hash de `ficha_report.xml`
REV permaneció idéntico. PDFs y evidencia en `.tmp/report-final-qa`. Sin commit, merge
ni despliegue a producción.

**Cierre de paleta, Chequeos y supercubos FEN — 2026-09-30:** se eligió B
(`#9FB4C3`) para FEN y REV; A queda descartada. REV mantiene sus subcubos de
Chequeos blancos y sin borde. FEN usa un marco redondeado con recorte real y gutter
de 2,5 pt alrededor de RND/TRN; columnas, altura interna y barras semánticas
permanecen iguales. Las pruebas cubren la paleta, los marcos y columnas, y evitan
sustituir una RND faltante por una reparación.

El `REV/00014` del PDF QA correspondía a una RND histórica cuyo número conservó el
prefijo anterior al cambio de secuencias; no hubo fallback a una revisión de
reparación. STAGING instaló la paleta B y pasó 50 pruebas. Los PDFs FEN con contenido,
FEN pendiente (`FEN/QA-PEND`) y REV real son Letter de una página; se revisaron en
color y escala de grises, incluidos los bloques de Chequeos. El badge de la muestra
pendiente ahora cabe completo. Las fixtures se revirtieron y Odoo quedó activo. Los
artefactos están en `.tmp/report-final-qa`. Sin commit, merge ni despliegue a
producción.

**Estados vacíos de Hallazgos/Observaciones REV y Observaciones FEN — 2026-09-30:**
se agregaron placeholders discretos solo cuando el bloque está vacío; una nota ámbar
suprime el placeholder de Observaciones. Las tarjetas REV conservan su estructura y la
prueba compara su geometría sin contenido contra el cierre completo. En STAGING pasaron
47 pruebas; los cuatro escenarios REV y los dos FEN se generaron en Letter de una página
(612 × 792 pt), con todos los fixtures revertidos y el servicio activo. Los PDFs están en
`.tmp/empty-copy-final/`. La inspección raster no estuvo disponible en este entorno; los
PDFs quedan para revisión visual manual. Sin commit.

**Geometría final compartida FEN/REV — 2026-09-29:** el header azul redondeado quedó
en 60,51 pt, con márgenes de 5,76 pt arriba, 5,19 pt laterales y 5,19 pt hasta metadata.
REV ganó interlineado y separación en las descripciones de Chequeos sin alterar la grilla
de tres columnas. Se ajustó el flujo del cierre para alinear firmas y footer con FEN y se
redujo el padding inferior del contenedor para evitar una página vacía. En STAGING pasaron
45 pruebas; servicio activo y fixtures revertidas. FEN real y REV vacío/full/solo Hallazgos/
solo Observaciones son Letter de una página, sin texto fuera de página y con pie completo.
Límites: tarjetas Hallazgos/Observaciones FEN 697,29 pt y REV 698,44–699,02 pt; líneas de
firma REV 739,93–741,08 pt frente a FEN 742,24 pt; footer REV 767,59–768,17 pt frente a
FEN 770,47 pt; margen inferior 9,52–10,10 pt. PDFs y crops están en
`.tmp/rev-geometry-final/`; métricas en `qa/metrics.json`. Sin producción ni commit.

**Ajuste compartido de metadata FEN/REV — 2026-09-29:** aumentó la legibilidad de
las etiquetas y valores normales en la fila de identificación, manteniendo intactas
la geometría y las tarjetas del encabezado. Solo los valores que superan umbrales
deterministas por campo reciben la clase compacta; las etiquetas nunca se compactan y
los valores extensos envuelven naturalmente. FEN y REV usan el mismo componente y
umbrales. `TestReporteFicha` y `TestFichaEquipoNuevo` pasaron en STAGING: 43 pruebas,
0 fallos y 0 errores. Los PDFs reales FEN/REV y el FEN de estrés son Letter de una
página, sin contenido fuera de página; el estrés muestra cliente y responsable en dos
líneas, sin clipping. El servicio quedó activo. PDFs y recortes están en
`.tmp/header-metadata-a5/`.

**Padding de metadata compartido FEN/REV — 2026-09-29:** las celdas usan padding
efectivo `6.45pt 6.8pt 3.8pt` (arriba, laterales y abajo), aplicado con un selector
que supera el reset previo de celdas de tabla. El render confirmó el inset visual real;
etiquetas y tamaños tipográficos permanecen sin cambios. En STAGING pasaron 43 pruebas.
Los PDFs reales de REV y FEN, más el estrés FEN con Cliente y Responsable envueltos en
dos líneas, son Letter de una página, sin texto fuera de página y con el footer completo.
El servicio quedó activo. PDFs, HTML y recortes están en
`.tmp/header-metadata-padding-final/`.

**Altura mínima de metadata compartida FEN/REV — 2026-09-29:** la fila normal pasó de
27,08 pt a 30,54 pt, igualando la altura previa de la fila FEN de estrés. Las cinco
celdas se expanden como una unidad mediante la altura mínima de la tabla; si el contenido
requiere más espacio, la fila puede crecer. Se conservan padding, alineación y tamaños:
labels 5,763 pt, values normales 7,492 pt y values compactos de estrés 6,339 pt. La
suite focalizada de STAGING pasó: 43 pruebas, 0 fallos y 0 errores; el servicio quedó
activo y los datos de estrés se revirtieron por `SAVEPOINT`. Los PDFs reales FEN/REV y
el FEN de estrés son Letter de una página, con footer completo y sin texto fuera de
página. PDFs, HTML y recortes están en `.tmp/header-metadata-height-final/`.

**Tarjetas REV para escritura manual — 2026-09-29:** `HALLAZGOS` y
`OBSERVACIONES` ahora permanecen como dos tarjetas de media anchura en toda ficha de
reparación, incluso cuando no hay contenido, para permitir completar la copia impresa a
mano. Hallazgos conserva el límite/resumen adaptativo y el contenido de Observaciones y
la nota ámbar siguen siendo condicionales; no se generan placeholders ni una nota vacía.
La tarjeta de Observaciones mantiene su sizer para acompañar la altura de Hallazgos sin
fijarla ni recortar texto. `TestReporteFicha` pasó en STAGING: 31 pruebas, 0 fallos y
0 errores; `odoo-staging` quedó activo. Los renders de `REV/00022` vacío, ambos bloques
rellenos, solo Hallazgos y solo Observaciones son Letter de una página, con las dos
tarjetas, pie completo y sin texto fuera de página. En los casos esperados aparecen el
resumen adaptativo y la nota ámbar. La regresión de FEN es idéntica píxel por píxel a la
referencia congelada. Todas las líneas QA se revirtieron mediante rollback. PDFs,
recortes y métricas están en `.tmp/rev-always-cards-final/`. La suite amplia de 325
pruebas tuvo un fallo en `TestRazonesDeCalidad.test_las_etiquetas_dicen_lo_mismo_en_las_dos_listas`
(clasificación C: expectativa de test desactualizada para el catálogo editable). Compara
`ORIGENES` con `quality.reason.name`: esperaba `No determinado` y leyó `No determinado odo*`.
Los otros cinco nombres coinciden. El rename está documentado desde 2026-08-25 y el catálogo
XML está bajo `noupdate="1"` intencionalmente; un upgrade no debe pisar personalizaciones.
El mismo fallo aparece en el log de la suite del 2026-09-10, antes de la normalización
FEN/REV; los archivos de `ORIGENES`, datos XML y `test_calidad.py` no están modificados en
esta rama. No se cambió el catálogo ni el test. Recomendación: separar la prueba de las
etiquetas iniciales del catálogo de una base STAGING con valores personalizados. El respaldo de STAGING quedó en
`/var/tmp/mc-rov-rev-always-cards-backup-20260929-121204`. Cambios locales y STAGING;
sin despliegue a producción ni commit.

**Normalización visual REV/FEN — 2026-09-28:** en la rama
`feature/ficha-equipo-nuevo-v49` se alinearon el logo recortado, la cabecera y los roles
tipográficos de REV con FEN, sin modificar el QWeb de FEN ni la lógica de revisión. REV
ya no imprime la marca BORRADOR; los Chequeos conservan descripción conforme neutra,
conteo conforme verde y solo el ítem no conforme en rojo. STAGING recibió estos cambios
y `TestReporteFicha` pasó con 30 pruebas, 0 fallos y 0 errores; el servicio quedó activo.
Los PDFs nuevos de Odoo son Letter de una página, sin texto fuera de página. La fixture
FEN normalizada es idéntica píxel por píxel al FEN congelado. El PDF real de `REV/00022`
conserva el mismo contenido funcional que el anterior, salvo BORRADOR; esa revisión tiene
0 hallazgos y carece de observaciones y diferencias, por lo que no muestra esas tarjetas.
Una muestra REV transaccional verificó ambas tarjetas, el resumen adaptativo y la nota
ámbar en una página; sus datos se revirtieron. PDFs y recortes están en
`.tmp/rev-normalization-final/`. Corte hist?rico, luego aprobado: aprobación visual, commit/PR; producción no
recibió esta normalización.

**Ficha de equipo nuevo — registro histórico del 2026-09-25:** la rama `feature/ficha-equipo-nuevo-v49`
(PR #87, entonces en borrador) contiene el modelo FEN persistente, el asistente que selecciona RND/TRN,
el PDF Letter y sus pruebas. La referencia visual vigente es exclusivamente
`D4.147A_baseline_amber_E5B54B.html` (V49.34). STAGING tiene la última variante QWeb
para revisión visual; producción aún no recibe la ficha nueva.
La suite focalizada pasó en STAGING. Se generaron cinco PDFs con datos temporales
revertidos: real, rechazado, chequeos extensos, nombres largos y datos técnicos largos.
Los cinco son de una página Letter, con pie completo; el rechazado conserva BORRADOR.
Los chequeos extensos usan resumen por grupo y muestran las excepciones, manteniendo el
detalle completo en las revisiones de Odoo. El commit `b6dd294` pasó pre-commit y CI
(320 pruebas, 0 fallos, 0 errores). En ese corte faltaba aprobación visual del PDF real antes de
integrar el PR.

**QA visual V49.34 — registro histórico del 25-09-2026:** el 25-09-2026 se renderizó el HTML final
en Edge y se comparó a 96 DPI con un PDF auténtico de Odoo y una fixture transaccional.
La corrección local e instalada en STAGING recupera las posiciones de Configuración,
Validaciones, Observaciones, firmas y pie. Ambos FEN son Letter de una página, sin texto
fuera de ella; el pie empieza a 768,1 pt frente a 767,8 pt del HTML. La fuente
NotoSans-SemiBold figura realmente en el PDF, junto con DejaVu Sans, Mono y Serif. La
suite focalizada pasó: 35 pruebas, 0 fallos, 0 errores. Los datos de QA se revirtieron.
La fixture visual reproduce `Sonar` en rojo y `1 de 2` con badge ámbar solo mediante una
variante temporal de QWeb: el modelo real considera rechazado un chequeo `no_ok`, por lo
que esa combinación de la maqueta no se trasladó a la lógica funcional. El PDF real
conserva los rótulos reales de Odoo (`Inox`, `6 en el equipo`) y `2 de 2` en Accesorios.
Se conservaron la comparación de imágenes, los recortes y la lista de fuentes en `.tmp`.
En ese corte faltaba revisión visual del usuario, commit/PR y despliegue de esta pasada; no se ha tocado
producción. El runbook incorpora la instalación de Noto en fontconfig antes del upgrade.

**Comparación visual actualizada — registro histórico del 2026-09-28:** se usó `D4.147A_baseline_amber_E5B54B.html` como golden y PDFs nuevos de Odoo como resultado comparado. En STAGING se corrigió el inset horizontal propio del `article` FEN, se ajustó el alto/badge de cabecera, el ritmo interno de Configuración, los tamaños de Chequeos y Observaciones, y la cuadrícula de Chequeos a parejas dinámicas de igual altura. Las cuatro firmas ahora ocupan columnas iguales y el pie queda en una línea. Real y fixture siguen en una página Letter, con el pie completo y sin texto fuera de página; la fixture verifica `TRN/00008`, `Paulo Haller` y `1 de 2`. Los datos temporales se revirtieron. `TestFichaEquipoNuevo`: 8 pruebas, 0 fallos, 0 errores. La comparación directa queda en `.tmp/side_by_side.png` y sus recortes; aún se ve una diferencia de wrapping en Observaciones (tres líneas en el PDF y dos en el HTML) y las Validaciones ocupan unos puntos más de alto. Esta evaluación fue un corte intermedio y quedó superada por las revisiones posteriores.

**Impresión de ficha reparada — 2026-09-25:** el error `wkhtmltopdf -11` en producción
se reprodujo con la revisión de reparación ID 25 aplicando el límite de memoria de 1 GiB
del worker; la misma revisión generó un PDF válido con 2 GiB. Se respaldó
`/etc/odoo/odoo.conf`, se elevó únicamente `limit_memory_hard` a 2 GiB y se reinició
`odoo`; `limit_memory_soft` permaneció en 512 MiB. Los workers nuevos muestran el límite
de 2 GiB, el login HTTP responde 200 y el render de la revisión ID 25 volvió a pasar.

**Última ficha desde la orden — 2026-09-24:** PR #86 integró en `main` la propuesta
automática de la revisión de reparación más reciente de la orden, ordenada por fecha e ID.
El asistente permite escoger otra revisión de la misma orden. El botón «Imprimir ficha»
ahora tiene separación respecto de «Nueva revisión». TDD comprobó la selección y el margen;
CI de la rama y del merge pasó con 313 pruebas, 0 fallos y 0 errores. Producción recibió
`19.0.23.5.1` en `319015c`; `odoo` quedó activo. STAGING no se actualizó. Falta únicamente
comprobar el espaciado en una sesión de usuario.

**Ficha desde la orden — 2026-09-24:** PR #85 integró en `main` el botón «Imprimir ficha»
junto a «Nueva revisión» en la pestaña Revisiones. Abre el asistente actual: propone la
única revisión de reparación de la visita o exige elegir si hay varias; impide imprimir
desde ese selector una revisión de otra orden. La fase roja de TDD confirmó los dos casos
ausentes; la versión final pasó pre-commit y CI con 313 pruebas, 0 fallos y 0 errores.
Producción recibió `19.0.23.5.0` en `68455d0`; `odoo` quedó activo y la base confirmó
el vínculo del asistente con la orden. No se modificó el PDF ni se actualizó STAGING.
Queda pendiente únicamente la comprobación visual del botón con una sesión de usuario.

**Chequeo de salida del brazo — 2026-09-24:** en `a4fd897`, publicado en `main`, se agregó
al catálogo estándar el chequeo RND cuyo nombre visible se acorta en `19.0.23.4.1` a «Salida
de brazo funcionando correctamente» (nombre de ficha «Salida de brazo»), sección Prueba de
accesorios, solo para rendimiento. «Manipulador responde» sigue
siendo un control distinto sobre el accesorio montado. «No aplica» corresponde si el equipo
carece de salida de brazo, no simplemente si no tiene un brazo conectado durante la prueba.
Se actualizaron las pruebas de catálogo y generación de checklist. Los recuentos estándar
se comprueban contra el XML, porque el catálogo instalado puede estar personalizado.
Pre-commit pasó y CI confirmó 0 fallos y 0 errores en 311 pruebas para `c826622`.
Producción recibió el upgrade de `mc_rov` a `19.0.23.4.1`, se reinició `odoo` y la consulta
a `odoo_prod` confirmó el nuevo nombre operativo del registro, solo para RND; STAGING no se
actualizó en esta entrega. Las revisiones RND en borrador ya
existentes requieren «Actualizar checklist» para incorporar la nueva línea.

## Trabajo actual — 2026-09-10

**Prioridad acordada con Paulo:** primero funcionalidad. Traspaso del repositorio a la
empresa y reorganización administrativa al final. `interview-prep.md`,
`rov-pipeline-roadmap.md` y las plantillas del directorio padre son material histórico,
no el plan vigente. Las secciones fechadas de este backlog conservan discusiones anteriores;
no interpretar una propuesta antigua como una tarea aún pendiente sin contrastar el código.

**Rama:** `feature/fichas-pdf`, basada en `1a300ce` (PR #83, versión `19.0.23.0.4`).
Remoto configurado: `https://github.com/amonpxh/mc_rov.git`. Las notas del 27 de agosto
registran ese despliegue a producción, pero la consulta SSH del 10 de septiembre encontró
otra realidad: producción y staging siguen en `c450535`, versión instalada `19.0.23.0.3`.
Para el estado del servidor prevalece esa comprobación sobre las notas antiguas.

**Implementado localmente y transferido a staging, sin publicar:** primera implementación `19.0.23.1.0` del reporte
por revisión (`reports/ficha_report.xml`), botón «Imprimir ficha» en la cabecera de la
revisión y asistente con opciones de firmas, sellos, hallazgos y diferencias. El botón
se comprobó en el navegador con la revisión de terreno `TRN/00003`: abre el asistente con
la revisión seleccionada y la opción de firmas; la acción «Descargar PDF» se inició sin
confirmar ni modificar el registro. El diseño y límites están en
[revisión técnica, § 12.1](designs/revision-tecnica.md#121-el-reporte-no-es-el-adorno-final).
La maqueta recuperada está en `designs/referencias/ficha-impresa-rov.html` y contiene datos
de ejemplo, no resultados de una prueba Odoo.

**Verificado:** sintaxis Python/XML, archivos del manifiesto, referencias entre plantillas,
compilación de expresiones QWeb y exclusión de campos internos prohibidos. La maqueta HTML
abre en Edge sin errores JavaScript. Las **6 pruebas `TestReporteFicha` pasan en Odoo 19 Enterprise
en staging**, tras corregir la llamada posicional al renderizador y los `t-field` sobre
celdas de tabla. La suite completa termina con **3 fallos, 0 errores de 289 pruebas**:
dos recuentos de chequeos (17 frente a 18) y una etiqueta de causa de calidad.
Coinciden con las personalizaciones documentadas abajo (sonar y «No determinado odo*»);
sus archivos de código y catálogo no cambiaron en esta rama. No se restauraron datos
para forzar verde, ni se hizo todavía una ejecución comparativa del código anterior.
También se generaron e inspeccionaron visualmente cinco PDF reales con wkhtmltopdf:
reparación con 2 hallazgos cabe en 1 página; con 7 y 20 usa 2 páginas sin truncar ni partir
hallazgos; rendimiento y terreno caben en 1 página. Todos son papel carta. Los datos
temporales se revirtieron y el detalle interno del hallazgo no aparece en el texto extraído.

**Siguiente paso:** revisar el diff y preparar el commit de la rama. La fidelidad fina a la
variante C y la compatibilidad de edición mediante Studio quedan para después de asegurar
el flujo funcional. No refrescar ni borrar la base. Producción y traspaso a la empresa
quedan fuera de esta etapa.

**Ajuste de composición del reporte — 2026-09-16:** para la ficha de reparación en papel
carta, Hallazgos usa un límite adaptativo: máximo siete, con presupuesto visual de 7,60
unidades. Una primera línea pesa 1 y cada línea estimada adicional pesa 0,52; la estimación
usa el mayor wrapping entre componente/subtipo y descripción. Así, el catálogo real muestra
siete líneas y el caso de estrés de dos líneas muestra cinco, siempre seguido de «y N hallazgos
más · ver en el sistema». Todas las líneas se conservan en Odoo. La escala final es +4 % sobre
la composición vigente al iniciar esta pasada. Tras ampliar la zona funcional de firma, el
render real deja 37 pt de reserva y el de estrés 26,5 pt; ambos son una única página Letter,
con firmas y pie completos. Hallazgos y Observaciones comparten la altura exterior natural de
su fila; la nota de diferencias se ancla visualmente al fondo de Observaciones.
**Incidencia de PDF resuelta en staging:** staging confirma `mc_rov|installed|19.0.23.1.0`.
El primer PDF caía en `wkhtmltopdf` con código -11 durante la inicialización de QtWebKit.
Una página mínima funcionaba y el mismo reporte se generaba al quitar el límite de memoria:
la causa era `limit_memory_hard = 1073741824`, no la plantilla. Staging quedó en
`limit_memory_soft = 1610612736` y `limit_memory_hard = 2147483648`; con esos límites se
repitieron los cinco PDF correctamente sin overrides de línea de comandos.

**Ensayo ejecutado:** respaldo previo de código y base en `/var/tmp/mc-rov-fichas.dTlpaE`.
Las pruebas se ejecutaron en el puerto separado 8199; sus logs `report-tests-8199.log` y
`module-tests-8199.log` están dentro del respaldo. El proceso manual que ocupaba 8070 fue
validado como staging y detenido de forma normal. `odoo-staging.service` quedó activo con
PID 621320, configuración `/etc/odoo/odoo-staging.conf` y respuesta HTTP en localhost:8070.
El código local y el de staging contienen las correcciones finales del reporte.

**Acceso identificado:** servidor `64.176.17.240`, usuario `root`; Paulo se autentica por
contraseña desde VS Code. El intento no interactivo fue rechazado y luego se completó
una consulta interactiva de solo lectura. Staging está verificado
como `odoo_staging`, `/opt/odoo/staging-addons/mc_rov`, configuración
`/etc/odoo/odoo-staging.conf`, puerto 8070, escuchando solo en `127.0.0.1`. Tiene marcador
`mc_rov.entorno=STAGING`, Studio instalado y checkout en `rehearsal` con los cambios locales
transferidos. Su servicio está activo; producción permanece en otro servicio, base y carpeta. El servidor
dispone de `wkhtmltopdf 0.12.6`. El CI documentado hace checkout en el addons path de producción:
no usar un PR para ensayar sin revisar esa configuración. Procedimientos en
[staging](runbooks/staging.md) y [testing](runbooks/testing.md).

**Continuidad:** se recuperó del código y de `../.remember/today-2026-08-27.done.md`,
`../.remember/today-2026-08-28.md` y `../.remember/now.md`, no de una lectura completa
de «Implementar bloque B de fabricación con quality.alert». `AGENTS.md` remite a las
reglas compartidas de `CLAUDE.md`; este archivo centraliza estado y siguiente paso.

### Verificar después del próximo deploy

**Tres cosas, y las tres prueban lo mismo: que los catálogos son del usuario y el módulo no
se los pisa.** Si alguna vuelve a su valor original después de un despliegue, el `noupdate`
de ese catálogo no está protegiendo y hay que perseguirlo — con él se pierde en silencio
cualquier ajuste que el taller haga desde la pantalla.

1. **«Sonar funciona» tiene «Aplica a rendimiento» apagado a mano** *(2026-08-24)*, desde
   Configuración → Catálogos ROV → Pasos de testeo ROV. No es un ajuste que el taller pidiera:
   está puesto a propósito para comprobar el `noupdate` que entró en `19.0.20.0.0`.
2. **La causa «No determinado» está renombrada a «No determinado odo\*»** *(2026-08-25)*, desde
   Calidad → Configuración → Causas. Comprueba el `noupdate` de `19.0.22.2.0`.
3. **Las cuatro causas de Odoo quedan archivadas** por la migración de `19.0.23.0.0`. Acá lo
   que hay que mirar es lo contrario: que **no vuelvan a aparecer** activas.

## Diseño abierto, salido de mirar las pantallas el 2026-08-17

Todo esto quedó discutido y **sin decidir**. El hilo está en el historial de esa sesión; lo que
sigue es lo que hay que resolver antes de escribir código.

- [ ] **Las pruebas de fabricación y de terreno ya existen en `stock.lot`, y la revisión las
  duplica.** El número de serie guarda los resultados de las dos: laboratorio
  (`mc_prueba_leak`, `mc_ancho_banda`, `mc_subida`, `mc_bajada`, las dos temperaturas `_lab`,
  `mc_tiempo_prueba_lab`, `mc_esfuerzo`, `mc_en_reposo`, `mc_consumo_corriente`,
  `mc_limitacion_pilot_gain`, `mc_ganancia_luz`) y terreno (`mc_fecha_prueba`, `mc_lugar`,
  `mc_profundidad`, `mc_velocidad_corriente`, `mc_alimentacion`, `mc_tiempo_prueba_terreno`,
  las dos temperaturas `_terreno`, `mc_observacion`). La revisión con `tipo` en `fabricacion`
  o `terreno` registra lo mismo, y está vacía porque nadie la usa.

  **En el lote, una prueba es un valor único: correrla dos veces pisa la anterior.** El campo
  se llama `mc_fecha_prueba` —tiene fecha, o sea que se entendió que era un evento— pero solo
  hay espacio para uno.

  Esto contradice el § 1.1 del diseño de la revisión, que descartó mover esos campos diciendo
  que eran «la ficha técnica de fabricación». **Esa corrección metió en la misma bolsa dos
  cosas**: chasis, motores, pesos y medidas del umbilical sí son ficha (*cómo es* el equipo);
  prueba de leak, ancho de banda, temperaturas, lugar y profundidad son resultados de un
  evento.

  **Posición de Paulo (2026-08-17):** los puso en el lote porque la fabricación se identifica
  por número de serie, y **no quiere mezclarlas con las revisiones de reparación** — una
  prueba de fabricación no es una revisión: no lleva sellos ni hallazgos, y los campos no son
  los mismos. Tampoco se hacen varias pruebas por equipo, **salvo en un diseño nuevo o un
  rediseño**, y ahí el enfoque es de troubleshooting.

  Entonces la pregunta no es «¿mover o no mover?» sino **qué modelo describe una prueba de
  fabricación**, que probablemente no sea ni el lote ni la revisión actual.

- [ ] **Las lecciones aprendidas de fabricación no se guardan en ninguna parte**, y esto es lo
  más valioso que salió de esa conversación. Hoy se hacen fabricaciones y modificaciones de
  fabricación **a partir de errores y problemas detectados al armar equipos**, y ese
  aprendizaje se pierde. Es el mismo hueco que el diagnóstico de fallas cerró del lado de la
  reparación, sin cerrar del lado de la manufactura.

### Lo que sí quedó decidido el 2026-08-17 sobre fabricación

Los tres puntos de arriba **no se diseñan por separado**: son un sistema. Decidido en
conversación, todavía sin spec.

1. **La lección es del modelo, no de la unidad.** Palabras de Paulo: *«la lección debería ser
   del modelo, actualmente se queda solo en la unidad — ese es el problema»*. Eso parte el
   diseño en dos niveles: la prueba es de un número de serie, la lección es de un
   `product.template` y aplica a todo lo que se fabrique de ahí en adelante. Promover un
   hallazgo a lección es un **acto deliberado**, no automático: «a este ROV se le filtró el
   E-pod» y «cambiamos cómo se sellan todos los MC-300» no son la misma afirmación.

2. **La lección ya tiene una segunda fuente, viva en producción hoy.** Una línea de trabajo
   con `origen = diseno` («lo pensamos mal») o `= falla_fabricacion` («lo hicimos mal») **es
   una lección de fabricación ya escrita**, del lado de reparación, sin destinatario. Cerrar
   ese lazo es lo que hace que `origen` pague: hoy es análisis retrospectivo y nada más.

3. **Se diseña completo, se despliega por etapas.** Diseñar la lección aislada la ajustaría a
   la única fuente que hoy tiene datos y no calzaría cuando llegue el hallazgo de fabricación.
   El orden de implementación se decide con el diseño entero a la vista, no antes.

4. ~~**La pregunta abierta que define el ancla: ¿se usa `mrp`?**~~ **Contestada, y que sí.**
   `mrp` es dependencia del módulo desde `19.0.15.3.0` y el bloque B ya cuelga de ahí: la orden
   de fabricación **crea el número de serie** (`lot_producing_ids`, Many2many en Odoo 19) y
   `_mc_sellar_alcance()` lo escribe en las alertas de la orden al cerrarla. PLM también está
   conectado, vía `quality.alert.mc_eco_id`. **Verificado en producción el 2026-08-21: 11
   órdenes de fabricación, 1 lista de materiales, 0 operaciones.** El lote es el *resultado* del
   armado, no el armado, y eso sigue siendo cierto.

5. **El riesgo a resolver antes de escribir código: un registro de lecciones que nadie lee
   mientras arma el equipo es un cementerio.** Y es peor que el riesgo habitual: esto *sí* se
   va a llenar —escribir la lección es satisfactorio— y no se va a leer. Guardarla en el
   producto y confiar en que alguien entre a mirarla no basta; hay que decidir **dónde
   aparece en el momento de fabricar**.

6. **La batería de fabricación deja de ser un pendiente suelto:** es el contenido del evento
   nuevo. Lleva años sin definirse justamente porque no había dónde ponerla.

- [ ] **La batería de fabricación no está definida.** Los 22 chequeos tienen las tres casillas
  `aplica_*` encendidas, así que un ROV recién armado recibe las mismas preguntas que uno que
  llegó roto — incluidas las que buscan desgaste y daño de uso. Quedó así por omisión al
  retirar el chequeo de marcas de plumón en `19.0.12.0.0`, que era el único que separaba las
  baterías. **El mecanismo para separarlas existe y está probado: son datos, no código.**

- [x] ~~**Falta software en la batería de reparación.**~~ — **hecho en `19.0.15.2.0`.** Dos
  chequeos en la sección `comunicacion`, solo reparación: «El software de superficie inicia y
  opera» y «El software instalado corresponde a la ficha».

- [x] ~~**La versión de software revierte sola.**~~ — **hecho en `19.0.15.2.0`, en su forma
  mínima.** Lo que Paulo corrigió el 2026-08-17 y que cambiaba el diseño: **no es un número de
  versión que retrocede, es el software mismo que vuelve al de fábrica** — ROVControl a
  QGroundControl, o QGroundControl a una versión más vieja. Un diseño de tres `Char` habría
  dejado pasar el caso más frecuente, porque el nombre de un programa no es un número. ArduSub
  «no se toca mucho, pero quizás».

  Quedó como un chequeo más los cinco `related` de la ficha al lado, para poder responderlo sin
  salir de la pantalla. **Sin modelo, sin comparación automática, a propósito** — razones y la
  regla para revisitarlo en [`designs/revision-tecnica.md`](designs/revision-tecnica.md) § 8.8.

  Lo que queda vivo del punto: **medir si se llena.** El `detalle` es la evidencia que decide
  si vale estructurarlo, y es opcional — el chequeo bloquea la confirmación, el detalle no. Sin
  detalle, un «No OK» dice que algo no cuadró y no dice qué software era. Mismo riesgo y misma
  mitigación que `hallazgo_origen_id` más abajo.

  Efecto secundario que ya vale: **obliga a mantener la ficha al día**, porque una diferencia
  es o un equipo que revirtió o una ficha desactualizada.

- [ ] **Sí se hacen pruebas en terreno**, sobre equipos fabricados, y hoy viven en el lote. El
  tipo `terreno` de la revisión existe **sin ninguna justificación escrita** y nada lo crea:
  hay que decidirlo junto con el primer punto. Ver el apartado de fabricación de más abajo —
  la decisión depende de una sola pregunta sin responder.

## Guiar al usuario dentro de Odoo *(diseño abierto, 2026-08-19)*

El problema: son varios módulos y **el usuario no lee documentación — abre Odoo y no sabe qué
botón tocar**. [`flujo-de-trabajo.md`](flujo-de-trabajo.md) sirve para nosotros, no para ellos.
La ayuda tiene que estar dentro del programa.

Dos principios que ordenan todo lo demás:

> **1. El siguiente paso tiene que ser un botón en el registro que ya estás mirando.** La guía
> por cercanía le gana siempre a la guía por documentación.
>
> **2. La pantalla vacía es el mejor momento para enseñar.** Quien llega a una lista sin nada
> está detenido y mirando, y Odoo ya reserva ese espacio.

Las ideas, por lo que rinden frente a lo que cuestan:

| | Idea | Comentario |
|---|---|---|
| **a** | **Botones de siguiente paso** | La más valiosa. *«Ir a la ficha del equipo»* al terminar la MO; *«Nueva prueba de rendimiento»* en el N° de serie; *«Levantar alerta»* en la línea de trabajo — ese último ya resuelve la fricción de que reparación termine en Calidad, porque el usuario nunca tiene que saber que Calidad existe |
| **b** | **Textos de lista vacía** | Gratis: es un atributo de la acción y Odoo lo muestra solo. Va de paso con lo demás, no compite con (a) |
| **c** | **Tablero de «qué me falta»** | Fichas incompletas, equipos sin pruebas, revisiones sin confirmar, alertas sin acción preventiva |
| **d** | **Menú propio ordenado por proceso** | *«ROV → 2. Aceptar»* en vez de *«Inventario → Números de serie»*. Resuelve la fricción del nombre de puerta |
| **e** | **Semáforo en la ficha del equipo** | Ya existe y funciona: el aviso de «faltan 3 de 16» es exactamente este patrón |

**Descartado: artículos de Knowledge o manuales embebidos.** Es otro lugar más al que nadie va a
entrar, y compite con el trabajo en vez de acompañarlo.

**(c) y (d) van juntas y aparte, como un «centro de mando», y después de (a).** Responden una
pregunta distinta —*«¿qué hago hoy?»* en vez de *«¿cómo sigo?»*— y mezclarlas empeora las dos.
Además: **un tablero construido antes de que el proceso esté en uso muestra lo que es fácil de
contar, no lo que importa.** Con tres meses de datos reales se sabrá qué miran de verdad.

### El presupuesto de indicadores

El patrón de (e) —un derivado que dice «a este registro le falta algo»— se gana su lugar **donde
la ausencia es silenciosa y la consecuencia es tardía**. Si el sistema ya reclama, un indicador
es ruido.

Candidatos, por cuán callada y cara es la falla:

1. **Fecha de puesta en servicio vacía** — sin ella el reloj de mantención no arranca y el equipo
   no aparece nunca en «mantención vencida». Nada reclama; te enteras cuando reclama el cliente.
2. **Producto ROV fuera de la rama de categorías** — se apagan las cuatro pestañas de ficha y
   **el síntoma no apunta a la causa**: se reporta «no me aparecen las pestañas».
3. **Alerta de calidad cerrada sin acción preventiva** — es una lección que nunca se escribió.
4. **Propietario mal puesto en un equipo vendido** — aparece como «Disponible» y ensucia la flota.
5. **Pruebas de aceptación** — ya diseñado en `designs/fabricacion.md` § 4.4.

Y uno que **ya existe y es de la misma familia**: `mc_revision_pendiente`, que en `19.0.14.0.0` se
decidió mostrar con un filtro en vez de bloquear.

> **La regla, para no repetir lo del `required` rojo: un indicador por registro, que agregue todo
> lo que le falta. No uno por campo.**

El aviso de la ficha ya lo hace bien —dice «faltan 3 de 16» y los nombra— en vez de cuatro avisos
compitiendo por la misma franja. **Conviene diseñarlos juntos y no de a uno**, porque el que
llegue segundo va a querer su propia franja.

### La cotización declara lo que la ficha después registra

Una cotización de ROV custom **declara lo que el equipo va a llevar** —cuántas luces, cámara
lateral, brazo— y la ficha registra lo que llevó. **Son la misma lista en dos momentos: promesa y
hecho.**

Eso importa porque resuelve por el lado correcto el pendiente de más abajo sobre las luces y
cámaras custom: ahí quedó anotado que la ficha debería declarar qué trae el equipo para que la
revisión no pregunte de más. **Si la cotización alimenta la ficha, el dato entra donde se decide
y no donde se transcribe.**

Sin decidir: si eso se modela o queda como convención.

## Fabricación — listo para implementar

**El diseño está cerrado y aprobado.** Ver [`designs/fabricacion.md`](designs/fabricacion.md),
790 líneas, y la guía para usuarios en [`flujo-de-trabajo.md`](flujo-de-trabajo.md).

### Cómo partirlo

| | Qué | Tamaño | Depende de |
|---|---|---|---|
| **A** | Las pruebas de aceptación. **No es un bloque: son cuatro con dependencias distintas**, ver abajo | Grande | — |
| ~~**B**~~ | ~~Los puentes a `quality.alert`~~ — **hecho en `19.0.15.3.0`** | Chico | — |
| **C** | Los indicadores agregados en el número de serie (§ 4.4), con el presupuesto de **uno por registro** | Chico | A |
| ~~**D**~~ | ~~Alinear `quality.reason` con `ORIGENES`~~ — **hecho en `19.0.22.2.0`**. La batería de armado se cayó, ver abajo | Datos, cero código | B |

**A y B son independientes.** B se nota antes —son los cuatro campos que cierran el círculo con
reparación— y no lleva migración, así que sirve de rodaje para el flujo nuevo con staging antes
de la migración grande.

### A2 también va antes de la carga, y esto salió de mirar la pantalla *(2026-08-20)*

Estaba dicho que A2 podía esperar. **No puede.** La pestaña «Umbilical» del número de serie
contiene, además de las especificaciones del cable, **una sección entera de prueba de rendimiento** —
modelo de fuente, alimentación, tensión, consumos, pilot gain, ancho de banda, temperaturas— que
son **las mismas mediciones que la revisión ya recoge**. El módulo está a medio mudar y esos
datos tienen dos casas.

Si se cargan equipos reales con esas secciones todavía en pantalla, **alguien las va a llenar, y
A2 las borra**. Y peor: entre las dos pruebas y la ficha, un técnico teclearía lo mismo dos o
tres veces sin ninguna señal de que sobra.

Dos cosas concretas que A2 tiene que resolver, además del retiro:

- **El largo del umbilical se pide siempre y se exige para confirmar.** Si el cable es *del
  equipo*, ese largo ya está en la ficha. El § 5.4 lo dice —*«umbilical usado y largo solo si es
  del taller»*— y no está implementado.
- **La pestaña «Umbilical» se queda solo con el umbilical.** Hoy su título nombra la primera de
  sus tres secciones, y las otras dos son la prueba de rendimiento. Viene de la época de Studio.

### Catálogos editables en Especificaciones y Periféricos *(pedido 2026-08-20)*

Las listas seleccionables de esas dos pestañas deberían **poder mantenerse sin tocar código**, y
mejor todavía si se actualizan solas. El patrón ya existe y está probado en el módulo:
`mc_software_superficie` y `mc_controlador_vuelo` dejaron de ser valores fijos y pasaron a ser
catálogos con su menú en Configuración.

Aplica al menos a **modelos de motores, periféricos y dispositivos extras**. La razón es la
misma que en aquellos dos: el día que llegue un modelo nuevo, agregarlo tiene que ser escribir
una fila, no abrir un PR.

### A se parte en cuatro, y solo una corre contra el reloj

Al leer el § 4 y el § 5 completos quedó claro que A no es una cosa. **Solo A1 tiene que estar
antes de que el sistema entre en uso real**, porque es la única con migración — y el § 8 lo dice:
*«la ventana para hacerlo es ahora; con equipos reales cargados, cada una de esas tres preguntas
vuelve»*.

| | Qué | Bump | Cuándo |
|---|---|---|---|
| **A1** | `fabricacion` → `rendimiento`, `observacion` → `detalle`, se retiran las columnas de terreno del lote, y el arreglo de `_compute_resultado` | `X`, con migración | **Antes de cargar datos reales** |
| **A2** | Las mediciones nuevas del § 5.4, y con ellas el retiro de las columnas de laboratorio | `Y` | Después |
| **A3** | Las secuencias `RND/` y `TRN/`, y congelar `tipo` una vez emitido | `X`, con migración | **Hecho en `19.0.19.0.0`** |
| **A4** | Las cuatro baterías del § 5.2 y § 5.3 | Datos | Después, y **quiere** equipos reales: los cinco chequeos de armado los escribió el diseño y no el taller |

**A3 está hecho en `19.0.19.0.0`, y resultó ser `X` y no `Y`.** Lo que el diseño no había
previsto: **congelar el tipo al confirmar no alcanza.** El tipo se cambia *entre* crear y
confirmar —es el caso corriente, porque el botón del número de serie crea la prueba y recién
ahí el técnico ve cuál era—, así que un prefijo puesto al crear queda mintiendo igual. La
salida fue renumerar el borrador cuando cambia de tipo, con nota en el chatter. Y el candado
no podía colgar de `estado`: devolver a borrador una prueba ya entregada habría reabierto el
tipo y renumerado un documento que el cliente tiene en la mano — de ahí el campo
`documento_emitido`, que es lo que obliga a la migración.

**A1 está hecho en `19.0.16.0.0`.** Dos cosas que salieron de implementarlo y que el diseño no
había previsto:

- **El renombre de etiquetas «En reposo» / «Esfuerzo» del lote salió de A1.** Son columnas de
  laboratorio, o sea que A2 las borra: renombrarlas antes es trabajo que se elimina un PR
  después. La decisión de vocabulario sigue en pie para los campos nuevos de A2.
- **Se retiró la acción «Revisiones de fabricación»**, que no referenciaba ningún menú y cuyo
  dominio, tras el renombre, no habría encontrado nada.

### Antes de empezar B: una verificación *(hecha el 2026-08-20, pasa)*

B agrega **`mrp`, `quality_control` y `mrp_plm` a las dependencias del módulo**. Eso hace que
`mc_rov` ya no se pueda instalar sin ellos — en producción están, pero **hay que confirmar que el
runner de CI puede instalar el módulo con esas dependencias**, o sea que su addons path incluye
Enterprise. Si no, el primer PR de B rompe CI y no por el código.

La alternativa sería un módulo puente aparte (`mc_rov_quality`), pero es mucha infraestructura
para cuatro campos en un módulo de una sola empresa. **Se elige agregar las dependencias**, y
queda anotado que ése es el costo.

**Resultado, verificado contra el VPS:**

- El `addons_path` de `/etc/odoo/odoo.conf` —el mismo archivo que usa el runner— incluye
  `/usr/lib/python3/dist-packages/odoo/addons`, y ahí viven `quality`, `quality_control`,
  `mrp_plm`, `quality_mrp` y `quality_repair`. Enterprise está en el path.
- En `odoo_test` los cinco salen `installed`. **Eso mata el riesgo mayor**, que no era el addons
  path sino la instalación primeriza: no hay módulos nuevos que instalar en la primera corrida,
  así que ni el `timeout-minutes: 30` ni los 189 tests actuales se mueven — ya venían corriendo
  en una base con `mrp` puesto.
- **Son cinco dependencias y no tres.** `quality_mrp` y `quality_repair` no estaban en el diseño
  y hacen falta: son ellos los que definen `quality.alert.production_id` y
  `quality.alert.repair_id`, que es por donde entran los puentes. Los dos son `auto_install`, así
  que ya estaban instalados; declararlos fija el orden de carga.

### Lo que queda de B después de `19.0.15.3.0`

- [x] ~~**Confirmar en pantalla el botón inteligente del número de serie.**~~ — **hecho el
  2026-08-20: no existe.** El lote trae los conteos de `quality_control` y ninguna vista los usa.
  Se escribió como pestaña en `19.0.15.4.0`.
- [x] ~~**Decidir quién ve el botón de la línea de trabajo.**~~ — **la pregunta no existe:** hay
  **un solo usuario activo** en `odoo_prod` y ya tiene `quality.group_quality_user`. Concuerda
  con el `CLAUDE.md`: los técnicos no tienen login propio porque las licencias se pagan por
  usuario, y por eso los responsables son `hr.employee`. Vuelve el día que alguien más tenga
  login.
- ~~**El ruido posible de la alerta automática.**~~ — **resuelto el 2026-08-20:** se acotó a la
  rama de categorías ROV. El § 6.1.4 no lo calificaba y se implementó sin restringir; Paulo lo
  corrigió al revisarlo. El § 6.1.4 quedó actualizado con la razón.

### Lo que no se va a pedir

- **La presión de prueba por modelo.** Se evaluó pedirla en la ficha para derivar el chequeo de
  estanqueidad y se descartó: los técnicos saben a cuánto va cada equipo. Se registran bar y
  tiempo, y la persona juzga. Ver § 5.6.
- **La profundidad máxima del modelo.** Se queda en la hoja de cotización. Un umbral ahí
  empujaría a arriesgar el equipo de más. Ver § 5.6.

### Lo único que necesita retroalimentación, y no bloquea

**Los cinco chequeos de armado** los escribió el diseño, no el taller. Se implementan como están
y se corrigen con el primer uso real. Está dicho así en § 5.3 para que nadie los confunda con
algo que dijo el taller.

## El puente reparación → lección — rediseñado e implementado *(2026-08-20)*

> **Implementado en `19.0.15.5.0`.** Lo que sigue es el razonamiento completo, que conviene
> conservar: la parte más valiosa no es el mecanismo sino por qué el anterior no servía.

**El § 6.1.3 del diseño pide «un botón que la pre-llene desde `origen`», y eso no sobrevive a la
pregunta de Paulo: ¿cómo sabe el usuario qué hace ese botón, y por qué lo apretaría?** No tiene
incentivo, y no necesariamente tiene la formación para escribir lo que viene después.

### Lo que sí está resuelto, y hay que no perderlo de vista

**El conocimiento del momento no se pierde.** Al cerrar, el técnico ya deja el `origen`
—obligatorio desde `19.0.13.0.0`— y el «por qué pasó», más componente, subtipo, acción y el
hallazgo que resolvió. Eso es la **observación**, y es durable.

Lo que falta es la **conclusión**, y es un juicio de ingeniería con consecuencias en repuestos,
costos y garantías. **No es trabajo del técnico**, y pedírselo produce o silencio o texto malo.

### La corrección: el sistema detecta, la persona concluye

Una línea suelta es una anécdota; **lo que la vuelve lección es la repetición**. Y la repetición
es contable, porque una línea de trabajo no es texto libre: componente, subtipo, acción y origen
salen todos de catálogo. Además el propio `origen` ya excluye lo que ensuciaría el conteo — si
dice diseño, manufactura propia o pieza de proveedor, el técnico **ya afirmó que no fue el cliente
ni el desgaste**.

El § 6.3 dice que *«los patrones de manufactura sí se detectan, pero en los datos de reparación»*
y **nunca dice quién detecta**. Ahí estaba el hueco: la respuesta es el sistema, no una persona.

**Regla, corregida el mismo día: no hay umbral.** La primera versión ponía `N` unidades distintas
en un parámetro de sistema. Sobra. Si la lista se agrupa por modelo, componente y origen y se
ordena **por cantidad de líneas sin resolver**, arriba queda *«E-pod · manufactura propia — 4»* y
abajo *«cable · diseño — 1»*. La pregunta «¿es suficiente repetición?» vuelve a ser un juicio, que
es lo que era — y desaparecen el número arbitrario, el parámetro y toda la lógica de qué pasa
cuando llega la cuarta unidad.

*Unidades distintas* sí importa para el conteo: el mismo equipo reparado dos veces no es un
patrón.

**Dónde:** `Reparaciones → Lecciones pendientes`, al lado de *Revisiones técnicas*. En Reparaciones
y no en Calidad porque **la evidencia que hay que leer para decidir es evidencia de reparación**, y
porque mantiene la regla de que nadie tenga que enterarse de que Calidad existe.

### Lo que quedó construido

La lista muestra los trabajos con origen hacia adentro que todavía no alimentaron una lección ni
fueron descartados, **agrupada por modelo**. El conteo de cada grupo es la evidencia del patrón, y
no hay umbral: cuatro trabajos sobre el mismo componente del mismo modelo saltan a la vista, y uno
solo también — decidir dónde está la línea es un juicio, y por eso no se codificó un número.

Se seleccionan los que son el mismo problema y **un botón de cabecera escribe una sola lección con
todos**: todas las unidades en el alcance del daño, y los «por qué pasó» uno tras otro en la
descripción, cada uno con su equipo delante. Si alguno ya alimentaba una lección, los demás se le
suman en vez de crear otra.

**Descartar es escribir por qué**, en una columna editable de la misma lista. No hay asistente ni
casilla: el motivo obligatorio es la fricción que evita el descarte distraído, igual que en la baja
de un equipo, y deja un dato que sirve después. Hay un filtro para volver a mirar lo descartado,
porque un juicio se revisa.

**No se mezclan modelos en una lección** — se rechaza con un error que los nombra. Y la causa raíz
solo se propone si los trabajos coinciden en el origen: elegir uno de dos sería inventar el dato.

### El botón se retiró de la línea de trabajo

Quedaba en la pantalla de la persona que ya habíamos concluido que no lo iba a apretar. Y hacía
daño, no solo ruido: **la cola filtra por `mc_alerta_id` vacío, así que un clic distraído del
técnico le escondía la evidencia al supervisor**, en silencio y sin que nadie pudiera notarlo.
Condicionarlo a ciertos orígenes habría arreglado el ruido y no eso.

El campo se queda como columna de solo lectura: qué lección alimentó ese trabajo.

### En qué se convierte la acción

De mecanismo de descubrimiento a acción sobre un patrón ya detectado. Cambia de **sujeto** (un
patrón, no una línea), de **dueño** (quien tiene el criterio, no el técnico), de **pre-llenado**
(las N unidades en el alcance del daño y los N «por qué pasó» juntos — leídos de corrido dicen algo
que ninguno dice solo) y de **nombre**. Y gana un hermano, **«Descartar»**: si el sistema propone,
tiene que poder decírsele que no, o el mismo patrón reaparece cada vez y la gente deja de abrir la
lista.

`mc.rov.linea.falla.mc_alerta_id`, que ya existe desde `19.0.15.3.0`, es lo que hace que un patrón
deje de estar pendiente: cuando todas sus líneas alimentaron una lección, sale de la cola.

### La pregunta que estaba abierta, y cómo se resolvió

Era **¿el patrón es un agrupamiento calculado o un registro?**, y de ella dependían dónde vive el
descarte y a qué se cuelga el botón.

**Resuelta: no se guarda el patrón, se guarda la decisión humana.** La razón está en el
`CLAUDE.md` sobre un caso idéntico —*«no existe un booleano "mantención vencida" almacenado, y no
debe agregarse: un equipo se vence por el paso del tiempo, no porque alguien lo edite, así que
quedaría desactualizado en silencio»*—. Un patrón existe porque existen las líneas. Materializarlo
en una tabla es volver a crear el defecto recurrente que este módulo ya identificó: el dato
derivado que se desincroniza y nada lo detecta.

| Qué | Dónde vive |
|---|---|
| El patrón | Agrupamiento calculado. **Nada que guardar** |
| La lección | La alerta, que ya existe |
| El descarte, que **sí** es un acto humano | Un campo en la línea, con motivo |
| «Esta línea ya alimentó una lección» | `mc_alerta_id`, ya construido |
| Los botones | Acciones sobre líneas seleccionadas, no sobre cabeceras de grupo |

Sin modelo nuevo, sin acción programada, sin tabla derivada. Y con una propiedad que se gana
gratis: **si se descarta un patrón y vuelve a ocurrir, reaparece arriba de la lista**, porque las
líneas nuevas no están descartadas.

**Cuándo revisitarlo:** el día que se quiera un responsable por patrón, un plazo, o el historial de
quién descartó qué. Ahí un registro se justifica.

### La alternativa que se evaluó y se descartó

**Crear la alerta automáticamente al cerrar la orden**, por cada línea con esos tres orígenes,
agrupando por modelo. Se descartó por dos razones: le pide el juicio a la persona equivocada, y se
lo pide **cuando el patrón todavía no se ve** —al cerrar la primera orden hay una anécdota—. Y su
modo de falla es peor que el de la cola: si nadie mira, deja veinte borradores vacíos en Calidad y
la sensación falsa de que algo quedó capturado. La cola, si nadie la mira, deja las cosas donde ya
estaban.

### Lo que no se automatiza, y conviene no prometerlo

**La acción preventiva.** Ningún diseño fabrica disciplina: lo que se puede hacer es que la
omisión sea visible y que actuar cueste poco, y ahí se acaba. El día que se quiera subir el piso,
el lugar no es más automatismo sino un indicador donde el supervisor ya mira — y eso cae en «el
presupuesto de indicadores» de más arriba, que pide diseñarlos todos juntos.

## Un historial de la ficha técnica: evaluado y descartado *(2026-08-21)*

**No se construye, y la razón es que ya existe.** Cada revisión confirmada guarda, congelada, la
ficha tal como estaba ese día — software, umbilical y conteo de luces (`19.0.18.2.0`). **La
secuencia de revisiones de un equipo es su historial de ficha**, y se consulta abriendo la
revisión más cercana a la fecha que interese.

Un modelo aparte duplicaría eso y repetiría el defecto que este módulo ya identificó dos veces:
el dato derivado que se guarda a mano y se desincroniza sin que nada lo detecte.

Los cambios hechos **directo en la ficha, sin correr ninguna prueba**, quedan en el chatter del
equipo con valor viejo, valor nuevo, fecha y autor — todos esos campos llevan `tracking`. Para
«quién tocó esto» alcanza; lo que no permite es preguntar *«¿qué decía la ficha el 3 de marzo?»*
cuando no hay revisión cerca.

**Cuándo vuelve:** el día que haya que reconstruir el estado de un equipo en una fecha sin
revisión cercana — típicamente por una discusión de garantía. **Si eso ocurre dos veces, el
modelo se gana su lugar.** Antes de eso es un registro que se llena solo y no lo consulta nadie.

## Fabricación — el diseño está escrito

**Ver [`designs/fabricacion.md`](designs/fabricacion.md).** Recoge todo lo discutido el
2026-08-17 y 18, con lo verificado contra `odoo_prod` en su § 2 y lo que queda sin decidir en su
§ 10. Lo que sigue aquí abajo es el detalle que le dio origen.

## Fabricación — lo verificado el 2026-08-18

Todo lo de aquí abajo **se comprobó contra `odoo_prod`**, no es de memoria. Cambia bastante lo
que había anotado el 2026-08-17: la mayor parte de lo que íbamos a construir ya existe.

### Los módulos están instalados, no solo disponibles

`mrp`, `mrp_plm`, `quality`, `quality_control` y `web_enterprise` salen todos `installed`. Es
una instancia **Enterprise**, así que PLM y Calidad están sobre la mesa y nadie los usa.

`mrp` asigna el número de serie por su cuenta (`mrp.production.lot_producing_ids`); hacen falta
dos configuraciones y ninguna línea de código: *Inventario → Trazabilidad → Lotes y números de
serie*, y en el producto *Trazabilidad → Por número de serie único*.

Tipos de punto de calidad disponibles: `passfail`, `measure`, `instructions`, `picture`,
`print_label`, `register_byproducts`, `register_consumed_materials`, `register_production`,
`spreadsheet`. **`measure` es el que sostiene toda la recomendación** — trae norma, mínimo,
máximo y unidad.

### La corrección grande: `quality.alert` **es** la lección aprendida

Estaba anotado que había que construir un modelo de lecciones sobre `product.template`. **No
hay que construirlo.** `quality.alert` ya trae, verificado en `ir_model_fields`:

| Lo que pedía el diseño | Campo |
|---|---|
| Lección **del modelo**, no de la unidad | `product_tmpl_id` → `product.template` |
| Qué unidades quedaron afectadas | `lot_ids` (m2m a `stock.lot`) |
| Por qué pasó | `reason_id` → `quality.reason` (catálogo) |
| Qué se corrigió | `action_corrective` (html) |
| **Qué hacemos para que no se repita** | `action_preventive` (html) |
| De dónde salió | `check_id`, `production_id` |
| Flujo e historial | `stage_id`, `team_id`, chatter |

Trae **más** de lo que se iba a escribir, incluido el alcance del daño, que el diseño del
2026-08-17 no contemplaba.

### Los huecos reales, y son chicos

1. **No hay puente alerta ↔ ECO.** Verificado: `mrp.eco` no tiene ningún campo hacia
   `quality.alert` ni al revés. Así que «cambiamos el BoM por esto» no queda registrado. Se
   arregla con **un campo**.
2. **`product.template` no tiene relación con `quality.alert`.** O sea que **el que arme el
   próximo ROV no va a ver las lecciones** salvo que se acuerde de ir a la app de Calidad. Es
   el riesgo del «cementerio» localizado en un campo que falta, y es el trabajo más valioso de
   todo el bloque.

   > **«Tampoco `stock.lot`» decía esto, y era falso.** El número de serie **sí** trae el botón
   > inteligente «Alertas de calidad» de `quality_control`, que busca lo mismo que buscaba
   > nuestra pestaña. Se verificó el 2026-08-20 **con cero alertas en la base**, y un botón
   > inteligente se esconde cuando su contador está en cero: se concluyó que no existía. La
   > pestaña duplicada se retiró en `19.0.22.3.0`. **Verificar la ausencia de una función exige
   > datos que la enciendan.**
3. **De la línea de trabajo a la alerta** falta un botón que la pre-llene desde `origen`.

### Lo inesperado: `repair.order` ya está integrado con Calidad

Tiene `quality_alert_ids` y `quality_check_ids` nativos. Dos consecuencias:

- **El puente reparación → fabricación está a medio construir de fábrica.** No hay que
  inventarlo, hay que usarlo.
- Odoo ya traía un mecanismo de chequeos sobre reparaciones cuando se construyó
  `mc.rov.revision`. **No se toca la revisión**: hace cosas que un `quality.check` no hace
  —inspección de sellos, catálogo de hallazgos por familia, «No aplica» como respuesta válida—
  y sobre todo **es un entregable al cliente**, que un chequeo de calidad no es. Pero
  `quality_check_ids` conviene **esconderlo de la vista**: dos mecanismos de chequeo en la
  misma pantalla es una invitación a llenar el equivocado.

**La regla que sale de esto y que conviene no olvidar:** *los chequeos pertenecen al proceso que
los define; las alertas son el idioma común.* En fabricación **no se construye una segunda
batería** — se configuran puntos de calidad.

### Alcance real en `mc_rov`

De «un sistema de fabricación» a esto:

| Qué | Dónde | Tamaño |
|---|---|---|
| Ver las lecciones del modelo al fabricar | `product.template` ← alertas | Chico, **y es el que importa** |
| Ver qué alertas afectan a una unidad | `stock.lot` ← inverso de `alert.lot_ids` | Chico |
| «Cambiamos el BoM por esto» | `quality.alert` → `mrp.eco` | Chico |
| De la línea de trabajo a la alerta | Botón que pre-llena desde `origen` | Chico |
| Ficha del cliente con resultados | Reporte QWeb sobre `quality.check` | Mediano — **es el PDF, va al final** |
| Batería de fabricación | Puntos de calidad | **Configuración, no código** |

### La batería de fabricación, propuesta

Dos cosas la hacen genuinamente distinta de la de reparación, y no es «la misma con menos
ítems»:

1. **En fabricación los umbrales existen.** Se construye contra una especificación, así que la
   especificación *es* el umbral — y por eso `measure` sirve acá y no en reparación, donde se
   decidió no derivar el ancho de banda porque nadie los había definido.
2. **El software se mide al revés.** En reparación se compara contra la ficha; en fabricación
   **se instala**, así que la fabricación es la *fuente* de la ficha. Registrar las versiones al
   armar es lo que haría que la ficha dejara de nacer vacía.

Y el orden importa porque el proceso es físico: **hay cosas que solo se pueden verificar antes
de cerrar el casco.** Si el punto de control no está amarrado a la operación, se responde
después, de memoria, mirando un equipo cerrado.

| Momento | Qué | Tipo |
|---|---|---|
| Antes de cerrar | Sellos y o-rings instalados y lubricados | Pass-Fail |
| | Penetradores y conectores apretados | Pass-Fail |
| | Cableado interno ordenado y asegurado | Pass-Fail |
| | Foto del interior armado | Picture |
| Cerrado | Estanqueidad bajo presión · Prueba de leak | Pass-Fail |
| Banco eléctrico | Tensión de salida (V) · Consumo en reposo (A) · Consumo bajo carga (A) | Measure |
| Comunicación | Ancho de banda subida / bajada (Mbps) | Measure |
| Propulsión | Thrusters responden y giran en el sentido correcto | Pass-Fail |
| | Movimiento vertical / horizontal / lateral | Pass-Fail |
| | *stabilize* · *depth hold* | Pass-Fail |
| Video y luces | Imagen y tilt | Pass-Fail |
| | Cantidad de luces encendidas · Ganancia de luz (%) | Measure |
| Esfuerzo | Duración (h) · Temperatura interior y exterior (°C) | Measure |
| Cierre | Registrar número de serie | Register Production |
| | Versiones de software, controlador y ArduSub — **alimentan la ficha** | Instructions |

**Casi la mitad ya se mide hoy**, guardada como columnas del número de serie. No es una batería
nueva: son esas columnas convertidas en un evento con umbrales.

**Arreglo gratis que viene con esto:** `mc_ancho_banda` y `mc_consumo_corriente` hoy son `Char`,
así que no se pueden promediar, comparar ni graficar. Como puntos `measure` pasan a ser números
con unidad, y recién ahí sirven para el pipeline.

### La batería de armado no se hace *(decidido 2026-08-21)*

**Los cinco chequeos del interior se caen, y con ellos la ruta de fabricación.** Un punto de
calidad se engancha a una **operación**, y producción tiene **0 operaciones**: las órdenes de
fabricación son planas. Sin ruta, los cinco aparecen con el casco ya cerrado — que es
exactamente el modo de falla que ponerlos en calidad venía a evitar.

Crear la ruta era la otra salida y se descartó. Palabras de Paulo: *« aún no somos lo
suficientemente grandes para justificar ese proceso »*. **Y el argumento técnico va en la misma
dirección: la prueba de presión — 2 h a 30 bar — ya caza el modo de falla que esos cinco
persiguen.** Un o-ring mal puesto o un penetrador flojo se ven ahí. Lo que los checks agregan es
saber *en qué paso* falló, y con 11 órdenes y una sola lista de materiales eso no paga tres
órdenes de trabajo que alguien tiene que abrir y cerrar.

**Lo único que se pierde de verdad es la foto del interior armado**, porque después del cierre ya
no se puede tomar. No necesita ruta ni puntos de calidad: se adjunta al chatter de la orden de
fabricación, cero configuración.

> **Cuándo reabrirlo:** cuando una filtración llegue a un cliente, o cuando armen lo suficiente
> como para que *«¿en qué paso falló?»* sea una pregunta real. Ahí los cinco vuelven a tener
> sentido, y con ellos la ruta mínima de tres operaciones — armado interno, cierre, pruebas.

**Y ojo con la duplicación que esto evita de paso:** la tabla de puntos de más abajo repite casi
entera la batería de rendimiento — banco eléctrico, comunicación, propulsión, video, esfuerzo—,
que `mc.rov.revision` ya recoge. Configurarlos como puntos de calidad habría pedido las mismas
mediciones dos veces.

### Lo que sigue sin decidir

1. **Los mínimos y máximos.** Qué tensión, qué consumo en reposo, qué ancho de banda es
   aceptable para cada modelo. **Si esos números no existen escritos hoy, eso mismo es el
   hallazgo**: un `measure` sin tolerancia guarda el número pero no dice si está bien.

2. **Cuántas veces se le hace prueba en terreno a un mismo equipo.** Es lo único que decide
   dónde vive, y hoy vive en dos lugares — los campos del lote, que se usan, y `tipo = terreno`
   en la revisión, que está muerto. **No es «agregar terreno a la revisión», es cuál de los dos
   sobrevive**, porque dejar los dos es duplicar.

   - *Una sola vez* (aceptación antes de entregar) → el lote está bien: una foto basta, y
     `terreno` sale de la revisión por muerto.
   - *Cada cierto tiempo o por trabajo* → tiene que ser un evento, porque hoy correrla de nuevo
     **pisa la anterior en silencio**. Gana la revisión y los campos del lote se migran.

   Es la misma pregunta que resolvió la corrida en `19.0.15.0.0`, y ahí cambió el modelo entero.

   Nota contra un argumento propio: *«dejarlo donde ya se hace»* no aplica limpio acá. Nadie
   llena el formulario del lote parado en un bote — los dos lugares son transcripción posterior.

3. **`tipo = fabricacion` se retira** de la revisión: la prueba de fabricación pasa a ser puntos
   de calidad sobre la MO. Sale con la migración de este bloque.

4. **El re-test tras rediseño no se diseña todavía.** Ocurre pocas veces al año, con enfoque de
   troubleshooting, y nadie sabe describir su forma. Modelarlo ahora es inventar la forma del
   dato antes de tener el dato — el mismo error que se evitó con el software en `19.0.15.2.0`.
   Mientras tanto cae en su lugar natural: el prototipo se arma con una MO, la MO trae sus
   chequeos, y si falla, la alerta se lleva el troubleshooting.

5. **Empezar con un solo modelo de ROV**, el que más se arme, y una MO completa de punta a
   punta antes de escribir una línea. Se está digitalizando un proceso hoy físico: no hay
   costumbre que aprovechar, hay costumbre que cambiar, y eso se descubre haciendo una.

6. **No rastrear todo por lote.** La trazabilidad es configuración *por producto*: se puede
   tener un BoM de 40 líneas con 4 rastreadas —o-rings, thrusters, tarjetas, controlador— y el
   resto consumido automáticamente. Eso convierte «registrar 40 piezas» en «elegir el lote de
   4», y deja intacto lo único que hoy no se puede responder de ninguna forma: **qué otras
   unidades llevan la pieza que salió mala.** Hoy `origen = pieza_proveedor` se registra en la
   reparación y muere ahí, sin poder mirar hacia los lados.

## Estado al 2026-08-17

`19.0.15.2.0` metió **software a la batería de reparación**: dos chequeos en `comunicacion` y
los cinco `related` de la ficha al lado, para poder contestarlos sin salir de la pantalla. Sin
modelo nuevo y sin comparación automática, deliberadamente — razones y la regla para revisitarlo
en [`designs/revision-tecnica.md`](designs/revision-tecnica.md) § 8.8.


`19.0.14.0.0` ordenó el flujo en pantalla: **las pestañas pasaron a ser los momentos del
proceso**, leídos de izquierda a derecha. En la orden, *Recepción · Diagnóstico · Reparación ·
Repuestos · Cierre · Notas*; en la revisión, de cinco pestañas a tres — *Sellos · Pruebas ·
Hallazgos*—. Además la temperatura bajó a la corrida (se mide una por corrida y sí depende del
cable), el cierre exige el repuesto cuando la acción lo consume, y la revisión sin confirmar se
muestra con un filtro en vez de bloquear. Razones en
[`designs/revision-tecnica.md`](designs/revision-tecnica.md) §§ 8.1–8.4.

## Estado al 2026-08-14

El **diagnóstico de fallas** está implementado (`19.0.13.0.0`): el catálogo de síntomas, los
dos campos de recepción, `causa_raiz` partido en `origen` con su análisis escrito, y la vista
de búsqueda que faltaba. Diseño en
[`designs/diagnostico-de-fallas.md`](designs/diagnostico-de-fallas.md), con las correcciones
que salieron de contrastarlo contra el código en su § 15.2. Lleva migración.

La **revisión técnica** está implementada (`19.0.12.0.0`): seis modelos, los catálogos de
chequeos y hallazgos, la inspección de sellos, y **una** revisión por visita que se abre sola
al confirmar la orden. Diseño en
[`designs/revision-tecnica.md`](designs/revision-tecnica.md).

`19.0.12.0.0` salió de probar el módulo en pantalla, que es de donde salió todo lo que
importaba: el par recepción/entrega se retiró, la pestaña de pruebas se rehízo por secciones
como la hoja de papel, y el catálogo salió del alcance de quien llena la ficha. Las
correcciones de alcance quedan registradas en § 1.3 y § 1.4 del diseño.

`19.0.12.1.0` corrigió el ancho de la pestaña de pruebas —cada sección es un `<group>`, que
sin `colspan="2"` deja la lista en media página con el nombre del chequeo cortado— y agregó
el botón **Actualizar checklist**.

`19.0.12.1.1` sacó las filas de relleno de esas listas con una regla en
[`static/src/css/mc_rov.css`](../static/src/css/mc_rov.css).

**Validado en producción, ya sin pendientes de este bloque:** `open_form_view` rinde en el
one2many embebido de Odoo 19 —la revisión se abre desde la orden en su propio formulario y se
edita— y esconder `tag_ids` con `position="attributes"` dejó «Etiquetas» efectivamente fuera
de la vista. Los dos se habían deducido de una captura, sin poder leer el arch base de
`repair`.

## Salido de probar `19.0.12.1.0` en pantalla

- [ ] **La batería es uniforme y los equipos no.** Las luces varían entre modelos, y los
  pedidos custom agregan cámaras laterales o traseras y luces extra —para las cámaras o
  simplemente para alumbrar más.

  Hoy eso no se puede registrar. Las luces son dos enteros (`luces_internas`,
  `luces_externas`) y la cámara es **un solo chequeo** para todo el equipo. Dos consecuencias:

  1. **El conteo dice cuántas encienden, nunca cuál está apagada.** Cuando el mismo equipo
     vuelva en seis meses no hay forma de saber si falla siempre la misma.
  2. **El `0` de un entero es ambiguo:** no distingue *no encendió ninguna* de *este modelo
     no lleva luces internas*. Es exactamente la ambigüedad que se sacó de los chequeos con
     «No aplica», y sobrevivió en las luces porque son enteros y un entero no tiene vacío.

  **No se arregla agregando campos.** Cuatro enteros en vez de dos aguantan hasta el próximo
  custom, y entonces son un `X` bump con migración. Es el mismo argumento por el que los
  pasos de testeo son catálogo y no columnas.

  **Forma propuesta, a diseñar:** que la ficha del equipo declare qué trae —N luces internas,
  N externas, cámara frontal, cámara lateral izquierda…— y que la revisión genere una línea
  por elemento. El mecanismo hermano ya existe y está probado: `por_componente` genera una
  línea por componente inspeccionable.

  **El riesgo que el diseño tiene que resolver antes de escribir código:** si la ficha del
  equipo está vacía —y hoy lo está en todos los equipos anteriores a Odoo— la revisión
  generaría cero líneas y el checklist desaparecería en silencio. Es un modo de falla peor
  que el que viene a arreglar. Necesita un respaldo: los chequeos genéricos de hoy cuando el
  equipo no declara nada.

  Es la misma familia de problema que el refinamiento anotado en
  [`designs/revision-tecnica.md`](designs/revision-tecnica.md) § 5.4 sobre el joystick y el
  cilindro fuente: *si el equipo declarara lo que tiene, la revisión no preguntaría de más*.
  Conviene diseñarlos juntos.

## Salido de implementar `19.0.13.0.0`

- [x] ~~Revisión a mano de las filas `falla_fabricacion`~~ — **no aplica.** La auditoría
  previa al desplegar `19.0.13.0.0` mostró que `odoo_prod` tenía **2 líneas de trabajo, ambas
  sin causa**: cero `corrosion`, cero `accidente`, cero `falla_fabricacion`. Las dos quedaron
  en `desconocida`.

  **Lo que sí queda vivo:** no confundir el `desconocida` de antes con el de ahora. Las líneas
  que nunca tuvieron causa quedaron ahí, así que un `desconocida` anterior a `19.0.13.0.0`
  puede significar «no se pudo determinar» o «nadie lo llenó», y eso ya no se distingue.

- [ ] **Separar Electrónica y Software / Configuración:** implementado y validado en
  STAGING (`19.0.23.7.0`, 20 pruebas); pendientes PR y producción. Parámetros y
  sus hallazgos/trabajos se reclasifican; los registros sin subtipo quedan en Electrónica.

- [ ] **Medir la tasa de llenado de `hallazgo_origen_id`** antes de confiar en cualquier
  análisis que cruce hallazgos con orígenes. Es opcional, y sin él la línea de trabajo tiene
  «por qué pasó» sin «qué se encontró». Un cruce sobre el 20% de las líneas se ve idéntico a
  un resultado (§ 9.1 del diseño).

- [ ] **Revisar en seis meses si `analisis_causa` se llena.** Entró en parte para cumplir un
  requerimiento y su aporte real no está probado: es plausible que sirva solo en los casos
  complejos. Si queda vacío en la gran mayoría de las líneas, sacarlo cuesta un campo — se
  eligió texto y no un modelo de porqués justamente para que retirarlo fuera barato.

Lo que sigue del plan original, en orden:

- [ ] **Reporte PDF de las dos fichas** (`19.0.9.0.0` del plan, ahora la siguiente versión
  grande). La ficha de revisión técnica quedó implementada y validada en staging; aún falta
  definir e implementar la ficha de fabricación.

  **2026-09-10 — reporte por revisión validado en STAGING, sin publicar.** Incluye opciones
  de impresión; maqueta C recuperada en `designs/referencias/ficha-impresa-rov.html`. Estado
  al inicio de este archivo y diseño en `designs/revision-tecnica.md`, § 12.1.

  **La revisión existe, entre otras cosas, para entregársela al cliente**, así que esto no
  es un extra. Obliga a decidir campo por campo qué es interno y qué va impreso — ver
  [`designs/revision-tecnica.md`](designs/revision-tecnica.md) § 12.1.

  **Ya hay un caso concreto que decide, y no es hipotético:** la **temperatura** de cada
  corrida vuelve a medirse como dato **interno** y **no debe salir impresa**. Antes se le
  entregaba al cliente y el cliente la usó en contra. Es el primer campo con una razón
  comercial —no estética— para quedarse adentro, y conviene arrancar el diseño del reporte
  por ahí: si un campo puede volverse en contra, la pregunta no es «¿se ve bien?» sino «¿qué
  hace el cliente con esto?».

- [ ] **Fotos de los hallazgos**, con `fields.Image(max_width=1920, max_height=1920)` y no
  `fields.Binary`. Decidido dejarlo para el final. El disco no es problema: 50 GB libres y
  los adjuntos van a disco, no a la base.

- [x] **Vista de búsqueda de `repair.order`** — hecha en `19.0.13.0.0`: filtro «Sin síntoma
  registrado», búsqueda y agrupación por tipo de intervención, y `sum` al pie de
  `mc_total_horas`.

  **«Agrupar por causa raíz» se retiró del pendiente y no se va a hacer.** Estaba anotado de
  cuando el campo vivía en la orden; desde `19.0.8.0.0` vive en la línea de trabajo. Una orden
  con tres trabajos tiene tres orígenes, y agruparla por uno exigiría el campo derivado que el
  diseño prohíbe explícitamente, porque elegiría uno y botaría los otros dos en silencio.

  Notas que siguen valiendo para cualquier herencia futura de esa vista: la base se llama
  **`repair.view_repair_order_form_filter`**, su grupo de "agrupar por" no tiene nombre pero
  el último filtro adentro sí (`group_by_repair_properties`), y **el schema de Odoo 19
  rechaza `expand` y `string` en el elemento `group`** — eso rompió el módulo una vez. La
  herencia que se escribió ancla en la raíz `<search>` justamente para no depender de nombres
  del arch base que no se pueden leer desde el entorno de desarrollo.

- [ ] **Phase -1 del pipeline roadmap — Foundation handoff** — prerequisito bloqueante para iniciar el pipeline. Checklist completo en `rov-pipeline-roadmap.md` Phase -1. Duración estimada: 1 semana.

- [ ] **Cambiar el `admin_passwd` de `/etc/odoo/odoo.conf`.** Quedó expuesto en una conversación
  el 2026-08-18. Es la contraseña maestra del gestor de bases de datos: permite crear, duplicar y
  **borrar** cualquier base. Se cambia en ese archivo y requiere reiniciar el servicio.

- [x] ~~**Montar staging**~~ — **hecho el 2026-08-18.** Base `odoo_staging`, servicio
  `odoo-staging` en el puerto 8070, checkout propio en `/opt/odoo/staging-addons/mc_rov`, y
  acceso solo por túnel SSH. Ver [`runbooks/staging.md`](runbooks/staging.md).

  **Todavía no se ha usado para lo que se montó:** ensayar una migración. La de fabricación va a
  ser la primera de verdad.

- [ ] **Separar el workspace del runner de CI del addons de producción.** Hoy son el mismo directorio: `/opt/odoo/custom-addons/mc_rov`. Descubierto el 2026-08-07 al desplegar `19.0.5.0.0`.

  **Se resuelve con la misma reorganización que staging:** tres checkouts separados —producción en `/opt/odoo/custom-addons`, staging en `/opt/odoo/staging-addons`, y CI fuera de los dos— en vez de dos procesos compartiendo un directorio.

  **El deploy en sí ya no es el problema**: el usuario `odoo` tiene deploy key y hace `fetch` por su cuenta. Lo único que fallaba era que el runbook decía `git pull` a secas, que corre como root — corregido en [`runbooks/deploy.md`](runbooks/deploy.md).

  Lo que queda es el directorio compartido: **un job de CI puede cambiar lo que Odoo está sirviendo**, porque el checkout aterriza en el addons path de producción. Desplegar no es lo único que mueve ese código.

  Arreglo: mover el workspace del runner fuera de `/opt/odoo/custom-addons/mc_rov`. No urge —el deploy funciona y es deliberado— pero es una fuente de sorpresas que nadie va a relacionar con CI cuando ocurra.

- [ ] **Carga de productos ROV** — el árbol de categorías ya está en producción (164 categorías), pero todavía no hay productos ROV cargados. Al cargarlos:

  1. **La categoría dejó de ser un dato descriptivo y pasó a ser funcional.** Desde `19.0.2.0.0` el campo `es_un_rov` se deriva de ella: un vehículo cargado fuera de la rama `ROV - Vehiculos` (id `968` en `odoo_prod`) no tendrá ficha técnica ni pestañas de mantención, y nadie podrá encenderlas a mano.
  2. `ROV-MC` para vehículos de marca propia, `ROV-XX` para los de otras marcas. Ambas ramas encienden la marca.
  3. **El síntoma de equivocarse no apunta a la causa.** El técnico va a reportar "no me aparecen las pestañas", no "la categoría está mal". Revisar la categoría del producto antes que el módulo.
  4. Los equipos de clientes entran en consignación: la categoría dice **qué es** el equipo, la propiedad se maneja aparte. Ver [`INVENTARIO.md`](../INVENTARIO.md) § Equipos de clientes.
  5. **Llenar `mc_propietario_id` al cargar cada número de serie.** Desde `19.0.5.0.0` de ahí sale el estado comercial: un equipo vendido que quede a nombre de la empresa va a aparecer como "Disponible" y va a ensuciar la lista de flota. Los que son de clientes se cargan a nombre del cliente; los de flota se dejan como vienen, ya que el valor por defecto es la propia empresa.
  6. **Llenar también `mc_fecha_puesta_servicio`** en los equipos que ya están en terreno, o el reloj de mantención no arranca y no aparecerán nunca en la lista de vencidos.
  7. **Desde `19.0.6.0.0` hay catorce campos más que llenar por equipo**, no dos. Toda la pestaña *Especificaciones* pasó a ser obligatoria para los ROV: chasis, modelo / N° / posición de motores, ambos pesos, sensor de presión, ambas tarjetas de comunicación, controlador de vuelo y su versión, ArduSub, software de superficie y su versión, y cantidad de luces.

     **Desde `19.0.15.2.1` ya no hay obligatoriedad en ninguna parte** — ni en el modelo ni en la vista. El `required` de la vista salió porque decía lo mismo que el aviso amarillo y además era todo o nada: quien conocía 12 de las 14 especificaciones no podía guardar las 12, y la salida era inventar las otras 2.

     **Esto cambia el procedimiento de carga, y es lo más importante de este punto.** Antes el formulario frenaba una ficha a medias; ahora **nada la frena**, así que se puede guardar cualquier cosa incompleta a mano, no solo por importación. Lo que encuentra a las series incompletas es `mc_ficha_completa` y el filtro **«Ficha incompleta»** en la lista de números de serie, y desde `19.0.15.2.2` el aviso dice cuántos datos faltan de cuántos. **Después de cada tanda hay que revisar ese filtro** — antes era recomendable, ahora es el único control que queda.

     Cuidado con los numéricos: en Odoo un `Integer` o un `Float` nunca queda vacío, se lee como 0, así que N° de motores, ambos pesos y cantidad de luces pueden entrar en cero sin que nada chiste. `mc_ficha_completa` los exige `> 0` justamente por eso.

     Y **ya no hay opción «Desconocido»**: se probó en `19.0.6.0.0` y se retiró en `19.0.7.0.0`, porque la decisión es obligar a averiguar las especificaciones reales del equipo. Para los equipos anteriores a Odoo eso significa que hay que ir a levantar el dato o poner un valor supuesto — y un valor supuesto es indistinguible de uno verificado, que es el precio conocido de esa decisión. **Sacar el `required` no ablanda esa decisión, la separa**: guardar 12 de 14 deja constancia honesta de que faltan 2; inventarlas no deja ninguna.

  **Residuo a limpiar antes de cargar datos reales:** quedan 2 números de serie de prueba con `es_un_rov = TRUE` cuya cadena producto → categoría está rota; por eso la migración `19.0.2.0.0` reportó 0 filas recalculadas y no los tocó. Se apagarán solos la primera vez que algo los escriba. Conviene borrarlos para no confundirlos con equipos reales.

- [ ] **Grupos de seguridad**: los accesos actuales son sin grupo. Implementar cuando haya múltiples usuarios. Diseño acordado:

  **Dos grupos jerárquicos** (`Coordinador ROV` hereda `Técnico ROV` vía `implied_ids`):

  | Grupo | `implied_ids` (grupos Odoo arrastrados) | Acceso mc_rov |
  |-------|----------------------------------------|---------------|
  | `Técnico ROV` | `repair.group_repair_user`, `stock.group_stock_user` | CRUD en `linea.falla`; lectura en `componente`/`subtipo`/`accion`; edición de ficha técnica y campos mc_rov en `repair.order` y `stock.lot` |
  | `Coordinador ROV` | `repair.group_repair_manager`, `stock.group_stock_manager`, `purchase.group_purchase_user`, `sale.group_sale_user`, `account.group_account_invoice` | Todo lo anterior + CRUD en `componente`/`subtipo`/`accion` |

  **Implementación involucra:**
  1. `security/mc_rov_groups.xml` — definir los dos grupos con `implied_ids`
  2. `ir.model.access.csv` — reemplazar líneas sin grupo por reglas por grupo
  3. `views/` — agregar `groups=` en campos que solo el Coordinador debe editar (ej. `mc_estado_comercial`)
  4. Registrar `mc_rov_groups.xml` en `__manifest__.py` bajo `data`

  **Para asignar grupos a usuarios:** `Ajustes → Usuarios → [usuario]` (sin tocar código). Cambiar qué puede hacer un grupo requiere modificar el módulo.

- [x] ~~Validación de línea de producto en cierre de orden~~ — **hecha en `19.0.14.0.0`.**
  `mc.rov.accion.consume_repuesto`, marcado en las dos acciones de cambio, y
  `_validar_repuestos` en la transición a `done`.

  **Su alcance está declarado y conviene recordarlo:** exige *al menos una* línea de producto,
  no una por cada cambio. Una orden con tres cambios y un repuesto registrado pasa. Subir a la
  correspondencia uno a uno obliga a decir qué repuesto va con qué trabajo, que es un campo
  nuevo en la línea y otra decisión.

- [ ] **Pipeline integration touchpoints** (Phase 1 del pipeline — requiere Phase -1 completada primero): agregar `controllers/api.py`, usuario `pipeline@marine-connection` con API key, y grupo `Pipeline API (Read-Only)`. Checklist en `rov-pipeline-roadmap.md` Phase 1 "Odoo access layer". Contrato en [`integrations/pipeline.md`](integrations/pipeline.md).
