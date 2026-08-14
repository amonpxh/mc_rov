# Diseño: el diagnóstico de fallas

> Estado: **acordado, sin implementar.** Versión objetivo `19.0.13.0.0` (bump de `X`: cambia
> datos existentes y lleva migración).
>
> Este documento se revisó contra el código el 2026-08-14, antes de escribir una línea. Esa
> revisión sacó un modelo entero, un campo y una lista en código, y corrigió tres afirmaciones
> que el código desmentía. Queda registrado en § 15.

---

## 1. El problema

Marine Connection no ve fallar los equipos. Los ROV llegan al taller **ya rotos**, muchas
veces con una descripción parcial o equivocada de lo que pasó, y hay que reconstruir la
historia hacia atrás. Es un diagnóstico post-mortem, no una observación en vivo.

Eso tiene una consecuencia que ordena todo el diseño: **el sistema tiene que distinguir lo
que alguien dice de lo que el taller comprueba.** Si las dos cosas caen en el mismo campo,
se pierde el único análisis que un taller puede producir y un fabricante no — *cuántas veces
lo que el cliente creía que estaba roto no era lo que estaba roto*.

Hoy falta la primera mitad: lo que dice el cliente entra como párrafo y no se puede contar.
Y la parte que sí está estructurada —la causa— mezcla dos preguntas distintas en un solo
campo.

### 1.1 Lo que ya existe y funciona

El módulo ya tiene una cadena causal estructurada, y conviene decirlo porque es mejor de lo
que parece desde afuera:

```
mc.rov.revision.chequeo          la prueba que se hizo
   │ chequeo_origen_id
   ▼
mc.rov.revision.hallazgo         lo que se encontró: componente, subtipo, severidad
   │ hallazgo_origen_id
   ▼
mc.rov.linea.falla               el trabajo que lo resolvió
   │
   ▼
causa_raiz                       por qué pasó
```

Cuatro eslabones, todos con clave foránea, todos agrupables. **Lo que falta no es la cadena.
Es el primer eslabón (el síntoma) y la calidad del último (la causa).**

El tercer eslabón tiene un problema propio que este diseño no crea pero sí tiene que
declarar: `hallazgo_origen_id` es opcional, y de él depende que "qué se encontró" y "por qué
pasó" se puedan leer en la misma fila. Ver § 9.1.

---

## 2. Las tres ventanas

La idea que ordena dónde va cada campo: **cada dato tiene una ventana en la que es barato de
capturar, y fuera de ella es caro o imposible.** Un campo puesto fuera de su ventana queda
vacío o se adivina.

| Ventana | Qué la hace única | Qué se captura ahí |
|---|---|---|
| **Recepción** | Es la única vez que hay alguien a quien preguntarle. El cliente se va y no vuelve. | Síntomas · qué componente señala el cliente · qué llegó con el equipo |
| **Diagnóstico** | Es la única vez que el equipo está abierto. Después se arma. | Pruebas · hallazgos · fotos *(pendiente)* |
| **Cierre** | Es el único momento en que se puede *afirmar* el origen. Antes es especulación. | Origen · por qué pasó |

Es la misma persona en los tres momentos — en Marine Connection el responsable de la orden
se hace cargo del trabajo completo. **Las ventanas son de tiempo, no de rol.** Por eso el
diseño no lleva estados intermedios, ni traspasos, ni permisos por rol.

La ventana de Cierre no es decorativa: es lo que decide que `origen` se valide al cerrar la
orden y no al guardar la línea de trabajo (§ 4.6), y es lo que decide en qué pestaña se ve
el análisis escrito (§ 5.2).

### 2.1 Por qué no hay un campo de «nivel de confianza»

Se evaluó y se descartó. Un porcentaje de confianza —o un `0.6 / 0.8 / 1.0`— nadie lo
calibra: se marca el mismo valor siempre, y un número no calibrado es peor que ningún número
porque se lee como medición.

Pero además es innecesario: **la certeza ya la codifica la ventana.** En recepción todo es
reporte, en diagnóstico todo es observación, y al cierre lo que se afirme debería estar
confirmado. El campo quería decir algo que la estructura ya dice.

Lo mismo aplica a repartir una causa en porcentajes («60% diseño, 40% uso»): además de no
calibrarse, obligaría a decidir si una falla cuenta 0,6 al sumarla.

### 2.2 Dónde se bloquea y dónde solo se muestra

> **Bloquear cuando el vacío sería indistinguible de un dato. Mostrar cuando el vacío es
> honesto.**

- **El checklist bloquea.** Un chequeo sin responder tiene que ser distinguible de uno
  respondido «OK»; si no, la ficha miente. Por eso la revisión no se confirma incompleta.
- **El origen bloquea el cierre.** Un trabajo sin origen es una reparación de la que no
  sabemos quién paga. Pero bloquea el **cierre de la orden**, no el guardado de la línea
  (§ 4.6).
- **El síntoma no bloquea.** Un síntoma vacío es honestamente vacío: no había nadie a quien
  preguntarle, o el que trajo el equipo no lo operó nunca. Obligar produciría inventos.
- **El análisis escrito no bloquea nunca.** Ver § 5.

La consecuencia del síntoma opcional hay que aceptarla de frente: el análisis de *reportado
vs real* puede no tener nunca datos y nadie se entera. La salida no es obligar, es **hacerlo
visible**: un filtro «Sin síntoma registrado» en la lista de órdenes, igual que el filtro
«Ficha incompleta» que ya existe para los números de serie.

Con una diferencia que hay que respetar al escribir el dominio: una serie incompleta se
puede completar cualquier día, pero **una orden cerrada hace un año no se puede arreglar** —
el cliente ya no está. Un filtro que devuelva todo el histórico nace con un piso de ruido
que nadie puede bajar, y un filtro que nunca llega a cero es un filtro que se deja de mirar.
Por eso se acota a **órdenes que todavía no están cerradas ni canceladas**: ahí el cliente
sigue siendo alcanzable y la fila se puede vaciar.

---

## 3. Recepción: el síntoma y la sospecha

Son **dos campos distintos**, y separarlos es el punto entero del bloque.

```
Falla reportada        Se apaga sola después de un rato y a veces
                       no se ve nada.               ← texto del cliente, intacto

Síntomas               [Se apaga solo ×] [Imagen con ruido ×]
                       [Falla después de un rato de uso ×]
                                                    ← catálogo, múltiple

El cliente sospecha de [Umbilical ×]                ← catálogo de componentes, opcional
```

### 3.1 El criterio para saber en qué lista va cada cosa

> **¿Lo vio, o lo deduce?** Lo que vio es síntoma. Lo que deduce es sospecha.

- «Un motor no gira» → **síntoma**. El thruster no se mueve cuando le da comando; lo ve.
- «Las luces no prenden» → **síntoma**. Lo ve.
- «Creo que es el umbilical», sin corte a la vista → **sospecha**.
- «Se cortó el umbilical», con el corte a la vista → **síntoma** (*Daño físico visible*)
  **más** sospecha (*Umbilical*).

### 3.2 Por qué la sospecha reusa el catálogo de componentes

Porque es el mismo catálogo con el que se registran los hallazgos y los trabajos. La
comparación queda directa y sin traducir:

> El cliente sospechó del **Umbilical**. El hallazgo real fue **Conector**.

Si el campo fuera texto libre, o un catálogo propio, esa consulta exigiría leer párrafos o
mantener una tabla de equivalencias que nadie mantendría.

Es opcional: muchas veces el cliente no dice nada. **Que quede vacío también es dato** —
significa que el equipo llegó sin diagnóstico.

**Eso obliga a que el catálogo de componentes cubra lo que los síntomas nombran.** Hoy tiene
once entradas y no incluye luces, sonar ni manipulador, que sí aparecen en el catálogo de
síntomas: el cliente vería «Luces no encienden» y no tendría de qué sospechar. Se agregan los
tres (§ 7.1).

**El cuarto candidato —«Software de superficie»— no entra, y por una razón distinta a la que
parecía.** No choca con el catálogo `mc.rov.software.superficie`: ese —QGroundControl, Crabby,
ROVControl— responde *qué software trae este equipo*, vive en la ficha técnica del número de
serie bajo Inventario, y ninguna consulta lo cruza con los componentes. Choca con
`comp_electronica`, que ya se llama **«Electrónica / Software»** y cubre el caso. Dos entradas
que significan lo mismo rompen el conteo, que es lo único que un catálogo tiene que proteger.

> Que `comp_electronica` mezcle dos cosas en una etiqueta es un problema aparte y anterior.
> Separarlas exigiría decidir qué pasa con las filas que ya la usan, así que se deja anotado
> y no se toca acá.

### 3.3 Lo que sí se pierde, asumido a propósito

Si el cliente reporta **dos** síntomas y señala **dos** componentes, no queda registrado cuál
va con cuál. «Un motor no gira» + «sin imagen», sospechas *Motor* y *Cámara*: el sistema no
sabe que el motor va con el primero.

Arreglarlo exigiría que cada queja fuera una fila en vez de una etiqueta, y eso pesa justo
en el momento en que el cliente está esperando en el mesón. Para el análisis no cambia nada
—lo que se cuenta es *sospechó de X, resultó ser Y*— y la frase completa queda en el texto
libre. Es una decisión, no un descuido.

### 3.4 La temporalidad es un síntoma, no un campo aparte

Que la falla vaya y venga, o que aparezca recién después de un rato de uso, es de las cosas
que más orientan el diagnóstico: una falla intermitente y una permanente mandan a mirar
lugares distintos, y «después de un rato» apunta a temperatura o a filtración.

El diseño original le daba un campo propio —`momento_falla`, un Selection de cinco valores en
la orden— y **se retiró**. Tres razones, en orden de peso:

1. **Pasa el propio test del § 3.1.** El cliente *vio* que la falla iba y venía. No lo dedujo.
   Es un síntoma según el único criterio que este diseño usa para decidirlo.
2. **El campo traía una contradicción que no tenía arreglo.** Llevaba un valor «No se sabe»
   por defecto y al mismo tiempo pedía distinguir «no se sabe» de «nadie preguntó» — que es
   exactamente lo que un valor por defecto vuelve imposible, y encima sin bloquear nada, en
   contra de la regla del § 2.2. Como etiqueta el problema desaparece: no poner el tag es
   honestamente no ponerlo.
3. **Cuesta menos.** Un clic más en el mismo campo de etiquetas, contra un desplegable aparte
   que hay que mirar. Un campo menos, una lista en código menos, un valor por defecto menos y
   una migración menos.

Entran como tres entradas del catálogo, en su propia familia (§ 6.1). El único argumento en
contra —que registrar la intermitencia en dos lados dejaría dos versiones del mismo hecho—
**solo valía mientras existieran los dos lados**.

---

## 4. El origen

Reemplaza a `causa_raiz`, que mezclaba dos preguntas: *qué le pasó físicamente* y *de quién
es el problema*. Dos de sus seis valores —`corrosion` y `accidente`— no eran causas raíz en
absoluto, y esa es la mejor evidencia de que el campo estaba mal planteado. En el caso de
`corrosion` la evidencia es literal: **«Corrosión» ya existe como hallazgo** en
`mc.rov.hallazgo`, familia *estructura*. El mismo hecho estaba en dos ejes distintos.

**El mecanismo no necesita campo propio: ya es el hallazgo.** «Rodamiento trabado» (hallazgo)
y «bloqueo mecánico» (mecanismo) son el mismo hecho dicho dos veces. El catálogo de hallazgos
existe, tiene familias y está en uso —Corrosión, O-ring dañado, Falso contacto, Trizadura— o
sea que *es* un catálogo de mecanismos. Se evaluó crear otro y se descartó por eso.

Entonces la cadena tiene dos ejes, no tres:

> **qué encontraste** (hallazgo) → **por qué pasó** (origen)

Con la advertencia del § 9.1: los dos ejes no viven en el mismo registro, y el puntero que
los une es opcional.

### 4.1 Los valores

| Etiqueta | Clave |
|---|---|
| **Diseño o especificación** (lo pensamos mal) | `diseno` — nueva |
| **Manufactura propia** (lo hicimos mal) | `falla_fabricacion` — reusada |
| **Pieza de proveedor** (vino fallada) | `pieza_proveedor` — nueva |
| **Uso del cliente** (mal uso o accidente) | `mal_uso` — reusada |
| **Desgaste normal** (duró lo que tenía que durar) | `desgaste` — sin cambios |
| **No determinado** | `desconocida` — reusada |

Los paréntesis van **en la etiqueta y no en un tooltip**. El campo es una columna de la lista
de trabajos realizados, así que el valor ya elegido se corta — pero **el desplegable abierto
muestra las opciones completas**, y ese es justo el momento en que hace falta la aclaración.

El criterio de redacción: **se nombra al responsable cuando hay uno.** Cuatro opciones llevan
dueño; desgaste y no determinado no tienen a quién apuntar.

- **«Pieza de proveedor», no «pieza comprada»** — esta última se lee como *compramos mal la
  pieza*, que es un problema de especificación y no del proveedor.
- **«Uso del cliente», no «mal uso»** — «mal uso» es un veredicto, y suena a acusación justo
  en el campo que decide quién paga. Para el análisis vale exactamente lo mismo.
- **«Uso del cliente (mal uso o accidente)»** absorbe el caso del choque, que si no se queda
  sin dónde caer.

### 4.2 Por qué no existe «ambiente»

Se propuso y se descartó, y el argumento cierra: **una especificación es precisamente la
declaración de qué condiciones aguanta el equipo.** Si el medio lo dañó, entonces:

- había un límite dicho y se pasó → **uso del cliente**;
- el límite estaba mal puesto → **diseño o especificación**;
- nunca lo dijimos → especificación incompleta → **diseño o especificación**.

No hay una cuarta rama. Un evento fortuito es *accidente*, que ya está en «uso del cliente»;
una falla prematura en condiciones normales es *manufactura* o *pieza de proveedor*.

Quitarla además mejora el análisis: «ambiente» no es accionable, «no especificamos para ese
medio» sí. Y siendo la única opción que no culpaba a nadie, habría atraído todo lo dudoso —
el mismo defecto que tenía la opción «pierde señal» en el catálogo de síntomas.

### 4.3 Texto de ayuda del campo

Va en el `help` del campo, o sea en el tooltip que ve quien lo llena:

> **Diseño o especificación** — se armó tal como estaba definido y aun así falló. Incluye
> elegir la pieza equivocada (un conector IP67 donde hacía falta IP68) y **no haber previsto
> las condiciones donde el equipo iba a trabajar**.
> **Manufactura propia** — estaba bien definido y el trabajo salió malo: soldadura, sellado,
> torque, cableado.
> **Pieza de proveedor** — la pieza comprada vino defectuosa de fábrica.
> **Uso del cliente** — se operó fuera de lo indicado, o hubo un accidente.
> **Desgaste normal** — cumplió su vida útil.
> **No determinado** — no se pudo establecer. Es una respuesta válida.

La primera línea es la que absorbe lo que antes habría ido a «ambiente»; sin ella esos casos
no los encuentra nadie. La última importa igual: si «no determinado» se siente como no haber
hecho la pega, se va a marcar cualquier otra cosa antes que dejarla.

### 4.4 El riesgo que no es técnico

Tres de las seis opciones apuntan hacia adentro. **Este campo es, en buena parte, una
autoevaluación.**

Si marcar «manufactura propia» le trae problemas a alguien, en seis meses todo va a ser
«desgaste normal» — y no va a haber forma de distinguirlo de la verdad, porque esa respuesta
es plausible siempre.

No se arregla con software. Se arregla con que quede dicho que el campo existe para mejorar
el producto y no para buscar culpables. **Es la condición de la que depende que todo lo demás
sirva** — y por eso no puede quedar solamente escrita acá, en un documento que lee una sola
persona. **Cierra el `help` del campo**, donde lo lee quien lo llena:

> Esto sirve para mejorar el producto, no para buscar culpables. «Manufactura propia» y
> «Diseño» son respuestas normales y esperables.

### 4.5 Es el campo que decide la garantía

La orden ya tiene «Bajo garantía». Si el origen es *diseño* o *manufactura*, la reparación la
paga la empresa; si es *uso del cliente*, la paga el cliente. **Es la misma pregunta,
contestada dos veces en la misma orden.**

De ahí sale la razón por la que este campo sí se va a llenar: alguien necesita la respuesta
para cobrar. Las estadísticas son el subproducto. Un campo que solo sirve para un reporte
futuro se llena a medias; uno que decide quién paga, no.

Y por eso **«no determinado» tiene que seguir permitiendo cerrar la orden**: obligar a
acusar produce acusaciones falsas.

**Es el único campo obligatorio de todo este diseño.**

### 4.6 Dónde se exige: al cerrar la orden, no en el modelo

Un `required=True` en el campo lo exigiría **al guardar cada línea de trabajo**, o sea
mientras el técnico todavía está reparando. Eso contradice la ventana del § 2 —al momento de
anotar el trabajo el origen suele ser especulación— y produce el peor resultado posible:
`desconocida` marcado para salir del paso, sin que nadie vuelva a mirarlo.

Va como validación en la transición a `done`, igual que
[`_validar_tipo_intervencion`](../../models/repair_order.py), y con la misma forma: un
`UserError` que nombra las líneas que faltan. El técnico anota trabajos durante la semana y
contesta las seis preguntas juntas al cerrar, que es cuando ya sabe las respuestas.

Dos consecuencias de implementación:

- `mc.rov.linea.falla` no tiene campo `name` ni `_rec_name`, así que hoy su `display_name`
  es `"mc.rov.linea.falla,42"`. Para que el error nombre algo legible lleva un
  `_compute_display_name` con componente y acción, como el que ya tiene
  `mc.rov.revision.corrida` por esta misma razón.
- **Una orden sin líneas de trabajo se cierra sin problema.** Una visita de diagnóstico puro
  no registra trabajos y no por eso está incompleta. La validación mira las líneas que
  existen, no exige que existan.

---

## 5. Por qué pasó: el análisis escrito

`origen` responde *de quién es el problema* en seis valores contables. No responde **cómo se
llegó a esa conclusión**, y en un campo que en tres de sus seis opciones es una
autoevaluación (§ 4.4), eso es justamente lo que hace falta para poder auditarlo después.

Entre el hallazgo y el origen hay un salto que hoy no se guarda en ninguna parte. Hallazgo:
*«O-ring dañado»*. Origen: *«diseño»*. En el medio está el razonamiento —por qué ese o-ring
se dañó, y por qué la conclusión es que la especificación estaba mal— y sin él, seis meses
después, un conteo alto de *diseño* no se puede revisar.

Un `Text` en la línea de trabajo, al lado de `origen`. La pareja funciona porque cada mitad
cubre el defecto de la otra: **el valor se cuenta, el texto se lee cuando el conteo llama la
atención.** Un Selection solo no se puede auditar; un texto solo no se puede contar.

### 5.1 Por qué texto libre y no cinco campos

Esto nace de un pedido concreto: registrar un «5 whys». La forma en que se implementa **no es
cinco campos de texto, ni un modelo de porqués numerados**, por dos razones distintas.

La primera es la del propio método: la cantidad de eslabones varía —a veces son tres, a veces
ocho— y obligar a cinco produce relleno. Un `Text` deja escribir cinco renglones cuando son
cinco y dos frases cuando son dos.

La segunda es de reversibilidad. El campo entra en parte para cumplir un requerimiento, y su
aporte real todavía no está probado: es plausible que sirva solo en los casos complejos y
quede vacío en la mayoría. **Un campo de texto se retira barato; un modelo con datos adentro
cuesta un bump de `X` con migración.** Si más adelante hace falta estructura de verdad, el
modelo hijo se agrega encima sin tocar nada de lo escrito.

Por lo mismo **la pantalla no dice «5 whys» en ninguna parte**: el campo se llama *Por qué
pasó*. Ponerle el nombre del método importa el ritual, y el técnico que tiene dos frases
siente que entregó una respuesta incompleta.

**Nunca es obligatorio, y en particular no se vuelve obligatorio cuando el origen apunta
hacia adentro.** Suena razonable exigir justificación en «manufactura propia» y «diseño», y
es exactamente lo que no hay que hacer: ponerle fricción a las tres opciones incómodas
empuja a marcar «desgaste normal», que es plausible siempre (§ 4.4). Tiene que costar lo
mismo en las seis.

**A revisar en seis meses:** qué proporción de las líneas lo tiene lleno. Si es marginal,
esa es la respuesta y sacarlo cuesta un campo.

### 5.2 Dónde se llena

En la pestaña **Resultado**, no en «Trabajos realizados».

El momento ya es el correcto por otra vía —el análisis se escribe junto con `origen`, y
`origen` se contesta al cerrar (§ 4.6)—, pero la pantalla no: «Trabajos realizados» es donde
se anota *mientras* se trabaja, y su lista ya lleva diez columnas. Un campo de texto como
columna doce es donde el texto se va a morir.

La pestaña Resultado es literalmente la pantalla de cierre: ahí ya están `fecha_entrega_real`
y las observaciones de salida. Entra un bloque con una fila por trabajo — componente, acción,
origen, por qué pasó.

Es la misma relación mostrada dos veces, con el patrón que el módulo ya usa en los siete
campos `chequeo_*_ids` de la revisión: dos `One2many` sobre la misma tabla y el mismo
inverso, que se diferencian por la vista. **La lista del cierre va con `create="0"
delete="0"`** y solo escribe `origen` y el análisis: de la pantalla de cierre no se crean ni
se borran trabajos, y así dos listas sucias en el mismo guardado nunca emiten comandos en
conflicto.

### 5.3 Por qué no hay catálogo de causas sistémicas

El diseño original llevaba un modelo `mc.rov.causa.sistemica` —un catálogo que nacía vacío y
al que se enlazaban las líneas cuando el mismo problema aparecía por segunda vez— y **se
retiró entero**. El argumento que lo justificaba era bueno: si no existe desde ya, se pierden
los primeros cien casos. El que lo mata es mejor:

> **Enlazar el segundo caso con el primero exige que una persona recuerde el primero.** Eso
> es memoria de patrones a través de meses, que es justo lo que una persona no tiene y una
> consulta sí.

Después de esta versión, todo lo que hace falta para encontrar un patrón va a estar
estructurado: síntoma, componente sospechado, hallazgo, componente, acción y origen. Un
`GROUP BY origen, componente_id` encuentra los casos repetidos solo, sin que nadie los haya
declarado. Un catálogo llenado a mano no agrega poder de consulta — agrega una etiqueta que
alguien tiene que acordarse de poner, y que si no se pone hace que la consulta mienta.

Se suma que el flujo no daba: el catálogo se administra desde Configuración (§ 7.4), la
columna entraba oculta, el campo era opcional y no había ninguna pantalla que ayudara a
encontrar el caso anterior para enlazarlo. Un campo así queda en cero.

**Lo que reemplaza a la causa sistémica es el análisis escrito del § 5.** Cuando la conclusión
sea sobre el modelo y no sobre ese equipo, se escribe ahí, en el caso donde se descubrió. Que
esté en prosa no es una pérdida: la parte contable del patrón —origen, componente, hallazgo—
ya está en campos.

---

## 6. El catálogo de síntomas

Es **selección múltiple**: un ROV llega con «sin imagen» *y* «pierde fuerza» a la vez, y
obligar a elegir uno perdería la mitad del reporte. Va con etiquetas, igual que «Tipo de
intervención».

Eso resuelve el problema del largo: con etiquetas y buscador se escribe «prof» y la lista se
filtra sola. **Lo que importa no es que la lista sea corta, sino que no haya dos entradas que
signifiquen lo mismo.**

Lleva `familia`, igual que el catálogo de hallazgos, para que el buscador agrupe.

### 6.1 Los valores semilla

**Energía** — No enciende · Se apaga solo · Se calienta

**Movimiento** — Pierde fuerza o no avanza · Un motor no gira · Se va de lado o gira solo (en
manual) · No sube o se queda en el fondo · No mantiene profundidad (depth hold) · No se
estabiliza (stabilize)

**Video** — Sin imagen · Imagen con ruido o intermitente · El tilt de la cámara no responde

**Comunicación** — Pierde conexión con superficie · Conectado pero no responde · El software
de superficie falla

**Sensores** — Un sensor marca mal o no marca

**Accesorios** — Luces no encienden · Manipulador no responde · Sonar no funciona

**Físico** — Entró agua · Fuga de aceite · Hace ruido o vibra raro · Daño físico visible

**Cuándo ocurre** — Falla intermitente (va y viene) · Falla después de un rato de uso · Pasó
una sola vez

**Otro** — Otro

Veintisiete entradas en nueve familias. Los paréntesis son parte del nombre: buscar «depth»
o «stabilize» tiene que encontrar la entrada, porque son las palabras que el piloto usa.

La familia **Cuándo ocurre** es la que absorbe al campo `momento_falla` retirado (§ 3.4). No
lleva un «Siempre, desde que ocurrió»: es el supuesto por defecto y marcarlo no agrega nada.

La familia **Otro** tiene una sola entrada, del mismo nombre. No es redundancia: ver § 6.5.

### 6.2 Por qué los modos de vuelo van separados

Los ROV tienen `manual`, `acro`, `stabilize` y `depth hold`, y depth hold incluye stabilize.
Un solo síntoma genérico —«se va de lado»— tapaba tres fallas que apuntan a lugares distintos:

| Síntoma | Hacia dónde apunta |
|---|---|
| Se va de lado o gira solo **en manual** | Empuje: un motor, una hélice, la posición de un thruster |
| **No mantiene profundidad** (depth hold) | El sensor de presión |
| **No se estabiliza** (stabilize) | IMU o compás |

Y hay una deducción que solo existe teniéndolos separados: **si depth hold falla pero
stabilize funciona, el problema es el sensor de profundidad y no el IMU**, porque uno depende
del otro.

### 6.3 Por qué los accesorios van separados y no en una entrada genérica

«Las luces no prenden» **el cliente lo vio**: es un síntoma, no una sospecha. Si se dejara
como «no responde un accesorio», el componente tendría que irse al campo de sospechas, donde
se mezclaría una observación con una adivinanza — y el análisis de *cuánto le achunta el
cliente* solo tiene sentido sobre las adivinanzas.

El criterio general:

> **Si dos entradas te mandan a mirar lugares distintos, son síntomas distintos.**

Por lo mismo se descartó **«Pierde señal»**, que se había propuesto explícitamente «para
cuando no queda claro si es comunicación, video u otra». Una opción que existe para lo dudoso
absorbe todo lo dudoso. Para eso está «Otro» más el texto libre.

### 6.4 Archivar un síntoma esconde el histórico, no lo conserva

Esto salió de correr los tests, no de diseñar, y contradice lo que este documento daba por
sentado. Retirar una entrada del catálogo es desmarcar `active` y nunca borrarla, para no
dejar huérfanas las órdenes que la usaron. **Pero el enlace no sobrevive a la lectura:** el
ORM aplica `active_test` al leer un `Many2many`, así que la orden pasa a informar un síntoma
menos y nada avisa. La fila de la tabla de relación sigue ahí; hay que leer con
`active_test=False` para verla.

La consecuencia es de análisis y no de pantalla: **archivar un síntoma de uso corriente baja
su conteo histórico a cero, y esa caída se ve idéntica a que hubiera dejado de ocurrir.**

- Quien cuente síntomas del pasado tiene que leer con `active_test=False`.
- Archivar una entrada muy usada es una decisión sobre los datos, no una limpieza de lista.
- Cuando lo que sobra es un duplicado, lo correcto no es archivarlo sino reapuntar las órdenes
  a la entrada buena antes de archivar.

Aplica igual a `mc.rov.hallazgo`, `mc.rov.componente` y a todo catálogo con `active` que se lea
por un x2many. No es nuevo de esta versión; lo nuevo es que quedó escrito.

### 6.5 «Otro» se queda

Aunque parezca redundante con el texto libre. Marcarlo explícitamente dice *«preguntamos y no
estaba en la lista»*, que es distinto de que nadie clasificó. **Si «Otro» empieza a aparecer
seguido, es la señal de que a la lista le falta una entrada.**

---

## 7. Catálogos y listas después de este cambio

### 7.1 Catálogos — se editan desde Configuración, sin desplegar

| Catálogo | Dónde se administra | Estado |
|---|---|---|
| Componentes ROV | Reparaciones → Config → Catálogos ROV | existe · **+3 entradas** |
| Subtipos | dentro de cada componente | existe |
| Acciones | Reparaciones → Config → Catálogos ROV | existe |
| Tipos de intervención | ídem | existe |
| Pasos de testeo | ídem | existe |
| Hallazgos | ídem | existe |
| **Síntomas** | ídem | **nuevo** |
| Software de superficie | Inventario → Config → Catálogos ROV | existe |
| Controladores de vuelo | ídem | existe |

De ocho a nueve: **el mecanismo no necesitó catálogo propio porque ya era el hallazgo, y las
causas sistémicas se retiraron (§ 5.3).**

Las tres entradas nuevas de componentes son **Luces**, **Sonar** y **Manipulador**, por lo del
§ 3.2. Ninguna es inspeccionable (`es_inspeccionable` queda en falso), así que no agregan
filas a la inspección de sellos ni una respuesta más por revisión.

### 7.2 Listas en código — cambiarlas exige desplegar

| Lista | Dónde | Estado |
|---|---|---|
| **Origen** (6) | línea de trabajo | **nueva**, reemplaza `causa_raiz` |
| **Familia de síntoma** (9) | catálogo de síntomas | **nueva** |
| Familia de hallazgo (6) | catálogo de hallazgos | existe |
| Sección de prueba (7) | catálogo de pasos de testeo | existe |
| Resultado de chequeo (3) | línea de chequeo | existe |
| Estado del sello (5) | inspección de sellos | existe |
| Severidad | hallazgo de la revisión | existe |
| Tipo de revisión (3) | revisión | existe |

### 7.3 El criterio

> **Catálogo si crece con el uso. Código si es la estructura del documento.**

Los síntomas van a crecer: entra el USBL, entra un modelo nuevo. Las familias no —son las
secciones de la hoja y son las mismas desde hace años—. El origen tampoco: son seis maneras
de responder *de quién es el problema*, y esa pregunta no cambia con el catálogo de productos.

### 7.4 Los catálogos nuevos no se editan desde donde se llena la ficha

Los dos campos que entran en esta versión —síntomas y sospecha— van con
`options="{'no_create': True}"`: quien recibe el equipo en el mesón elige de la lista y no
puede agregar entradas al vuelo. Si se puede, en dos meses hay cuatro maneras de escribir «no
enciende» y el conteo se muere.

**Esta regla hoy no existe en el resto del módulo, y esta versión no la extiende.** Conviene
decirlo con precisión porque una versión anterior de este documento afirmaba lo contrario: en
`19.0.12.0.0` lo que se cerró fue la creación de **líneas del checklist** (`create="0"
delete="0"`), no el quick-create de catálogos. En hallazgos y componentes el técnico todavía
puede crear una entrada escribiendo el nombre en el campo — el comentario de
`views/mc_rov_menus.xml` lo dice explícitamente. Cerrarlos ahí es una decisión aparte, con su
propio costo, y no se toma acá.

---

## 8. El flujo completo

### Momento 1 — Recepción · orden de reparación

| Campo | Catálogo |
|---|---|
| Falla reportada | ninguno — texto del cliente, intacto |
| Síntomas | **Síntomas** |
| El cliente sospecha de | **Componentes** |
| Equipos recibidos | números de serie |
| Tipo de intervención | **Tipos de intervención** |

Al confirmar la orden, la revisión se crea sola.

### Momento 2 — Diagnóstico · revisión técnica

| Bloque | Catálogo |
|---|---|
| Corridas con cada umbilical | ninguno |
| Sellos por componente | **Componentes** (los inspeccionables) |
| Pruebas, en secciones | **Pasos de testeo** |
| Hallazgos | **Componentes** + **Subtipos** + **Hallazgos** |

No se confirma con un chequeo sin responder. Cada hallazgo guarda **qué prueba lo destapó**,
o queda vacío, que significa que se vio por fuera del checklist.

### Momento 3 — Reparación · trabajos realizados

| Campo | Catálogo |
|---|---|
| Componente + subtipo | **Componentes** + **Subtipos** |
| Acción | **Acciones** |
| Resuelve el hallazgo | apunta al hallazgo del momento 2 |

Los repuestos van por la pestaña de Odoo, con productos de inventario.

### Momento 4 — Cierre · pestaña Resultado

| Campo | Catálogo |
|---|---|
| **Origen**, por trabajo | lista en código · **obligatorio para cerrar** |
| **Por qué pasó**, por trabajo | ninguno — texto |
| Observaciones de salida | ninguno — es lo único que ve el cliente |

Más el tipo de intervención obligatorio, que ya se exigía, y una segunda revisión si se probó
de nuevo.

### 8.1 Las dos columnas que cruzan los cuatro momentos

**El vocabulario de componentes**, que aparece cuatro veces:

```
Componentes ──┬── sospecha del cliente      (recepción)
              ├── inspección de sellos      (diagnóstico)
              ├── hallazgos                 (diagnóstico)
              └── trabajos realizados       (reparación)
```

Por eso *«el cliente sospechó del umbilical, ¿qué encontramos y dónde trabajamos?»* es una
consulta y no una lectura.

**La cadena causal**, con punteros reales y no texto:

```
Paso de testeo  →  línea de prueba
                        │  ¿qué prueba lo destapó?
                        ▼
Hallazgo        →  hallazgo de la revisión
                        │  ¿qué trabajo lo resolvió?
                        ▼
Acción          →  línea de trabajo
                        │
                        ▼
                     Origen  +  por qué pasó
```

---

## 9. La unidad de análisis es la línea de trabajo, no la orden

Una orden puede tener varias revisiones —la de recepción y la del segundo pase— y varias
líneas de trabajo. **Ninguna revisión representa a la orden**: son evidencia en momentos
distintos, la primera dice cómo llegó y la segunda cómo quedó.

Si una orden tiene tres líneas de trabajo con orígenes *diseño*, *uso* y *desgaste*, **la
orden tiene tres orígenes**. Eso es correcto y no hay que colapsarlo.

**No debe existir un campo derivado «causa de la orden».** Cualquier regla para elegir una
—la primera, la más grave, la más repetida— sería arbitraria y botaría las otras dos en
silencio. Es el mismo error que ya se evitó con `numero_en_visita` en las revisiones.

Eso tiene una consecuencia práctica en la vista de búsqueda: **agrupar órdenes por origen no
se puede y no se va a poder.** Quedó anotado como pendiente cuando `causa_raiz` todavía vivía
en la orden; desde `19.0.8.0.0` vive en la línea, y agruparlo a nivel de orden exigiría
exactamente el campo derivado que este párrafo prohíbe. Se retira del pendiente.

Para el pipeline: **el grano es `mc.rov.linea.falla`.**

### 9.1 El cruce cuando `hallazgo_origen_id` está vacío

El § 4 dice que la cadena tiene dos ejes, *qué encontraste* → *por qué pasó*. Hay que agregar
que **los dos ejes no viven en el mismo registro.** La línea de trabajo no tiene hallazgo
propio: tiene `hallazgo_origen_id`, un puntero **opcional** a un hallazgo de la revisión, que
además exige que alguien haya cargado ese hallazgo.

Entonces es perfectamente posible —y probablemente frecuente al principio— tener «por qué
pasó» sin «qué se encontró» en la misma fila. Nada lo detecta solo. Las reglas:

- **El cruce primario es** `linea.hallazgo_origen_id → hallazgo_id`, con `componente_id` y
  `subtipo_id` del hallazgo.
- **Cuando el puntero está vacío, el respaldo es `componente_id` + `accion_id` de la propia
  línea**, que sí son obligatorios. Dice dónde se trabajó y qué se hizo, no qué se encontró.
  Alcanza para agrupar por componente; no alcanza para hablar de mecanismos.
- **Antes de confiar en cualquier análisis que use el puntero, hay que medir qué proporción
  de líneas lo tiene lleno.** Un cruce sobre el 20% de las líneas no es una muestra, es un
  sesgo — y se ve idéntico a un resultado.

---

## 10. Modelo de datos

### 10.1 `mc.rov.sintoma` — catálogo de síntomas *(nuevo)*

```
name       Char      required
sequence   Integer   default 10
familia    Selection required, default 'otro'
active     Boolean   default True
_order     familia, sequence, name
```

`FAMILIAS_SINTOMA`: `energia` · `movimiento` · `video` · `comunicacion` · `sensores` ·
`accesorios` · `fisico` · `temporalidad` · `otro`.

### 10.2 `repair.order` — campos nuevos

```
sintoma_ids               M2m mc.rov.sintoma
                          relation mc_rov_repair_order_sintoma_rel
componente_sospechado_ids M2m mc.rov.componente
                          relation mc_rov_repair_order_sospecha_rel
linea_falla_cierre_ids    O2m mc.rov.linea.falla, inverso repair_id
```

Los nombres de tabla van explícitos, igual que en `tipo_intervencion_ids`, para que una
migración futura pueda escribir en ellas.

`linea_falla_cierre_ids` es la misma relación que `linea_falla_ids`, mostrada en la pestaña
Resultado con otra lista (§ 5.2). No agrega ninguna columna a la base.

Más el método `_validar_origen`, llamado desde el `write` a `done` junto a
`_validar_tipo_intervencion` (§ 4.6).

### 10.3 `mc.rov.linea.falla` — cambios

```
causa_raiz  →  origen          Selection, NO required en el modelo, ver § 4.1 y § 4.6
               analisis_causa  Text, "Por qué pasó"
               _compute_display_name   componente · acción
```

### 10.4 Vistas

- **Orden de reparación** — el bloque de recepción (síntomas y sospecha) va junto a
  `falla_reportada`, no en una pestaña. Es lo primero que se ve al abrir la orden, que es
  cuando el cliente está delante. Los dos con `no_create` (§ 7.4).
- **Trabajos realizados** — `origen` reemplaza a `causa_raiz` en la columna. `analisis_causa`
  **no** entra a esta lista.
- **Pestaña Resultado** — bloque «Por qué pasó»: una fila por trabajo con componente, acción,
  origen y análisis, en una lista `create="0" delete="0"` (§ 5.2).
- **Vista de búsqueda de `repair.order`** *(no existe hoy; se crea)* — hereda de
  `repair.view_repair_order_form_filter`:
  - filtro **«Sin síntoma registrado»**, acotado a órdenes no cerradas ni canceladas (§ 2.2);
  - búsqueda y agrupación por tipo de intervención;
  - **sin** «agrupar por origen», por lo del § 9.

  El schema de Odoo 19 rechaza `expand` y `string` en el elemento `group`, y el último filtro
  del grupo de agrupaciones se llama `group_by_repair_properties`.
- **Lista de órdenes** — `sum` al pie de la columna `mc_total_horas`, que estaba pendiente.

### 10.5 Seguridad

Una línea nueva en `ir.model.access.csv` para `mc.rov.sintoma`, sin grupo, como el resto
mientras no existan los grupos de seguridad.

---

## 11. Migración `19.0.13.0.0`

**Todo en `pre-migrate.py`**, y la razón es concreta: aunque `origen` no lleve `required` en
el modelo, la columna tiene que estar escrita antes de que el ORM procese el modelo nuevo,
para que ninguna fila quede con el valor perdido entre medio. El ORM crea las columnas nuevas
después del pre-migrate, así que la columna se crea a mano para poder leer la vieja.

```sql
-- 1. La columna nueva se crea a mano: el ORM la crearía después del pre-migrate,
--    demasiado tarde para leer la vieja.
ALTER TABLE mc_rov_linea_falla ADD COLUMN IF NOT EXISTS origen varchar;
UPDATE mc_rov_linea_falla SET origen = causa_raiz;

-- 2. `corrosion` es un mecanismo, no un origen: no hay a dónde mapearlo sin inventar.
--    Se conserva en el detalle para no perderlo.
UPDATE mc_rov_linea_falla
   SET origen  = 'desconocida',
       detalle = COALESCE(detalle || E'\n', '') || '[Migración 19.0.13.0.0] Causa anterior: corrosión.'
 WHERE causa_raiz = 'corrosion';

-- 3. `accidente` conserva su significado dentro de "Uso del cliente (mal uso o accidente)".
UPDATE mc_rov_linea_falla SET origen = 'mal_uso' WHERE causa_raiz = 'accidente';

-- 4. `causa_raiz` era OPCIONAL, así que hay filas sin ningún valor. Sin esto quedan con
--    origen NULL, que es indistinguible de un dato que se perdió en la migración.
UPDATE mc_rov_linea_falla SET origen = 'desconocida' WHERE origen IS NULL;

ALTER TABLE mc_rov_linea_falla DROP COLUMN IF EXISTS causa_raiz;
```

El paso 4 es el que se había omitido y es el que más filas toca: `causa_raiz` nunca fue
obligatorio, así que en producción hay líneas sin causa. Quedan en «No determinado», que es
la verdad.

El script lleva el guard `if not version: return` que usan las migraciones anteriores, para
que una instalación limpia no lo corra.

**Auditoría previa, en `odoo_prod` y de solo lectura:**

```sql
SELECT causa_raiz, count(*) FROM mc_rov_linea_falla GROUP BY causa_raiz;
```

**Y una revisión a mano que no puede hacer el script:** las filas que hoy dicen
`falla_fabricacion` — ¿se referían a *nosotros* o a *el proveedor*? Con el volumen actual se
miran una por una. Si alguna era del proveedor, se corrige a `pieza_proveedor` después de
desplegar.

No hay nada que migrar para los síntomas ni para la sospecha: nacen vacíos en todas las
órdenes, que es la verdad — a nadie se le preguntó.

---

## 12. Qué análisis habilita

**Desde el primer mes**

- *Reportado vs real*: de qué componente sospechó el cliente contra dónde estuvo el hallazgo.
- Cuántas órdenes llegan sin ningún diagnóstico del cliente.
- Qué síntomas llegan más seguido, por familia.
- **Qué proporción de las líneas tiene `hallazgo_origen_id` lleno** — no es un análisis del
  taller, es el que dice si los demás son confiables (§ 9.1).

**Con algunos meses**

- Distribución de orígenes: cuánto es nuestro y cuánto del cliente.
- **Un hallazgo frecuente que ninguna prueba detecta** → falta un chequeo en el checklist.
- **Un hallazgo que nunca tiene trabajo asociado** → se está mirando algo que no se arregla.
- Qué síntoma predice qué hallazgo: el valor diagnóstico de cada queja.
- **Qué proporción de las fallas intermitentes termina sin ningún hallazgo** — cuántos equipos
  vuelven al cliente sin que hayamos podido reproducir nada. Hoy nadie lo sabe, y es el
  número que justifica que la temporalidad se registre (§ 3.4).

**Con un año**

- **Un origen que se repite deja de ser una reparación y pasa a ser un cambio de producto.**
  Sale de agrupar por origen y componente, no de que alguien lo haya declarado (§ 5.3).
- Reincidencia por equipo: el mismo hallazgo en el mismo número de serie en visitas
  distintas.

### 12.1 Lo que NO se puede calcular, y hay que decirlo

**MTBF por subsistema.** Se propuso y no es calculable con estos datos. El MTBF necesita las
horas de operación de **toda la flota, incluidos los equipos que no fallaron**, y al taller
solo llegan los que se rompieron: el que anda bien nunca entra. Cualquier MTBF salido de acá
va sesgado hacia abajo, y por un factor que nadie puede estimar.

Es el mismo problema de denominador que apareció con `numero_en_visita`. Un número que parece
dato y no lo es hace más daño que no tenerlo.

---

## 13. Fuera de alcance

- **Instancias de componentes** — que el sistema sepa que *este* ROV tiene cuatro motores y
  cuál es cuál. Es lo que haría falta para registrar cuál luz está apagada o cuál cámara
  falló, y arrastra también el joystick y el cilindro fuente. Sesión de diseño propia; ver
  [`../pendientes.md`](../pendientes.md).
- **Fotos de los hallazgos** — ya estaba anotado, deliberadamente al final.
- **Qué proveedor** cuando el origen es *pieza de proveedor*. Sería accionable —saber a quién
  dejar de comprarle— pero se decide después de ver si `pieza_proveedor` se usa.
- **Mediciones eléctricas estructuradas** (corriente, voltaje) como evidencia numérica. Hoy
  van en el detalle del hallazgo.
- **Cerrar el quick-create de catálogos** en hallazgos y componentes (§ 7.4).
- **Un modelo de porqués numerados** encima del texto del § 5, si el texto libre resulta
  insuficiente después de usarlo.

---

## 14. Verificación

### 14.1 Tests

| Caso | Espera |
|---|---|
| Orden con dos síntomas y dos sospechas | Ambos se guardan; ninguno se pisa |
| Cerrar una orden con una línea sin origen | `UserError` que nombra la línea por componente y acción |
| Cerrar con origen `desconocida` | Se cierra: «No determinado» es respuesta válida (§ 4.5) |
| Cerrar una orden **sin ninguna línea** de trabajo | Se cierra: una visita de diagnóstico no registra trabajos (§ 4.6) |
| Cerrar con `analisis_causa` vacío | Se cierra: el análisis no bloquea nunca (§ 5.1) |
| Guardar una línea sin origen, sin cerrar la orden | Se guarda: la exigencia es del cierre, no del modelo |
| Sospecha y hallazgo sobre el mismo componente | La comparación los relaciona sin traducir (§ 3.2) |
| Catálogo de síntomas con `active = False` | No aparece al elegir **ni en la orden**; el enlace sigue y se lee con `active_test=False` (§ 6.4) |
| `display_name` de una línea | Nombra componente y acción, no `mc.rov.linea.falla,42` |
| El error nombra solo las líneas que faltan | Con dos líneas y una completa, la completa no aparece |
| `linea_falla_cierre_ids` | Devuelve exactamente las mismas líneas que `linea_falla_ids` |
| Los componentes que los síntomas nombran | Luces, sonar y manipulador existen y no son inspeccionables |

El módulo va en 153 tests; estos suman sobre esa base. Uno existente cambia:
`test_mc_rov_revision.py` crea una línea con `causa_raiz: "corrosion"` y pasa a `origen`.

**La migración no lleva tests, y es a propósito.** Ninguna de las trece migraciones del módulo
los tiene: corren contra la base al actualizar, fuera de la transacción de los tests, y un
test que simulara la columna vieja estaría probando el simulacro. Lo que la verifica es la
auditoría previa del § 11 contra el conteo posterior del § 14.2 — números reales de
producción, no un caso construido.

### 14.2 A mano, después de desplegar

1. Abrir una orden: el bloque de recepción se ve **sin entrar a ninguna pestaña**.
2. Escribir «prof» en Síntomas → filtra a *No mantiene profundidad*. Escribir «depth» →
   la misma.
3. En Síntomas, escribir algo que no está en la lista → **no ofrece crearlo** (§ 7.4).
4. Filtro **«Sin síntoma registrado»**: devuelve las órdenes abiertas sin síntoma, y **no**
   las cerradas de antes del despliegue.
5. Cerrar una orden con trabajos sin origen → el error nombra cuáles.
6. En Trabajos realizados, abrir el desplegable de Origen → **las seis opciones se leen
   completas, con su paréntesis**. Es lo que decidió que la aclaración fuera a la etiqueta
   (§ 4.1).
7. Pestaña Resultado: el bloque «Por qué pasó» muestra una fila por trabajo y **no** deja
   agregar ni borrar filas.
8. `SELECT origen, count(*) FROM mc_rov_linea_falla GROUP BY origen;` contra los números de
   la auditoría previa (§ 11).

---

## 15. Correcciones durante el diseño

Se registran igual que en [`revision-tecnica.md`](revision-tecnica.md) § 1.1–1.4, porque el
razonamiento descartado vale tanto como el aceptado — y porque sin el motivo escrito, la
misma propuesta vuelve dentro de seis meses y hay que rehacer la discusión entera.

### 15.1 Descartado durante el diseño

| Se propuso | Por qué se descartó |
|---|---|
| Un catálogo de **mecanismos** | Ya era el hallazgo. «Rodamiento trabado» y «bloqueo mecánico» son el mismo hecho dos veces (§ 4). |
| Un campo de **nivel de confianza** (%) | Nadie lo calibra, y la ventana ya codifica la certeza (§ 2.1). |
| **Causas en porcentajes** (60/40) | Además de no calibrarse, obligaría a sumar 0,6 de una falla. |
| **Cuatro causas en columnas** (inmediata, intermedia, raíz, sistémica) | La «causa inmediata» *es* la falla física ya registrada: el mismo dato dos veces. |
| **`ambiente`** como origen | No existe un caso sin responsable: o se pasó un límite, o el límite estaba mal, o nunca se dijo (§ 4.2). |
| **«No responde un accesorio»** como entrada única | Tapaba tres fallas que mandan a mirar lugares distintos (§ 6.3). |
| **«Pierde señal»** como síntoma | Existía para lo dudoso, así que habría absorbido todo lo dudoso (§ 6.3). |
| **Un paso de hipótesis** entre diagnóstico y reparación | La hipótesis vive minutos en la cabeza del técnico y se resuelve en el hallazgo. El único caso que importa —no se determinó— es un valor de origen. |
| **Cinco campos de texto** para el 5 whys | La cantidad de eslabones varía; obligar a cinco produce relleno (§ 5.1). |

### 15.2 Corregido al contrastar el documento contra el código

Antes de escribir una línea se leyó el diseño completo contra el módulo. Lo que cambió:

| Decía | Dice ahora | Por qué |
|---|---|---|
| `origen` con `required=True` en el modelo, **y** un test de `UserError` al cerrar, **y** la ventana de Cierre | Validación en el `write` a `done`, sin `required` en el modelo | Las tres cosas eran incompatibles: con `required` la exigencia cae al guardar la línea, no al cerrar, y el test no se puede construir por ORM (§ 4.6). |
| `momento_falla`, Selection de 5 valores con default `no_se_sabe` | Retirado; tres entradas del catálogo de síntomas | El default volvía imposible la distinción que el propio campo pedía, y la temporalidad pasa el test de «¿lo vio o lo deduce?» (§ 3.4). |
| `mc.rov.causa.sistemica`, catálogo que nace vacío | Retirado entero | Enlazar el segundo caso con el primero exige memoria de patrones a través de meses. Eso lo hace una consulta, no una persona (§ 5.3). |
| «Ningún catálogo se edita desde donde se llena la ficha… la misma decisión de `19.0.12.0.0`» | La regla aplica solo a los campos nuevos, y se dice que en el resto no existe | En el módulo no hay un solo `no_create`; lo que se cerró en `19.0.12.0.0` fueron las líneas del checklist. El comentario de `mc_rov_menus.xml` decía lo contrario (§ 7.4). |
| La migración copiaba `causa_raiz` y movía dos casos | Además rellena las filas sin causa | `causa_raiz` nunca fue obligatorio; sin ese paso quedan filas en NULL, indistinguibles de un dato perdido (§ 11). |
| «Agrupar por causa raíz» en la vista de búsqueda, heredado de `pendientes.md` | Se retira | Desde `19.0.8.0.0` el campo vive en la línea; agruparlo por orden exigiría el campo derivado que el § 9 prohíbe. |
| El catálogo de componentes se daba por suficiente | Entran Luces, Sonar y Manipulador | Tres síntomas nombraban componentes que no existían, y el cruce *reportado vs real* se caía justo ahí (§ 3.2). |
| «Software de superficie» iba a entrar como cuarto componente | No entra | Apareció al escribir los datos: `comp_electronica` ya se llama «Electrónica / Software». El choque no era con el catálogo de software de la ficha técnica —ese es otro eje— sino dentro del propio catálogo de componentes (§ 3.2). |
| Los dos ejes «hallazgo → origen» se daban por unidos | § 9.1, con el camino de cruce y el respaldo | No viven en el mismo registro y el puntero que los une es opcional. |
| § 4.4 vivía solo en este documento | Cierra el `help` del campo | Si es «la condición de la que depende que todo lo demás sirva», tiene que leerla quien llena el campo. |
| «Archivar un síntoma: las órdenes viejas lo conservan» | Lo conservan en la tabla, **no en la lectura** | Lo destapó el test al correrlo: el ORM aplica `active_test` al leer un x2many, así que archivar una entrada muy usada hunde su conteo histórico y se ve igual que si hubiera dejado de ocurrir (§ 6.4). |
