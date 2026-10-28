# Seguimiento de ingeniería y operaciones de Inventario

Estado: propuesta para revisión; no autoriza implementación ni activación real.
Base: producción 19.0.25.4.1, main `d6f5efe`.

## Propósito y decisiones del usuario

Completar la evaluación de automatismos del Centro de trabajo antes de diseñar
Compras, definir KPI y preparar el uso real. Los pendientes deben estar ligados a
eventos reales de Odoo, con responsable, plazo, historial y cierre comprobable.

El usuario eligió:

- Ingeniería: **un año calendario total desde la creación del cambio**. No un año
  por etapa; aprobar, cambiar de etapa o reabrir no reinicia ese límite.
- Operaciones de Inventario: **tres días laborables**.
- Mantener la configuración de destinatarios reales para la preparación del uso
  real. Esta entrega no crea cuentas ni activa políticas reales.
- Compras/abastecimiento se diseña después; IA/Telegram se aplaza hasta estabilizar
  la operación y el reemplazo de Defontana queda al final.

Son propuestas del agente, todavía revisables: los disparadores exactos, el alcance
por tipo de operación, la precedencia de fechas logísticas, los nombres de los
pendientes y las reglas de parciales descritas abajo. No atribuirlas al usuario.

## Evidencia instalada y límites de la auditoría

Dos consultas en STAGING, READ ONLY y rollback, sin ejecutar acciones de negocio:
`.tmp/design-inventory-automation-pilot/installed.json` y `details.json` en la raíz
de trabajo. Se inspeccionaron 17 modelos y 38 funciones nativas adicionales.

- `mrp.eco` ya tiene actividades. `_create_approvals` crea la aprobación y una
  actividad nativa por aprobador. No añadir una segunda actividad de aprobación.
- `approve`/`reject` actualizan la aprobación, autor, fecha e historial. La función
  capturada no cierra la actividad nativa: no prometer ese cierre ni inferirlo del
  texto de la actividad. La relación actividad/aprobación no está explicitada por
  el módulo nativo. Esta entrega no intenta deducirla por título o autor.
- No había plantillas de aprobación en STAGING. Es un dato de configuración de
  ese entorno, no una decisión de quitar aprobaciones ni un diagnóstico productivo.
- `allow_apply_change` depende de la etapa y de `state` confirmed/progress. No
  significa por sí solo que todas las aprobaciones estén satisfechas. La decisión
  de preparar/aplicar debe incluir las restricciones nativas de aprobación/avance.
- `stock.picking` tiene actividades; `stock.quant` y
  `stock.warehouse.orderpoint` no tienen `activity_ids`.
- Reabastecimiento ya calcula necesidades y puede generar aprovisionamiento;
  el planificador además reserva movimientos y puede confirmar fabricaciones.
  Los cron nativos de aprovisionamiento y recordatorio de compras estaban apagados
  en STAGING. Su estado productivo no se consultó y no se modifica aquí.
- Conteos, usuarios/fechas de conteo y conflictos de ajuste ya existen en Odoo.

## Alcance inicial propuesto

Dos procesos separables, reutilizando las políticas y servicios de seguimiento
existentes. Se implementaría primero Ingeniería y después logística.

### Ingeniería: un cambio de ingeniería como origen

El origen es un ECO (`mrp.eco`), tanto cambios de producto como de BoM. Crear o
editar directamente un producto o BoM no inicia un pendiente: no existe una
solicitud de trabajo inequívoca y no queremos tratar cada edición como un proyecto.

Propuesta de alcance: ECO de productos pertenecientes a la jerarquía ROV que ya
usa el Centro. Se conserva el vínculo con lecciones/Calidad; no se crea un ECO
automáticamente por cada alerta. Solo empresa explícita y producto accesible al
destinatario; ECO sin empresa válida queda sin seguimiento y con explicación.

Estados de seguimiento, independientes de los estados nativos:

| Evento real | Pendiente propio | Resolución |
| --- | --- | --- |
| Creación de ECO elegible, activo, no terminado | Preparar cambio de ingeniería | Se completa al llegar realmente a una situación aplicable con las aprobaciones nativas necesarias satisfechas. Iniciar revisión no equivale a terminar la preparación. |
| Transición real a situación aplicable y autorizada por el flujo nativo | Aplicar cambio de ingeniería | Se completa cuando la aplicación nativa termina con `state=done`. |
| Retroceso/rechazo que deja de permitir aplicar | Se retira el pendiente de aplicar; vuelve a preparación si corresponde | Se conserva el historial y el límite original; no crear una tarea adicional de «rechazo» sin necesidad. |
| Archivo del ECO | Se cancelan los pendientes propios | Se conserva la identidad/historial. Desarchivar es un nuevo evento elegible, con el mismo límite total. |

La elegibilidad para aplicar debe usar las reglas nativas reales de etapa,
aprobaciones y bloqueo, no nombres de etapas ni solo `allow_apply_change`. Antes de
implementar, los contratos nativos deben reproducir aprobación obligatoria
pendiente, rechazo y aprobación satisfecha. Un cambio de configuración de etapas
no reconstruye por sí solo pendientes de todos los ECO antiguos.

Puede haber actividades nativas de aprobación mientras existe «Preparar cambio»:
son responsabilidades distintas. Las aprobaciones nativas conservan sus propios
destinatarios y fechas; esta entrega no las reprograma ni cierra automáticamente.
El año total elegido se aplica al seguimiento propio de preparar/aplicar. Cambiar
este alcance para gestionar también su ciclo nativo requeriría decisión explícita.

### Inventario: un documento logístico como origen

Origen `stock.picking`, con pendientes distintos según el código nativo del tipo:

- `incoming`: gestionar recepción.
- `outgoing`: gestionar entrega.
- `internal`: gestionar transferencia interna.

Una política por empresa selecciona **tipos concretos de operación**. No se
incluyen todos los almacenes automáticamente. Dentro de los tipos seleccionados
se incluyen equipos, repuestos y componentes: no un filtro exclusivo de ROV.

La confirmación real del documento/movimientos inicia un único seguimiento;
`waiting`, `confirmed` y `assigned` son situaciones pendientes, no tres tareas.
`draft` no genera actividad. La cobertura debe incluir confirmación nativa directa,
autoconfirmación y creación de órdenes restantes; no depender solo del botón de UI.

- `done`: completa el pendiente propio de ese documento.
- `cancel`: cancela el pendiente propio.
- Parcial: cierra la parte terminada y deja un pendiente en cada documento restante
  confirmado. La orden restante hereda el límite vigente de la operación original;
  dividir no gana otros tres días. Mantener trazabilidad sin actividades huérfanas.
- Una devolución es otro documento: si su tipo está configurado, se atiende como
  una nueva operación; no reabrir el documento original terminado.
- Cambiar disponibilidad, reservar o cambiar a listo no crea duplicados ni vuelve
  a contar el plazo. No validar una operación por dar «Hecho» a su actividad.

Los avisos nativos de excepción/reserva no se renombran, eliminan ni convierten en
pendientes propios. Nuestro historial identifica únicamente actividades propias.

## Plazos y fechas

### Ingeniería

Propuesta técnica: calcular el aniversario de `create_date` en la zona operativa
explícita de la política. Un año es un año calendario, no 365 días fijos. Para una
creación el 29 de febrero, usar 28 de febrero del año no bisiesto siguiente.

El límite se captura al crear el primer seguimiento elegible y siempre se calcula
desde la creación real del ECO, aunque el primer evento seguido sea aplicar.
Ambas etapas y reaperturas conservan ese límite. No cambiar `effectivity_date`:
fecha de efectividad de ingeniería y vencimiento de actividad no son equivalentes.

El plazo general es configurable para nuevos casos; modificar una política no
recalcula casos existentes. Reprogramar un caso exige la acción explícita, motivo
y permisos de coordinación; su historial conserva límite original y vigente.

### Logística: decisión de anclaje por confirmar

Los tres días laborables se calculan con `mc.rov.work.deadline._working_date`,
calendario explícito por empresa, jornadas/excepciones y zona horaria. Se excluye el
día del evento, igual que los procesos laborales ya entregados. No modificar esos
procesos ni sus calendarios.

Falta confirmar **desde cuándo** contar esos tres días si una recepción está
confirmada hoy pero programada para una fecha futura. Propuesta del agente:

1. Registrar el seguimiento al confirmar.
2. Contar desde la mayor entre confirmación y fecha programada inicial, para no
   exigir recibir físicamente material antes de la llegada prevista.
3. Si existe un `date_deadline` nativo anterior, respetarlo como límite más exigente.
4. Un cambio posterior de `scheduled_date` no mueve silenciosamente el vencimiento
   capturado. Se necesita reprogramación explícita con motivo.

Alternativa: contar siempre desde confirmación y considerar esos tres días como
plazo de gestión, aunque la operación física esté programada después. La elección
cambia lo que significa el pendiente, y debe quedar resuelta antes del plan.

## Configuración, responsables y controles

Conservar `Centro de trabajo → Configuración → Seguimiento automático`, añadiendo
Ingeniería e Inventario. El control general pausa solo las actividades propias;
no desactiva aprobaciones, cron, reglas de compra o reservas nativas.

Ingeniería: empresa, activado, cuenta responsable de preparación/aplicación,
duración en años calendario (inicial 1) y zona operativa explícita. Logística:
empresa, activado, tipos de operación, cuenta responsable por clase de operación,
calendario y días laborales (inicial 3). Son parámetros, no nuevas cuentas reales.

Reutilizar el patrón existente de validar destinatario interno/activo, pertenencia
a la empresa y acceso al origen bajo **su propio contexto**, sin heredar empresas
del actor. Sin destinatario/configuración válida no se genera un pendiente ni se
amplían permisos. Empleado ejecutor opcional y repartible después; no se deduce del
usuario autor o del responsable del registro.

La instalación no crea políticas activas, destinatarios, aprobadores ni cron. La
configuración inicial solo se ensaya con cuentas/datos QA de STAGING.

## Ciclo de vida, identidad y privacidad

- Actividad propia única por origen, ciclo y etapa; carreras concurrentes deben
  mantener esa identidad y reintentos transaccionales nativos.
- Historial privado con origen, empresa, etapa, fechas, actividad, resultado y
  motivo. Los usuarios trabajan mediante el origen autorizado; no acceso directo
  amplio a historiales ni acceso técnico a acciones.
- Pausar impide nuevos pendientes propios y permite cerrar los existentes. Al
  reactivar no se reconstruyen eventos pasados. Una transición futura elegible
  puede crear su nueva etapa aunque la anterior no se haya seguido.
- «Hecho» o cancelar manualmente una actividad registra esa decisión; no aprueba
  un ECO, no aplica un cambio, no valida stock y no genera de nuevo el mismo evento.
- Reprogramación/reparto conserva auditoría y no amplía el límite por cambios
  indirectos en el documento. Las divisiones heredan el límite vigente capturado.
- Con seguimiento activo, impedir sustituir la identidad del origen: empresa,
  producto/ECO, tipo operativo y ubicaciones según corresponda. Los cambios
  legítimos de líneas/cantidades deben seguir permitidos por Odoo; no congelar el
  trabajo real. El diseño técnico decidirá validaciones exactas antes de los tests.
- Proteger orígenes/historiales contra borrado con explicación comprensible.
  Registros temporales o sin origen persistente no crean efectos persistentes.

## Centro de trabajo

Ingeniería usa el filtro Diseño existente en Trabajo asignado → Actividades.
Agregar Inventario para actividades cuyo origen inmediato sea `stock.picking`,
con los permisos y filtros actuales de Mi trabajo/Trabajo del equipo/Empleado.
No mezclar stock.quant/orderpoints sin soporte de actividades ni inferir proceso
por el resumen de una tarea. Mantener dominios propios de Aceptación y el resto.

No se añade otro botón al menú principal. Se conservan las cinco secciones de
Inventario y la apertura de la aplicación completa.

## Fuera de esta entrega

- Aprobación o aplicación automática de ECO, cambios automáticos de BoM.
- Validación de recepciones/entregas/transferencias o aplicación automática de
  conteos por marcar una actividad como terminada.
- Duplicar mínimos/reabastecimiento, activar el planificador o crear compras por
  estas políticas de seguimiento.
- Actividades nuevas por cada faltante/cambio de cantidad, conteos o revisiones de
  productos sin un diseño adicional. Se revisan con Compras y preparación real.
- IA/Telegram, KPI, cuentas reales, cambios de permisos, calendario productivo,
  PDFs, migración comercial/tributaria y pendientes históricos retroactivos.

## Validación y entrega

TDD por recorrido, reutilizando escenarios nativos reales. RED antes de producto,
GREEN focalizado, permisos/multiempresa/identidad/registros temporales, parciales,
fechas laborales y aniversario/bisiesto, decisiones manuales y pausas. No agregar
pruebas triviales que solo repitan literales de implementación.

Primero Ingeniería completa; luego logística. Usar STAGING con respaldo y retiro
de pruebas temporales; concurrencia en copias aisladas sin cron/correo. QA manual
con cuentas temporales, incluida convivencia con aprobación nativa. Tras cambios
relevantes, regresión exacta completa y pruebas HOOT donde cambia el Centro.

Retirar QA conservando historial. PR/CI/revisión/merge y entrega productiva con
respaldo y autorización concreta; las políticas reales quedan sin activar hasta
la preparación operativa. Preservar producción 19.0.25.4.1 y los PDFs congelados
mientras esta propuesta y el posterior plan se revisan.

## Lo que queda a criterio técnico del constructor

Nombres y estructura exactos de clases/tablas, separación de servicios y locking,
ubicación precisa de hooks nativos y organización de contratos. Debe justificar
los hooks con la evidencia instalada y probar eventos reales, no señales de UI.
Puede dividir la entrega en PR separados para ingeniería y logística.

No quedan a su criterio: ampliar silenciosamente a todos los almacenes, elegir
destinatarios reales, el significado de los tres días logísticos, reiniciar el año
de ingeniería, cerrar aprobaciones nativas por coincidencia de texto ni activar
reglas nativas de aprovisionamiento.
