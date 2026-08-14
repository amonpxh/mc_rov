# Diseño: el diagnóstico de fallas

> Estado: **acordado, sin implementar.** Versión objetivo `19.0.13.0.0` (bump de `X`: cambia
> datos existentes y lleva migración).

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

Cuatro eslabones, todos con clave foránea, todos agrupables. Un «5 whys» guardado como cinco
campos de texto sería peor: no se puede contar, y la cantidad de eslabones varía —a veces son
tres, a veces ocho— así que obligar a cinco produce relleno.

**Lo que falta no es la cadena. Es el primer eslabón (el síntoma) y la calidad del último
(la causa).**

---

## 2. Las tres ventanas

La idea que ordena dónde va cada campo: **cada dato tiene una ventana en la que es barato de
capturar, y fuera de ella es caro o imposible.** Un campo puesto fuera de su ventana queda
vacío o se adivina.

| Ventana | Qué la hace única | Qué se captura ahí |
|---|---|---|
| **Recepción** | Es la única vez que hay alguien a quien preguntarle. El cliente se va y no vuelve. | Síntomas · qué componente señala el cliente · cuándo ocurre · qué llegó con el equipo |
| **Diagnóstico** | Es la única vez que el equipo está abierto. Después se arma. | Pruebas · hallazgos · fotos *(pendiente)* |
| **Cierre** | Es el único momento en que se puede *afirmar* el origen. Antes es especulación. | Origen · causa sistémica |

Es la misma persona en los tres momentos — en Marine Connection el responsable de la orden
se hace cargo del trabajo completo. **Las ventanas son de tiempo, no de rol.** Por eso el
diseño no lleva estados intermedios, ni traspasos, ni permisos por rol.

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
- **El síntoma no bloquea.** Un síntoma vacío es honestamente vacío: no había nadie a quien
  preguntarle, o el que trajo el equipo no lo operó nunca. Obligar produciría inventos.

La consecuencia hay que aceptarla de frente: si el síntoma queda opcional, el análisis de
*reportado vs real* puede no tener nunca datos y nadie se entera. La salida no es obligar,
es **hacerlo visible**: un filtro «Sin síntoma registrado» en la lista de órdenes, igual que
el filtro «Ficha incompleta» que ya existe para los números de serie. El responsable lo ve y,
mientras el cliente siga siendo alcanzable, lo arregla.

---

## 3. Recepción: el síntoma y la sospecha

Son **dos campos distintos**, y separarlos es el punto entero del bloque.

```
Falla reportada        Se apaga sola después de un rato y a veces
                       no se ve nada.               ← texto del cliente, intacto

Síntomas               [Se apaga solo ×] [Imagen con ruido ×]
                                                    ← catálogo, múltiple

El cliente sospecha de [Umbilical ×]                ← catálogo de componentes, opcional

Cuándo ocurre          Después de un rato de uso ▾
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

### 3.3 Lo que sí se pierde, asumido a propósito

Si el cliente reporta **dos** síntomas y señala **dos** componentes, no queda registrado cuál
va con cuál. «Un motor no gira» + «sin imagen», sospechas *Motor* y *Cámara*: el sistema no
sabe que el motor va con el primero.

Arreglarlo exigiría que cada queja fuera una fila en vez de una etiqueta, y eso pesa justo
en el momento en que el cliente está esperando en el mesón. Para el análisis no cambia nada
—lo que se cuenta es *sospechó de X, resultó ser Y*— y la frase completa queda en el texto
libre. Es una decisión, no un descuido.

### 3.4 «Cuándo ocurre» es uno por orden, no uno por síntoma

El patrón es una propiedad **del relato del cliente**, no de cada queja: cuenta una historia
—«anduvo diez minutos y ahí se apagó y se fue la imagen»— y esa historia tiene un solo
tiempo. Partirlo modelaría algo que el cliente no dijo por separado.

Lleva un valor **«No se sabe» explícito**, y es el valor por defecto. «El que trajo el equipo
no era el piloto» es información —dice que ese reporte vale menos— y tiene que distinguirse
de «nadie preguntó». Acá el valor explícito sí corresponde, porque a diferencia del checklist
no hay ninguna confirmación que garantice la distinción de otro modo.

---

## 4. El origen

Reemplaza a `causa_raiz`, que mezclaba dos preguntas: *qué le pasó físicamente* y *de quién
es el problema*. Dos de sus seis valores —`corrosion` y `accidente`— no eran causas raíz en
absoluto, y esa es la mejor evidencia de que el campo estaba mal planteado.

**El mecanismo no necesita campo propio: ya es el hallazgo.** «Rodamiento trabado» (hallazgo)
y «bloqueo mecánico» (mecanismo) son el mismo hecho dicho dos veces. El catálogo de hallazgos
existe, tiene familias y está en uso. Se evaluó crear un catálogo de mecanismos y se
descartó por eso.

Entonces la cadena tiene dos ejes, no tres:

> **qué encontraste** (hallazgo) → **por qué pasó** (origen)

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

No se arregla con software. Se arregla con que quede dicho desde el principio que el campo
existe para mejorar el producto y no para buscar culpables. **Es la condición de la que
depende que todo lo demás sirva**, y por eso está escrita acá.

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

---

## 5. Las causas sistémicas

Cuando la conclusión no es sobre *ese* equipo sino sobre el modelo —«este sello no sirve en
agua con sedimento»— hoy queda escrita dentro de la orden de ese equipo. Al siguiente equipo
se vuelve a escribir con otras palabras, y nunca se sabe que se dijo diez veces.

`origen = diseño` permite contar **cuántas** fallas son de diseño. No dice **cuáles**: diez
órdenes marcadas así pueden ser diez problemas distintos o uno repetido diez veces, y esas
dos situaciones piden cosas opuestas.

### 5.1 Nace vacío y crece por uso

Se evaluó posponerlo hasta tener volumen y se descartó: si no existe desde ya, se pierden los
primeros cien casos y después hay que ir a minarlos del texto.

Pero tampoco se define ninguna categoría por adelantado. **El catálogo se crea ahora, vacío.**
Cuando el mismo problema aparece por segunda vez, *ese* es el momento de crear la entrada y
enlazar los dos casos.

Así no hay categorías inventadas hoy ni ejercicio de minería después. Y es lo contrario del
scope creep: crece una entrada por cada hallazgo real repetido.

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
manual) · No sube o se queda en el fondo · No mantiene profundidad *(depth hold)* · No se
estabiliza *(stabilize)*

**Video** — Sin imagen · Imagen con ruido o intermitente · El tilt de la cámara no responde

**Comunicación** — Pierde conexión con superficie · Conectado pero no responde · El software
de superficie falla

**Sensores** — Un sensor marca mal o no marca

**Accesorios** — Luces no encienden · Manipulador no responde · Sonar no funciona

**Físico** — Entró agua · Fuga de aceite · Hace ruido o vibra raro · Daño físico visible

**Otro**

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

Y **«Falla intermitente» no es un síntoma**: es el campo «cuándo ocurre». Tenerlo en los dos
lados haría que el mismo hecho se registrara de dos formas y ninguna quedara confiable.

### 6.4 «Otro» se queda

Aunque parezca redundante con el texto libre. Marcarlo explícitamente dice *«preguntamos y no
estaba en la lista»*, que es distinto de que nadie clasificó. **Si «Otro» empieza a aparecer
seguido, es la señal de que a la lista le falta una entrada.**

---

## 7. Catálogos y listas después de este cambio

### 7.1 Catálogos — se editan desde Configuración, sin desplegar

| Catálogo | Dónde se administra | Estado |
|---|---|---|
| Componentes ROV | Reparaciones → Config → Catálogos ROV | existe |
| Subtipos | dentro de cada componente | existe |
| Acciones | Reparaciones → Config → Catálogos ROV | existe |
| Tipos de intervención | ídem | existe |
| Pasos de testeo | ídem | existe |
| Hallazgos | ídem | existe |
| **Síntomas** | ídem | **nuevo** |
| **Causas sistémicas** | ídem | **nuevo, nace vacío** |
| Software de superficie | Inventario → Config → Catálogos ROV | existe |
| Controladores de vuelo | ídem | existe |

De ocho a diez, no a once: **el mecanismo no necesitó catálogo propio porque ya era el
hallazgo.**

### 7.2 Listas en código — cambiarlas exige desplegar

| Lista | Dónde | Estado |
|---|---|---|
| **Origen** (6) | línea de trabajo | **nueva**, reemplaza `causa_raiz` |
| **Cuándo ocurre** (5) | orden de reparación | **nueva** |
| **Familia de síntoma** (8) | catálogo de síntomas | **nueva** |
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

### 7.4 Ningún catálogo se edita desde donde se llena la ficha

Ni el técnico en la revisión, ni quien recibe el equipo en el mesón. Todos se administran
desde Configuración. Es la misma decisión que se tomó con los chequeos en `19.0.12.0.0`: si
se puede agregar al vuelo, en dos meses hay cuatro maneras de escribir «no enciende» y el
conteo se muere.

---

## 8. El flujo completo

### Momento 1 — Recepción · orden de reparación

| Campo | Catálogo |
|---|---|
| Falla reportada | ninguno — texto del cliente, intacto |
| Síntomas | **Síntomas** |
| El cliente sospecha de | **Componentes** |
| Cuándo ocurre | lista en código |
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
| **Origen** | lista en código |
| **Causa sistémica** | **Causas sistémicas**, opcional |

Los repuestos van por la pestaña de Odoo, con productos de inventario.

### Momento 4 — Cierre

Segunda revisión si se probó de nuevo · tipo de intervención obligatorio · observaciones de
salida, que es lo único que ve el cliente.

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
                     Origen  →  Causa sistémica
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

Para el pipeline: **el grano es `mc.rov.linea.falla`.**

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
`accesorios` · `fisico` · `otro`.

### 10.2 `mc.rov.causa.sistemica` — catálogo de causas sistémicas *(nuevo, sin datos semilla)*

```
name         Char     required
descripcion  Text     el caso concreto, en palabras
sequence     Integer  default 10
active       Boolean  default True
```

### 10.3 `repair.order` — campos nuevos

```
sintoma_ids               M2m mc.rov.sintoma
                          relation mc_rov_repair_order_sintoma_rel
componente_sospechado_ids M2m mc.rov.componente
                          relation mc_rov_repair_order_sospecha_rel
momento_falla             Selection, default 'no_se_sabe'
```

Los nombres de tabla van explícitos, igual que en `tipo_intervencion_ids`, para que la
migración pueda escribir en ellas.

`MOMENTOS`: `siempre` («Siempre, desde que ocurrió») · `intermitente` («Va y viene») ·
`tras_uso` («Después de un rato de uso») · `una_vez` («Pasó una sola vez») · `no_se_sabe`
(«No se sabe»).

### 10.4 `mc.rov.linea.falla` — cambios

```
causa_raiz  →  origen             Selection, required, ver § 4.1
               causa_sistemica_id M2o mc.rov.causa.sistemica, ondelete set null
```

`origen` es **el único campo obligatorio de todo este diseño** (ver § 4.5).

### 10.5 Vistas

- **Orden de reparación** — el bloque de recepción va junto a `falla_reportada`, no en una
  pestaña. Es lo primero que se ve al abrir la orden, que es cuando el cliente está delante.
- **Vista de búsqueda de `repair.order`** — filtro **«Sin síntoma registrado»** (§ 2.2).
  Entra junto con los filtros por tipo de intervención que ya estaban pendientes.
- **Trabajos realizados** — `origen` reemplaza a `causa_raiz` en la columna. `causa_sistemica_id`
  entra como columna `optional="hide"`: se usa poco y no debe estorbar.

---

## 11. Migración `19.0.13.0.0`

**Todo en `pre-migrate.py`**, para que los datos declarados en XML ganen después.

```sql
-- 1. La columna nueva se crea a mano: el ORM crea columnas después del pre-migrate,
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

ALTER TABLE mc_rov_linea_falla DROP COLUMN IF EXISTS causa_raiz;
```

Las claves `falla_fabricacion`, `mal_uso`, `desgaste` y `desconocida` se reutilizan tal cual,
así que **solo dos casos se mueven**.

**Auditoría previa, en `odoo_prod` y de solo lectura:**

```sql
SELECT causa_raiz, count(*) FROM mc_rov_linea_falla GROUP BY causa_raiz;
```

**Y una revisión a mano que no puede hacer el script:** las filas que hoy dicen
`falla_fabricacion` — ¿se referían a *nosotros* o a *el proveedor*? Con el volumen actual se
miran una por una. Si alguna era del proveedor, se corrige a `pieza_proveedor` después de
desplegar.

---

## 12. Qué análisis habilita

**Desde el primer mes**

- *Reportado vs real*: de qué componente sospechó el cliente contra dónde estuvo el hallazgo.
- Cuántas órdenes llegan sin ningún diagnóstico del cliente.
- Qué síntomas llegan más seguido, por familia.

**Con algunos meses**

- Distribución de orígenes: cuánto es nuestro y cuánto del cliente.
- **Un hallazgo frecuente que ninguna prueba detecta** → falta un chequeo en el checklist.
- **Un hallazgo que nunca tiene trabajo asociado** → se está mirando algo que no se arregla.
- Qué síntoma predice qué hallazgo: el valor diagnóstico de cada queja.

**Con un año**

- **Un origen que se repite deja de ser una reparación y pasa a ser un cambio de producto.**
  Ahí es donde el catálogo de causas sistémicas se llena solo.
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

---

## 14. Correcciones durante el diseño

Se registran igual que en [`revision-tecnica.md`](revision-tecnica.md) § 1.1–1.4, porque el
razonamiento descartado vale tanto como el aceptado.

| Se propuso | Por qué se descartó |
|---|---|
| Un catálogo de **mecanismos** | Ya era el hallazgo. «Rodamiento trabado» y «bloqueo mecánico» son el mismo hecho dos veces (§ 4). |
| Un campo de **nivel de confianza** (%) | Nadie lo calibra, y la ventana ya codifica la certeza (§ 2.1). |
| **Causas en porcentajes** (60/40) | Además de no calibrarse, obligaría a sumar 0,6 de una falla. |
| **Cuatro causas en columnas** (inmediata, intermedia, raíz, sistémica) | La «causa inmediata» *es* la falla física ya registrada: el mismo dato dos veces. |
| **`ambiente`** como origen | No existe un caso sin responsable: o se pasó un límite, o el límite estaba mal, o nunca se dijo (§ 4.2). |
| **«No responde un accesorio»** como entrada única | Tapaba tres fallas que mandan a mirar lugares distintos (§ 6.3). |
| **«Pierde señal»** como síntoma | Existía para lo dudoso, así que habría absorbido todo lo dudoso (§ 6.3). |
| **Posponer** las causas sistémicas hasta tener volumen | Se perderían los primeros cien casos. Nace vacío y crece por uso (§ 5.1). |
| **Un paso de hipótesis** entre diagnóstico y reparación | La hipótesis vive minutos en la cabeza del técnico y se resuelve en el hallazgo. El único caso que importa —no se determinó— es un valor de origen. |
