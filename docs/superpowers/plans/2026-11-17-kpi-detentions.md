# F2: detenciones — plan de implementación

> Ejecución nativa con superpowers:executing-plans y TDD; revisión independiente final.

**Objetivo:** medir detenciones efectivas sin modificar el flujo nativo de las órdenes.
**Arquitectura:** motor puro de unión de intervalos; historial privado autorizado por
origen; asistentes Odoo y agregador del tablero. UTC interno, America/Santiago en UI.
**Tecnología:** Python, Odoo19, PostgreSQL y vistas nativas; sin dependencias nuevas.
**Especificación:** ../specs/2026-11-17-kpi-detentions.md y catálogo2026-11-04.

## Límites globales

Sin producción/STAGING/QA, cuentas, políticas, stock o datos reales en la fase local.
Sin tasas con denominadores inventados, retroactividad, suma doble ni permisos nuevos
sobre fuentes. No publicar/merge/desplegar sin el alcance correspondiente.

## Foco de revisión

Entradas inválidas, intervalos futuros, solapes entre causas/órdenes, cierres repetidos,
RPC/contexto falsificado, empresa ajena y carrera inicio/cierre/fin nativo.

## Tareas

1. **Motor puro** — models/detention_kpi_metrics.py y tests/unit/test_detention_kpi_metrics.py.
   API summarize_detentions(orders, intervals, start, end, cutoff), UTC naive explícito.
   - [x] RED: unión, corte, causas no aditivas, orden/causa inválidos, sin evidencia.
   - [x] GREEN y controles puros existentes; no conectar con tablero aún.
2. **Captura** — models/detention_history.py, models/detention_capture.py y pruebas
   tests/test_detention_capture.py. API privada por origen; fuente bloqueada antes
   de escribir; inicio/fin/actor/empleado y vínculo protegidos.
   - [x] RED nativo:20ausencias de servicio,4controles y0errores. Los escenarios de
     autorización/empresa/idempotencia/rollback se ejercitarán realmente enGREEN.
   - [x] GREEN de captura: 24 casos reales, cero fallos y errores.
   - [x] Matriz focalizada de 35 casos y ocho carreras nativas, v3 confirmado el 18nov.
     No concede membresías reales; cierre normal y movimientos aprobados después en45+10 (18nov).
   - [x] Preparados24contratos:20ausenciasdelservicio y4controles nativos. Ejecutor
     en copia con PostgreSQL propio, sin red/HTTP/cron, verificación de fuente y
     bloqueo/parada propios al terminar. No ejecutado en servidor todavía.
3. **Presentación y consulta** — asistente temporal, vistas por origen, servicio y
   sección F2 con cobertura y etiquetas de tiempos no aditivos.
   - [ ] RED de vistas/servicio y de navegador, conservando casos anteriores.
   - [ ] GREEN, concurrencia, regresión integral y QA visual en entorno autorizado.
4. **Entrega** — revisión independiente, continuidad y diff; preparar paquete concreto
   de pruebas/instalación. Informar explícitamente qué se verificó localmente y qué
   exige Odoo/servidor. No declarar listo el F2 completo por aprobar solo el motor.

## Registro de decisiones y evidencia

- Trabajo aislado nativo en feature/kpi-detentions desde f67f997. No se modificó
  el checkout anterior ni sus notas pendientes de despliegue.
- RED observado40fallos concretos por motor ausente; GREEN43contratos después
  de aclarar cobertura histórica y causa repetida.8casos del verificador RED,
  incluido rechazo de mensajes redistribuidos entre dos fallos.
- Suite pura completa145/145. Pruebas nativas24 y ejecución Unix/PostgreSQL
  pendientes. models/detention_kpi_metrics.py todavía no está conectado al ORM,
  al tablero ni a las órdenes. Los contratos nativos se cargan solo en la copia.
- Revisión independiente: unión/corte/DST correctos. Se corrigió una ventana de
  descubrimiento de la copia por cron usando clúster PostgreSQL propio, no el
  operativo. Motivos de fallo ahora se comprueban por identidad individual.
- Ruling: duración/cobertura desconocida describe la historia suministrada de la
  población, rotulada population_history; no es tasa de cobertura del período.
- Ruling: no implementar captura antes de observar su RED real. No hay Odoo local
  ni acceso SSH vigente para este alcance. El acceso temporal de producción fue
  revocado y no se amplía a STAGING. El siguiente paso requiere ejecutar el paquete
  concreto en servidor con autorización/autenticación del usuario.

## Diagnóstico real y siguiente intento

STAGING observado19.0.25.2.0, no8.0. El primer intento abortó antes de crear
la copia. El paquete actual toma esos datos y actualiza solamente su copia en
PGprivado a fuente f67/8.0. Antes/después sella los168archivos reales y exige
exactamente las28diferencias de nombres/tipos diagnosticadas. No hay SHA
previo de esas28rutas en el diagnóstico: se acredita conservación desde el
inicio del nuevo intento. Revisión y148pruebas puras aprobadas; RED nativo
pendiente. No modificar STAGING para hacerlo coincidir.

## Captura local y GREEN

RED confirmado en intento25e4c2ef77054d798af450400ad1e7e5; copiaeFHXHu bloqueada
yPG detenido. Implementados detention_history.py ydetention_capture.py con
importación ORM; versión candidata19.0.25.9.0.161pruebas puras, lint/formato y
revisión independientes aprobados. SinACL general del historial, fuente autorizada,
guardas de empresa y finporcierres nativos. get_intervals no expone historial
de otra empresa. Todavía no se acredita GREEN real ni carreras/matriz ampliada.
PaqueteGREEN usa tarbasef67 más5overlays exactos y mismo ejecutor privado validado
enRED; la firma del recibo describe bytes del tar. Ejecución solicitada al usuario.

## Resultado GREEN y frontera RPC

Captura24GREEN real confirmada17nov, intento78e4f2c135be4af187ff0211c7b6efd4:
0fallos/errores,fuente/PIDpreservados,copiajQxV13bloqueada/PGdetenido. No reabrir.
Se prepara sondeo25 sobre ese código CONGELADO, sin arreglar todavía la sospecha
de defaultsRPC.1nuevofallo concreto esperado y24controles previosverdes. Native
RPC RED aún pendiente; si pasa25/25, estudiarporquéno se reproduce en vezde
alterarproducto otest artificialmente.166pruebas puras y revisión delpaquete pasan.

## Sondeo RPC y siguiente matriz — 2026-11-17

El sondeo nativo ejecutó 25 casos verdes; no reprodujo el cierre falso por defaults.
El driver esperaba un fallo y por eso rechazó el intento. Se conserva el resultado
positivo sin modificar producto, ni relajar el contrato del driver RED original.
Copia WI6T33 bloqueada y PostgreSQL detenido; comparación final de archivos no
alcanzada por ese driver. Evidencia exacta en el resumen vigente de pendientes.

Preparada matriz de 35 casos sobre source.tar idéntico al GREEN24: 24 originales,
control RPC y diez fronteras de acceso/empresa/identidad. 170 pruebas puras,
formato, linter, transporte y CheckOnly locales aprobados; revisión focalizada sin
hallazgos materiales. Ejecución Odoo de esta matriz pendiente; no sustituye carreras,
integral ni presentación del F2. No actualizar ni reiniciar entornos operativos.

## Lote de concurrencia y acceso temporal autorizado

El usuario autorizó preparar acceso temporal y concurrencia para ejecución autónoma.
Se conserva el producto congelado GREEN24 y la matriz nativa de 35 casos. El lote
crea otra copia y PostgreSQL privado: ocho carreras, cuatro por origen Reparación/
Fabricación, con conexiones independientes y reintento acotado de serialización.
Escenarios: inicio duplicado, fin duplicado, inicio frente a cancelación nativa y
rollback de inicio frente a inicio comprometido. Verificar identidad, autores,
inicio conservado, fin único y ausencia de intervalos abiertos en origen cancelado.

Acceso: clave nueva generada por el activador en el terminal del usuario, carpeta
privada fuera de Git; comando forzado y hashes de todos los archivos congelados.
Solo ejecutar una vez, consultar resultado y revocar la línea exacta de esa clave.
Caducidad de dos horas calculada en servidor; sin shell, forwarding ni subida libre.
La activación instala únicamente el ejecutor y paquete de pruebas, no ejecuta tests.
Preparar pruebas puras negativas del acceso/verificador, revisar paquete y después
solicitar una activación autenticada. No instalar o reiniciar entornos operativos.

Lote concreto preparado en Code/.tmp/kpi-detentions-races. 180 controles puros,
revisión focalizada y validación de transporte aprobados. Activación remota y
carreras nativas pendientes. El sondeo confirma bloqueo real antes del rollback;
los PIDs iniciales se conservan aunque el pool reutilice conexiones al reintentar.
El log de Odoo se fija a la copia privada y se une con consola antes de verificar.
No ejecutar este sondeo desde stdin como módulo importable: Odoo shell proporciona
`env` en globals; el script comprueba socket/base privados antes de crear fixtures.

## Ejecución autónoma y corrección del auxiliar — 2026-11-18

35 controles y dos carreras aprobaron; el resto no quedó acreditado porque el
auxiliar usaba action_cancel en Reparación. Acción correcta comprobada en los
contratos nativos: action_repair_cancel. Delegación por origen corregida, prueba
local RED→GREEN y 181 controles puros. Revisión focalizada sin hallazgos materiales.
Copia g5bpmn bloqueada y PG detenido, clave revocada; fuentes finales no comparadas
por aborto anterior. Evidencia y paquete anterior preservados. Nuevo v2 requiere
activación inicial para ejecutar las mismas ocho carreras con código de producto
idéntico. No ampliar la autorización del acceso consumido.

## RED real de cancelación MRP y candidato v3 — 2026-11-18

V2: 35 nativos y seis carreras verdes; MRP inicio/cancelación deja intervalo
abierto. _compute_state nativo deriva cancel de stock.move; write(state) no basta.
Nueva guarda _action_cancel con lock antes/super/filtrado final/reconciliación y
retorno nativo. 182 pruebas puras y revisión focalizada aprobadas. Misma población
35+8, sin relajar controles. V3 modifica solo detention_capture.py del producto.
La copia GPyAYx está bloqueada, PG detenido y acceso revocado; no reabrir.
V3 pendiente de activación/ejecución. Comprobar luego también finalización normal
y caminos directos de movimientos antes de entregar la función completa.

## V3 confirmado y cerrado — 2026-11-18

35 casos nativos y ocho carreras exactas aprobados. Cancelación MRP corregida
con el mismo contrato que falló en v2. Huellas/PID STAGING preservados; copia
h9Vvqt bloqueada, PostgreSQL detenido y acceso revocado. Evidencia vinculada por
SHA en Code/.tmp/kpi-detentions-races-v3/verified-result.json. No reabrir/repetir.
No acredita todavía finalización normal MRP, cierres directos por movimientos,
interfaz, consulta agregada del tablero, regresión integral o QA visual F2.

## Continuación autorizada: cierre normal y movimientos antes de UI — 2026-11-18

Brief: comprobar caminos nativos sin escribir estados/stock artificiales ni
reconstruir historia. Diez contratos nuevos en test_detention_manufacturing_events,
con los35 previos y producto v3 idéntico. Sondeo45 clasifica solo ausencias de cierre
acotadas y rechaza errores/regresiones; no fuerza reproducción ni cantidad de RED.
Ocho carreras previas no se repiten con producto idéntico. Si aparecen ausencias,
corregir solo después del resultado real y probar esos mismos contratos.

Paquete/activador preparados, 188 pruebas puras y controles locales aprobados;
activación y ejecución nativa pendientes. UI sigue después: acciones nativas para
registrar inicio y reanudación de una causa, historial protegido según origen y
empresa, sin Hecho/Cancelar manual sobre automáticas. Agregado F2 conserva unión
de intervalos, causas no aditivas, horas-orden, corte actual y cobertura histórica
explícita. Falta evidencia no se convierte en cero. No agregar grupos/permisos
sobre órdenes o empleados ni abrir ACL general del historial para mostrarlo.

## Caracterización nativa y corrección de movimientos — 2026-11-18

45 casos:43 verdes y dos ausencias exactas de cierre por stock, sin errores.
Copia voeiqi bloqueada, PostgreSQL detenido, fuente/PID preservados, acceso revocado.
Root cause confirmado: esos caminos no pasan por write(state) ni cancelación MRP.
Añadido StockMoveDetentionCapture en el mismo archivo, observando movimientos
nativos y reconciliando solo estado final. No modifica cantidades ni retorna otra
acción. Los movimientos sin seguimiento no adquieren requisitos de acceso MRP.

Siguiente lote: mismos45contratos en GREEN, más10carreras (ocho previas y dos de
primer inicio frente a cierre/cancelación directa de stock). Los nuevos casos
parten sin historial y deben verificar conflicto/reintento por estado almacenado;
no asumir ese comportamiento hasta ejecutar el lote real. Producto modificado en
un único archivo;190pruebaspuras y revisión focalizada aprobadas. Paquete/activador
listos, ejecución nativa pendiente. UI/tablero después, sin ampliar acceso revocado.

## Captura completa focalizada y siguiente RED69 — 2026-11-18

GREEN45+10 real verificado: cierres normales, asistentes pendientes, parciales,
movimientos y diez carreras. Fuente/PID preservados, copia4c7uIO bloqueada y PG
parado, acceso revocado. No repetir con producto idéntico.

Siguiente brief: asistentes nativos de inicio/reanudación e historial autorizado,
servicio mc.rov.detention.kpi y sección F2 del tablero. Preparados12+12 contratos,
con todos45controles previos (69exactos), sobre la fuente GREEN idéntica. RED exige
24ausencias específicas y cero errores; no sustituye controles.194pruebaspuras y
revisión focalizada aprobadas. Activación/ejecución nativa pendientes; no se escribió
todavía producto UI/KPI antes de observar ese RED.

Contratos de implementación fijados: asistente por repair_id o production_id,
decision start/finish, causa, responsable público y explicación; intervalo a cerrar
identificado explícitamente (interval_key), nunca una nueva ocurrencia elegida solo
por causa. Validar pertenencia/origen al confirmar aunque el contexto default sea
falso. Historial sin ACL general, HTML escapado y cálculo sin sudo del usuario.
Consulta F2 con permiso de equipo/origen/empresa; fechas de Santiago y corte del
servidor; process all/repair/manufacturing. Opcional detention_filters al tablero
para no reinterpretar sus otros seis procesos. Mostrar órdenes actuales frente a
duración del período, horas-orden y causas no aditivas; sin evidencia histórica no
hay ausencia demostrada. No tocar políticas reales o datos anteriores.
