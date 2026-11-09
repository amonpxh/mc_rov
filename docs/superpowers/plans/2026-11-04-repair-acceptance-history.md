# Historial de aceptación final de reparación Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Mantener el método autorizado, con revisión independiente final.

**Goal:** Conservar los intentos de revisión final por visita/serie sin confundir diagnóstico, reapertura o aprobación posterior con primer pase.

**Architecture:** Extender revisión con finalidad explícita y un historial privado e inmutable. Capturar únicamente la confirmación validada de una revisión final; conservar evidencia existente y reutilizar el núcleo puro empresarial. No conectar todavía el tablero ni imponer nuevos ensayos reales.

**Tech Stack:** Odoo19, Python, PostgreSQL, unittest/TransactionCase y vistas nativas.

**Spec:** docs/superpowers/specs/2026-11-04-kpi-catalogo-consolidado.md

## Global Constraints

- Base productiva19.0.25.6.0 intacta; instalación real y destinatarios no autorizados por este plan.
- Reutilizar25 chequeos instalados; no sustituirlos por semillas ni reactivar quality.point.
- Revisión final de reparación diferenciada del diagnóstico; finalidad nueva sin clasificación retrospectiva automática.
- Observación informativa exige requisitos aprobados y ausencia explícita de corrección/reensayo.
- Historial no concede acceso al origen ni a otras empresas; identidad de orden/serie protegida.
- No cambiar plazos, stock, aprobaciones de Ingeniería, PDFs emitidos o guard de actividades automáticas.
- No inferir empleado desde cuenta ni umbrales técnicos desde comentarios.

## Review Focus

1. Confirmación repetida/concurrente no duplica intento; reapertura real y nueva confirmación sí crea otro.
2. Confirmación fallida revierte también la captura; datos históricos no se recalculan desde revisión actual.
3. RPC/contexto no puede escribir un primer veredicto falso ni saltar validación nativa.
4. Diagnóstico histórico o revisión confirmada importada no crea una aceptación retrospectiva.
5. Historial privado no filtra resultados de documentos restringidos, incluso al cambiar empresas.

## Archivos y contratos propuestos

- Create models/repair_acceptance_history.py: modelo privado `mc.rov.repair.acceptance.attempt` y API de lectura protegida.
- Create models/repair_acceptance_capture.py: extensión de revisión y confirmación validada.
- Modify models/__init__.py: registrar únicamente esos dos módulos al instalar GREEN.
- Seguridad: sin ACL pública ni regla nueva para historial privado, como los historiales existentes; comprobar origen y empresa antes de consultas sudo. No modificar permisos del origen.
- Create tests/test_repair_acceptance_history.py: escenarios nativos focalizados.
- Modify tests/__init__.py: registro de las pruebas temporales para RED y definitivo en rama.
- Interfaz visual de clasificación final se añade después del GREEN de modelo, con pruebas propias.

**Revisión:** `mc_acceptance_purpose` en unset/diagnostic/final, default unset;
`mc_correction_required` y `mc_retest_required` en unknown/no/yes, default unknown.
No cambiar motivo existente. La finalidad final requiere tipo reparacion, repair_id
y lot_id coherentes. Clasificar solo en borrador; historial existente protege identidad.

**Intento:** repair_id, lot_id, revision_id, ordinal, confirmed_at, actor_id,
responsable_id cuando exista, verdict_snapshot, correction_snapshot, retest_snapshot,
requirements_snapshot y configuration_digest. Datos guardados, no related a valores
mutables. Identidad del episodio: orden de reparación+serie; ordinal único por episodio.
El digest identifica la configuración capturada, no certifica por sí solo un protocolo.

**Lectura:** `_get_repair_acceptance_attempts(repair)` comprueba usuario interno,
consulta del equipo, empresas y lectura de repair/revision antes de acceder al historial.
Sin ACL pública para leer/escribir directamente la tabla; errores de acceso no se
convierten en cero intentos. Reutilizar patrón de historial privado ya existente.

**Inicio formal:** `action_start_final_acceptance()` exige finalidad final y origen
válido, bloquea episodio y reserva ordinal pendiente con requisitos capturados.
Repetir inicio devuelve el intento pendiente, no otro ordinal. Cambiar catálogo no
altera requisitos de ese intento; inconsistencias con evidencia actual impiden sellarlo.

**Captura:** override `action_confirmar()`; validar fuente y bloquear episodio antes
de leer transición. Ejecutar super nativo y solo después anexar evidencia de la
transición borrador→confirmado de revisión final con intento pendiente iniciado.
Finalizar ese intento con snapshot de respuestas,
inspecciones y resultado del intento confirmado, no únicamente IDs del catálogo.
Un contexto RPC no autoriza crear historial; capacidad interna no serializable.
Rechazar creación/edición/borrado arbitrarios de intentos; pendiente solo cambia por
acciones internas validadas y se vuelve inmutable al finalizar. No atrapar errores de
serialización: conservar reintento transaccional Odoo y restricciones únicas.

Una escritura directa de estado no puede inventar aceptación final eludiendo
action_confirmar; mantener las escrituras y fixtures diagnósticos previos intactos.
Volver a borrador conserva intento anterior; nuevo inicio reserva otro ordinal.
Doble confirmación de la misma revisión ya confirmada no genera otro intento.

**Fallo que interrumpe:** `action_abort_final_acceptance(reason)` sella el intento
pendiente como failed sin forzar confirmación de revisión incompleta. Exigir motivo
y evidencia de fallo real (chequeo no_ok, condición rechazada o hallazgo bloqueante
del intento); una nota libre no basta. Guardar snapshot parcial. Mantener borrador
nativo; un nuevo intento requiere nuevo inicio explícito, conservando el fallo.
Repetir interrupción sobre el mismo intento no crea otro. No clasificar invalidación
de instrumento como fallo real ni permitir borrar fallo real mediante invalidación.

## Task1: RED nativo y controles del recorrido

- [ ] Verificar fixtures de RevisionCommon usando action_confirmar real; no usar
  helper _emitir que fuerza estado para comprobar capturas.
- [ ] Añadir controles: diagnóstico no capturado; revisión incompleta rechazada;
  checklist generado según tipo sin modificar configuración instalada.
- [ ] Añadir contratos ausentes: finalidad final explícita; fallo→reapertura→aprobación
  conserva fallo; cambio de catálogo no reescribe snapshot; notas informativas con
  flags no/no pasan; flags unknown conservan cobertura desconocida; corrección/retest
  yes fallan primer pase; confirmación duplicada no duplica ordinal.
- [ ] Añadir interrupción con protocolo incompleto: fallo real registrado, revisión
  sigue borrador, segundo intento aprobado mantiene failed en primer pase; inicio/
  interrupción duplicados no crean ordinales adicionales ni confirmaciones falsas.
- [ ] Añadir límites: RPC no crea/edita historial, empresas/origen restringido,
  identidad protegida y rollback completo si falla confirmación o captura.
- [ ] Preparar transporte test-only desde baseline instalado139, respaldo y restauración
  de pruebas, sin instalar producto; nombres exactos obtenidos de AST de estos tests.
- [ ] Ejecutar mediante SSH privado y exigir fallos de contratos ausentes únicamente,
  controles verdes y cero errores de fixture. No implementar antes de observar RED.

## Task2: GREEN de captura y privacidad

- [x] Implementar campos/modelo/API anteriores con pruebas de permisos por origen;
  usar los campos de empleado existentes y guardar actor de cuenta por separado.
- [x] Capturar configuración vigente y resultado tras super; ningún snapshot histórico
  se completa desde chatter, tipo de secuencia ni fecha de última modificación.
- [x] Comprobar mismas pruebas focalizadas y controles de revisión/seguridad anteriores.
- [x] Preparar instalación solo STAGING con respaldo y recuperación probados; conservar
  la fallida si ocurre error, sin instalar perfiles ni destinatarios reales.
- [x] Comprobar hashes, datos, stock, configuración y PDFs emitidos intactos.

## Task3: Clasificación visible y lectura empresarial

- [ ] Vista nativa: finalidad explícita en borrador y requisitos de clasificación;
  comunicar que marcar final no confirma prueba ni libera/saca equipo.
- [ ] Lectura de intentos desde origen autorizado, sin acceso técnico a Ventana de acción.
- [ ] Adaptar evidencia a first_pass_status; lista ordenada solo del episodio formal,
  nunca todas las revisiones/diagnósticos de la serie.
- [ ] QA Taller/Supervisor ficticios, empresas y notas con/sin corrección; comprobar
  que la selección no altera actividades existentes ni equivale a Hecho genérico.
- [ ] Regresión integrada y concurrencia en copia aislada; revisión final y commit.

## Estado y dependencias

RED nativo52 confirmado (13 ausentes y39 controles); GREEN focalizado52/52 instalado
solo en STAGING, intento20261104-165400-603, backup
/var/tmp/mc-rov-repair-acceptance-green-HSL19z. Captura/no-retroactivos, hashes141,
configuración y pruebas restauradas verificados. Interfaz nativa instalada tras GREEN82/82, intento20261104-173022-174, backup
/var/tmp/mc-rov-repair-acceptance-presentation-green-VrwEcR.142 fuentes verificadas;
pendiente comprobación visual. Controles de permisos y rollback aprobados72/72.

Permisos/origen/empresas y rollback comprobados por los20 controles adicionales.
Pendientes: regresión completa1328, concurrencia aislada, revisión visual y revisión
independiente final. No declarar la entrega integral todavía. La liberación completa
aún requiere evidencia documental/NC, y compromisos/bloqueos/retornos tienen incrementos
separados. No presentar esta captura como entrega del tablero de11 familias.

### Concreción de interfaz nativa (decisiones de implementación)

En la misma revisión: finalidad y corrección/reensayo explícitos; indicador de intento
pendiente, botón Iniciar intento final y motivo de fallo con acción Registrar fallo.
Esta última delegará en la interrupción validada: exige evidencia real y no confirma
una revisión incompleta. Confirmar final solo visible tras inicio pendiente. No añade
Hecho, Cancelar ni retirada genérica del seguimiento.

Historial HTML calculado, sin almacenar ni conceder ACL al modelo privado, campo
restringido a consulta del equipo. Cada lectura valida origen/empresas antes de sudo;
texto libre escapado, conserva primer rechazo y aprobaciones posteriores. No consulta
Ventana de acción ni crea asistentes. Un fallo requiere motivo introducido en borrador.
RED UI:8 contratos ausentes y2 controles nativos, junto con72 anteriores =82.

### Verificación integral y concurrencia preparada

Full1328/1328 comprobado20261104-173604-112, backupF7Y66w, fuentes142 y datos intactos.
Sin cambio de producto desde cc8022e y sin reemplazar casos anteriores. Preparado
probador nativo de siete carreras en copia neutralizada: inicio repetido, dos revisiones
del mismo episodio, doble confirmación, doble interrupción, reinicio tras fallo seguido
de aprobación, rollback frente a confirmación y finalidad frente a inicio. Exige ordinales
consecutivos, máximo un pendiente por episodio, cero intentos huérfanos, conservación
del primer rechazo y actor correcto cuando otro cierre se revierte. Usa usuarios propios
con permisos nativos; eventos sin sudo. No ejecutar contra STAGING directamente.

Concurrencia7/7 nativa verificada20261105-090113-594; copia y BDyz8uRM
preservadas/bloqueadas. Primer rechazo inmutable, ordinales coherentes, cero intentos
huérfanos, rollback no roba autor del cierre real. QA visual y revisión final pendientes.

### Hallazgos de revisión independiente y lote RED93 (2026-11-05)

Antes de declarar terminado el incremento, corregir estos defectos demostrables:
1. P1: el digest basado en catálogo mutable impide cierre normal y por fallo tras
   renombrar/reordenar; Actualizar checklist puede alterar el alcance durante pendiente.
2. P2: faltan componentes en requisitos/evidencia de chequeos e inspecciones.
3. P2: create mira vals incompletos, sin defaults efectivos, y admite final confirmada.

Test-only93 preparado:9 regresiones y2 controles nuevos, mantiene82 previos. Exige
9 fallos concretos/84 verdes/0errores. No cambiar producto antes de observar ese RED.
Dirección de corrección: conservar configuración original, separar identidad/alcance
estructural de metadatos vivos; impedir alteraciones estructurales de un intento abierto
sin ofrecer retirada genérica ni borrar fallos. Completar identidad congelada de cada
componente y validar finalidad/estado efectivos incluidos defaults. Mantener edición
normal de respuestas y flujo diagnóstico. Definir cobertura adicional estructural si
surgen más entradas públicas equivalentes; no reducir a ocultar botones.

RED93 confirmado20261105-092032-493 (9fallos/84verdes, backupWERXY1).
Fix local: schema2 congela componente/nombre en requisitos de chequeos e inspecciones;
evidencia conserva componente/detalle. Cierre valida scope de filas e identidad y usa
configuración/digest inicial, sin comparar nombres/secuencias de catálogo vivo.
Guards de create/write/unlink de ambas líneas y refresh toman locks antes de consultar
finalidad; reparación→revisión incluye diagnóstico aún sinrepair y se revalida tras
invalidar caché. Respuestas continúan editables; no retirada genérica. Defaults efectivos
validados antes de create y estado final revalidado después. Vista oculta refresh pendiente.
Revisor original acepta por inspección los3hallazgos y la carrera adicional. Falta caso8
real clasificación/inicio vs edición de componente de inspección con snapshot anterior.
GREENfull1339 preparado, sin instalar:2productos/baseline142, recupera freshDB anterior,
snapshot íntegro y82contratos anteriores conservados además del resto de1328 previos.

GREENfull1339 nativo aprobado20261105-094259-101, backupZbbonp,142 fuentes y datos
intactos. Correcciones de revisión instaladas, sin ACL/esquema/activación real.
Paquete8races preparado y NO ejecutado: anterior7 archivado, nueva clasificación/inicio
sobre diagnóstico aún sin orden vs cambio tardío de componente; evento garantiza que
ambos lean antes y que el intento se confirme transaccionalmente antes del cambio.
Exige bloqueo del cambio, vínculo final válido y scope de inspección intacto. Arreglo
sin orden cubierto por lock de revisión además del padre; validación real pendiente.

Concurrencia8/8 nativa aprobada20261105-100833-976, copyUaTSL5 bloqueada/conservada.
El cambio de componente posterior a clasificación/inicio desde snapshot antiguo se
rechaza y conserva alcance; producto sin cambios desde full1339. Preparada QAvisual
nueva en copia8071 con empresa/roles/seriales/4recorridos propios, automatismos apagados;
no reutilizar ni abrir las copias de carreras. Falta seed nativo, visual y cierre QA.

### QA visual ejecutada — 2026-11-05

Seed nativo aprobado en copia mc_rov_repair_acceptance_qa_tnuRgD, empresa1503,
work /var/tmp/mc-rov-repair-acceptance-operational-qa-tnuRgD. Sin cambios a STAGING
o producción ni activaciones reales. Acceso exclusivamente en IAB de Codex.

- Taller: diagnóstico20527 confirma sin iniciar aceptación formal; normal20528
  inicia y confirma Aprobado con identidad protegida; fallo20529 registra motivo,
  conserva borrador y permite iniciar otro intento. No ve historial privado.
- Supervisor:20528 conserva un intento aprobado por Taller;20529 conserva un intento
  rechazado con su motivo y autor;20530 muestra rechazo seguido de aprobación sin
  sustituir el primer resultado. Tabla sin edición directa.
- Claro y oscuro, escritorio1440x1000 y móvil390x844 inspeccionados. Tabla móvil en
  contenedor con overflow auto, página390px; tema Sistema y viewport restaurados.
  Cuatro capturas y recibo Taller guardados en preparacion-uso-real-pilot.

Sin defectos nuevos observados ni cambios de producto; full1339 y carreras8 previos
siguen siendo la evidencia nativa. Falta cerrar la copia con el script preparado,
respaldando historial y bloqueando conexiones; no recrear escenarios.

Orden final solicitado por usuario e instalado con validación nativa en STAGING y
QA: Sellos, Mediciones, Chequeos, Hallazgos, Aceptación final. Solo movimiento de página
XML, respaldo /var/tmp/mc-rov-repair-tab-order-c4kTMU; datos intactos. Nueva apertura
de20530 y captura repair-acceptance-tab-order-verified.png confirman orden/historial.
Cierre QA ejecutado y recibo verificado2026-11-05: servicio detenido, conexiones
bloqueadas, historial respaldado/conservado, STAGING activo. No cambios a producción.
Incremento validado solo en STAGING; integración/entrega y adaptador KPI pendientes.
