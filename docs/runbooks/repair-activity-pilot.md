# Piloto: actividades automáticas de reparación

La instalación no activa una cuenta destinataria ni crea pendientes históricos.
El piloto se valida en STAGING antes de autorizar producción.

## Configuración

Un usuario con el permiso de Coordinación abre **Seguimiento de reparaciones**
en Centro de trabajo. Crear una política para la empresa, seleccionar una cuenta
interna activa con permiso de lectura y escritura sobre las órdenes y elegir su
calendario laboral. El empleado es opcional y corresponde a la persona asignada;
no se deduce de la cuenta compartida ni del técnico que confirmó la REV.

**Activado** viene marcado. Los dos plazos iniciales son de **2 días laborables**.
En STAGING se verificó el calendario de empresa con zona **America/Santiago**.
Instalar o actualizar el módulo no cambia calendarios ni agrega festivos.
Solo se excluyen ausencias globales efectivamente registradas en el calendario.

## Eventos y vencimientos

| Evento | Resultado |
| --- | --- |
| Orden ROV sale de borrador a estado abierto | Diagnóstico para la primera REV de reparación, si está sin confirmar |
| Orden entra en reparación iniciada | Actividad de reparación del ciclo vigente |
| Se confirma la REV exacta seguida | Se completa únicamente su diagnóstico |
| Orden termina correctamente | Se completa únicamente la reparación |
| Orden se cancela | Se cancelan los pendientes automáticos; no cuentan como realizados |
| Orden se reabre | Nuevo ciclo; un diagnóstico anterior pendiente se cancela por sustitución |

Cada plazo empieza con su propio evento. Ese día es el día cero: un evento del
viernes vence el martes siguiente si lunes y martes tienen jornada y no hay
ausencias completas. Dos franjas de trabajo en una fecha cuentan como un solo día.
El cálculo usa la zona del calendario; una ausencia parcial conserva el día si
todavía queda tiempo laborable.

Los vencimientos no se alargan solos. Cambiar el calendario después tampoco mueve
fechas ya calculadas. Para reprogramar, usar **Repartir actividades**, marcar
únicamente fecha límite e indicar el motivo; la acción conserva los campos no
seleccionados y deja auditoría en el origen.

## Decisiones manuales e historial

Marcar una actividad como hecha no confirma la REV ni termina la orden. Se conserva
como decisión manual, distinta de una etapa terminada por su evento de negocio.
Cancelar una actividad tampoco cancela la orden. Las ediciones posteriores no
recrean el mismo pendiente ni sobrescriben cuenta, empleado o fecha repartidos.

Mientras exista seguimiento pendiente, no se puede cambiar el equipo, empresa u
origen de la etapa seguida. Una REV u orden con historial de seguimiento no se
borra; se conserva para trazabilidad. El historial técnico no tiene acceso público
ni exportación para las cuentas operativas.

Si se termina la orden antes de confirmar la documentación, el diagnóstico sigue
pendiente y puede completarse al confirmar su REV exacta. Si se reabre la orden
antes, el diagnóstico anterior queda cancelado con motivo y la nueva etapa tiene
su propio ciclo. No se acredita una revisión como realizada por cerrar la orden.

## Configuración incompleta y desactivación

Sin política, cuenta, calendario o acceso suficiente, el evento deja un aviso
accionable en la orden y no inventa destinatarios ni vencimientos. Un error
inesperado de creación revierte la transacción del evento, evitando medias etapas.

Desmarcar **Activado** evita nuevas creaciones. Los pendientes existentes conservan
su historial y siguen cerrándose cuando ocurre su evento correspondiente. No hay
reconstrucción retrospectiva de órdenes antiguas.

## Verificación y recuperación

Se validaron por etapas 14 pruebas de calendario, 14 de generación, 12 de ciclo
de vida, 15 de acceso e integración y 11 de fronteras/revisión: **66 aprobadas en
STAGING**. La suite general previa a los 11 casos finales pasó **478/478**;
la revalidación completa con 489 casos sigue pendiente. Dos conexiones simultáneas por etapa también pasaron en
una copia aislada: una actividad de diagnóstico, otra de reparación y ninguna
huérfana. Los conflictos de serialización requirieron reintentar la transacción
completa, como en las solicitudes nativas de Odoo. La QA operativa sigue pendiente.

El ensayo reproducible está en `scripts/qa/repair_activity_concurrency.py`.
Ejecutarlo con Odoo shell solo sobre una copia cuyo nombre empiece por
`mc_rov_repair_ci_`, con cron/correo desactivados. Crea fixtures y hace commits
únicamente en esa copia. El script de STAGING crea la copia sin instalar módulos,
verifica los hashes del código/PDF y bloquea conexiones al terminar. No es un test
para ejecutar sobre una base operativa ni se importa en la suite transaccional.

La QA operativa necesita una cuenta destinataria elegida explícitamente. Probar
inicio, vencimientos por etapa, reparto solo de empleado, confirmación REV, cierre
de orden y cancelación/reapertura con permisos Taller y Supervisor. No reactivar
cuentas QA antiguas ni crear pendientes en producción para probar.

Los instaladores guardan BD, archivos y hashes de los dos reportes PDF. Si falla
una instalación, restaurar primero los archivos y recuperar el dump en una base
nueva, verificarla y sustituir STAGING conservando la anterior. No usar
`pg_restore --clean` sobre la base viva ni una restauración global en una única
transacción: ambas estrategias fallaron en este entorno. Conservar respaldos y
bases preservadas hasta una retirada autorizada.
