# Piloto: diagnóstico y reparación con actividades separadas

Estado: alcance aprobado el 2026-10-14. Dos actividades nativas, cada una con
2 días laborables desde el inicio de su etapa; regla activada por defecto.
No implementado ni instalado. Sustituye tanto el piloto limitado a primera REV
como la propuesta intermedia de un único pendiente de tres días.
Trabajo asignado manual está en producción (19.0.24.5.0, PR #102).

## Objetivo y alcance

- «Completar diagnóstico técnico»: al entrar una orden ROV al taller, sigue su
  primera REV de reparación y termina al confirmar exactamente esa REV.
- «Realizar reparación»: al iniciar la reparación mediante el evento nativo,
  sigue la orden y termina cuando esta alcanza `done` tras sus validaciones.

Ambas actividades pertenecen a la orden, aparecen en Trabajo asignado y usan el
asistente de reparto existente. Diagnóstico incluye acceso a su REV.
No se duplican tareas de Proyecto ni se construye otro Kanban.
REV conserva Sellos, Mediciones, Chequeos y Hallazgos; trabajos y repuestos
permanecen en la orden. Confirmar REV acredita registro técnico completo,
no una reparación autorizada, iniciada o terminada.

## Eventos y comportamiento

| Evento real | Resultado |
| --- | --- |
| Orden en borrador o equipo no ROV | No generar seguimiento |
| Orden ROV sale de borrador a estado abierto, excluyendo cancelación y cierre directo | Crear diagnóstico para la primera REV de reparación existente o creada por la lógica actual |
| La primera REV ya estaba confirmada al entrar | No crear diagnóstico pendiente para trabajo ya confirmado |
| Se confirma la REV seguida | Completar solo diagnóstico pendiente |
| Se confirma otra REV, RND o TRN | No cerrar diagnóstico de otra revisión ni crear reparación |
| Orden entra al estado nativo de reparación iniciada | Crear reparación una vez en el ciclo vigente |
| Orden llega directamente a reparación iniciada desde borrador | Evaluar ambos eventos sin duplicados; no imponer una secuencia nueva |
| Orden pasa a `done` | Completar reparación pendiente después de las validaciones actuales; no confirmar REV ni acreditar diagnóstico por sustitución |
| Orden cancelada | Cancelar sus pendientes automáticos, con auditoría y resultado distinto de realizado |
| Ediciones posteriores | No duplicar ni sobrescribir cuenta, empleado o fecha repartidos manualmente |
| Usuario termina o cancela una actividad manualmente | Guardar resultado y no recrearla por una edición; no cambiar REV ni orden |
| Una REV vuelve a borrador | No recrear diagnóstico por corrección documental ni iniciar reparación |
| Orden cancelada vuelve a borrador | Conservar historia; no crear pendientes en borrador |
| Orden vuelve realmente de terminal a estado abierto | Nuevo ciclo una sola vez; diagnóstico solo si su REV aplicable está sin confirmar, reparación solo al iniciarse |
| Se añade otra REV manualmente | Fuera del piloto; no generar otro pendiente |

No se exige confirmar REV para iniciar reparación: se conservan el flujo y las
validaciones existentes. Ambos pendientes pueden coexistir si se inicia reparación
con diagnóstico abierto. Los 4 días son una estimación para etapas consecutivas,
no un plazo total forzado ni una promesa de entrega.

Auditar transiciones instaladas antes de elegir hooks: la fuente de verdad es el
cambio efectivo de estado, no el título de un botón. Un cierre directo o una
importación de datos terminados no crea ni completa trabajo ficticio.
Los efectos pertenecen a la transacción del evento; una operación fallida no deja
creación o cierre a medias. Concurrencia no puede duplicar pendientes.

## Configuración por empresa

Regla activada por defecto. Requiere cuenta destinataria activa y calendario
laboral válido; empleado opcional, elegido explícitamente. Puede usarse la misma
cuenta para ambas etapas. Si falta configuración o acceso al origen, mostrar
configuración incompleta y avisar al coordinador sin bloquear la operación ni
inventar cuenta, empleado o fecha. No conceder grupos a usuarios reales.

Cuenta/empleado compatibles con empresa y permisos del origen. Empleado asignado
no se deduce del creador, editor, cuenta compartida ni técnico de REV.
Repartir no modifica el técnico que acredita la revisión.

## Fechas y trazabilidad

Cada etapa tiene **2 días laborables desde su propio inicio**, con calendario y
zona horaria de la empresa, considerando días no laborables.
El día del evento es día cero: contar los dos días laborables siguientes.
En calendario lunes-viernes sin festivos, lunes vence miércoles y viernes
vence martes. Dos franjas en una jornada cuentan una vez. Respetar semanas
alternas, descansos y ausencias globales; una ausencia parcial no invalida el día
si aún existe tiempo laboral. No usar ausencias personales de un empleado
opcional para modificar el plazo de toda la actividad.

Guardar instante del evento, calendario/zona, fecha original y resultados por
etapa/ciclo. Cambiar posteriormente el calendario no mueve fechas calculadas.
No usar fecha de entrega real, fecha documental REV ni fecha programada de inicio
como sustituto de estos plazos. Verificar calendario instalado antes del cálculo;
si falta, avisar y no inventar una semana laboral.

No extender vencimientos automáticamente. Reprogramar conserva motivo y auditoría.
Marcar actividad como hecha no prueba finalización del proceso: distinguir cierre
manual y cierre por evento de negocio. KPIs después en tableros nativos;
no se implementan en este piloto.

## Identidad y seguridad

Referencia persistente: empresa + orden + ciclo + etapa, con REV exacta para
diagnóstico, actividad nativa y eventos de creación, cierre/cancelación.
No identificar por título ni presencia actual de actividad: Odoo puede archivar
o retirar actividades completadas. Es seguimiento técnico, no otra lista de tareas.

Solo gestionar actividades creadas por estas reglas. Las manuales con igual título
permanecen intactas. Deshabilitar evita nuevas creaciones, no borra historia ni
abandona el cierre de pendientes automáticos existentes.
Solo consultar orígenes autorizados, sin nombres privados de empleados ni datos
de otra empresa. Conservar protecciones del reparto y consultas actuales.

## Verificación y entrega

1. Auditar fuentes instaladas de repair, REV, mail.activity, calendario y empresa.
2. Plan con eventos, cálculo, identidad/atomicidad y permisos concretos.
3. TDD: creación/cierre independiente, REV exacta, estados directos/repetidos,
   borradores/no ROV, configuración inválida, fines de semana/ausencias/zona,
   repartos manuales, cancelación/reapertura, concurrencia y rollback.
4. QA STAGING con cuentas autorizadas, vencimientos y cierre de cada etapa,
   retorno orden/REV, temas e invariancia de PDFs.
5. Revisión, CI y despliegue posterior. Sin retroactivos ni datos QA en producción.
   Instalar el módulo no genera pendientes de órdenes antiguas.

## Configuración operativa aún necesaria

Calendario instalado comprobado; elegir cuenta destinataria de la empresa de
prueba. No reutilizar como activas las cuentas QA anteriores archivadas.
Estos datos se requieren antes de probar generación en STAGING; no cambian
el alcance ni plazos aprobados.

Auditoría de STAGING completada con rollback: 10 fuentes y ninguna ausente,
`draft/confirmed/under_repair/done/cancel` confirmados. Done de actividad archiva;
cancelación elimina. Calendario empresa 1 originalmente UTC, lunes-viernes y sin
ausencias globales registradas. Por decisión del usuario se reutiliza calendario
de empresa, sin duplicarlo. Cambio STAGING a America/Santiago confirmado con
recurso activo 3 actualizado y jornadas/ausencias intactas; tres comprobaciones
de vencimiento correctas, incluidas diferencia de fecha UTC/Chile y fin de semana.
Respaldo `/var/tmp/mc-calendar-santiago-zDs8HQ`. Los festivos deben registrarse:
elegir la zona no los incorpora. Producción sin cambios.
Plan preparado: `../plans/2026-10-14-repair-activities.md`. Revisión del plan y
método de ejecución pendientes; implementación aún no iniciada.
