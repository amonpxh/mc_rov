# Trabajo pendiente

> Actualizar esta sección al cerrar cada sesión de trabajo.

## Diseño abierto, salido de mirar las pantallas el 2026-08-17

Todo esto quedó discutido y **sin decidir**. El hilo está en el historial de esa sesión; lo que
sigue es lo que hay que resolver antes de escribir código.

- [ ] **Las pruebas de fabricación y de terreno ya existen en `stock.lot`, y la revisión las
  duplica.** El número de serie guarda los resultados de las dos: laboratorio
  (`mc_prueba_leak`, `mc_ancho_banda`, `mc_subida`, `mc_bajada`, las dos temperaturas `_lab`,
  `mc_tiempo_prueba_lab`, `mc_esfuerzo`, `mc_en_reposo`, `mc_consumo_corriente`,
  `mc_limitacion_pilot_gain`, `mc_ganancia_luz`) y terreno (`mc_fecha_prueba`, `mc_lugar`,
  `mc_profundidad`, `mc_velocidad_corriente`, `mc_alimentacion`, `mc_tiempo_prueba_terreno`,
  las dos temperaturas `_terreno`, `mc_observacion`). La revisión con `tipo` en `fabricacion`
  o `terreno` registra lo mismo, y está vacía porque nadie la usa.

  **En el lote, una prueba es un valor único: correrla dos veces pisa la anterior.** El campo
  se llama `mc_fecha_prueba` —tiene fecha, o sea que se entendió que era un evento— pero solo
  hay espacio para uno.

  Esto contradice el § 1.1 del diseño de la revisión, que descartó mover esos campos diciendo
  que eran «la ficha técnica de fabricación». **Esa corrección metió en la misma bolsa dos
  cosas**: chasis, motores, pesos y medidas del umbilical sí son ficha (*cómo es* el equipo);
  prueba de leak, ancho de banda, temperaturas, lugar y profundidad son resultados de un
  evento.

  **Posición de Paulo (2026-08-17):** los puso en el lote porque la fabricación se identifica
  por número de serie, y **no quiere mezclarlas con las revisiones de reparación** — una
  prueba de fabricación no es una revisión: no lleva sellos ni hallazgos, y los campos no son
  los mismos. Tampoco se hacen varias pruebas por equipo, **salvo en un diseño nuevo o un
  rediseño**, y ahí el enfoque es de troubleshooting.

  Entonces la pregunta no es «¿mover o no mover?» sino **qué modelo describe una prueba de
  fabricación**, que probablemente no sea ni el lote ni la revisión actual.

- [ ] **Las lecciones aprendidas de fabricación no se guardan en ninguna parte**, y esto es lo
  más valioso que salió de esa conversación. Hoy se hacen fabricaciones y modificaciones de
  fabricación **a partir de errores y problemas detectados al armar equipos**, y ese
  aprendizaje se pierde. Es el mismo hueco que el diagnóstico de fallas cerró del lado de la
  reparación, sin cerrar del lado de la manufactura.

### Lo que sí quedó decidido el 2026-08-17 sobre fabricación

Los tres puntos de arriba **no se diseñan por separado**: son un sistema. Decidido en
conversación, todavía sin spec.

1. **La lección es del modelo, no de la unidad.** Palabras de Paulo: *«la lección debería ser
   del modelo, actualmente se queda solo en la unidad — ese es el problema»*. Eso parte el
   diseño en dos niveles: la prueba es de un número de serie, la lección es de un
   `product.template` y aplica a todo lo que se fabrique de ahí en adelante. Promover un
   hallazgo a lección es un **acto deliberado**, no automático: «a este ROV se le filtró el
   E-pod» y «cambiamos cómo se sellan todos los MC-300» no son la misma afirmación.

2. **La lección ya tiene una segunda fuente, viva en producción hoy.** Una línea de trabajo
   con `origen = diseno` («lo pensamos mal») o `= falla_fabricacion` («lo hicimos mal») **es
   una lección de fabricación ya escrita**, del lado de reparación, sin destinatario. Cerrar
   ese lazo es lo que hace que `origen` pague: hoy es análisis retrospectivo y nada más.

3. **Se diseña completo, se despliega por etapas.** Diseñar la lección aislada la ajustaría a
   la única fuente que hoy tiene datos y no calzaría cuando llegue el hallazgo de fabricación.
   El orden de implementación se decide con el diseño entero a la vista, no antes.

4. **La pregunta abierta que define el ancla: ¿se usa `mrp`?** Si fabricación se maneja con
   órdenes de fabricación de Odoo, el evento de armado cuelga de ahí y no del lote —el lote es
   el *resultado* del armado, no el armado—. Y además resuelve gratis el riesgo del punto 5,
   porque una orden de fabricación es un momento en que alguien tiene que mirar la pantalla.
   Hoy `mrp` **no** es dependencia del módulo.

5. **El riesgo a resolver antes de escribir código: un registro de lecciones que nadie lee
   mientras arma el equipo es un cementerio.** Y es peor que el riesgo habitual: esto *sí* se
   va a llenar —escribir la lección es satisfactorio— y no se va a leer. Guardarla en el
   producto y confiar en que alguien entre a mirarla no basta; hay que decidir **dónde
   aparece en el momento de fabricar**.

6. **La batería de fabricación deja de ser un pendiente suelto:** es el contenido del evento
   nuevo. Lleva años sin definirse justamente porque no había dónde ponerla.

- [ ] **La batería de fabricación no está definida.** Los 22 chequeos tienen las tres casillas
  `aplica_*` encendidas, así que un ROV recién armado recibe las mismas preguntas que uno que
  llegó roto — incluidas las que buscan desgaste y daño de uso. Quedó así por omisión al
  retirar el chequeo de marcas de plumón en `19.0.12.0.0`, que era el único que separaba las
  baterías. **El mecanismo para separarlas existe y está probado: son datos, no código.**

- [x] ~~**Falta software en la batería de reparación.**~~ — **hecho en `19.0.15.2.0`.** Dos
  chequeos en la sección `comunicacion`, solo reparación: «El software de superficie inicia y
  opera» y «El software instalado corresponde a la ficha».

- [x] ~~**La versión de software revierte sola.**~~ — **hecho en `19.0.15.2.0`, en su forma
  mínima.** Lo que Paulo corrigió el 2026-08-17 y que cambiaba el diseño: **no es un número de
  versión que retrocede, es el software mismo que vuelve al de fábrica** — ROVControl a
  QGroundControl, o QGroundControl a una versión más vieja. Un diseño de tres `Char` habría
  dejado pasar el caso más frecuente, porque el nombre de un programa no es un número. ArduSub
  «no se toca mucho, pero quizás».

  Quedó como un chequeo más los cinco `related` de la ficha al lado, para poder responderlo sin
  salir de la pantalla. **Sin modelo, sin comparación automática, a propósito** — razones y la
  regla para revisitarlo en [`designs/revision-tecnica.md`](designs/revision-tecnica.md) § 8.8.

  Lo que queda vivo del punto: **medir si se llena.** El `detalle` es la evidencia que decide
  si vale estructurarlo, y es opcional — el chequeo bloquea la confirmación, el detalle no. Sin
  detalle, un «No OK» dice que algo no cuadró y no dice qué software era. Mismo riesgo y misma
  mitigación que `hallazgo_origen_id` más abajo.

  Efecto secundario que ya vale: **obliga a mantener la ficha al día**, porque una diferencia
  es o un equipo que revirtió o una ficha desactualizada.

- [ ] **Sí se hacen pruebas en terreno**, sobre equipos fabricados, y hoy viven en el lote. El
  tipo `terreno` de la revisión existe **sin ninguna justificación escrita** y nada lo crea:
  hay que decidirlo junto con el primer punto. Ver el apartado de fabricación de más abajo —
  la decisión depende de una sola pregunta sin responder.

## Fabricación — el diseño está escrito

**Ver [`designs/fabricacion.md`](designs/fabricacion.md).** Recoge todo lo discutido el
2026-08-17 y 18, con lo verificado contra `odoo_prod` en su § 2 y lo que queda sin decidir en su
§ 10. Lo que sigue aquí abajo es el detalle que le dio origen.

## Fabricación — lo verificado el 2026-08-18

Todo lo de aquí abajo **se comprobó contra `odoo_prod`**, no es de memoria. Cambia bastante lo
que había anotado el 2026-08-17: la mayor parte de lo que íbamos a construir ya existe.

### Los módulos están instalados, no solo disponibles

`mrp`, `mrp_plm`, `quality`, `quality_control` y `web_enterprise` salen todos `installed`. Es
una instancia **Enterprise**, así que PLM y Calidad están sobre la mesa y nadie los usa.

`mrp` asigna el número de serie por su cuenta (`mrp.production.lot_producing_id`); hacen falta
dos configuraciones y ninguna línea de código: *Inventario → Trazabilidad → Lotes y números de
serie*, y en el producto *Trazabilidad → Por número de serie único*.

Tipos de punto de calidad disponibles: `passfail`, `measure`, `instructions`, `picture`,
`print_label`, `register_byproducts`, `register_consumed_materials`, `register_production`,
`spreadsheet`. **`measure` es el que sostiene toda la recomendación** — trae norma, mínimo,
máximo y unidad.

### La corrección grande: `quality.alert` **es** la lección aprendida

Estaba anotado que había que construir un modelo de lecciones sobre `product.template`. **No
hay que construirlo.** `quality.alert` ya trae, verificado en `ir_model_fields`:

| Lo que pedía el diseño | Campo |
|---|---|
| Lección **del modelo**, no de la unidad | `product_tmpl_id` → `product.template` |
| Qué unidades quedaron afectadas | `lot_ids` (m2m a `stock.lot`) |
| Por qué pasó | `reason_id` → `quality.reason` (catálogo) |
| Qué se corrigió | `action_corrective` (html) |
| **Qué hacemos para que no se repita** | `action_preventive` (html) |
| De dónde salió | `check_id`, `production_id` |
| Flujo e historial | `stage_id`, `team_id`, chatter |

Trae **más** de lo que se iba a escribir, incluido el alcance del daño, que el diseño del
2026-08-17 no contemplaba.

### Los huecos reales, y son chicos

1. **No hay puente alerta ↔ ECO.** Verificado: `mrp.eco` no tiene ningún campo hacia
   `quality.alert` ni al revés. Así que «cambiamos el BoM por esto» no queda registrado. Se
   arregla con **un campo**.
2. **`product.template` no tiene relación con `quality.alert`.** Tampoco `stock.lot`. O sea que
   **el que arme el próximo ROV no va a ver las lecciones** salvo que se acuerde de ir a la app
   de Calidad. Es el riesgo del «cementerio» localizado en un campo que falta: **dos
   `One2many`, y es el trabajo más valioso de todo el bloque.**
3. **De la línea de trabajo a la alerta** falta un botón que la pre-llene desde `origen`.

### Lo inesperado: `repair.order` ya está integrado con Calidad

Tiene `quality_alert_ids` y `quality_check_ids` nativos. Dos consecuencias:

- **El puente reparación → fabricación está a medio construir de fábrica.** No hay que
  inventarlo, hay que usarlo.
- Odoo ya traía un mecanismo de chequeos sobre reparaciones cuando se construyó
  `mc.rov.revision`. **No se toca la revisión**: hace cosas que un `quality.check` no hace
  —inspección de sellos, catálogo de hallazgos por familia, «No aplica» como respuesta válida—
  y sobre todo **es un entregable al cliente**, que un chequeo de calidad no es. Pero
  `quality_check_ids` conviene **esconderlo de la vista**: dos mecanismos de chequeo en la
  misma pantalla es una invitación a llenar el equivocado.

**La regla que sale de esto y que conviene no olvidar:** *los chequeos pertenecen al proceso que
los define; las alertas son el idioma común.* En fabricación **no se construye una segunda
batería** — se configuran puntos de calidad.

### Alcance real en `mc_rov`

De «un sistema de fabricación» a esto:

| Qué | Dónde | Tamaño |
|---|---|---|
| Ver las lecciones del modelo al fabricar | `product.template` ← alertas | Chico, **y es el que importa** |
| Ver qué alertas afectan a una unidad | `stock.lot` ← inverso de `alert.lot_ids` | Chico |
| «Cambiamos el BoM por esto» | `quality.alert` → `mrp.eco` | Chico |
| De la línea de trabajo a la alerta | Botón que pre-llena desde `origen` | Chico |
| Ficha del cliente con resultados | Reporte QWeb sobre `quality.check` | Mediano — **es el PDF, va al final** |
| Batería de fabricación | Puntos de calidad | **Configuración, no código** |

### La batería de fabricación, propuesta

Dos cosas la hacen genuinamente distinta de la de reparación, y no es «la misma con menos
ítems»:

1. **En fabricación los umbrales existen.** Se construye contra una especificación, así que la
   especificación *es* el umbral — y por eso `measure` sirve acá y no en reparación, donde se
   decidió no derivar el ancho de banda porque nadie los había definido.
2. **El software se mide al revés.** En reparación se compara contra la ficha; en fabricación
   **se instala**, así que la fabricación es la *fuente* de la ficha. Registrar las versiones al
   armar es lo que haría que la ficha dejara de nacer vacía.

Y el orden importa porque el proceso es físico: **hay cosas que solo se pueden verificar antes
de cerrar el casco.** Si el punto de control no está amarrado a la operación, se responde
después, de memoria, mirando un equipo cerrado.

| Momento | Qué | Tipo |
|---|---|---|
| Antes de cerrar | Sellos y o-rings instalados y lubricados | Pass-Fail |
| | Penetradores y conectores apretados | Pass-Fail |
| | Cableado interno ordenado y asegurado | Pass-Fail |
| | Foto del interior armado | Picture |
| Cerrado | Estanqueidad bajo presión · Prueba de leak | Pass-Fail |
| Banco eléctrico | Tensión de salida (V) · Consumo en reposo (A) · Consumo bajo carga (A) | Measure |
| Comunicación | Ancho de banda subida / bajada (Mbps) | Measure |
| Propulsión | Thrusters responden y giran en el sentido correcto | Pass-Fail |
| | Movimiento vertical / horizontal / lateral | Pass-Fail |
| | *stabilize* · *depth hold* | Pass-Fail |
| Video y luces | Imagen y tilt | Pass-Fail |
| | Cantidad de luces encendidas · Ganancia de luz (%) | Measure |
| Esfuerzo | Duración (h) · Temperatura interior y exterior (°C) | Measure |
| Cierre | Registrar número de serie | Register Production |
| | Versiones de software, controlador y ArduSub — **alimentan la ficha** | Instructions |

**Casi la mitad ya se mide hoy**, guardada como columnas del número de serie. No es una batería
nueva: son esas columnas convertidas en un evento con umbrales.

**Arreglo gratis que viene con esto:** `mc_ancho_banda` y `mc_consumo_corriente` hoy son `Char`,
así que no se pueden promediar, comparar ni graficar. Como puntos `measure` pasan a ser números
con unidad, y recién ahí sirven para el pipeline.

### Lo que sigue sin decidir

1. **Los mínimos y máximos.** Qué tensión, qué consumo en reposo, qué ancho de banda es
   aceptable para cada modelo. **Si esos números no existen escritos hoy, eso mismo es el
   hallazgo**: un `measure` sin tolerancia guarda el número pero no dice si está bien.

2. **Cuántas veces se le hace prueba en terreno a un mismo equipo.** Es lo único que decide
   dónde vive, y hoy vive en dos lugares — los campos del lote, que se usan, y `tipo = terreno`
   en la revisión, que está muerto. **No es «agregar terreno a la revisión», es cuál de los dos
   sobrevive**, porque dejar los dos es duplicar.

   - *Una sola vez* (aceptación antes de entregar) → el lote está bien: una foto basta, y
     `terreno` sale de la revisión por muerto.
   - *Cada cierto tiempo o por trabajo* → tiene que ser un evento, porque hoy correrla de nuevo
     **pisa la anterior en silencio**. Gana la revisión y los campos del lote se migran.

   Es la misma pregunta que resolvió la corrida en `19.0.15.0.0`, y ahí cambió el modelo entero.

   Nota contra un argumento propio: *«dejarlo donde ya se hace»* no aplica limpio acá. Nadie
   llena el formulario del lote parado en un bote — los dos lugares son transcripción posterior.

3. **`tipo = fabricacion` se retira** de la revisión: la prueba de fabricación pasa a ser puntos
   de calidad sobre la MO. Sale con la migración de este bloque.

4. **El re-test tras rediseño no se diseña todavía.** Ocurre pocas veces al año, con enfoque de
   troubleshooting, y nadie sabe describir su forma. Modelarlo ahora es inventar la forma del
   dato antes de tener el dato — el mismo error que se evitó con el software en `19.0.15.2.0`.
   Mientras tanto cae en su lugar natural: el prototipo se arma con una MO, la MO trae sus
   chequeos, y si falla, la alerta se lleva el troubleshooting.

5. **Empezar con un solo modelo de ROV**, el que más se arme, y una MO completa de punta a
   punta antes de escribir una línea. Se está digitalizando un proceso hoy físico: no hay
   costumbre que aprovechar, hay costumbre que cambiar, y eso se descubre haciendo una.

6. **No rastrear todo por lote.** La trazabilidad es configuración *por producto*: se puede
   tener un BoM de 40 líneas con 4 rastreadas —o-rings, thrusters, tarjetas, controlador— y el
   resto consumido automáticamente. Eso convierte «registrar 40 piezas» en «elegir el lote de
   4», y deja intacto lo único que hoy no se puede responder de ninguna forma: **qué otras
   unidades llevan la pieza que salió mala.** Hoy `origen = pieza_proveedor` se registra en la
   reparación y muere ahí, sin poder mirar hacia los lados.

## Estado al 2026-08-17

`19.0.15.2.0` metió **software a la batería de reparación**: dos chequeos en `comunicacion` y
los cinco `related` de la ficha al lado, para poder contestarlos sin salir de la pantalla. Sin
modelo nuevo y sin comparación automática, deliberadamente — razones y la regla para revisitarlo
en [`designs/revision-tecnica.md`](designs/revision-tecnica.md) § 8.8.


`19.0.14.0.0` ordenó el flujo en pantalla: **las pestañas pasaron a ser los momentos del
proceso**, leídos de izquierda a derecha. En la orden, *Recepción · Diagnóstico · Reparación ·
Repuestos · Cierre · Notas*; en la revisión, de cinco pestañas a tres — *Sellos · Pruebas ·
Hallazgos*—. Además la temperatura bajó a la corrida (se mide una por corrida y sí depende del
cable), el cierre exige el repuesto cuando la acción lo consume, y la revisión sin confirmar se
muestra con un filtro en vez de bloquear. Razones en
[`designs/revision-tecnica.md`](designs/revision-tecnica.md) §§ 8.1–8.4.

## Estado al 2026-08-14

El **diagnóstico de fallas** está implementado (`19.0.13.0.0`): el catálogo de síntomas, los
dos campos de recepción, `causa_raiz` partido en `origen` con su análisis escrito, y la vista
de búsqueda que faltaba. Diseño en
[`designs/diagnostico-de-fallas.md`](designs/diagnostico-de-fallas.md), con las correcciones
que salieron de contrastarlo contra el código en su § 15.2. Lleva migración.

La **revisión técnica** está implementada (`19.0.12.0.0`): seis modelos, los catálogos de
chequeos y hallazgos, la inspección de sellos, y **una** revisión por visita que se abre sola
al confirmar la orden. Diseño en
[`designs/revision-tecnica.md`](designs/revision-tecnica.md).

`19.0.12.0.0` salió de probar el módulo en pantalla, que es de donde salió todo lo que
importaba: el par recepción/entrega se retiró, la pestaña de pruebas se rehízo por secciones
como la hoja de papel, y el catálogo salió del alcance de quien llena la ficha. Las
correcciones de alcance quedan registradas en § 1.3 y § 1.4 del diseño.

`19.0.12.1.0` corrigió el ancho de la pestaña de pruebas —cada sección es un `<group>`, que
sin `colspan="2"` deja la lista en media página con el nombre del chequeo cortado— y agregó
el botón **Actualizar checklist**.

`19.0.12.1.1` sacó las filas de relleno de esas listas con una regla en
[`static/src/css/mc_rov.css`](../static/src/css/mc_rov.css).

**Validado en producción, ya sin pendientes de este bloque:** `open_form_view` rinde en el
one2many embebido de Odoo 19 —la revisión se abre desde la orden en su propio formulario y se
edita— y esconder `tag_ids` con `position="attributes"` dejó «Etiquetas» efectivamente fuera
de la vista. Los dos se habían deducido de una captura, sin poder leer el arch base de
`repair`.

## Salido de probar `19.0.12.1.0` en pantalla

- [ ] **La batería es uniforme y los equipos no.** Las luces varían entre modelos, y los
  pedidos custom agregan cámaras laterales o traseras y luces extra —para las cámaras o
  simplemente para alumbrar más.

  Hoy eso no se puede registrar. Las luces son dos enteros (`luces_internas`,
  `luces_externas`) y la cámara es **un solo chequeo** para todo el equipo. Dos consecuencias:

  1. **El conteo dice cuántas encienden, nunca cuál está apagada.** Cuando el mismo equipo
     vuelva en seis meses no hay forma de saber si falla siempre la misma.
  2. **El `0` de un entero es ambiguo:** no distingue *no encendió ninguna* de *este modelo
     no lleva luces internas*. Es exactamente la ambigüedad que se sacó de los chequeos con
     «No aplica», y sobrevivió en las luces porque son enteros y un entero no tiene vacío.

  **No se arregla agregando campos.** Cuatro enteros en vez de dos aguantan hasta el próximo
  custom, y entonces son un `X` bump con migración. Es el mismo argumento por el que los
  pasos de testeo son catálogo y no columnas.

  **Forma propuesta, a diseñar:** que la ficha del equipo declare qué trae —N luces internas,
  N externas, cámara frontal, cámara lateral izquierda…— y que la revisión genere una línea
  por elemento. El mecanismo hermano ya existe y está probado: `por_componente` genera una
  línea por componente inspeccionable.

  **El riesgo que el diseño tiene que resolver antes de escribir código:** si la ficha del
  equipo está vacía —y hoy lo está en todos los equipos anteriores a Odoo— la revisión
  generaría cero líneas y el checklist desaparecería en silencio. Es un modo de falla peor
  que el que viene a arreglar. Necesita un respaldo: los chequeos genéricos de hoy cuando el
  equipo no declara nada.

  Es la misma familia de problema que el refinamiento anotado en
  [`designs/revision-tecnica.md`](designs/revision-tecnica.md) § 5.4 sobre el joystick y el
  cilindro fuente: *si el equipo declarara lo que tiene, la revisión no preguntaría de más*.
  Conviene diseñarlos juntos.

## Salido de implementar `19.0.13.0.0`

- [x] ~~Revisión a mano de las filas `falla_fabricacion`~~ — **no aplica.** La auditoría
  previa al desplegar `19.0.13.0.0` mostró que `odoo_prod` tenía **2 líneas de trabajo, ambas
  sin causa**: cero `corrosion`, cero `accidente`, cero `falla_fabricacion`. Las dos quedaron
  en `desconocida`.

  **Lo que sí queda vivo:** no confundir el `desconocida` de antes con el de ahora. Las líneas
  que nunca tuvieron causa quedaron ahí, así que un `desconocida` anterior a `19.0.13.0.0`
  puede significar «no se pudo determinar» o «nadie lo llenó», y eso ya no se distingue.

- [ ] **`comp_electronica` se llama «Electrónica / Software» y mezcla dos cosas en una
  etiqueta.** Apareció al agregar los componentes que faltaban: fue la razón por la que
  «Software de superficie» no entró como componente propio. Separarlas obliga a decidir qué
  pasa con las filas que ya la usan, así que queda anotado.

- [ ] **Medir la tasa de llenado de `hallazgo_origen_id`** antes de confiar en cualquier
  análisis que cruce hallazgos con orígenes. Es opcional, y sin él la línea de trabajo tiene
  «por qué pasó» sin «qué se encontró». Un cruce sobre el 20% de las líneas se ve idéntico a
  un resultado (§ 9.1 del diseño).

- [ ] **Revisar en seis meses si `analisis_causa` se llena.** Entró en parte para cumplir un
  requerimiento y su aporte real no está probado: es plausible que sirva solo en los casos
  complejos. Si queda vacío en la gran mayoría de las líneas, sacarlo cuesta un campo — se
  eligió texto y no un modelo de porqués justamente para que retirarlo fuera barato.

Lo que sigue del plan original, en orden:

- [ ] **Reporte PDF de las dos fichas** (`19.0.9.0.0` del plan, ahora la siguiente versión
  grande). Ni la ficha de fabricación ni la revisión técnica se pueden imprimir hoy; el
  único documento imprimible de una orden es el presupuesto por defecto de Odoo.

  **La revisión existe, entre otras cosas, para entregársela al cliente**, así que esto no
  es un extra. Obliga a decidir campo por campo qué es interno y qué va impreso — ver
  [`designs/revision-tecnica.md`](designs/revision-tecnica.md) § 12.1.

  **Ya hay un caso concreto que decide, y no es hipotético:** la **temperatura** de cada
  corrida vuelve a medirse como dato **interno** y **no debe salir impresa**. Antes se le
  entregaba al cliente y el cliente la usó en contra. Es el primer campo con una razón
  comercial —no estética— para quedarse adentro, y conviene arrancar el diseño del reporte
  por ahí: si un campo puede volverse en contra, la pregunta no es «¿se ve bien?» sino «¿qué
  hace el cliente con esto?».

- [ ] **Fotos de los hallazgos**, con `fields.Image(max_width=1920, max_height=1920)` y no
  `fields.Binary`. Decidido dejarlo para el final. El disco no es problema: 50 GB libres y
  los adjuntos van a disco, no a la base.

- [x] **Vista de búsqueda de `repair.order`** — hecha en `19.0.13.0.0`: filtro «Sin síntoma
  registrado», búsqueda y agrupación por tipo de intervención, y `sum` al pie de
  `mc_total_horas`.

  **«Agrupar por causa raíz» se retiró del pendiente y no se va a hacer.** Estaba anotado de
  cuando el campo vivía en la orden; desde `19.0.8.0.0` vive en la línea de trabajo. Una orden
  con tres trabajos tiene tres orígenes, y agruparla por uno exigiría el campo derivado que el
  diseño prohíbe explícitamente, porque elegiría uno y botaría los otros dos en silencio.

  Notas que siguen valiendo para cualquier herencia futura de esa vista: la base se llama
  **`repair.view_repair_order_form_filter`**, su grupo de "agrupar por" no tiene nombre pero
  el último filtro adentro sí (`group_by_repair_properties`), y **el schema de Odoo 19
  rechaza `expand` y `string` en el elemento `group`** — eso rompió el módulo una vez. La
  herencia que se escribió ancla en la raíz `<search>` justamente para no depender de nombres
  del arch base que no se pueden leer desde el entorno de desarrollo.

- [ ] **Phase -1 del pipeline roadmap — Foundation handoff** — prerequisito bloqueante para iniciar el pipeline. Checklist completo en `rov-pipeline-roadmap.md` Phase -1. Duración estimada: 1 semana.

- [ ] **Montar staging** siguiendo [`runbooks/staging.md`](runbooks/staging.md). Escrito el 2026-08-18; falta correr los comandos en el servidor.

  **La ventana es ahora.** Hoy staging vale poco —4 números de serie, 2 líneas de trabajo— pero está a punto de valer mucho, y por tres cosas que llegan juntas: la carga de productos ROV reales, el bump `X` de fabricación que borra columnas, y MRP + Calidad tocando inventario de verdad. Ensayar una migración por primera vez *después* de cargar los datos reales es ensayarla cuando ya no puede salir mal barato.

  Las tres migraciones de esta sesión se probaron en producción. Salieron bien porque no había qué romper: la de `19.0.15.0.0` habría descartado corridas si hubieran existido, y el log lo habría dicho **después**.

- [ ] **Separar el workspace del runner de CI del addons de producción.** Hoy son el mismo directorio: `/opt/odoo/custom-addons/mc_rov`. Descubierto el 2026-08-07 al desplegar `19.0.5.0.0`.

  **Se resuelve con la misma reorganización que staging:** tres checkouts separados —producción en `/opt/odoo/custom-addons`, staging en `/opt/odoo/staging-addons`, y CI fuera de los dos— en vez de dos procesos compartiendo un directorio.

  **El deploy en sí ya no es el problema**: el usuario `odoo` tiene deploy key y hace `fetch` por su cuenta. Lo único que fallaba era que el runbook decía `git pull` a secas, que corre como root — corregido en [`runbooks/deploy.md`](runbooks/deploy.md).

  Lo que queda es el directorio compartido: **un job de CI puede cambiar lo que Odoo está sirviendo**, porque el checkout aterriza en el addons path de producción. Desplegar no es lo único que mueve ese código.

  Arreglo: mover el workspace del runner fuera de `/opt/odoo/custom-addons/mc_rov`. No urge —el deploy funciona y es deliberado— pero es una fuente de sorpresas que nadie va a relacionar con CI cuando ocurra.

- [ ] **Carga de productos ROV** — el árbol de categorías ya está en producción (164 categorías), pero todavía no hay productos ROV cargados. Al cargarlos:

  1. **La categoría dejó de ser un dato descriptivo y pasó a ser funcional.** Desde `19.0.2.0.0` el campo `es_un_rov` se deriva de ella: un vehículo cargado fuera de la rama `ROV - Vehiculos` (id `968` en `odoo_prod`) no tendrá ficha técnica ni pestañas de mantención, y nadie podrá encenderlas a mano.
  2. `ROV-MC` para vehículos de marca propia, `ROV-XX` para los de otras marcas. Ambas ramas encienden la marca.
  3. **El síntoma de equivocarse no apunta a la causa.** El técnico va a reportar "no me aparecen las pestañas", no "la categoría está mal". Revisar la categoría del producto antes que el módulo.
  4. Los equipos de clientes entran en consignación: la categoría dice **qué es** el equipo, la propiedad se maneja aparte. Ver [`INVENTARIO.md`](../INVENTARIO.md) § Equipos de clientes.
  5. **Llenar `mc_propietario_id` al cargar cada número de serie.** Desde `19.0.5.0.0` de ahí sale el estado comercial: un equipo vendido que quede a nombre de la empresa va a aparecer como "Disponible" y va a ensuciar la lista de flota. Los que son de clientes se cargan a nombre del cliente; los de flota se dejan como vienen, ya que el valor por defecto es la propia empresa.
  6. **Llenar también `mc_fecha_puesta_servicio`** en los equipos que ya están en terreno, o el reloj de mantención no arranca y no aparecerán nunca en la lista de vencidos.
  7. **Desde `19.0.6.0.0` hay catorce campos más que llenar por equipo**, no dos. Toda la pestaña *Especificaciones* pasó a ser obligatoria para los ROV: chasis, modelo / N° / posición de motores, ambos pesos, sensor de presión, ambas tarjetas de comunicación, controlador de vuelo y su versión, ArduSub, software de superficie y su versión, y cantidad de luces.

     **Desde `19.0.15.2.1` ya no hay obligatoriedad en ninguna parte** — ni en el modelo ni en la vista. El `required` de la vista salió porque decía lo mismo que el aviso amarillo y además era todo o nada: quien conocía 12 de las 14 especificaciones no podía guardar las 12, y la salida era inventar las otras 2.

     **Esto cambia el procedimiento de carga, y es lo más importante de este punto.** Antes el formulario frenaba una ficha a medias; ahora **nada la frena**, así que se puede guardar cualquier cosa incompleta a mano, no solo por importación. Lo que encuentra a las series incompletas es `mc_ficha_completa` y el filtro **«Ficha incompleta»** en la lista de números de serie, y desde `19.0.15.2.2` el aviso dice cuántos datos faltan de cuántos. **Después de cada tanda hay que revisar ese filtro** — antes era recomendable, ahora es el único control que queda.

     Cuidado con los numéricos: en Odoo un `Integer` o un `Float` nunca queda vacío, se lee como 0, así que N° de motores, ambos pesos y cantidad de luces pueden entrar en cero sin que nada chiste. `mc_ficha_completa` los exige `> 0` justamente por eso.

     Y **ya no hay opción «Desconocido»**: se probó en `19.0.6.0.0` y se retiró en `19.0.7.0.0`, porque la decisión es obligar a averiguar las especificaciones reales del equipo. Para los equipos anteriores a Odoo eso significa que hay que ir a levantar el dato o poner un valor supuesto — y un valor supuesto es indistinguible de uno verificado, que es el precio conocido de esa decisión. **Sacar el `required` no ablanda esa decisión, la separa**: guardar 12 de 14 deja constancia honesta de que faltan 2; inventarlas no deja ninguna.

  **Residuo a limpiar antes de cargar datos reales:** quedan 2 números de serie de prueba con `es_un_rov = TRUE` cuya cadena producto → categoría está rota; por eso la migración `19.0.2.0.0` reportó 0 filas recalculadas y no los tocó. Se apagarán solos la primera vez que algo los escriba. Conviene borrarlos para no confundirlos con equipos reales.

- [ ] **Grupos de seguridad**: los accesos actuales son sin grupo. Implementar cuando haya múltiples usuarios. Diseño acordado:

  **Dos grupos jerárquicos** (`Coordinador ROV` hereda `Técnico ROV` vía `implied_ids`):

  | Grupo | `implied_ids` (grupos Odoo arrastrados) | Acceso mc_rov |
  |-------|----------------------------------------|---------------|
  | `Técnico ROV` | `repair.group_repair_user`, `stock.group_stock_user` | CRUD en `linea.falla`; lectura en `componente`/`subtipo`/`accion`; edición de ficha técnica y campos mc_rov en `repair.order` y `stock.lot` |
  | `Coordinador ROV` | `repair.group_repair_manager`, `stock.group_stock_manager`, `purchase.group_purchase_user`, `sale.group_sale_user`, `account.group_account_invoice` | Todo lo anterior + CRUD en `componente`/`subtipo`/`accion` |

  **Implementación involucra:**
  1. `security/mc_rov_groups.xml` — definir los dos grupos con `implied_ids`
  2. `ir.model.access.csv` — reemplazar líneas sin grupo por reglas por grupo
  3. `views/` — agregar `groups=` en campos que solo el Coordinador debe editar (ej. `mc_estado_comercial`)
  4. Registrar `mc_rov_groups.xml` en `__manifest__.py` bajo `data`

  **Para asignar grupos a usuarios:** `Ajustes → Usuarios → [usuario]` (sin tocar código). Cambiar qué puede hacer un grupo requiere modificar el módulo.

- [x] ~~Validación de línea de producto en cierre de orden~~ — **hecha en `19.0.14.0.0`.**
  `mc.rov.accion.consume_repuesto`, marcado en las dos acciones de cambio, y
  `_validar_repuestos` en la transición a `done`.

  **Su alcance está declarado y conviene recordarlo:** exige *al menos una* línea de producto,
  no una por cada cambio. Una orden con tres cambios y un repuesto registrado pasa. Subir a la
  correspondencia uno a uno obliga a decir qué repuesto va con qué trabajo, que es un campo
  nuevo en la línea y otra decisión.

- [ ] **Pipeline integration touchpoints** (Phase 1 del pipeline — requiere Phase -1 completada primero): agregar `controllers/api.py`, usuario `pipeline@marine-connection` con API key, y grupo `Pipeline API (Read-Only)`. Checklist en `rov-pipeline-roadmap.md` Phase 1 "Odoo access layer". Contrato en [`integrations/pipeline.md`](integrations/pipeline.md).
