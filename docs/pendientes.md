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

## Guiar al usuario dentro de Odoo *(diseño abierto, 2026-08-19)*

El problema: son varios módulos y **el usuario no lee documentación — abre Odoo y no sabe qué
botón tocar**. [`flujo-de-trabajo.md`](flujo-de-trabajo.md) sirve para nosotros, no para ellos.
La ayuda tiene que estar dentro del programa.

Dos principios que ordenan todo lo demás:

> **1. El siguiente paso tiene que ser un botón en el registro que ya estás mirando.** La guía
> por cercanía le gana siempre a la guía por documentación.
>
> **2. La pantalla vacía es el mejor momento para enseñar.** Quien llega a una lista sin nada
> está detenido y mirando, y Odoo ya reserva ese espacio.

Las ideas, por lo que rinden frente a lo que cuestan:

| | Idea | Comentario |
|---|---|---|
| **a** | **Botones de siguiente paso** | La más valiosa. *«Ir a la ficha del equipo»* al terminar la MO; *«Nueva prueba de rendimiento»* en el N° de serie; *«Levantar alerta»* en la línea de trabajo — ese último ya resuelve la fricción de que reparación termine en Calidad, porque el usuario nunca tiene que saber que Calidad existe |
| **b** | **Textos de lista vacía** | Gratis: es un atributo de la acción y Odoo lo muestra solo. Va de paso con lo demás, no compite con (a) |
| **c** | **Tablero de «qué me falta»** | Fichas incompletas, equipos sin pruebas, revisiones sin confirmar, alertas sin acción preventiva |
| **d** | **Menú propio ordenado por proceso** | *«ROV → 2. Aceptar»* en vez de *«Inventario → Números de serie»*. Resuelve la fricción del nombre de puerta |
| **e** | **Semáforo en la ficha del equipo** | Ya existe y funciona: el aviso de «faltan 3 de 16» es exactamente este patrón |

**Descartado: artículos de Knowledge o manuales embebidos.** Es otro lugar más al que nadie va a
entrar, y compite con el trabajo en vez de acompañarlo.

**(c) y (d) van juntas y aparte, como un «centro de mando», y después de (a).** Responden una
pregunta distinta —*«¿qué hago hoy?»* en vez de *«¿cómo sigo?»*— y mezclarlas empeora las dos.
Además: **un tablero construido antes de que el proceso esté en uso muestra lo que es fácil de
contar, no lo que importa.** Con tres meses de datos reales se sabrá qué miran de verdad.

### El presupuesto de indicadores

El patrón de (e) —un derivado que dice «a este registro le falta algo»— se gana su lugar **donde
la ausencia es silenciosa y la consecuencia es tardía**. Si el sistema ya reclama, un indicador
es ruido.

Candidatos, por cuán callada y cara es la falla:

1. **Fecha de puesta en servicio vacía** — sin ella el reloj de mantención no arranca y el equipo
   no aparece nunca en «mantención vencida». Nada reclama; te enteras cuando reclama el cliente.
2. **Producto ROV fuera de la rama de categorías** — se apagan las cuatro pestañas de ficha y
   **el síntoma no apunta a la causa**: se reporta «no me aparecen las pestañas».
3. **Alerta de calidad cerrada sin acción preventiva** — es una lección que nunca se escribió.
4. **Propietario mal puesto en un equipo vendido** — aparece como «Disponible» y ensucia la flota.
5. **Pruebas de aceptación** — ya diseñado en `designs/fabricacion.md` § 4.4.

Y uno que **ya existe y es de la misma familia**: `mc_revision_pendiente`, que en `19.0.14.0.0` se
decidió mostrar con un filtro en vez de bloquear.

> **La regla, para no repetir lo del `required` rojo: un indicador por registro, que agregue todo
> lo que le falta. No uno por campo.**

El aviso de la ficha ya lo hace bien —dice «faltan 3 de 16» y los nombra— en vez de cuatro avisos
compitiendo por la misma franja. **Conviene diseñarlos juntos y no de a uno**, porque el que
llegue segundo va a querer su propia franja.

### La cotización declara lo que la ficha después registra

Una cotización de ROV custom **declara lo que el equipo va a llevar** —cuántas luces, cámara
lateral, brazo— y la ficha registra lo que llevó. **Son la misma lista en dos momentos: promesa y
hecho.**

Eso importa porque resuelve por el lado correcto el pendiente de más abajo sobre las luces y
cámaras custom: ahí quedó anotado que la ficha debería declarar qué trae el equipo para que la
revisión no pregunte de más. **Si la cotización alimenta la ficha, el dato entra donde se decide
y no donde se transcribe.**

Sin decidir: si eso se modela o queda como convención.

## Fabricación — listo para implementar

**El diseño está cerrado y aprobado.** Ver [`designs/fabricacion.md`](designs/fabricacion.md),
790 líneas, y la guía para usuarios en [`flujo-de-trabajo.md`](flujo-de-trabajo.md).

### Cómo partirlo

| | Qué | Tamaño | Depende de |
|---|---|---|---|
| **A** | Las pruebas de aceptación. **No es un bloque: son cuatro con dependencias distintas**, ver abajo | Grande | — |
| ~~**B**~~ | ~~Los puentes a `quality.alert`~~ — **hecho en `19.0.15.3.0`** | Chico | — |
| **C** | Los indicadores agregados en el número de serie (§ 4.4), con el presupuesto de **uno por registro** | Chico | A |
| **D** | Configurar los puntos de calidad del armado y alinear `quality.reason` con `ORIGENES` | Datos, cero código | B |

**A y B son independientes.** B se nota antes —son los cuatro campos que cierran el círculo con
reparación— y no lleva migración, así que sirve de rodaje para el flujo nuevo con staging antes
de la migración grande.

### A2 también va antes de la carga, y esto salió de mirar la pantalla *(2026-08-20)*

Estaba dicho que A2 podía esperar. **No puede.** La pestaña «Umbilical» del número de serie
contiene, además de las especificaciones del cable, **una sección entera de prueba de rendimiento** —
modelo de fuente, alimentación, tensión, consumos, pilot gain, ancho de banda, temperaturas— que
son **las mismas mediciones que la revisión ya recoge**. El módulo está a medio mudar y esos
datos tienen dos casas.

Si se cargan equipos reales con esas secciones todavía en pantalla, **alguien las va a llenar, y
A2 las borra**. Y peor: entre las dos pruebas y la ficha, un técnico teclearía lo mismo dos o
tres veces sin ninguna señal de que sobra.

Dos cosas concretas que A2 tiene que resolver, además del retiro:

- **El largo del umbilical se pide siempre y se exige para confirmar.** Si el cable es *del
  equipo*, ese largo ya está en la ficha. El § 5.4 lo dice —*«umbilical usado y largo solo si es
  del taller»*— y no está implementado.
- **La pestaña «Umbilical» se queda solo con el umbilical.** Hoy su título nombra la primera de
  sus tres secciones, y las otras dos son la prueba de rendimiento. Viene de la época de Studio.

### Catálogos editables en Especificaciones y Periféricos *(pedido 2026-08-20)*

Las listas seleccionables de esas dos pestañas deberían **poder mantenerse sin tocar código**, y
mejor todavía si se actualizan solas. El patrón ya existe y está probado en el módulo:
`mc_software_superficie` y `mc_controlador_vuelo` dejaron de ser valores fijos y pasaron a ser
catálogos con su menú en Configuración.

Aplica al menos a **modelos de motores, periféricos y dispositivos extras**. La razón es la
misma que en aquellos dos: el día que llegue un modelo nuevo, agregarlo tiene que ser escribir
una fila, no abrir un PR.

### A se parte en cuatro, y solo una corre contra el reloj

Al leer el § 4 y el § 5 completos quedó claro que A no es una cosa. **Solo A1 tiene que estar
antes de que el sistema entre en uso real**, porque es la única con migración — y el § 8 lo dice:
*«la ventana para hacerlo es ahora; con equipos reales cargados, cada una de esas tres preguntas
vuelve»*.

| | Qué | Bump | Cuándo |
|---|---|---|---|
| **A1** | `fabricacion` → `rendimiento`, `observacion` → `detalle`, se retiran las columnas de terreno del lote, y el arreglo de `_compute_resultado` | `X`, con migración | **Antes de cargar datos reales** |
| **A2** | Las mediciones nuevas del § 5.4, y con ellas el retiro de las columnas de laboratorio | `Y` | Después |
| **A3** | Las secuencias `REN/` y `TER/`, y congelar `tipo` una vez emitido | `X`, con migración | **Hecho en `19.0.19.0.0`** |
| **A4** | Las cuatro baterías del § 5.2 y § 5.3 | Datos | Después, y **quiere** equipos reales: los cinco chequeos de armado los escribió el diseño y no el taller |

**A3 está hecho en `19.0.19.0.0`, y resultó ser `X` y no `Y`.** Lo que el diseño no había
previsto: **congelar el tipo al confirmar no alcanza.** El tipo se cambia *entre* crear y
confirmar —es el caso corriente, porque el botón del número de serie crea la prueba y recién
ahí el técnico ve cuál era—, así que un prefijo puesto al crear queda mintiendo igual. La
salida fue renumerar el borrador cuando cambia de tipo, con nota en el chatter. Y el candado
no podía colgar de `estado`: devolver a borrador una prueba ya entregada habría reabierto el
tipo y renumerado un documento que el cliente tiene en la mano — de ahí el campo
`documento_emitido`, que es lo que obliga a la migración.

**A1 está hecho en `19.0.16.0.0`.** Dos cosas que salieron de implementarlo y que el diseño no
había previsto:

- **El renombre de etiquetas «En reposo» / «Esfuerzo» del lote salió de A1.** Son columnas de
  laboratorio, o sea que A2 las borra: renombrarlas antes es trabajo que se elimina un PR
  después. La decisión de vocabulario sigue en pie para los campos nuevos de A2.
- **Se retiró la acción «Revisiones de fabricación»**, que no referenciaba ningún menú y cuyo
  dominio, tras el renombre, no habría encontrado nada.

### Antes de empezar B: una verificación *(hecha el 2026-08-20, pasa)*

B agrega **`mrp`, `quality_control` y `mrp_plm` a las dependencias del módulo**. Eso hace que
`mc_rov` ya no se pueda instalar sin ellos — en producción están, pero **hay que confirmar que el
runner de CI puede instalar el módulo con esas dependencias**, o sea que su addons path incluye
Enterprise. Si no, el primer PR de B rompe CI y no por el código.

La alternativa sería un módulo puente aparte (`mc_rov_quality`), pero es mucha infraestructura
para cuatro campos en un módulo de una sola empresa. **Se elige agregar las dependencias**, y
queda anotado que ése es el costo.

**Resultado, verificado contra el VPS:**

- El `addons_path` de `/etc/odoo/odoo.conf` —el mismo archivo que usa el runner— incluye
  `/usr/lib/python3/dist-packages/odoo/addons`, y ahí viven `quality`, `quality_control`,
  `mrp_plm`, `quality_mrp` y `quality_repair`. Enterprise está en el path.
- En `odoo_test` los cinco salen `installed`. **Eso mata el riesgo mayor**, que no era el addons
  path sino la instalación primeriza: no hay módulos nuevos que instalar en la primera corrida,
  así que ni el `timeout-minutes: 30` ni los 189 tests actuales se mueven — ya venían corriendo
  en una base con `mrp` puesto.
- **Son cinco dependencias y no tres.** `quality_mrp` y `quality_repair` no estaban en el diseño
  y hacen falta: son ellos los que definen `quality.alert.production_id` y
  `quality.alert.repair_id`, que es por donde entran los puentes. Los dos son `auto_install`, así
  que ya estaban instalados; declararlos fija el orden de carga.

### Lo que queda de B después de `19.0.15.3.0`

- [x] ~~**Confirmar en pantalla el botón inteligente del número de serie.**~~ — **hecho el
  2026-08-20: no existe.** El lote trae los conteos de `quality_control` y ninguna vista los usa.
  Se escribió como pestaña en `19.0.15.4.0`.
- [x] ~~**Decidir quién ve el botón de la línea de trabajo.**~~ — **la pregunta no existe:** hay
  **un solo usuario activo** en `odoo_prod` y ya tiene `quality.group_quality_user`. Concuerda
  con el `CLAUDE.md`: los técnicos no tienen login propio porque las licencias se pagan por
  usuario, y por eso los responsables son `hr.employee`. Vuelve el día que alguien más tenga
  login.
- ~~**El ruido posible de la alerta automática.**~~ — **resuelto el 2026-08-20:** se acotó a la
  rama de categorías ROV. El § 6.1.4 no lo calificaba y se implementó sin restringir; Paulo lo
  corrigió al revisarlo. El § 6.1.4 quedó actualizado con la razón.

### Lo que no se va a pedir

- **La presión de prueba por modelo.** Se evaluó pedirla en la ficha para derivar el chequeo de
  estanqueidad y se descartó: los técnicos saben a cuánto va cada equipo. Se registran bar y
  tiempo, y la persona juzga. Ver § 5.6.
- **La profundidad máxima del modelo.** Se queda en la hoja de cotización. Un umbral ahí
  empujaría a arriesgar el equipo de más. Ver § 5.6.

### Lo único que necesita retroalimentación, y no bloquea

**Los cinco chequeos de armado** los escribió el diseño, no el taller. Se implementan como están
y se corrigen con el primer uso real. Está dicho así en § 5.3 para que nadie los confunda con
algo que dijo el taller.

## El puente reparación → lección — rediseñado e implementado *(2026-08-20)*

> **Implementado en `19.0.15.5.0`.** Lo que sigue es el razonamiento completo, que conviene
> conservar: la parte más valiosa no es el mecanismo sino por qué el anterior no servía.

**El § 6.1.3 del diseño pide «un botón que la pre-llene desde `origen`», y eso no sobrevive a la
pregunta de Paulo: ¿cómo sabe el usuario qué hace ese botón, y por qué lo apretaría?** No tiene
incentivo, y no necesariamente tiene la formación para escribir lo que viene después.

### Lo que sí está resuelto, y hay que no perderlo de vista

**El conocimiento del momento no se pierde.** Al cerrar, el técnico ya deja el `origen`
—obligatorio desde `19.0.13.0.0`— y el «por qué pasó», más componente, subtipo, acción y el
hallazgo que resolvió. Eso es la **observación**, y es durable.

Lo que falta es la **conclusión**, y es un juicio de ingeniería con consecuencias en repuestos,
costos y garantías. **No es trabajo del técnico**, y pedírselo produce o silencio o texto malo.

### La corrección: el sistema detecta, la persona concluye

Una línea suelta es una anécdota; **lo que la vuelve lección es la repetición**. Y la repetición
es contable, porque una línea de trabajo no es texto libre: componente, subtipo, acción y origen
salen todos de catálogo. Además el propio `origen` ya excluye lo que ensuciaría el conteo — si
dice diseño, manufactura propia o pieza de proveedor, el técnico **ya afirmó que no fue el cliente
ni el desgaste**.

El § 6.3 dice que *«los patrones de manufactura sí se detectan, pero en los datos de reparación»*
y **nunca dice quién detecta**. Ahí estaba el hueco: la respuesta es el sistema, no una persona.

**Regla, corregida el mismo día: no hay umbral.** La primera versión ponía `N` unidades distintas
en un parámetro de sistema. Sobra. Si la lista se agrupa por modelo, componente y origen y se
ordena **por cantidad de líneas sin resolver**, arriba queda *«E-pod · manufactura propia — 4»* y
abajo *«cable · diseño — 1»*. La pregunta «¿es suficiente repetición?» vuelve a ser un juicio, que
es lo que era — y desaparecen el número arbitrario, el parámetro y toda la lógica de qué pasa
cuando llega la cuarta unidad.

*Unidades distintas* sí importa para el conteo: el mismo equipo reparado dos veces no es un
patrón.

**Dónde:** `Reparaciones → Lecciones pendientes`, al lado de *Revisiones técnicas*. En Reparaciones
y no en Calidad porque **la evidencia que hay que leer para decidir es evidencia de reparación**, y
porque mantiene la regla de que nadie tenga que enterarse de que Calidad existe.

### Lo que quedó construido

La lista muestra los trabajos con origen hacia adentro que todavía no alimentaron una lección ni
fueron descartados, **agrupada por modelo**. El conteo de cada grupo es la evidencia del patrón, y
no hay umbral: cuatro trabajos sobre el mismo componente del mismo modelo saltan a la vista, y uno
solo también — decidir dónde está la línea es un juicio, y por eso no se codificó un número.

Se seleccionan los que son el mismo problema y **un botón de cabecera escribe una sola lección con
todos**: todas las unidades en el alcance del daño, y los «por qué pasó» uno tras otro en la
descripción, cada uno con su equipo delante. Si alguno ya alimentaba una lección, los demás se le
suman en vez de crear otra.

**Descartar es escribir por qué**, en una columna editable de la misma lista. No hay asistente ni
casilla: el motivo obligatorio es la fricción que evita el descarte distraído, igual que en la baja
de un equipo, y deja un dato que sirve después. Hay un filtro para volver a mirar lo descartado,
porque un juicio se revisa.

**No se mezclan modelos en una lección** — se rechaza con un error que los nombra. Y la causa raíz
solo se propone si los trabajos coinciden en el origen: elegir uno de dos sería inventar el dato.

### El botón se retiró de la línea de trabajo

Quedaba en la pantalla de la persona que ya habíamos concluido que no lo iba a apretar. Y hacía
daño, no solo ruido: **la cola filtra por `mc_alerta_id` vacío, así que un clic distraído del
técnico le escondía la evidencia al supervisor**, en silencio y sin que nadie pudiera notarlo.
Condicionarlo a ciertos orígenes habría arreglado el ruido y no eso.

El campo se queda como columna de solo lectura: qué lección alimentó ese trabajo.

### En qué se convierte la acción

De mecanismo de descubrimiento a acción sobre un patrón ya detectado. Cambia de **sujeto** (un
patrón, no una línea), de **dueño** (quien tiene el criterio, no el técnico), de **pre-llenado**
(las N unidades en el alcance del daño y los N «por qué pasó» juntos — leídos de corrido dicen algo
que ninguno dice solo) y de **nombre**. Y gana un hermano, **«Descartar»**: si el sistema propone,
tiene que poder decírsele que no, o el mismo patrón reaparece cada vez y la gente deja de abrir la
lista.

`mc.rov.linea.falla.mc_alerta_id`, que ya existe desde `19.0.15.3.0`, es lo que hace que un patrón
deje de estar pendiente: cuando todas sus líneas alimentaron una lección, sale de la cola.

### La pregunta que estaba abierta, y cómo se resolvió

Era **¿el patrón es un agrupamiento calculado o un registro?**, y de ella dependían dónde vive el
descarte y a qué se cuelga el botón.

**Resuelta: no se guarda el patrón, se guarda la decisión humana.** La razón está en el
`CLAUDE.md` sobre un caso idéntico —*«no existe un booleano "mantención vencida" almacenado, y no
debe agregarse: un equipo se vence por el paso del tiempo, no porque alguien lo edite, así que
quedaría desactualizado en silencio»*—. Un patrón existe porque existen las líneas. Materializarlo
en una tabla es volver a crear el defecto recurrente que este módulo ya identificó: el dato
derivado que se desincroniza y nada lo detecta.

| Qué | Dónde vive |
|---|---|
| El patrón | Agrupamiento calculado. **Nada que guardar** |
| La lección | La alerta, que ya existe |
| El descarte, que **sí** es un acto humano | Un campo en la línea, con motivo |
| «Esta línea ya alimentó una lección» | `mc_alerta_id`, ya construido |
| Los botones | Acciones sobre líneas seleccionadas, no sobre cabeceras de grupo |

Sin modelo nuevo, sin acción programada, sin tabla derivada. Y con una propiedad que se gana
gratis: **si se descarta un patrón y vuelve a ocurrir, reaparece arriba de la lista**, porque las
líneas nuevas no están descartadas.

**Cuándo revisitarlo:** el día que se quiera un responsable por patrón, un plazo, o el historial de
quién descartó qué. Ahí un registro se justifica.

### La alternativa que se evaluó y se descartó

**Crear la alerta automáticamente al cerrar la orden**, por cada línea con esos tres orígenes,
agrupando por modelo. Se descartó por dos razones: le pide el juicio a la persona equivocada, y se
lo pide **cuando el patrón todavía no se ve** —al cerrar la primera orden hay una anécdota—. Y su
modo de falla es peor que el de la cola: si nadie mira, deja veinte borradores vacíos en Calidad y
la sensación falsa de que algo quedó capturado. La cola, si nadie la mira, deja las cosas donde ya
estaban.

### Lo que no se automatiza, y conviene no prometerlo

**La acción preventiva.** Ningún diseño fabrica disciplina: lo que se puede hacer es que la
omisión sea visible y que actuar cueste poco, y ahí se acaba. El día que se quiera subir el piso,
el lugar no es más automatismo sino un indicador donde el supervisor ya mira — y eso cae en «el
presupuesto de indicadores» de más arriba, que pide diseñarlos todos juntos.

## Un historial de la ficha técnica: evaluado y descartado *(2026-08-21)*

**No se construye, y la razón es que ya existe.** Cada revisión confirmada guarda, congelada, la
ficha tal como estaba ese día — software, umbilical y conteo de luces (`19.0.18.2.0`). **La
secuencia de revisiones de un equipo es su historial de ficha**, y se consulta abriendo la
revisión más cercana a la fecha que interese.

Un modelo aparte duplicaría eso y repetiría el defecto que este módulo ya identificó dos veces:
el dato derivado que se guarda a mano y se desincroniza sin que nada lo detecte.

Los cambios hechos **directo en la ficha, sin correr ninguna prueba**, quedan en el chatter del
equipo con valor viejo, valor nuevo, fecha y autor — todos esos campos llevan `tracking`. Para
«quién tocó esto» alcanza; lo que no permite es preguntar *«¿qué decía la ficha el 3 de marzo?»*
cuando no hay revisión cerca.

**Cuándo vuelve:** el día que haya que reconstruir el estado de un equipo en una fecha sin
revisión cercana — típicamente por una discusión de garantía. **Si eso ocurre dos veces, el
modelo se gana su lugar.** Antes de eso es un registro que se llena solo y no lo consulta nadie.

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

`mrp` asigna el número de serie por su cuenta (`mrp.production.lot_producing_ids`); hacen falta
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

- [ ] **Cambiar el `admin_passwd` de `/etc/odoo/odoo.conf`.** Quedó expuesto en una conversación
  el 2026-08-18. Es la contraseña maestra del gestor de bases de datos: permite crear, duplicar y
  **borrar** cualquier base. Se cambia en ese archivo y requiere reiniciar el servicio.

- [x] ~~**Montar staging**~~ — **hecho el 2026-08-18.** Base `odoo_staging`, servicio
  `odoo-staging` en el puerto 8070, checkout propio en `/opt/odoo/staging-addons/mc_rov`, y
  acceso solo por túnel SSH. Ver [`runbooks/staging.md`](runbooks/staging.md).

  **Todavía no se ha usado para lo que se montó:** ensayar una migración. La de fabricación va a
  ser la primera de verdad.

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
