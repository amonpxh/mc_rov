# Piloto de seguimiento de Aceptación y Calidad

## Estado y alcance

Versión candidata: `19.0.25.2.0`. Producción conserva `19.0.25.1.0` hasta una
autorización de entrega nueva. Instalar el módulo no crea políticas, cuentas
destinatarias ni pendientes retrospectivos. La activación real se aplazó hasta
elegir la cuenta de Taller y verificar el calendario operativo.

La revisión técnica y la prueba operativa son requisitos distintos. No considerar
la aprobación de pruebas automáticas como aprobación de producción.

## Evidencia automática

- Suite nativa exacta: **825 casos**, cero fallos/errores, después de corregir
  la concurrencia y los hallazgos de revisión. Respaldo:
  `/var/tmp/mc-rov-automation-review-green-bMDIRX`. Código `0b8053c`.
- Navegador HOOT: **31/31**; archivos temporales restaurados.
- Calidad: seis carreras reales, dos conexiones por caso, reintento de la
  transacción completa; un ciclo por evento y cero actividades huérfanas.
  Copia `mc_rov_quality_ci_jfvASv`; respaldo
  `/var/tmp/mc-rov-quality-concurrency-jfvASv`.
- Aceptación: cinco carreras reales, dos conexiones por caso: finalizar MRP,
  seleccionar las mismas pruebas, confirmar rendimiento, confirmar terreno y
  emitir la misma ficha. Un ciclo, dos selecciones auditadas, tres etapas,
  un PDF real y cero pendientes al terminar. Copia
  `mc_rov_acceptance_ci_Fs4il6`; respaldo
  `/var/tmp/mc-rov-acceptance-concurrency-Fs4il6`.

Las copias se neutralizan antes de abrir conexiones Odoo: cron/correo desactivados,
sin servidor HTTP ni workers. Aceptación copia también el filestore para probar
el PDF real. Al terminar, se bloquean conexiones y se terminan las existentes.
Las bases, binarios y respaldos se conservan; no se eliminan automáticamente.

Los scripts temporales están en `.tmp/acceptance-quality-activity-pilot/` del
workspace exterior. Las sondas versionadas están en
`scripts/qa/acceptance_activity_concurrency.py` y
`scripts/qa/quality_activity_concurrency.py`. Ambas rechazan bases sin su prefijo
aislado. Un RC distinto de cero, un marcador ausente o un número incompleto de
casos invalida el resultado, aunque otra línea diga PASSED.

## Preparar la prueba operativa

Usar únicamente STAGING, con respaldo previo y un escenario propio registrado por
IDs. Crear dos cuentas QA nuevas (Taller y Supervisor), empleados ficticios,
producto seriado ROV, calendario QA en `America/Santiago` y documentos identificados
como prueba. No reutilizar cuentas ajenas ni sustituir políticas existentes.
La contraseña se introduce solamente en el terminal; no se guarda en evidencias.

El creador preparado es `.tmp/staging-acceptance-quality-activity-qa-users.ps1`
del workspace exterior. Exige evidencia825 y ambas concurrencias, y verifica las
114 fuentes instaladas contra las ya validadas antes de crear nada. Crea cuatro
órdenes borrador (normal, parcial, rechazo y pausa), cinco series y diez pruebas
borrador con datos ficticios prellenados. El rendimiento de la serie de rechazo
lleva un chequeo `no_ok`; los demás llevan `ok`. Incluye un chequeo de Calidad
pendiente, un equipo y dos etapas de Calidad propios. No confirma ni emite pruebas.
Guarda los IDs en un parámetro de STAGING y en `operational-qa-created.json`, sin
claves. Si ya existe, reutiliza el escenario sin cambiar su contraseña.

Las políticas QA de Aceptación y Calidad nacen **desactivadas**, con un día
laborable por etapa y destinatario Taller QA. El empleado puede quedar vacío:
cuenta asignada y persona encargada son datos distintos.

Supervisor tiene grupos nativos de Fabricación, Inventario y Calidad, consulta de
equipo y coordinación; Taller usa los grupos operativos nativos. Ninguna cuenta
real recibe permisos adicionales. El control general preexistente conserva su
valor; si está pausado, detener la preparación y revisar, no activarlo en silencio.

## Recorrido de Aceptación

1. Como Supervisor, activar únicamente la política QA y conservar el calendario
   y los cuatro plazos de un día laborable. Activarla no genera trabajo pasado.
2. Confirmar y fabricar una unidad de la orden QA normal, eligiendo su serie.
   Si aparece la advertencia de ausencia de componentes, aceptarla solo porque
   se trata de este equipo ficticio. No aplicar esa instrucción al trabajo real.
3. Centro de trabajo → Trabajo asignado → Actividades → Trabajo del equipo,
   proceso Aceptación: deben aparecer rendimiento y terreno, ambos sobre la serie
   realmente fabricada, asignados a Taller QA, sin duplicados.
4. Repartir a uno de los empleados QA sin cambiar cuenta ni vencimiento. Después,
   reprogramar una actividad: exigir motivo y comprobar auditoría en el equipo.
5. Abrir la selección de evidencia del equipo. Elegir explícitamente las pruebas
   QA de rendimiento y terreno. Abrir o confirmar una prueba no seleccionada no
   debe cerrar estos pendientes. RND/TRN no llevan inspección de sellos.
6. Revisar los datos ficticios y confirmar rendimiento aprobado: cerrar solo su
   realización. Confirmar terreno aprobado: cerrar terreno y crear un pendiente
   de preparación/emisión de ficha con su propio día laborable desde ese evento.
7. Guardar o previsualizar una ficha borrador: el pendiente sigue abierto. Emitir
   la ficha con ambas pruebas seleccionadas y aprobadas: guardar PDF real y cerrar
   el pendiente. Descargar de nuevo debe obtener el mismo documento congelado.
8. En otro equipo QA, confirmar rendimiento rechazado: cerrar realización y crear
   resolución de rechazo. Volver a borrador no resuelve el rechazo. Corregir y
   confirmar aprobado, o seleccionar una repetición aprobada con motivo: cerrar
   resolución. Conservar la prueba anterior y la selección auditada.
9. Fabricación parcial QA: terminar una de dos unidades y crear la orden restante.
   Solo la serie terminada obtiene aceptación; la otra la obtiene cuando se fabrica.
10. Pausar la política y fabricar la orden QA de pausa: no crear aceptación nueva.
    Reactivar y editar no recupera ese evento. Un pendiente anterior sí se puede
    cerrar por su evento real mientras la política está pausada.

Cada etapa usa su propio evento y fecha. No sumar los días como una única fecha
global ni cambiar vencimientos existentes al editar la política.

## Recorrido de Calidad

1. Activar la política QA de Calidad con Taller QA y calendario QA. Crear una
   alerta abierta sobre el producto/serie QA: un pendiente «Resolver alerta de
   Calidad», plazo de un día laborable. No crear otro por mover entre etapas abiertas.
2. Desde Centro, proceso Calidad, comprobar cuenta/empleado/alcance y reparto con
   motivo al reprogramar. Taller ve su trabajo; Supervisor puede consultar el equipo.
3. Marcar la actividad hecha o cancelarla: la alerta sigue abierta. Editarla no
   recrea el pendiente. Cerrar la alerta y reabrirla crea un nuevo ciclo si está activo.
4. Cerrar por una etapa con `done=True`: retirar el pendiente. Reabrir por una etapa
   abierta: crear uno nuevo. Probar también cambiar el indicador `done` de una
   etapa **propia de QA**, nunca de una etapa compartida por trabajo ajeno.
5. Fallar el chequeo QA nativo: una única alerta y un único pendiente. Repetir el
   fallo no duplica. Pasar luego el chequeo no cierra automáticamente la alerta.
6. Pausar Calidad y crear/reabrir una alerta QA: no generar. Reactivar/editar no
   reconstruye. Cerrar una alerta ya seguida durante la pausa sí cierra su pendiente.

## Retiro y entrega

El retiro debe usar los IDs registrados del escenario, respaldar antes y cancelar
solo sus pendientes. Archivar cuentas/empleados/producto propios y dar de baja las
series por el mecanismo del módulo. Conservar órdenes, pruebas, fichas, PDF,
alertas, calendario e historial. Retirar destinatarios QA; restaurar el estado del
control general solo si el escenario lo modificó y aún coincide con lo esperado.
No borrar documentos ni tocar políticas ajenas.

Después: resolver hallazgos importantes de la revisión, verificar CI del PR,
adjuntarlo al chat y solicitar nueva aprobación para merge/producción. El despliegue
debe respaldar BD/filestore/código, conservar recuperación fresca y verificar que
no creó políticas ni actividades retrospectivas. Confirmar aparte la cuenta Taller
y el calendario operativo antes de habilitar automatismos reales.
