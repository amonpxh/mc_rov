# Trabajo pendiente

> Fuente de continuidad. Actualizar al cerrar cada sesión y distinguir código local,
> pruebas, merge y despliegue. Las propuestas no aprobadas no son tareas de implementación.

## Estado vigente — 2026-10-07

- Producción: `mc_rov 19.0.24.1.0`, código funcional `9731f68` (merge del
  [PR #95](https://github.com/amonpxh/mc_rov/pull/95)). Upgrade y reinicio completos
  verificados; servicio activo desde 19:23:57 UTC, PID 1039946.
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
  QA manual: FEN/00878 → TRN/00003 y equipo 26-02; retorno por breadcrumb comprobado.
  Emitidas, varias fichas, referencias antiguas y permisos cubiertos por pruebas
  transaccionales; no confundirlas con muestras reales emitidas.
- Producción confirmó pestaña Fichas y ubicación final de Imprimir ficha mediante
  vista instalada. Contiene **cero FEN**: no se certificó apertura de una FEN real
  allí. La sonda se revirtió, sin emitir documentos ni consumir correlativos.
  Ambos reportes QWeb conservaron sus hashes antes/después del despliegue.
- Respaldo de producción:
  `/var/backups/mc-rov-prod-fen-navigation-NwTnL0/odoo_prod.dump`.
  Evidencia: `../.tmp/prod-fen-navigation` y `../.tmp/fen-navigation-qa`.
  No publicar archivos `.tmp`. No queda despliegue pendiente para esta entrega.
- Mapa de relaciones aprobado: recorridos abiertos y ramas por escenario, no una
  secuencia obligatoria. Auditoría y límites en diseño § 12–13. Equipo → Trazabilidad
  → fabricación de origen funciona; alerta → reparación abre la orden exacta.
  Reparaciones/alertas del equipo son botones inteligentes nativos, no pestañas.
  Calidad → fabricación: corte directo confirmado en la vista instalada; la alerta
  guardaba la MO sin ofrecer acceso a ella. Botón Fabricación implementado e
  instalado en STAGING `19.0.24.2.0`, tres contratos y suite 362/362 aprobados.
  Producción conserva `19.0.24.1.0`; no tiene este botón todavía.

## Próximos pasos acordados, en orden

### 1. Muestras adicionales de FEN cuando existan

La implementación y el despliegue de navegación están cerrados. La ruta actual es
**Equipo → Fichas → Retomar / Abrir**, con acceso a la evidencia exacta seleccionada.
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
Pendiente cierre git/PR/CI y posterior despliegue de producción; no afirmar que el
cambio esté en producción. La primera sonda GREEN falló por conversión ASCII de la
tilde en Windows PowerShell; corregida con escape Unicode, sin cambiar el botón.

### 3. Centro de trabajo ROV, después de los recorridos

Entrada central por Reparaciones, Fabricación/aceptación, Equipos y Calidad.
Reutilizar acciones y criterios existentes para encontrar y retomar registros.
Primero definir necesidades del usuario; no duplicar pantallas ni crear un segundo
proceso. Conteos operativos verificables antes de indicadores de desempeño.
Las tareas personales requieren definir responsables y permisos; no están diseñadas aún.

Diseño y auditoría: [Recorridos guiados](designs/flujo-guiado.md).
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
