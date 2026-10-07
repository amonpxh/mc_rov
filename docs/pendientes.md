# Trabajo pendiente

> Fuente de continuidad. Actualizar al cerrar cada sesión y distinguir código local,
> pruebas, merge y despliegue. Las propuestas no aprobadas no son tareas de implementación.

## Estado vigente — 2026-10-07

- Producción: `mc_rov 19.0.24.0.0`, código funcional `1fe6fcc` (merge del PR #92).
  Upgrade y reinicio completos verificados; servicio activo desde 15:37:29 UTC,
  PID 1035666. Los accesos de 21 revisiones reales se comprobaron con rollback.
- Último cierre documental en main: `a991ad8` (PR #93). No requiere otro despliegue.
- STAGING: navegación instalada y aprobada manualmente por el usuario. CI del merge
  funcional: **352 pruebas, cero fallos/errores**, lint aprobado.
- Respaldo de producción:
  `/var/backups/mc-rov-prod-revision-navigation-C5c2EN/odoo_prod.dump`.
  Evidencia local en `../.tmp/prod-revision-navigation`; no publicar archivos `.tmp`.
- Trabajo actual: ordenar este documento, después verificar los recorridos FEN y
  fabricación descritos abajo. Sin nuevos cambios funcionales autorizados para esos recorridos.

## Próximos pasos acordados, en orden

### 1. Retomar una FEN existente

Comprobar en STAGING el acceso desde Equipo → Pruebas → fichas de equipo nuevo:

- FEN en borrador: abrir el registro existente, consultar la RND/TRN seleccionadas
  y localizar Vista previa / Emitir ficha según su estado.
- FEN emitida: abrir y consultar el documento almacenado, sin crear otra emisión
  ni reemplazar automáticamente las pruebas seleccionadas.
- Distinguir cero, una y varias fichas. No seleccionar silenciosamente una ficha distinta.
- Verificar retorno al equipo y continuidad al entrar por el menú general.

La lista y el modelo ya existen; falta QA del recorrido, no crear otro modelo ni
rediseñar el PDF. Los equipos de la auditoría inicial no tenían FEN registradas.
Preferir registros existentes; si se necesita una fixture, identificarla y acordar
su limpieza. No emitir fichas de clientes ni consumir correlativos para probar navegación.

### 2. Completar la auditoría de fabricación

La MO WH/MO/00010 → botón nativo Números de serie → equipo 0000008 ya fue comprobada.
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
