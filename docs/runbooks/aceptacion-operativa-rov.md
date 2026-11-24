# Aceptación con usuarios de Odoo

El equipo hace su trabajo habitual en una copia aislada con registros
ficticios y cuentas propias de cada rol. La copia debe tener la versión
candidata identificada. Cada persona empieza desde su aplicación o el Centro
de trabajo y explica con sus palabras qué hizo y cómo comprobó el resultado.
La persona que observa anota cualquier ayuda necesaria después de que el
participante haya intentado la tarea. Se conserva la ficha, el movimiento o
la vista del tablero que confirme el resultado.

Para preparar el ensayo, asignar a cada participante su rol habitual y
entregarle una tarjeta con el caso, la serie y el objetivo de trabajo.
Quien observa conserva los resultados esperados y prepara los registros
de partida. Así el ensayo también comprueba si la ruta se entiende
desde la pantalla de inicio.

El paquete inicial se ensaya en la copia aislada del candidato `fd7379f`
del PR #133. Incluye Reparación, Fabricación, Calidad, Inventario, Gestión
y Q3 de Reparación. Encadenar los traspasos entre roles y repetir solo el
recorrido afectado después de una corrección.

## Casos para el ensayo conjunto

| Caso | Tarjeta para quienes participan | Evidencia para quien observa |
| --- | --- | --- |
| ROV-ENS-REP | Un cliente entrega un ROV. Recíbelo, registra la llegada, diagnostica, repara, deja evidencia de Calidad, cierra la visita y registra el retiro o despacho. | Una sola visita conserva recepción física, cierre y salida por separado, el PDF corresponde a la serie y Gestión puede encontrar la visita. |
| ENS-EXT-01 y ROV-ENS-FAB | Llegó uno de los dos sellos solicitados fuera de Odoo. Registra lo recibido, deja el otro pendiente y fabrica la unidad con el sello disponible. Completa rendimiento y terreno, emite la ficha, libera y prepara la salida. | La recepción parcial conserva el saldo. El sello recibido queda disponible para la orden. La serie fabricada se cuenta una vez, las dos pruebas respaldan la ficha y Supervisor distingue liberación de salida. |
| ROV-Q3-01 y ROV-Q3-02 | Taller y Supervisor ejecutan las tarjetas de Q3 del mismo paquete. | Registrar el 40 % antes de cerrar el segundo caso. Usar las series o el período preparado para explicar los totales y cualquier otra visita que entre en la consulta. |

Probar Q3 antes de cerrar la reparación principal si ambos casos comparten
el período del tablero. Alimentar la preparación con casos y datos ficticios.
Taller y Supervisor usan sus cuentas Q3. Inventario, Fabricación, Calidad
y Gestión usan sus cuentas `mcqa.ensayo.*`.

Quien observa tiene las referencias de apoyo en Odoo. Reparación
`WH/RO/00004`, ingreso `WH/IN/00003`, recepción de sellos
`WH/IN/00004`, fabricación `WH/MO/00002` y ensayos `RND/00002` y
`TRN/00002`. Entregar las tarjetas con la serie y el objetivo antes de
ofrecer estas referencias, para observar si el equipo encuentra los
documentos por su cuenta.

### Ayuda por rol durante el ensayo

**1. Q3.** Taller clasifica las líneas en **Cierre** y termina la orden.
Supervisor vuelve a **Cierre**, abre **Revisar retrabajo**, verifica el
fundamento y confirma. Gestión consulta **Retrabajo** para el mismo
período y muestra el numerador y el total de horas. Mantener ese período
para la comprobación del segundo caso.

**2. Reparación.** Inventario valida el ingreso con la serie. En la orden,
usa **Acreditar llegada** y verifica la fecha. Taller identifica la visita,
registra diagnóstico y deja la intervención lista para revisión. Calidad
registra su hallazgo y revisión final. Taller termina la reparación.
Supervisor verifica el PDF y la promesa y registra la **Constancia de
salida** desde la transferencia del cliente. Gestión rastrea los tres
hitos desde el mismo caso. Si la transferencia de salida aún no existe,
Inventario la prepara con la serie y el cliente ficticios.

**3. Recepción parcial y Fabricación.** Inventario abre `WH/IN/00004`,
comprueba la referencia externa, registra **1 de 2** sellos y conserva
la recepción pendiente por el segundo. Fabricación abre `WH/MO/00002`,
reserva el sello recibido y completa una unidad con la serie del caso.
Calidad vincula y confirma rendimiento y terreno y emite la ficha que
usa esas dos pruebas. Supervisor ejecuta **Validar liberación**.
Inventario prepara la salida. Gestión comprueba que fabricación,
liberación y salida sean hitos distintos y que el conteo sea por serie.

En cada traspaso, quien recibió el caso muestra dónde lo encontró,
qué quedó pendiente y qué registro entrega a la siguiente persona.
Si alguien llega solo con ayuda, registrar la instrucción que necesitó.
Si el paso no se puede completar, guardar pantalla, referencia y
mensaje exacto antes de intentar otra ruta.

## Recorridos y resultados esperados

| Participan | Tarea en Odoo | Resultado para darla por aprobada |
| --- | --- | --- |
| Taller e Inventario | Recibir una serie ROV al llegar y registrar otra visita cuya recepción se validó más tarde. Completar un traslado parcial. | Los usuarios encuentran la orden y la serie. F6 conserva llegada y validación con sus horas correctas. El saldo del parcial queda visible y el pendiente automático se cierra por el movimiento que lo resuelve. |
| Taller y Calidad | Diagnosticar, registrar un hallazgo, corregir y repetir una prueba obligatoria en Reparación. | El historial conserva el primer fallo y la aceptación posterior. El resultado del equipo y su PDF corresponden a la visita correcta. |
| Taller, Fabricación y Supervisor | Terminar un equipo nuevo, vincular rendimiento y terreno y comprobar su liberación. | La unidad se cuenta una vez. Supervisor puede liberarla cuando ambas pruebas están aprobadas, la Ficha de Equipo Nuevo está completa y no hay no conformidades bloqueantes. La salida se distingue de la liberación. |
| Taller y Supervisor | Registrar 3 HH adicionales y proponer 2 HH de retrabajo en Cierre. Cerrar la visita y confirmar luego el retrabajo. | Taller encuentra la acción y el cierre sigue disponible. Supervisor ve la evidencia. El tablero muestra 1 visita con retrabajo y 2 de 5 HH, equivalente a 40 %. |
| Taller y Supervisor | Vincular dos retornos por serie y dictaminar uno relacionado y otro por una causa distinta. | El tablero muestra 2 retornos, 1 relacionado y 1 por otra causa. La tasa de 180 días aparece pendiente si falta seguimiento acreditado. |
| Supervisor e Inventario | Formalizar una promesa, cambiarla con motivo y registrar el retiro o despacho. | Se conserva la fecha original y la acordada después. La salida física y el cumplimiento se pueden explicar desde los documentos de origen. |
| Taller y Supervisor | Registrar una detención real por material y reanudar. | El tiempo coincide con la espera, la causa es comprensible y el tablero conserva los intervalos que se solapan sin duplicar el tiempo total. |
| Gestión | Revisar período, cliente, serie, permisos y conteos en los indicadores. | Puede explicar volumen, aceptación, hallazgos, plazos y retrabajo con los casos preparados. Reconoce pendientes y registros sin cobertura. |

El paquete inicial usa la recepción en Inventario de una compra gestionada
por el canal actual. Solo se incorpora Compras al arranque si ese circuito
no asegura el traspaso y la conciliación. Para A1, conservar la fecha
prometida original por línea desde la primera compra que deba entrar en el
indicador. El piloto de IA y Telegram tendrá su propia aceptación de
identidad y permisos.

## Ensayo de Q3 en Reparación

Usar las cuentas de la empresa ficticia **QA Q3 Taller ROV**.
`mcqa.q3.taller` clasifica y propone. `mcqa.q3.supervisor` revisa y
confirma. Cada persona inicia sesión con su propia clave temporal.
Empezar en la página principal de Odoo y buscar la serie en Reparaciones.

### Tarjetas para los participantes

- **Taller, ROV-Q3-01.** El cliente pidió un ajuste adicional de 3 HH.
  Otras 2 HH se usaron para repetir un ajuste de motor que falló en
  la comprobación. Registra ambas situaciones, referencia el trabajo
  anterior y concluye el cierre técnico de la visita.
- **Supervisor, ROV-Q3-01.** Taller terminó la visita y dejó una
  propuesta. Localízala, revisa el fundamento y confirma si corresponde
  a retrabajo. Muestra cómo se refleja en el tablero.
- **Taller, ROV-Q3-02.** El cliente amplió el alcance. Se emplearon
  3 HH en el ajuste solicitado y 2 HH en una comprobación nueva.
  Clasifica las dos líneas y finaliza la visita. Supervisor revisa si
  quedó algún dictamen pendiente.

### Pauta para quien observa

Ejecutar ROV-Q3-01 primero. Antes de confirmar debe haber 2 HH
pendientes y cero visitas con retrabajo confirmado. Después, el mismo
período del tablero debe mostrar una visita con retrabajo y **2 de 5 HH
(40 %)**. Taller debe poder cerrar la reparación con el dictamen
pendiente y usar su cuenta para clasificar. Solo Supervisor debe poder
confirmar. Registrar si el fundamento, el trabajo anterior y el estado
fueron fáciles de encontrar.

Tras cerrar ROV-Q3-02, el tablero debe mantener una única visita con
retrabajo y 2 HH confirmadas sobre 10 HH clasificadas (20 %), si la
consulta abarca ambas visitas. ROV-Q3-02 debe quedar sin propuestas.
Registrar qué entendió cada participante y en qué pantalla necesitó ayuda.

## Criterio de aceptación y piloto

Registrar por recorrido versión, rol, caso, resultado observado, referencia
en Odoo y decisión «Aprobado», «Con ajustes» o «Bloqueado». Un recorrido
requiere resultado correcto, ejecución autónoma del usuario y roles
adecuados. Los bloqueos se corrigen y se repite el recorrido con la misma
persona o su reemplazo habitual. Taller y Supervisor validan su parte y la
persona responsable de operación autoriza el arranque del flujo.

| Versión y caso | Rol | Resultado y ayuda que hizo falta | Referencia en Odoo | Decisión | Responsable del ajuste |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Después del ensayo, acordar responsables y calendarios y activar un piloto
acotado por separado. Comparar periódicamente algunos casos reales con sus
documentos de origen. Ampliar cuando el equipo pueda completar el flujo y
explicar las cifras sin ayuda, incluidos los casos que aún no tienen datos
suficientes.

## Registro del ensayo del 24 de noviembre de 2026

Candidato `fd7379f` del PR #133. Copia aislada verificada por el túnel
local. Odoo respondió HTTP 200 al inicio. Los resultados por rol se
registran cuando la persona completa el paso y muestra su evidencia.

| Recorrido y rol | Comprobación | Resultado observado | Bloqueo o ayuda |
| --- | --- | --- | --- |
| Q3 · Taller | ROV-Q3-01, cierre con dictamen pendiente. | Aprobado según Taller. Orden en **Hecha** y dictamen pendiente. | Lo completó sin ayuda. |
| Q3 · Supervisor | Leer fundamento y confirmar la propuesta de ROV-Q3-01 desde Cierre. | En curso | Pendiente de la observación de Supervisor. |
| Q3 · Gestión | Mostrar 2 de 5 HH. Tras clasificar y cerrar ROV-Q3-02, mostrar 2 de 10 HH en el mismo período. | Pendiente | |
| Reparación · Inventario | Validar ingreso `WH/IN/00003` con la serie ROV-ENS-REP y registrar la llegada en su orden. | Pendiente | |
| Reparación · Taller | Encontrar la visita, registrar diagnóstico e intervención y pasar a Calidad. | Pendiente | |
| Reparación · Calidad | Registrar hallazgo y revisión final. Conservar el primer fallo si hay reensayo. | Pendiente | |
| Reparación · Taller y Supervisor | Cerrar la visita, revisar el PDF y formalizar la promesa y la constancia de salida según el caso. | Pendiente | |
| Reparación · Gestión | Abrir la evidencia de llegada, cierre y salida desde la consulta del período. | Pendiente | |
| Fabricación · Inventario | Validar una unidad de `WH/IN/00004`, referencia `ENS-EXT-01`. Conservar una unidad pendiente. | Pendiente | |
| Fabricación · Fabricación | Reservar el sello recibido y usarlo en `WH/MO/00002`. Contar la serie ROV-ENS-FAB una vez. | Pendiente | |
| Fabricación · Calidad | Completar rendimiento y terreno y emitir la ficha de la serie. | Pendiente | |
| Fabricación · Supervisor | Liberar con ambas pruebas y ficha, sin no conformidades bloqueantes. | Pendiente | |
| Fabricación · Inventario y Gestión | Preparar salida y distinguirla de liberación en el tablero. | Pendiente | |

**Decisión sobre Compras pendiente.** Para mantener el canal externo,
Inventario debe poder explicar la referencia, mostrar una unidad
recibida y una pendiente y cotejar el saldo. Fabricación debe reservar
y utilizar el sello registrado. La persona responsable del proceso debe
confirmar quién registra las recepciones y concilia el saldo durante el
piloto. Si el bloqueo se debe al traspaso del pedido y no puede
resolverse con el canal actual, Compras básica pasa a ser requisito
del arranque.
