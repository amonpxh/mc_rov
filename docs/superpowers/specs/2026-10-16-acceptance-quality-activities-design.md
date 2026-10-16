# Seguimiento de aceptación de equipos y Calidad

Estado: diseño escrito aprobado por el usuario el2026-10-16. Planes de aceptación
y Calidad preparados para revisión; implementación aún no iniciada.
Base: main b25d15fe90dbb99bf28be90989da53ed5e1f3dde, mc_rov19.0.25.1.0.

## Objetivo y acuerdos

Al terminar la fabricación de un equipo ROV, mostrar los siguientes pasos en las
actividades nativas y en Centro de trabajo. Separar realizar una prueba, aprobar
su resultado y emitir el documento de aceptación. Conectar las alertas de Calidad
con su resolución sin duplicar los controles o las alertas existentes.

El usuario aprobó:

- Fin real de fabricación genera pendientes de rendimiento y terreno.
- Confirmar la prueba completa su realización, incluso si resulta rechazada.
- Con ambas pruebas confirmadas y aprobadas, generar el pendiente de emitir FEN.
- Una prueba rechazada genera un pendiente de resolver ese rechazo. Se resuelve
  con la corrección o repetición vinculada y aprobada, sin abrir reparaciones solas.
- Alertas de Calidad tienen seguimiento hasta entrar a una etapa terminada.
- **Cada actividad tiene1día laborable**, incluido resolver un rechazo.
- Conservar cuenta y empleado independientes, reparto, reprogramación con motivo,
  control general y configuración por proceso. No elegir Dev como destinatario.

No se aprueban pruebas ni se emiten documentos automáticamente. No se crean tareas
de Proyecto espejo, nuevos Kanban, pendientes históricos o cambios en los PDFs.

## Evidencia instalada

Auditoría de8modelos STAGING25.1, READ ONLY y rollback:
`.tmp/acceptance-quality-activity-pilot/installed.json` en el workspace.

- RND/TRN viven en mc.rov.revision: tipo, lote y reparación opcional; estado
  borrador/confirmado separado del resultado aprobado/con observaciones/rechazado.
  Existe acción de volver a borrador. El responsable es quien realizó el trabajo.
- No hay vínculo actual de la revisión con una fabricación o ciclo de aceptación.
  No basta encontrar la última prueba del mismo equipo para acreditar un ciclo.
- FEN selecciona explícitamente RND/TRN del mismo lote, sin reparación. Solo emite
  con ambas confirmadas y aceptadas; el PDF emitido queda inmutable.
- Lote y alerta admiten actividades nativas. Revisiones y FEN no exponen actualmente
  activity_ids. Se propone anclar aceptación en el lote, sin añadirles mixins.
- Un chequeo fallido ya genera alerta mediante do_fail del módulo. Mantenerlo.
  quality.check.user_id se sella con quien ejecuta el control, no identifica por
  sí solo a quien debe resolver el siguiente paso.
- Cierre de quality.alert se reconoce por stage_id.done, no por nombre de etapa.
  Hay0reglas base.automation para los modelos auditados; esto no elimina lógica
  automática nativa o del módulo.

## Alternativas y decisión propuesta

1. **Actividades sobre el equipo con evidencia explícita**: conserva las pantallas
   y pruebas manuales; necesita una acción pequeña para asociar pruebas al ciclo.
   Es la opción propuesta en este diseño.
2. Preparar automáticamente RND/TRN y FEN en borrador: simplifica el enlace, pero
   crea documentos adicionales sin intervención humana. No se propone aquí.
3. Buscar automáticamente la prueba más reciente: no distingue correcciones,
   reparaciones ni otra aceptación del mismo lote; se descarta por ambigüedad.

## Inicio, alcance e identidad

Tras la transición real de una MO a done, identificar las series ROV efectivamente
producidas por sus movimientos terminados. No usar solo una cantidad prevista o
una lista de series preparada. El asistente anterior a done no inicia aceptación.

Abrir un ciclo por pareja fabricación/serie. En fabricación parcial, solo las
unidades producidas comienzan su aceptación; el resto espera al cierre de su MO.
Una unidad sin serie o un producto fuera del alcance ROV no recibe una aceptación
inventada. No inferir este evento de editar la ficha o ingresar inventario histórico.

Una identidad única y bloqueo transaccional evitan duplicados ante dos cierres,
reintentos o hooks nativos diferentes. El seguimiento no reabre fabricación.
No impedir el cierre de MRP por faltar política o destinatario: registrar la causa
de configuración incompleta siguiendo el comportamiento de los procesos instalados.

## Evidencia y recorrido del usuario

Las actividades RND/TRN/FEN y rechazo residen en stock.lot y enlazan el equipo.
Desde el equipo, una acción nativa de **Pruebas de aceptación** permite consultar
el ciclo y seleccionar o crear sus pruebas mediante los formularios existentes.
El Centro mantiene sus vistas nativas y accesos actuales.

Crear una prueba desde el contexto explícito de aceptación la vincula a ese ciclo.
También se puede seleccionar una existente, tras comprobar lote, tipo, ausencia
de reparación, empresa, permisos y que no acredita otro ciclo incompatible.
Sin contexto explícito, los botones manuales conservan su comportamiento anterior.
Nunca vincular por título, fecha reciente o responsable coincidente.

Vincular una repetición conserva la prueba rechazada y deja auditoría del cambio;
no la borra ni altera su resultado. Seleccionar evidencia ya completada puede
resolver el pendiente, pero queda registrada la selección explícita y su actor.
Los campos y acciones no conceden acceso adicional a otros equipos o empleados.

## Actividades y cierre de negocio

| Evento | Actividad | Cierre |
| --- | --- | --- |
| Equipo efectivamente fabricado | Realizar prueba de rendimiento | Su RND vinculada pasa a confirmado |
| Mismo evento | Realizar prueba en terreno | Su TRN vinculada pasa a confirmado |
| Prueba vinculada confirmada y rechazada | Resolver rechazo de rendimiento/terreno | Esa prueba corregida o repetición explícita queda confirmada y aceptada |
| Ambas pruebas vigentes confirmadas y aceptadas | Preparar y emitir ficha de equipo nuevo | Emisión de FEN del ciclo con esas pruebas |
| Creación de alerta de Calidad dentro del alcance configurado | Resolver alerta de Calidad | Su etapa pasa a done=True |

Aceptada significa aprobado o aprobado_con_observaciones, como exige FEN hoy.
No se impone orden entre RND y TRN: ambas quedan pendientes desde fin de fabricación.
Un rechazo bloquea el avance a emisión, no declara reparado ni aceptado el equipo.
Si ambas pruebas rechazan, cada una conserva su resolución independiente.

Volver una prueba a borrador antes de emitir FEN retira su acreditación para emitir
la ficha. Si ya había pendiente de emisión, se cancela por pérdida de requisitos;
la corrección genera el seguimiento que corresponda sin duplicar uno activo.
Un rechazo abierto continúa pendiente mientras se corrige la prueba. Al volver a
aprobar ambas se inicia una nueva elegibilidad de emisión, con auditoría.

Una FEN ya emitida conserva su PDF y evidencia. Corregir una revisión después no
reescribe ese documento ni reabre su ciclo cerrado. Una nueva aceptación requiere
una nueva decisión explícita; no se genera silenciosamente por editar una prueba.

Marcar una actividad hecha o cancelarla manualmente registra esa decisión; no
confirma pruebas ni emite FEN. Una edición ordinaria no reconstruye la actividad.
Las actividades manuales con títulos iguales quedan fuera del automatismo.

## Calidad

Política separada de aceptación, con destinatario y calendario propios. Propuesta
de alcance inicial: alertas de equipos ROV, identificados por producto o serie,
incluidas las que vienen de reparación/fabricación. No inventar un ROV cuando una
alerta solo identifica un componente sin vínculo al equipo; ampliar ese alcance
requiere una decisión explícita posterior.

Crear una alerta abierta inicia un pendiente. Crear una ya terminada no lo inicia.
Moverla entre etapas abiertas no duplica ni reinicia el plazo. Volver de una etapa
done a otra abierta inicia un nuevo ciclo si el seguimiento está habilitado.
Cerrar funciona aunque la política o el control general estén pausados.

No añadir un pendiente por cada chequeo de fabricación: Odoo ya los presenta dentro
del proceso. Tampoco duplicar la alerta que ya se crea al fallar un chequeo.
No exigir nuevas acciones correctivas/preventivas como condición universal de cierre.

## Plazos y configuración

Todos los plazos iniciales: **1 día laborable desde su propio evento**. Rendimiento
y terreno comparten inicio; la ficha empieza cuando ambas se aceptan; resolver un
rechazo empieza cuando se confirma el rechazo; la alerta desde su creación/reapertura.
El total del proceso no es un único vencimiento de un día.

Usar el calendario operativo y su zona horaria explícitos; respetar jornadas y
ausencias/festivos registrados. Fines de semana sin jornada no cuentan. Reutilizar
el cálculo laborable validado de reparación, con sus pruebas de bordes de fecha.
No cambiar el calendario general durante una instalación. Producción aún usa UTC:
su calendario real debe verificarse antes de activar estos procesos.

Configuración → Seguimiento automático incorpora Aceptación y Calidad, con plazos
por actividad, cuenta, empleado opcional y calendario. Cambiar plazos afecta nuevos
eventos; reprogramar existentes conserva el motivo y la auditoría. No autoextender.
Defaults enabled=True como políticas existentes; configuración operativa incompleta
no genera pendientes. El upgrade no crea políticas ni elige cuentas reales.

Pausa general o de proceso impide actividades nuevas, conserva pendientes y permite
cierre real. Reactivar no recupera eventos anteriores. Si una etapa siguiente nace
durante la pausa, no se reconstruye por editar después; se atiende manualmente.

## Persistencia, acceso y auditoría

Mantener servicios de aceptación, de Calidad y de plazos separados. Un historial
privado identifica ciclo, origen, serie, evidencia explícita, actividad, inicio,
vencimiento original/vigente, calendario/zona, resultado y actor/motivo de cierre.
La interfaz solo obtiene un resumen del origen que el usuario ya puede consultar.

Aplicar permisos del registro y empresa con el actor original, también desde hooks
que Odoo eleva internamente. No ampliar RRHH privado ni exponer el ledger por ACL,
exportación, nombres de registros restringidos o contextos falsificables.
Proteger cambio de equipo/empresa/tipo/evidencia durante seguimiento; una corrección
legítima usa selección explícita validada y auditada. Prohibir borrar evidencia con
historial explicando la causa al usuario; conservar referencias después de cancelar.
No otorgar permisos de configuración o coordinación a Taller por instalar el módulo.

## Verificación y entrega

TDD por bloques: políticas/calendario; nacimiento por unidad; vínculo explícito y
rechazo; emisión/corrección; alerta/reapertura; permisos y registros temporales.
Probar lote múltiple, parcial, concurrencia, repetición de eventos, actividad manual,
pausa, destinatario sin acceso, multiempresa y ausencia de pendientes retroactivos.

Conservar la suite de594casos y descubrir exactamente la nueva suite completa.
Concurrencia en copia aislada sin correo/cron; QA manual con escenario propio y
retiro posterior conservando historial. PDFs y validadores actuales permanecen.

Orden: aprobación de este diseño → plan de implementación revisado → TDD/STAGING →
QA y PR/CI → aprobación de merge/despliegue. Activación real separada hasta elegir
cuenta Taller y calendario. Este documento no afirma implementación instalada.
