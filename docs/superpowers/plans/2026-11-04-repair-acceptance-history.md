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
- Modify security/ir.model.access.csv y security/mc_rov_security.xml: historial privado y frontera empresarial, sin ampliar permisos del origen.
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

- [ ] Implementar campos/modelo/API anteriores con pruebas de permisos por origen;
  usar los campos de empleado existentes y guardar actor de cuenta por separado.
- [ ] Capturar configuración vigente y resultado tras super; ningún snapshot histórico
  se completa desde chatter, tipo de secuencia ni fecha de última modificación.
- [ ] Comprobar mismas pruebas focalizadas y controles de revisión/seguridad anteriores.
- [ ] Preparar instalación solo STAGING con respaldo y recuperación probados; conservar
  la fallida si ocurre error, sin instalar perfiles ni destinatarios reales.
- [ ] Comprobar hashes, datos, stock, configuración y PDFs emitidos intactos.

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

Plan técnico preparado. No hay campos nuevos instalados ni RED nativo de este
incremento ejecutado. La liberación completa aún requiere evidencia documental/NC
y los compromisos/bloqueos/retornos tienen incrementos separados. No presentar esta
captura como entrega del tablero de11 familias.

Primer lote RED preparado:16 casos nuevos (13 esperados ausentes/3 controles nativos)
y36 KPI previos,52 total. tests/test_repair_acceptance_history.py reutiliza fixtures
nativas; Black99/pylint10. Transporte test-only/139 fuentes, parser exacto por nombre
con2válidos/16rechazos, AST/Bash/PowerShell y hashgate locales aprobados. Pendiente
SSH privado para observar RED. Añadir después los casos restantes de empresas/origen
y rollback antes de declarar GREEN integral de Task1; no están cubiertos por el lote52.
