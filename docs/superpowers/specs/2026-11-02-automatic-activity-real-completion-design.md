# Cierre real de actividades automáticas — diseño aprobado en conversación

Fecha: 2026-11-02. Rama activa: feature/inventory-activities, base de este ajuste4084eaa. Inventario aún no entregado; producción conserva19.0.25.5.0. Este ajuste interrumpe el caso QA de cierre manual y pasa a ser requisito previo de la entrega. No recrear ni borrar el escenario QA wamR0o.

## Intención y autorización

El usuario detectó que «Hecho» podía retirar del Centro un pendiente automático sin resolver el trabajo. Aprobó corregirlo para TODOS. Refinamiento posterior confirmado: sin Hecho, Cancelar actividad, retirada excepcional ni botón Abrir redundante; la tarjeta o referencia abre el trabajo y el resultado real cierra el aviso. Las actividades manuales generales conservan su comportamiento. Se desarrolla en Odoo19 y el módulo mc_rov existentes, con pruebas en STAGING antes de cualquier entrega. No se activa ninguna cuenta real ni se despliega a producción durante el desarrollo.

## Alcance funcional

- Reparación: diagnóstico cierra al confirmar la revisión técnica vinculada válida; reparación al terminar realmente la orden; cancelación real conserva su semántica. Revisar sustitución de ciclos/reapertura sin duplicar.
- Fabricación: cierre por fabricación realizada o cancelada; parciales mantienen la tarea de su restante y el compromiso original/vigente.
- Aceptación: rendimiento y terreno por las pruebas seleccionadas confirmadas y sus resultados; rechazo por su resolución válida; ficha por emisión real del documento. Abrir el equipo/prueba/asistente correcto, sin cerrar por abrir o imprimir una vista previa.
- Calidad: cerrar por resolución real de la alerta y preservar reaperturas y nuevas etapas.
- Ingeniería: preparación termina al estar listo para aplicar conforme a las aprobaciones nativas; aplicación por cambio aplicado. Las actividades NATIVAS de aprobación no son los recordatorios propios de mc_rov y conservan sus acciones de aprobación.
- Inventario: recepción/entrega/interno por validación o cancelación nativas; parciales heredan plazo. Marcar recordatorio nunca mueve mercancía.

## Comportamiento aprobado

Una actividad propia pendiente se abre pulsando su tarjeta o referencia, con navegación nativa y teclado accesible. No añadir un botón «Abrir operación» si repite esa navegación. En chatter/popover, donde el resumen no abre por sí mismo, hacerlo un enlace al documento con los permisos nativos, sin un segundo botón. No ofrece «Hecho», «Hecho y siguiente» ni «Cancelar» genéricos en Centro/lista/kanban/calendario/formulario, chatter, popovers o menú global de actividades. La protección aplica también desde RPC: feedback/_action_done, cancelación, unlink, archivo active=False y lotes mixtos. Se rechaza la transacción completa con mensaje claro antes de cambiar auditoría o estado. Permisos de administrador/sudo y contextos JSON no son autorización para saltarse la regla. Se conserva la vía privada de cierres reales, validada por cada flujo; comprobar que registran el resultado real antes de ejecutar el cierre nativo, y cubrir el orden MRO para que ningún hook registre manual_done antes del guard común.

Clasificar por la identidad real del seguimiento privado y su origen, nunca por resumen, nombre del tipo ni usuario. Actividades manuales y tipos homónimos sin seguimiento siguen nativos. No convertir temporales/NewId en su origen persistido. Consultar enlaces privados solo tras autorizar actividad/origen/empresa; no exponer historial privado ni conceder ACL.

## Sin retirada manual

Decisión explícita del usuario, posterior al RED176: no existe retirada excepcional para Supervisor ni administrador. No agregar asistente, ACL, outcome exception_withdrawn ni campo current_deadline nuevo en Repair por esta causa. Descartar el producto local de esa etapa, nunca instalado, y los72 contratos que exigían el asistente. Mantener los recibos RED176 como evidencia de un alcance sustituido, no como requisito vigente. Los instaladores de retirada quedan bloqueados antes de SSH.

Un duplicado o un seguimiento generado por error se corrige técnicamente con evidencia; no se ofrece un escape cotidiano al usuario. No desactivar pendientes al pausar la política. Reprogramar y reasignar con los permisos y motivos existentes conserva el aviso. Las cancelaciones reales, sustituciones de ciclo y retiradas nativas por cambios de etapa conservan su significado actual.

## Arquitectura y límites

Protección común sobre mail.activity registrada después de los hooks de seis flujos. Reutilizar validaciones de origen y bloqueos en orden estable; los cierres de negocio siguen usando servicios de cada flujo. No confiar en un booleano de contexto ni revalidar solo la interfaz. Datos de presentación mínimos/autorizados para vistas nativas y el store de Mail; averiguar primero las firmas/templates reales instalados. Mantener el Centro con su bridge nativo y las actividades manuales intactas. Sin rediseño del Centro ni motor nuevo de tareas. Repartir/reprogramar con motivo continúa funcionando sin cerrar recordatorios.

Los resultados históricos manual_done no se reescriben, ni se reconstruyen pendientes automáticamente. Preparar informe de casos previos de trabajo abierto para decidir su recuperación sin cambios silenciosos. No contar pruebas anteriores que validaban cierre manual como contratos vigentes: mantener sus controles de permisos/auditoría y sustituir explícitamente las expectativas incompatibles por bloqueo del cierre manual; documentar cada sustitución. No afirmar que la suite1120 prueba este comportamiento nuevo.

## Verificación y entrega

1. Lectura de fuentes nativas/vistas/store y estado QA preservado; sin cambios ni reinicios.
2. RED por los seis flujos y todas las vías manuales; controles de cierres reales, actividad manual/homónima, portales/multiempresa, temporales, lotes mixtos y rollback. Clasificador exacto de resultados.
3. GREEN servidor, indicadores autorizados y vistas; pruebas focalizadas y luego suite completa por descubrimiento exacto.
4. Interfaz nativa, chatter y Centro: HOOT y comprobación visual claro/oscuro; cerrar/abrir/volver conserva filtros y no modifica stock/documentos.
5. Carreras cierre real/archivo/reprogramación y evidencias sin pendientes duplicados/huérfanos.
6. QA aislado actualizado con ambas cuentas; completar los casos pendientes y comparar fecha del parcial con su ciclo original en lectura. Preservar historia y cerrar la copia antes de entrega.
7. Revisión independiente final integral, versión compatible revalidando main, CI y paquete concreto antes de autorización de producción.

## Pendientes técnicos que debe resolver el constructor

Firmas de Mail y ubicaciones exactas de botones desde fuentes instaladas; interfaz nativa de acción abierta; campos de fechas por cada run; semántica de «listo para aplicar» comprobada por implementación actual; cantidad final de tests y adaptación explícita de expectativas viejas. En listas con selección mixta, no permitir acciones masivas de Hecho/Cancelar si incluyen automáticas; conservarlas para selección exclusivamente manual. El guard del servidor sigue siendo obligatorio aunque falle o se omita la interfaz. Estas son decisiones técnicas delegadas, no cambios de alcance.
