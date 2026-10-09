# Trabajo asignado en el Centro de trabajo

Fecha: 2026-10-09. Estado: base aprobada por el usuario; compatibilidad con ejemplos
documentada, primera entrega manual implementada en STAGING; suite 415/415 aprobada y correcciones de privacidad verificadas;
Exportación focalizada 1/1 aprobada; QA visual con roles reales pendiente. No desplegado
en producción.

## Objetivo y acuerdos

El jefe debe distribuir el trabajo real del taller y consultar quién tiene cada
pendiente. Los empleados deben encontrar las acciones asignadas y abrir el registro
donde se realizan, sin copiar la reparación o fabricación a un sistema paralelo.

Acuerdo del usuario: separar **Usuario asignado** (cuenta que gestiona el pendiente)
de **Empleado asignado** (persona concreta que lo ejecuta). Escenario previsto:
cuentas Taller, Dev y Supervisor, con varias personas usando una misma cuenta.
No asumir que esas cuentas ya existen ni resolverlas por su nombre visible.

El usuario solicita alcance personal y global con permisos. Se propone llamarlos
**Mi trabajo** y **Trabajo del equipo**. La asignación a un empleado no acredita que
ya realizó el trabajo ni sustituye al responsable de una orden o revisión.

## Evidencia y límites del sistema actual

Auditoría de STAGING con rollback: `../../../../.tmp/task-activity-audit/installed.json`.

- Actividades pendientes y Proyecto comparten `project.task`; las primeras son
  tareas sin proyecto. Mis tareas incluye tareas asignadas con y sin proyecto.
- `mail.activity` ofrece acciones vinculadas por modelo/registro, usuario y fecha.
  Mis actividades (acción 124) tiene lista, Kanban y calendario verificados.
- Reparación, fabricación, equipo, BoM, ECO, alerta y control de calidad admiten
  actividades. REV/RND/TRN y FEN no las admiten actualmente.
- Fabricación y BoM tienen vínculo nativo a proyecto; no equivale a tarea concreta.
  No se detectaron relaciones directas de tareas con los registros operativos auditados.
- El módulo crea la primera REV de reparación al salir la orden de borrador,
  exclusivamente para ROV con serie, y evita duplicarla si ya existe.
- Una REV pasa de borrador a confirmado y puede volver a borrador. No tiene un
  estado independiente «diagnóstico terminado».
- La fecha límite de una actividad nativa es obligatoria. El estado de urgencia
  depende de esa fecha; no representa etapas como En curso o Bloqueado.

Fuente técnica complementaria: modelo oficial Odoo 19
https://github.com/odoo/odoo/blob/19.0/addons/mail/models/mail_activity.py.
Antes de implementar el ciclo de terminación se verificará el comportamiento
instalado: completar puede retirar o archivar la actividad según su configuración.
No diseñar la prevención de duplicados suponiendo que la fila permanece activa.

## Alternativas y recomendación

| Alternativa | Ventaja | Coste / límite |
| --- | --- | --- |
| Actividades sobre órdenes existentes | Contexto exacto y seguimiento nativo | No sustituye la planificación por etapas de Proyecto |
| Una tarea por cada orden | Tablero de tareas con etapas | Duplica seguimiento y exige sincronización con la orden |
| Mezclar tareas y actividades en un tablero nuevo | Una sola pantalla | Modelos y ciclos diferentes; una tarea puede tener actividades y aparecer dos veces |

Recomendación: actividades nativas para acciones sobre órdenes; tareas de Proyecto
para trabajos que requieren etapas/subtareas propias. Centralizar ambas mediante
accesos separados y reutilizar vistas nativas. No crear otra tarea automática por
cada reparación, otro Kanban ni una lista duplicada de estados operativos.

## Pantalla propuesta

### Compatibilidad con los casos reales aportados

El usuario aportó ejemplos como contexto de uso, no como instrucciones para crear
registros ni como evidencia consultada en Odoo. No importar ni generar pendientes
a partir de esa lista. Trabajo asignado admite taller, desarrollo, compras y
coordinación, incluyendo componentes y equipos no ROV. Los filtros ROV de las seis
áreas actuales no se reutilizan para excluir estos pendientes. El alcance sigue
limitado por permisos y empresas, no por es_un_rov.

| Caso aportado | Registro principal y seguimiento compatible |
| --- | --- |
| Equipo entregado que vuelve al taller | Conservar orden/entrega anterior; nueva visita con su orden y pendientes propios |
| Cable o componente reparado/fabricado | Orden operativa correspondiente aunque no sea ROV completo; actividad manual si admite seguimiento |
| Chasis terminado, secado/pintura/prueba pendientes | Conservar avances documentados; acciones restantes sobre la orden, sin dar por terminado el conjunto |
| Fabricar sustituto de un cable destinado a otro cliente | Fabricación/compromiso vigente; transferir o reservar material en inventario, no desde una actividad |
| Prueba que detecta fuga | Resultado real en prueba/control; actividad para corregir, sin inferir causa ni aprobación |
| Prueba que no reproduce la falla | Conservar resultado; no demuestra ausencia de falla ni cierra automáticamente la visita |
| Informe preparado, firma y envío pendientes | Actividades separadas sobre registro/documento accesible; preparado no equivale a firmado/enviado |
| Entrega o retiro sin confirmar | Pendiente «Confirmar entrega/retiro»; no «Entregar» ni cambiar a entregado sin evidencia |
| Compra/recepción, envío, certificado de origen | Compra, transferencia o documento pertinente; comprobar soporte instalado antes de prometer cada acción |
| Reunión, consulta de licitación, aceptación de cotización | Contacto/oportunidad/cotización/tarea adecuada; no inventar una reparación para darle origen |
| Correcciones de BoM y desarrollo nuevo | Ingeniería/BoM o tarea de Proyecto según trabajo; no obligación en cada fabricación |

Operaciones, inventario, entregas y resultados se registran en sus módulos. Una
actividad completada no ejecuta una recepción, reserva, entrega, firma, prueba ni
aprobación. No convertir un rechazo, cambio de destino o nueva visita en un simple
cambio de tarjeta. Los trabajos realizados aportados son historial, no pendientes.

«Realizado por» en un avance no se copia a Empleado asignado del siguiente paso.
Cuando varias acciones formen un trabajo con etapas y dependencias, usar tareas
de Proyecto. Su asignación por empleado y vínculos operativos permanecen en fase 3;
la primera entrega no promete esas ampliaciones de tareas ya implementadas.

El primer piloto automático permanece exclusivamente para la primera REV de una
orden ROV. Los demás casos admiten seguimiento manual según el modelo instalado;
las futuras reglas se diseñan explícitamente, no se activan por aprobar el diseño.

### Organización visual

Conservar los seis accesos por proceso del Centro. Incorporar una entrada
**Trabajo asignado**, con selector **Mi trabajo / Trabajo del equipo** y dos
pestañas **Actividades / Tareas**. Proyectos será un acceso a los proyectos
autorizados, sin tratarlos como pendientes ni sumar sus conteos con tareas.

Mi trabajo filtra por usuario conectado. Si la cuenta es Taller, muestra las
asignaciones a Taller; no identifica automáticamente al empleado que está usando
esa cuenta. Filtro **Empleado** opcional, visible y conservado al volver al Centro.
No convertir ese filtro en una identidad, una autorización ni una firma del autor.

Trabajo del equipo permite filtrar usuarios, empleados, empresa, documento y fecha.
**Sin empleado asignado** diferencia la falta de persona concreta de la falta de
cuenta. No confundirlo con «Sin responsable» del registro operativo.

Primera entrega: Actividades con lista, Kanban y calendario nativos; Tareas y
Proyectos mediante accesos nativos. La asignación por empleado de tareas de Proyecto
y sus vínculos operativos se incorporarán en una fase posterior, explícita.
No mostrar tareas con información de empleado que el modelo aún no conserva.

Cada actividad muestra resumen, usuario, empleado (o «Sin empleado asignado»),
fecha límite y documento exacto. Acción **Abrir registro** y acciones nativas para
reprogramar/completar. Para el piloto automático, mostrar además la REV concreta.
La lista facilita seleccionar varias actividades y asignar usuario/empleado/fecha.
Agrupar Kanban por empleado o por fecha; no añadir etapas de Proyecto a actividades.
No sumar tareas y actividades en un único contador de carga de trabajo.

## Asignación y permisos

Extender `mail.activity` con empleado asignado opcional. Usuario conserva su campo
nativo. Para la primera automatización, la cuenta destinataria se configura por
empresa y regla; no usar al creador ni al último editor como destinatario implícito.

El jefe puede cambiar ambos campos y la fecha mediante un asistente de asignación
individual o múltiple. Persona sin login es válida; persona archivada no es válida
para una nueva asignación, pero su referencia histórica se conserva. Usuario y
empleado deben ser compatibles con la empresa del documento. No exigir que ese
empleado tenga el usuario seleccionado: precisamente se permite cuenta compartida.

Nombres y selección deben respetar acceso a empleados públicos, como las columnas
existentes del Centro. No dar acceso a información privada de RRHH para asignar
trabajo. Un nombre restringido no debe exponerse en búsqueda, tarjeta o conteo.

Permisos propuestos: **Consultar trabajo del equipo** y **Coordinar asignaciones**,
separados. No inferirlos del nombre Supervisor ni de ser administrador de otra app.
Mi trabajo no amplía permisos existentes. Consultar no habilita editar; coordinar
no concede acceso a órdenes, proyectos o empresas no autorizados.

Ocultar una pestaña no es una barrera de seguridad. Consultas, conteos y asistentes
deben aplicar los controles en servidor. Abrir un documento exige sus permisos,
incluso si Odoo permite leer una actividad por estar asignada al usuario. No usar
sudo para exponer nombres, registros o reasignar actividades no autorizadas.
Acceso global siempre significa global dentro de la autorización del usuario.

Con una cuenta compartida, el autor del cambio sigue siendo esa cuenta. Empleado
asignado no prueba quién tecleó, quién confirmó o quién realizó efectivamente la
acción. La propuesta organiza trabajo; no ofrece trazabilidad personal inexistente.

## Primer piloto automático: completar la revisión de una reparación

Pendiente: **Completar revisión técnica** sobre `repair.order`, con referencia
explícita a la primera REV que el módulo crea para esa visita. No requiere añadir
actividades al modelo de revisiones ni cambia sus pruebas, ficha o validaciones.

| Evento | Comportamiento propuesto |
| --- | --- |
| Cotización en borrador / reparación no ROV | No generar actividad del piloto |
| La orden entra al taller y se crea su primera REV | Crear una actividad, si la regla está habilitada y configurada |
| Guardar o editar nuevamente | No duplicar ni sobrescribir asignación/fecha manual |
| Confirmar esa REV exacta | Completar la actividad automática ligada a ella |
| Confirmar otra REV o una de otra visita | No completar este pendiente |
| Cancelar la orden | Cancelar el pendiente automático con motivo; no registrarlo como realizado |
| Reabrir la orden después de cancelar, con la misma REV en borrador | Volver a poner pendiente una vez; preservar historial y política de fecha |
| Volver esa REV a borrador con orden abierta | Reactivar el seguimiento una vez por reapertura real |
| Volver esa REV a borrador con orden terminada/cancelada | No generar trabajo automático de una orden cerrada |
| Crear una segunda REV manualmente | No generar actividad en el primer piloto |

Confirmar una REV no cierra la orden. Marcar manualmente una actividad como hecha
no confirma la REV. Una actividad ya completada manualmente no se recrea por una
edición cualquiera; su reapertura requiere el evento explícito previsto arriba.
Solo completar/cancelar automáticamente actividades identificadas por esta regla;
las manuales, incluso con el mismo título, conservan su ciclo manual.

Identidad estable del seguimiento: regla + empresa + orden + REV + ciclo de
reapertura. Preservar terminación/cancelación para impedir recreaciones aunque
la actividad nativa se retire. La implementación definirá persistencia y control
de concurrencia en el plan; no resolver identidad comparando títulos o notas.
No se cambia automáticamente el técnico responsable de la REV al asignar actividad.

Regla desactivada por defecto; activar explícitamente en STAGING. No generar
pendientes retroactivos para órdenes antiguas al instalar. Una transición fallida
debe revertir también la actividad. Falta de configuración no bloquea una operación
existente ni inventa destinatario o plazo: se informa al coordinador.

### Política de fechas

El usuario propone prioridad: plazo por actividad, luego fecha prevista de la orden,
y plantea alargar automáticamente cuando no existe ninguno. Se acepta como base
la prioridad de las dos primeras fuentes; se desaconseja el alargamiento continuo
porque oculta vencimientos y altera la planificación sin decisión humana.

Propuesta para revisar: plazo por tipo de actividad desde el evento de creación;
si no está configurado, fecha prevista de la orden cuando su significado sea
adecuado; si tampoco existe, plazo general de respaldo configurable por empresa.
No se fija aquí una cantidad de días ni una fecha prevista todavía no auditada.
Una fecha prevista ya pasada se conserva como vencida con aviso; no se empuja al futuro.
No usar fecha de entrega real o fecha de la REV como sustituto de planificación.

La fecha asignada se conserva aunque transcurra el tiempo o cambie la configuración.
Reprogramación explícita por persona autorizada con motivo; no sobrescribir fechas
manuales al editar la orden. Para una reapertura real, calcular una nueva fecha
desde el nuevo evento y conservar el vencimiento anterior en el historial.

Si no está configurado ninguno de los tres criterios, la regla no queda habilitada
y se informa al coordinador. No inventar fecha ni bloquear una operación existente.
La automatización requiere cuenta destinataria y política de fecha completas.
Actividades manuales conservan la fecha elegida por quien las programa.

## Entregas y verificación

1. Asignación usuario/empleado, permisos y acceso desde el Centro; actividades
   manuales antes de automatizar. Tareas y proyectos abiertos en vistas nativas.
2. Regla única para primera revisión de reparación, con configuración y ciclo completo.
3. Según resultado del piloto: actividades propias de REV/FEN, reglas de fabricación
   y asignación/vínculos de tareas de Proyecto. No incluidos silenciosamente en 1–2.

Pruebas necesarias: cuenta compartida con dos empleados; sin empleado; reasignación
múltiple con registros no autorizados; permisos separados de lectura/coordinación;
empleados privados/inactivos; empresa incorrecta; origen inaccesible; filtros y
retorno; actividad futura visible; manual y automática con igual título; borrador
y no ROV; confirmación exacta; cancelación; reapertura; repetición/concurrencia;
configuración incompleta; rollback. Verificar el historial sin simular autores humanos.

QA con supervisor y Taller: asignar una acción a un empleado, filtrar por él desde
Taller, abrir la orden exacta y confirmar que la asignación no altera la REV.
Comparar reportes/validaciones vigentes; ningún cambio de PDFs ni emisión de FEN.

## Estado y siguiente paso

El usuario aprobó diseño base y fechas sin alargamiento automático. Sus ejemplos
amplían el contexto de uso, no autorizan creación/importación de registros.
[Plan de primera entrega manual](../plans/2026-10-09-trabajo-asignado-manual.md)
preparado para revisión. No se escribió producto, instaló nada ni creó actividades.
La automatización se planifica por separado tras validar asignación manual.
