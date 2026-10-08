# Centro de trabajo — historial de implementación 2026-10-08

> Registro de ensayos y decisiones intermedias. El estado vigente está en pendientes.md.

Prioridad actual acordada: diseñar el **Centro de trabajo ROV**. Las muestras de
los puntos 1 y 2 se completarán durante la puesta en marcha, cuando existan datos
adecuados; no bloquean el diseño del centro. Propuesta de contenido y límites en
[Centro de trabajo ROV](designs/centro-trabajo-rov.md).

Maqueta C actualizada el 2026-10-08: nombres por necesidad y selección de área,
con registros existentes y creaciones separadas. Se añaden entrada Diseño/BoM
y accesos explícitos de Calidad; no se presentan como pasos obligatorios.
Nombres «Aceptar un equipo nuevo» y «Trabajar en diseño / BoM» aprobados. Maqueta
refinada con tipos de registro separados, búsqueda local, estados y filtro de
modelo en equipos; ajustes visuales aprobados.
Pasada adicional de estilo preparada: selección lateral, pestañas subrayadas,
jerarquía y espacios refinados; sin cambios de comportamiento ni despliegue.
Maqueta C y estilo aprobados por el usuario. Plan de implementación preparado en
[Centro ROV — plan](superpowers/plans/2026-10-08-centro-trabajo-rov.md).
Campos/acciones instalados contrastados con sonda de solo lectura
`../.tmp/staging-center-work-audit.ps1`; rollback confirmado por el usuario.
Destinos y estados reales incorporados al plan, aprobado el 2026-10-08.
Implementación iniciada en `feature/centro-trabajo-rov`: seis contratos backend
en `tests/test_work_center.py`; runner `../.tmp/staging-center-work-red.ps1`
preparado y validado sintácticamente. RED confirmado por el usuario: seis fallos
por servicio ausente, pruebas restauradas y STAGING activo; evidencia en
`../.tmp/center-work-qa/center-red-tests.log`.
Servicio abstracto local implementado con ámbitos/acciones compartidos, permisos
y apertura por ID exacta. Runner `../.tmp/staging-center-work-green.ps1` preparado:
seis contratos + consulta de todas las áreas. GREEN remoto confirmado: **6/6**,
cero fallos/errores; ámbitos y conteos contrastados mediante consulta con rollback.
STAGING activo; QWeb FEN/REV conserva sus hashes. Servicio backend instalado allí.
Pantalla pendiente: cinco contratos HOOT preparados en `static/tests/work_center.test.js`;
runner `../.tmp/staging-center-work-frontend-red.ps1` instala solo su bundle QA.
Bundle RED frontend instalado en STAGING (respaldo
`/var/tmp/mc-rov-center-frontend-red-wuTFtq`).
Túnel recuperado y RED HOOT observado: **5 fallos esperados por acción cliente
ausente**, sin error de importación. Evidencia `frontend-red-visible.txt` y
`frontend-red.png` en `../.tmp/center-work-qa`. Fuente instalada de `useSetupAction`
capturada en `frontend-install.json` para restaurar filtros.
Maqueta local preparada con tres composiciones, datos ficticios y destinos
simulados en `../.tmp/centro-trabajo-rov-prototype` (puerto 8079). Pantalla OWL
implementada localmente con seis áreas, filtros, selección de modelo, paginación
y acciones nativas. Runner `../.tmp/staging-center-work-frontend-green.ps1` preparado
para instalar assets sin menú. Assets reinstalados en STAGING, último respaldo
`/var/tmp/mc-rov-center-frontend-green-xTNsv9`; reportes intactos y servicio activo.
GREEN HOOT observado en navegador: **5/5**, tras completar la fixture Mail con
`defineModels(mailModels)`. Selección sin creación, ID elegida, capacidad de lectura,
restauración de filtros y descarte de respuestas atrasadas aprobados. Evidencia
`frontend-green-visible.txt` y `frontend-green.png` en `../.tmp/center-work-qa`.
Diez contratos backend ejecutados: **9 aprobados y 1 fallo esperado** por acceso
a Candidatas a lección ausente. ACL parcial, categoría ausente y compañía aprobados;
pruebas restauradas y STAGING activo. Evidencia `center-contracts-tests.log`.
Acceso a la cola nativa implementado localmente después del RED: conserva filtros
removibles de pendientes, limita al ámbito ROV/compañía y no crea alertas.
GREEN de candidatas confirmado en STAGING: **10/10**, consulta de todas las áreas
revertida, reportes intactos y servicio activo. Respaldo
`/var/tmp/mc-rov-center-work-candidates-green-uLN8T6`; evidencia
`center-candidates-green-tests.log` en `../.tmp/center-work-qa`.
Dos contratos HOOT adicionales preparados para el acceso en pantalla: abrir la
cola exacta sin crear y ocultar el acceso sin permiso. Bundle instalado y RED
observado en navegador: **6 aprobadas, 1 fallo esperado** por botón ausente;
evidencia `candidates-frontend-red-visible.txt` y captura correspondiente.
Botón implementado localmente en Calidad → Lecciones; capacidad de lectura de
la cola publicada por backend, sin sumar candidatas al conteo de lecciones.
Runner `../.tmp/staging-center-work-candidates-frontend-green.ps1` preparado:
instala assets/permiso y verifica diez contratos backend; HOOT de siete casos
ejecutado en navegador: **7/7 aprobadas**; diez contratos backend también verdes.
Respaldo `/var/tmp/mc-rov-center-candidates-frontend-green-DJ37rz`; evidencia
`candidates-frontend-green-visible.txt` y captura en `../.tmp/center-work-qa`.
Entrada ROV → Centro de trabajo implementada localmente y versión compatible
`19.0.24.3.0` preparada. Runner `../.tmp/staging-center-work-pilot.ps1` activa el
menú en STAGING, respalda BD/archivos, ejecuta la suite mc_rov y verifica acción,
conteos y QWeb intactos; retira la entrada nueva si falla la instalación.
Piloto instalado en STAGING `19.0.24.3.0`: **373 pruebas, cero fallos/errores**.
Menú activo, acción 1018; respaldo `/var/tmp/mc-rov-center-work-pilot-cMUxkc`.
Sonda con rollback y reportes intactos; producción sin cambios.
QA real: equipo 26-02 abierto y retorno por breadcrumb conserva búsqueda; fabricación
WH/MO/00011 visible; Lecciones vacías ofrece cola nativa de candidatas con filtro
«Esperando decisión». Ventana de 390 px sin desborde global (scrollWidth=390).
Evidencia `pilot-tests.log`, `pilot-desktop.png`, `pilot-mobile.png` en center-work-qa.
Dos detalles encontrados antes del cierre: ayuda HTML nativa visible como etiquetas
en listas vacías y búsqueda de modelo Petrohue sin opciones aunque su equipo aparece.
Regresión local del primer fallo observada; ajuste OWL markup implementado después,
octava prueba HOOT añadida. Runner `../.tmp/staging-center-work-help-green.ps1`
preparado para corregir assets y capturar diagnóstico de modelos de solo lectura.
Corrección de ayuda instalada, respaldo `/var/tmp/mc-rov-center-work-help-green-nOKoNQ`;
**8/8 HOOT aprobadas** y cola nativa vacía verificada sin etiquetas visibles.
Diagnóstico de modelos: Petrohue está archivado y sin categoría; Patagonia MC
también sin categoría. Sus lotes conservan es_un_rov=True y son accesibles al centro,
pero el catálogo de diseño por categoría los excluye. No normalizar datos legados
durante este cambio de navegación; el filtro debe usar modelos de equipos accesibles.
Dos pruebas añadidas antes de cambiar el filtro: modelo archivado fuera de categoría
ROV con lote legado visible, y modelo vinculado únicamente a un lote oculto por regla.
Runner `../.tmp/staging-center-work-models-red.ps1` preparado: trece contratos,
RED confirmado: once anteriores pasan y dos fallan por endpoint ausente; pruebas
restauradas y STAGING activo. Filtro corregido localmente mediante consulta de
modelos de lotes accesibles, incluyendo archivados y sin elevar permisos. Catálogo
de diseño y datos históricos permanecen intactos. Regresión frontend local falló
contra llamada anterior y pasó tras cambiar el endpoint; novena prueba HOOT añadida.
Runner `../.tmp/staging-center-work-models-green.ps1` preparado: instala ajuste,
ejecuta suite completa y comprueba con rollback cada modelo de equipos visibles.
GREEN remoto del filtro confirmado: **375 pruebas, cero fallos/errores**; los cuatro
modelos de unidades visibles disponibles, incluyendo Petrohue archivado. Reportes
intactos, sonda revertida y STAGING activo. Respaldo
`/var/tmp/mc-rov-center-work-models-green-nxiJFN`.
**9/9 HOOT aprobadas** observadas en navegador; evidencia `models-green-visible.txt`.
Filtro Petrohue abre 26-02 y se conserva al volver por breadcrumb; captura
`models-filter-return.png`. Terreno abre la revisión elegida REV/00021 sin editar.
Revisión final independiente detectó tres brechas antes de entregar el piloto:
contexto nativo propone Rendimiento desde Nueva revisión de reparación; revisiones
/FEN no filtran compañía a través de lot_id; falta selector de estado operativo de
los equipos. Tres contratos añadidos antes del ajuste (16 backend en total).
Runner `../.tmp/staging-center-work-review-red.ps1` preparado para confirmar esos
fallos contra STAGING y restaurar pruebas. RED confirmado en STAGING: **13 aprobados y 3 fallos esperados**, pruebas restauradas
y servicio activo. Evidencia `review-red-tests.log`.
Correcciones locales: contextos default_tipo por sección, ámbito de compañía por
lot_id en REV/FEN y selector operativo para equipos con filtros conservados.
Regresión local del selector observada RED→GREEN; décima prueba HOOT añadida para
el cambio de estado y su conservación entre áreas.
Runner `../.tmp/staging-center-work-review-green.ps1` preparado: suite completa,
consulta de tipos/estados/modelos con rollback, respaldo y reportes intactos.
La suite integrada pasó **378/378**; luego falló la sonda de estados con tilde y
el helper restauró el código previo, manteniendo servicio activo. No considerar
el ajuste instalado. Evidencia `review-green-response.txt` / `review-green-tests.log`.
Causa reproducida: Windows PowerShell puede enviar stdin SSH en ASCII y sustituir
ó por ?. Runner corregido con escapes Unicode en código de sonda ASCII; contrato
backend ampliado a los tres estados. Reejecución limita a los **16 focalizados**,
con respaldo, rollback y consulta real, sin repetir suite completa ya aprobada.
Instalación corregida confirmada: **16/16 contratos**, los tres estados consultados
(Operativo 3, En mantención 0, En reparación 1), cuatro modelos disponibles y tipos
reparación/rendimiento/terreno correctos. Sonda revertida, reportes intactos y
STAGING activo. Respaldo `/var/tmp/mc-rov-center-work-review-green-SrgKLa`.
Intento HOOT bloqueado por conexión local rechazada: túnel 8070 sin listener;
túnel reabierto por el usuario. HOOT ejecutado: **9 pasan y 1 falla**.
La décima verifica el estado operativo al cambiar de área: petición conserva En
reparación, pero el select remonta mostrando all. Regresión observada en navegador,
evidencia `state-selector-red-visible.txt`. Corregido localmente el binding OWL
(t-model en lugar de atributo value); no cambia consultas ni filtros persistidos.
Runner `../.tmp/staging-center-work-state-selector-green.ps1` instala solo assets,
no repite suite backend y verifica sus hashes junto con reportes intactos.
Primer binding reinstalado, respaldo state-selector-green-6l6VGn. HOOT real sigue
**9 aprobadas / 1 fallo**: t-model no conserva el valor visible al cambiar el conjunto
condicional de opciones. Evidencia `state-selector-model-red-visible.txt`.
Corrección local refinada: opciones con selected explícito desde filter.state_filter,
con evento change existente; sin cambios backend. Assets finales instalados:
respaldo `/var/tmp/mc-rov-center-work-state-selector-green-8FSlGt`, servicio activo
y hashes backend/reportes conservados. **10/10 HOOT aprobadas** observadas después
de recargar y ejecutar el bundle; evidencia `state-selector-green-visible.txt`.
Selector operativo muestra En reparación y filtra solo serie 0000008.
Abrir ese equipo y volver por la ruta superior conserva el filtro y el resultado;
evidencia `../.tmp/center-work-qa/state-selector-return.png` y su snapshot de texto.
Pendiente aprobación manual del piloto antes de cerrar rama/PR/producción.
Revisión visual del usuario detectó contornos abiertos en las tarjetas: el borde
izquierdo no seleccionado era transparente. Corregido localmente a gris #dce1e6,
sin alterar dimensiones ni selección morada. Instalación y QA visual pendientes;
runner `../.tmp/staging-center-work-card-border-green.ps1` instala solo SCSS.
Borde instalado y verificado en STAGING (respaldo card-border-green-gxD2V2).
Detectado scroll inaccesible: raíz de Centro mide 1319 px dentro de contenedor
Odoo de 622 px con overflow hidden. Corrección local limita altura a 100% y
min-height a 0; conserva overflow auto. Instalar con
`../.tmp/staging-center-work-scroll-green.ps1` y verificar llegada al pie.
Instalado y verificado en STAGING, respaldo scroll-green-TVXkIc: altura 622 px,
contenido 1337 px y scroll hasta el final (714.4 px). Barra vertical visible;
tabla y controles inferiores accesibles. Evidencia `../.tmp/center-work-qa/scroll-bottom.png`.
Usuario solicita probar «Centro de trabajo» como nombre del acceso de aplicación
en lugar de «ROV». Cambio local solo en menu_mc_rov_root; título y acción conservados.
Instalación pendiente con `../.tmp/staging-center-work-menu-name.ps1`; revisar
legibilidad del nombre en el menú antes de aprobar el piloto.
Nombre aprobado por usuario. Elegida propuesta de icono de conexiones (B),
refinada con geometría y superposiciones de color inspiradas en los iconos
Odoo instalados: amarillo, coral, turquesa y morado, cruces más oscuros.
PNG 256 px y fuente SVG locales en static/src/img/work_center_icon.*;
web_icon configurado en el menú. XML/SVG/PNG y runners validados.
Usuario autoriza cerrar y shippear; pendiente instalación final del icono con
`../.tmp/staging-center-work-icon.ps1`, comprobación visual y cierre de rama/PR
antes de preparar despliegue a producción. No confundir aprobación con deploy hecho.
Icono refinado v2 tras feedback: colores tomados de captura Odoo (#FBB945,
#FC868B, #1AD3BB, #985184), cuatro círculos iguales en una grilla simétrica,
brazos de igual ancho que pasan por sus centros y cruce común en (128,128).
Superposiciones por mezcla multiplicativa; no se afirma replicar el algoritmo
interno de los iconos originales. Preview icon-final-preview-v2.png;
el runner de icono existente recoge los archivos actualizados.
Instalación e interfaz verificadas en STAGING; producción todavía sin cambios del centro.
Issue QA preparado localmente; publicación GitHub rechazada por revisión automática
por falta de autorización explícita para transmitir el diagnóstico. Autorización solicitada.
Black local no ejecutado: carga DLL denegada por sandbox y revisión automática
rechazada por falta de créditos del workspace; sintaxis y diff-check aprobados.
No listo todavía para merge/producción.
No hay merge ni despliegue del centro en producción.
No se recupera la guía lateral descartada; no se crean tareas personales ni nuevos
requisitos de cierre. Las decisiones documentales se conservan en la rama feature.
