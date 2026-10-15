# Trabajo pendiente

## Piloto de actividades automáticas — 2026-10-15

- Etapa 1 instalada en STAGING: política por empresa y cálculo de 2 días laborables, **14/14 pruebas GREEN** tras RED 14/14. No genera actividades todavía. Lint 10/10, formato y XML verificados.
- Respaldo de instalación `/var/tmp/mc-rov-repair-calendar-green-8QxoWu`; PDFs intactos, pruebas temporales restauradas, servicio active. Calendario empresa America/Santiago conservado.
- Recuperación previa completada y verificada con restore en base nueva; base anterior preservada `odoo_staging_preserved_8iFkRF`, respaldo `/var/tmp/mc-rov-calendar-fresh-8iFkRF`. Evitar pg_restore clean sobre base viva o transacción global: fallaron por FKs nuevas y límite de locks.
- Rama feature/repair-activities desde b9bbd63. Plan/spec en docs/superpowers. Sigue generación única de diagnóstico/reparación, luego cierre y permisos. Sin merge ni producción.

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
