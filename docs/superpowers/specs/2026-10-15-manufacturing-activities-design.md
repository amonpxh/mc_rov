# Seguimiento automático de fabricación

Estado: diseño para revisión; no implementado ni instalado.

## Objetivo y decisiones del usuario

Mostrar el trabajo pendiente de fabricación en las actividades nativas y en
Centro de trabajo, conectado con su orden real. Mantener cuenta Odoo y empleado
como identidades distintas, conservar reparto y auditoría, y no duplicar tareas
de Proyecto ni operaciones de taller.

El usuario aprobó un pendiente principal «Completar fabricación» y un plazo
máximo inicial de **4 semanas: 28 días corridos desde la confirmación de la orden**.
Confirmó expresamente esta interpretación; no son días laborables. El plazo
será configurable y no se ampliará solo.

Se conserva el acuerdo operativo: instalar y verificar primero en STAGING;
no seleccionar la cuenta Dev como destinataria. La cuenta Taller real todavía
no existe. La configuración real y el calendario se elegirán explícitamente,
sin cambiar calendarios durante un upgrade.

## Evidencia de la instalación

Auditoría STAGING en transacción READ ONLY con rollback, sobre mc_rov
19.0.25.0.0. Evidencia del workspace:
`.tmp/manufacturing-activity-pilot/installed.json`.

- MRP, órdenes de trabajo, Calidad y project_mrp están instalados.
- Hay 11 órdenes de fabricación, una operación y ningún punto/control de
  calidad en la muestra. No hay reglas base.automation para los modelos auditados.
  Esto no implica que Odoo carezca de lógica automática nativa.
- mrp.production admite mail.activity; su estado es computado y almacenado.
  Confirmación, movimientos y operaciones participan en las transiciones.
- button_mark_done puede devolver un asistente antes de terminar. Producción
  parcial puede crear otra MO para lo restante; done de la original no prueba
  que la cantidad restante esté fabricada.
- quality_mrp exige responder controles pendientes cuando existen. Un resultado
  fail es una respuesta, no una aprobación. No se añadirán validadores universales.
- RND/TRN y FEN tienen identidad y resultados propios. Terminar MO no equivale a
  aceptar el equipo ni emitir su ficha.
- Las fechas históricas de la muestra son insuficientes para estimar duración
  real. El plazo proviene del compromiso comercial indicado por el usuario.

## Alcance y alternativa elegida

Se elige una actividad por orden de fabricación de producto incluido en la raíz
ROV que utiliza el Centro de trabajo. La categoría se resuelve por el mecanismo
existente; no por nombres, IDs fijos ni por una serie que todavía puede no existir.
Las fabricaciones de componentes fuera de esa raíz no reciben silenciosamente
el mismo compromiso de cuatro semanas; se tratarán al ampliar el alcance.

Se descarta crear una tarea de Proyecto espejo: añadiría otro estado de trabajo
que mantener sincronizado. Tampoco se crea una actividad por cada operación:
MRP ya tiene sus operaciones, empleados, tiempos y secuencia. Los controles de
Calidad y las pruebas de aceptación seguirán sus propios flujos. Esta entrega
no crea RND/TRN, FEN, alertas, ECO ni movimientos de inventario adicionales.

## Política, cuenta y vencimiento

Política explícita por empresa, accesible solo a Coordinación, con Activado
por defecto, cuenta interna activa, empleado público opcional, calendario para
zona horaria y plazo de 28 días corridos. Crear la política no crea actividades.
No se elige cuenta, empleado o calendario automáticamente durante la instalación.

La propuesta de vencimiento respeta una fecha límite explícita de MO si es
anterior: fecha inicial = menor entre la fecha local de confirmación +28 días
y date_deadline convertida a la zona del calendario, cuando esta exista.
Una fecha ya vencida permanece vencida; no se mueve a hoy. Una fecha de MO más
tardía no amplía el máximo configurado. No se reescriben las fechas de la MO.
date_finished estimada y duración de operaciones no son una promesa comercial.

La cuenta destinataria debe pertenecer a la empresa y poder leer/escribir la MO
en contexto limitado a esa empresa. No se usa al creador, editor ni administrador
como sustituto. Sin configuración válida, aviso accionable en el origen y no
crear un pendiente incompleto. Un fallo inesperado revierte el evento completo.

## Ciclo de vida

| Evento real | Efecto |
| --- | --- |
| Confirmar una MO aplicable que estaba en borrador | Crear una sola actividad «Completar fabricación» |
| Empezar o terminar una operación; MO progress/to_close | Mantener el pendiente sin duplicarlo |
| MO termina realmente en done | Completar solo su pendiente como trabajo terminado |
| Cancelación que deja MO en cancel | Cancelar su pendiente, sin acreditarlo como realizado |
| Asistente devuelto antes del cierre o validación fallida | No cerrar prematuramente ni conservar cambios parciales |
| Editar fechas, responsable u otros campos después | No recrear ni sobrescribir el reparto del pendiente |
| Duplicar una MO | No copiar identidad, actividad ni historial; esperar confirmación nueva |
| Cantidad restante pasa a otra MO confirmada | Nueva identidad y pendiente propio, conservando el vencimiento de la fabricación seguida |

Si la MO original tiene seguimiento, la MO restante conserva su vencimiento
vigente, o una fecha límite explícita anterior de la nueva MO: producir una parte
no reinicia otras cuatro semanas para el resto. No se copia actividad, resultado
ni empleado; la nueva identidad guarda su relación privada con el seguimiento
original. Si no existe seguimiento original, aplicar la regla de nueva confirmación
y fecha límite explícita, sin reconstruir eventos históricos ni inventar fechas
de inicio. No se modifica el pedido comercial ni se oculta un atraso.

No se añade un botón para reabrir fabricación. Si el flujo nativo permite una
vuelta efectiva desde cancel a borrador y una nueva confirmación, se conserva
el resultado anterior y se abre un ciclo nuevo, sin duplicar el mismo evento.
Modificar una MO terminada no se interpreta como una nueva fabricación.

Una actividad marcada hecha manualmente registra decisión manual; no termina
la MO. Cancelarla tampoco cancela la MO. No se recrea en la siguiente edición.
Repartir actividades conserva campos no seleccionados y exige el motivo de
reprogramación existente. Ningún vencimiento se extiende automáticamente.

## Integración y seguridad

Extensión separada de los automatismos de reparación: política e identidad
privada de seguimiento de fabricación, un tipo nativo de actividad sin sucesor
automático y servicios privados que verifican el origen antes de elevar acceso
técnico. No hacer una refactorización general de reparación en esta entrega.

No producir efectos desde _compute_state: reconciliar registros persistidos en
eventos nativos de confirmación, finalización/inventario y cancelación, comprobando
el estado efectivo después del evento. Cubrir caminos de órdenes restantes y
finalización desde operaciones, además del botón principal. Una notificación o
acción devuelta no equivale por sí sola a éxito ni a fallo de la operación.

Bloqueo de filas ordenado y unicidad por MO/ciclo/etapa antes de crear el pendiente;
dos transacciones simultáneas no pueden generar duplicados ni huérfanos. El
reintento por serialización repite la transacción completa. Solo se procesan IDs
persistidos; copias temporales/onchange no crean ni cierran seguimiento real.

Mientras haya seguimiento pendiente, proteger identidad de MO/producto/empresa
y el origen de la actividad. Conservar historial al archivar o retirar la
actividad; impedir borrado de MO con historial mediante un mensaje comprensible.
Campos internos y servicio no pueden falsificarse por RPC/contexto. El historial
no tiene ACL pública, ni expone empleados privados o nombres de orígenes ocultos.

Las actividades aparecerán en las vistas nativas ya integradas y en el filtro
Fabricación de Trabajo asignado. No se añade otra lista, Kanban ni pantalla de
reparto; se revalidará el filtro dinámico y el retorno a la MO.

## Validación y entrega

TDD focalizado: 28 días corridos en zona Santiago (incluidos fin de semana y
cambio horario), prioridad de fecha explícita, configuración incompleta,
permisos y multiempresa; unicidad/copia/temporal, confirmación repetida,
producción parcial, asistentes, fallos con rollback, cierre real/cancelación,
reparto y decisiones manuales, privacidad y ausencia de backfill.

Luego suite completa con cada caso descubierto, revisión del diff, concurrencia
real en BD aislada sin cron/correo y QA STAGING Taller/Supervisor con cuentas y
documentos ficticios nuevos autorizados para ese escenario. No reutilizar QA
archivada ni probar con documentos reales. Preservar PDFs y fuentes de reparación.

Instalador con respaldo de BD/archivos y recuperación en base nueva verificada,
conservando la anterior; no pg_restore --clean sobre una base operativa. Upgrade
no configura destinatarios, cambia calendarios ni genera trabajo histórico.
Merge/despliegue de esta ampliación se autorizarán después de QA; la autorización
anterior de producción correspondía a reparación. El próximo paso tras aprobar
este diseño es el plan de implementación, todavía sin código de producto.
