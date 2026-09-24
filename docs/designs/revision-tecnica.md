# Diseño: la revisión técnica

**Versión objetivo:** implementado en `19.0.8.0.0` … `19.0.11.0.1` — `19.0.6.x` y `19.0.7.x` se ocuparon en la ficha de
fabricación, que se adelantó por ser corta e independiente
**Estado:** **aprobado por Paulo el 2026-08-12.** Listo para implementar
**Fecha:** 2026-08-11, reescrito el mismo día (§ 1.1) y ampliado el 2026-08-12 (§ 16)

---

## 1. El problema

En el taller llenan a mano una **ficha de reparación**. Registra principalmente *qué se
probó*: inspección física, esfuerzo, presión, leak, navegación, video, sistema, luces. Y
al final, **todos los hallazgos caen en un campo de observaciones en texto libre.**

Eso hace imposible el análisis de patrones sin leer los párrafos uno por uno. No se puede
preguntar *cuál es la falla más común del motor*, *cuántos equipos llegan intervenidos por
terceros*, ni *qué hallazgo predice una falla posterior*.

El módulo ya tiene **la mitad buena de la solución**. `mc.rov.linea.falla` registra
componente + subtipo contra catálogos configurables — esa era la idea correcta desde el
principio. Lo que falta es una sola cosa:

> El modelo guarda `accion_id`, que es **lo que se hizo**. No tiene ningún campo para **lo
> que se encontró**. Se llama `linea.falla` y no guarda ninguna falla.

Por eso todo termina en observaciones: no hay otro lugar donde ponerlo.

### 1.1 Corrección de alcance

Una versión anterior de este documento proponía **mover 24 campos de `stock.lot`** al
revisión, argumentando que repetir las pruebas sobrescribía los valores anteriores.

**Era falso, por dos razones independientes:**

1. Esos campos son la **ficha técnica de fabricación** de un equipo nuevo. Otra hoja, otro
   departamento, otro momento. La ficha de reparación es una cosa distinta.
2. Los resultados de una reparación **nunca se escriben ahí** — van al texto libre. No hay
   nada que se esté sobrescribiendo.

El error de origen fue no preguntar de cuál de las dos fichas venían esos campos, y esa
pregunta decidía todo el diseño.

**`stock.lot` queda completamente fuera del alcance: cero campos movidos, cero columnas
eliminadas, cero cambios en la ficha técnica, ninguna migración de mediciones.**

### 1.2 Corrección de nombre

Este diseño se implementó llamando **«protocolo»** al registro, y se renombró a **«revisión
técnica»** en `19.0.11.0.0`.

*Protocolo* significa **procedimiento**, y el registro no es el procedimiento — el
procedimiento es el catálogo de pasos de testeo (§ 5.3). Lo que se crea en cada visita es el
**resultado de ejecutarlo**.

El nombre alcanzó a causar una confusión real antes de corregirse: *"¿no debería ser siempre
el mismo?"*. Y la respuesta es que sí — el **procedimiento** es siempre el mismo; el registro
lleno no.

*Revisión técnica* se eligió porque en Chile el modelo mental ya existe: una batería
estandarizada y periódica sobre un vehículo, cuyo resultado es aprobado / aprobado con
observaciones / rechazado, que deja un documento y un historial por unidad. Coincide hasta
en los tres resultados, que ya estaban implementados con esos nombres.

### 1.3 Corrección de alcance: una revisión por visita, no dos

El diseño original partía cada visita en **dos** revisiones, una de *recepción* y una de
*entrega*, con el argumento de que comparar ambas era la evidencia de que el trabajo sirvió.
Se retiró en `19.0.12.0.0`: `tipo` pasó a **fabricación / reparación / terreno**.

El argumento era correcto y aun así la decisión estaba mal, porque **suponía que las dos
fichas se iban a llenar**. La hoja de papel que esto reemplaza es *una* por equipo reparado.
Pedir dos no produce dos fichas: produce una llena y otra vacía, y no hay forma de saber
cuál de las dos quedó vacía en cada visita. Una comparación entre un registro real y uno en
blanco no es una comparación.

**Lo que se pierde, dicho explícitamente:** ya no queda registrado dentro de una misma orden
el estado *antes* y *después* del trabajo. Lo reemplazan dos cosas:

1. **La comparación entre visitas.** La revisión de esta visita contra la de la anterior —
   que además es el intervalo que le interesa al análisis de fallas, porque entre medio el
   equipo voló.
2. **El botón «Nueva revisión»**, para el caso que sí ocurre: se prueba, se arregla, se
   vuelve a probar. Ahí las dos revisiones existen porque alguien tuvo una razón para
   crearlas, no porque el sistema las exigiera. `numero_en_visita` distingue cuál es cuál.

La pestaña Revisiones de la orden también ofrece **«Imprimir ficha»**. Abre el mismo
asistente de la revisión: propone la revisión de reparación más reciente de la visita
por fecha e ID y deja al usuario elegir otra cuando corresponda.
El selector solo acepta revisiones de esa orden y el PDF conserva la marca BORRADOR cuando
corresponde.

**Consecuencia que hay que vigilar:** el estado de los sellos ahora se registra en la única
revisión de la visita, y debe ser siempre **el estado con que llegó el equipo**. Antes lo
garantizaba el tipo del registro; ahora lo garantizan la etiqueta del campo («Estado del
sello al recibir») y el aviso de la pestaña. Si alguien anota ahí un sello que rompió el
propio taller durante el trabajo, `manipulacion_externa` cuenta trabajo propio como
intervención de terceros — es el único dato del modelo que se puede dar vuelta por llenarlo
en el momento equivocado.

### 1.4 «No lo tiene» pasa a «No aplica»

La etiqueta de `no_lo_tiene` —en chequeos y en sellos— se cambió a **«No aplica»** en
`19.0.12.0.0`. La clave técnica no cambió, así que no hubo migración de datos.

Este documento defendía lo contrario: que «No aplica» no distingue *el equipo no lo tiene*
de *no lo revisamos*, y que perder esa distinción arruina el denominador de cualquier
estadística. El argumento se cayó por donde no se había mirado: **«no lo revisamos» no es un
valor, es el campo vacío**, y un chequeo vacío impide confirmar la revisión. La distinción
estaba garantizada por otra vía desde el principio; lo único que hacía la etiqueta larga era
nombrar mal el caso de un componente que existe pero no corresponde revisar.

---

## 2. Las dos fichas

No confundirlas es lo más importante de este documento.

| | Ficha técnica de fabricación | Ficha de reparación |
|---|---|---|
| Qué describe | Cómo **es** el equipo | Qué **pasó** en una visita al taller |
| Dónde vive | `stock.lot` (número de serie) | **no existe en el sistema** |
| Quién la llena | Manufactura, al fabricar | El taller, en cada visita |
| Cada cuánto | Una vez; se actualiza si el equipo se modifica | Cada vez que el equipo entra |
| Este diseño la toca | **No** | Es todo el alcance |

---

## 3. Decisiones tomadas

| Decisión | Elección |
|---|---|
| `stock.lot` | **Fuera de alcance.** No se toca |
| Relación con la orden de reparación | `repair_id` **opcional** — "técnico que fabrica y/o repara" |
| Responsable | `hr.employee`, no `res.users` — 3-4 logins para no pagar suscripciones |
| Hallazgos | Catálogo obligatorio; el texto libre deja de ser el registro |
| Chequeos que crecen (6DOF, sonar…) | Catálogo configurable, sin desplegar |
| Corridas con dos umbilicales | Modelo de línea propio (§ 5.2) |
| Resultado de la prueba de esfuerzo | Binario + **duración** |
| Responsable en la línea de trabajo | **Sí** — es el único campo que no se puede retrofitear |
| `resultado` de la revisión | **Derivado, no forzable** — un override sería el texto libre en otra forma |
| Chequeos de algo que el equipo no lleva | Se muestran todos y se responden ***No lo tiene***, que afirma algo del equipo y no del técnico |
| Cliente vs dueño en la revisión | Ninguno propio: ambos derivados |
| Firma / aprobación con nombre | Se posterga; `estado: confirmado` es la aprobación por sistema |
| Fotos de hallazgos | Se implementan al final, con `fields.Image` (§ 12) |
| Ficha de papel como fuente | **No.** El diseño se hizo sin verla, a propósito |
| `item_2` … `item_5` | Se eliminan — 0 de 10 órdenes los usaron |
| Fabricación y reparación | **No corren la misma batería** — el catálogo de chequeos declara a qué tipos aplica cada uno (§ 5.3.1) |
| ¿Se hacen todas las pruebas siempre? | **Sí**, confirmado por el taller. *No lo tiene* queda solo para componentes ausentes |

---

## 4. Qué contiene la ficha de reparación

Inventario cerrado con Paulo. Es lo que hacen hoy.

**Cabecera:** responsable (técnico que fabrica y/o repara), fecha, modelo del ROV, N° de
serie, cliente/dueño.

**Inspección física** — para saber si alguien más aparte de ellos intervino el equipo. Se
revisa en E-pod, cilindro fuente, motores, consola y joystick si hay **marcas de plumón,
sellos antiguos o sellos nuevos**.

**Pruebas:**

| Prueba | En qué consiste | Depende del cable |
|---|---|---|
| Esfuerzo | El ROV funcionando en un bin con agua, 1 a 1½ horas o más, para ver si algo falla — típicamente los motores | **sí** |
| Presión | Si el equipo está bien sellado, usando el sensor de presión | no |
| Leak | Si el sensor de leak funciona | no |
| Navegación | Hélices en posición correcta, movimiento vertical, movimiento horizontal | no |
| Video | Cámara y tilt | no |
| Sistema | Ancho de banda, subida, bajada | **sí** |
| Luces | Cantidad de internas, externas y total | no |

**Observaciones finales:** los hallazgos, en texto libre. Esto es lo que el diseño cambia.

### 4.1 El umbilical como muestra de control

Normalmente se prueba con **el cable con el que viene el equipo**. Si viene sin cable, se
usa el **umbilical de prueba estándar**. Y a veces se prueba con **ambos**, para ver si el
umbilical propio tiene algo o si hay comportamiento que varíe con el largo: el de prueba
funciona como **muestra de control**.

Cuando eso pasa, las pruebas que dependen del cable —esfuerzo y sistema— **se hacen dos
veces**. Las demás se hacen una sola vez. La primera corrida siempre existe.

Ahí está el diagnóstico de mayor valor de toda la ficha, y hoy no se puede sacar de ella:
mismo ROV, mismo banco, distinto cable. **Si el ancho de banda solo cae con el umbilical
propio, el problema es el cable y no el vehículo.**

---

## 5. Modelo de datos

Seis modelos nuevos: una cabecera, tres modelos de línea, dos catálogos.

### 5.1 `mc.rov.revision` — la ficha

```
name              Char       secuencia PROT/00001, readonly
lot_id            M2o stock.lot        required, index
repair_id         M2o repair.order     opcional, index, ondelete set null
tipo              Selection  fabricacion | recepcion | entrega | terreno   required
fecha             Date       required, default hoy
responsable_id    M2o hr.employee      default env.user.employee_id
estado            Selection  borrador | confirmado                          default borrador
horas_operacion   Float h    lectura del horómetro, si el equipo tiene
```

**`horas_operacion` es el dato de mayor apalancamiento del modelo, y es opcional.** Solo
algunos ROV traen horómetro. Se anota **la lectura**, no un acumulado calculado, y en cada
visita: lo que sirve para análisis es el **delta entre dos revisiones consecutivos** — las
horas que el equipo voló entre una visita y la siguiente. Es el denominador que le falta a
cualquier cálculo de confiabilidad, porque un equipo que bucea ocho horas diarias y uno
guardado en bodega acumulan el mismo tiempo de calendario.

Verificación gratis: como la prueba de esfuerzo corre el ROV 1 a 1½ horas, la lectura del
revisión de entrega menos la de recepción debería dar aproximadamente las horas de prueba
de esa visita.

**`repair_id` es opcional a propósito.** Un ROV nuevo pasa por el mismo revisión antes de
despacharse y ahí no hay orden de reparación. Si la revisión colgara de la orden, toda la
fabricación quedaría fuera del análisis.

**`tipo` con recepción y entrega** permite probar al recibir, arreglar, y volver a probar
antes de entregar. Dos revisiones, misma visita; la comparación entre ambos es la evidencia
de que el trabajo sirvió.

**La revisión de recepción es la actividad de diagnosticar.** Tres niveles que conviene no
mezclar:

| Cosa | Qué es | Nombre |
|---|---|---|
| La lista de qué se prueba siempre | catálogo configurable | pasos de testeo estándar (`mc.rov.chequeo`) |
| El registro de haberlos corrido un día | el documento | revisión técnica (`mc.rov.revision`) |
| Para qué sirve al recibir el equipo | el propósito | diagnóstico |

El registro no se puede llamar "diagnóstico" porque la misma batería se corre **antes de
entregar**, y ahí no diagnostica: verifica.

`tipo_diagnostico` (tipo de intervención) no cambia: sigue siendo el tipo de **visita**. Una
visita de solo diagnóstico produce una revisión de recepción con hallazgos y **cero líneas
de trabajo** — su resultado completo, que hoy no queda registrado en ninguna parte.

**`estado`** existe para llenar la ficha por partes. En `borrador` se guarda incompleta; al
confirmar se valida que todos los chequeos estén respondidos y el registro queda en solo
lectura. Sin eso, un checklist a medio llenar no se distingue de uno completo.

**`responsable_id` no es `required` a nivel de modelo, sí en la vista.** Un empleado ficticio
tipo "Sin registrar" ensuciaría la lista de empleados para siempre.

Derivados, sin columna propia:

```
product_id       related lot_id.product_id            readonly   el modelo del ROV
propietario_id   related lot_id.mc_propietario_id     readonly   el dueño registrado
partner_id       related repair_id.partner_id         readonly   quién paga esta visita
es_un_rov        related lot_id.es_un_rov             readonly
```

**Cliente vs dueño:** la revisión no lleva contacto propio. `propietario_id` es de quién es
el equipo (dura años); `partner_id` es a quién se factura esta visita. Un tercer contacto
aquí reabriría la confusión que se cerró en `19.0.5.0.0`.

Mediciones que **no** dependen del cable:

```
--- luces ---
luces_internas    Integer
luces_externas    Integer
luces_total       Integer   computed, internas + externas
luces_ficha       Integer   related lot_id.mc_cantidad_luces, readonly
luces_difieren    Boolean   computed, total != ficha

--- condiciones ---
temperatura_interior   Float °C
temperatura_exterior   Float °C

--- solo cuando tipo = terreno ---
lugar                  Char
profundidad            Integer m
velocidad_corriente    Float knots
```

`luces_difieren` compara el conteo de la prueba contra la especificación del equipo: si
debería tener 6 luces y se contaron 4, el sistema lo dice. Es **la única lectura que este
modelo hace de la ficha técnica**, y es de solo lectura.

Líneas y resumen:

```
corrida_ids    O2m mc.rov.revision.corrida
chequeo_ids    O2m mc.rov.revision.chequeo
hallazgo_ids   O2m mc.rov.revision.hallazgo
resultado      Selection  aprobado | aprobado_con_observaciones | rechazado   computed, store
```

`resultado`, en orden de precedencia:

1. Algún chequeo en `no_ok`, alguna corrida con esfuerzo `con_problemas`, o algún hallazgo
   con severidad `impide_operar` → **rechazado**
2. Algún hallazgo → **aprobado con observaciones**
3. Si no → **aprobado**

### 5.2 `mc.rov.revision.corrida` — una pasada con un umbilical

```
revision_id          M2o mc.rov.revision    required, ondelete cascade
sequence              Integer
umbilical             Selection  equipo | prueba          required
largo                 Float m                             required
alimentacion          Selection  UPS | Generador | Transformador
tension_salida        Integer V

--- esfuerzo ---
esfuerzo_duracion     Float h
esfuerzo_resultado    Selection  ok | con_problemas

--- sistema (ancho de banda) ---
subida                Float Mbps
bajada                Float Mbps
```

**No hay un campo `ancho_banda`.** "Ancho de banda" es el nombre de la prueba, no una tercera
medición: lo que se mide es la velocidad de **subida** y de **bajada**, ambas en Mbps. En la
ficha de fabricación existe un `mc_ancho_banda` de texto que sí es otra cosa — un valor
nominal— y que no se toca, porque esa ficha está fuera de alcance.

Existe porque **el umbilical es una condición de la corrida, no un dato de una prueba**.
Normalmente hay una sola línea, con el cable del equipo. Hay dos cuando usan el de control,
y entonces la comparación entre líneas aísla el cable como fuente de falla.

Lo que **no** depende del cable se queda en la revisión y se hace una sola vez, aunque haya
dos corridas: repetir la inspección física dos veces no aporta nada.

**`esfuerzo_duracion` es el campo que hoy no existe y más vale.** El resultado de la prueba
es binario —pasó o presentó problemas— pero *cuánto aguantó* es información distinta y
comparable: "aguantó 90 minutos" y "falló a los 15" hoy quedan registrados igual, o sea, no
registrados. Si falló, la duración es tiempo hasta la falla; si pasó, es la fuerza de la
evidencia. Es la materia prima de cualquier análisis de confiabilidad.

### 5.3 `mc.rov.chequeo` — catálogo de pasos de testeo

```
name                Char       required
sequence            Integer
seccion             Selection  inspeccion_fisica | presion | leak | navegacion | video
                               | luces | otro
por_componente      Boolean    si la línea debe indicar sobre qué componente se hizo
aplica_fabricacion  Boolean
aplica_reparacion   Boolean    default True
aplica_terreno      Boolean
active              Boolean    default True
```

### 5.3.1 Fabricación y reparación no corren la misma batería

Los tres booleanos separan qué chequeos aparecen en cada tipo de revisión, y la generación
automática de líneas (§ 5.4) filtra por el `tipo` de la revisión.

**El caso que lo justificaba era la inspección física** — marcas de plumón, sellos ajenos,
tornillería cambiada: nadie busca huellas de terceros en un equipo que armó uno mismo la
semana pasada. Ese caso desapareció en `19.0.12.0.0` junto con el chequeo de marcas de
plumón (§ 7), y **hoy el catálogo semilla corre entero en los tres tipos**:

| Chequeos | fabricación | reparación | terreno |
|---|:---:|:---:|:---:|
| Presión, leak, navegación, video | sí | sí | sí |

Lo que separa a fabricación no son los chequeos sino la **inspección de sellos**, que se
genera solo en las revisiones de reparación (`TIPOS_CON_INSPECCION`).

**El mecanismo se conserva aunque no lo use nadie**, y eso es deliberado: es lo que permite
agregar un chequeo de terreno —profundidad máxima alcanzada, comportamiento con corriente—
sin que aparezca en toda ficha de taller. Los tests lo cubren con un chequeo creado en el
propio test, no con registros del catálogo, justamente porque el catálogo cambia sin
desplegar.

Son booleanos y no un modelo de tipos porque `tipo` es un `Selection` estable: los tipos de
revisión son la estructura del proceso, no un catálogo operativo. Es la misma distinción que
se hizo con `seccion`.

El mismo criterio ordena la navegación: el menú de revisiones se filtra por tipo, para que
el taller no tenga que mirar los de fabricación ni manufactura los de reparación.

Agregar *lateral*, *yaw*, *roll* o *pitch* para un equipo 6DOF es crear cuatro registros
desde `Reparaciones → Configuración`, no tocar código. Lo mismo para sonar, USBL o cualquier
chequeo de un modelo nuevo.

`seccion` sí es `Selection`, o sea que una **sección** nueva requiere código. Límite
deliberado: las secciones son la estructura de la ficha y son estables; los chequeos dentro
de ellas son operativos y cambian.

### 5.4 `mc.rov.revision.chequeo` — línea de chequeo

```
revision_id    M2o mc.rov.revision      required, ondelete cascade
sequence        Integer
chequeo_id      M2o mc.rov.chequeo        required
componente_id   M2o mc.rov.componente     required si chequeo_id.por_componente
resultado       Selection  ok | no_ok | no_lo_tiene
detalle         Char
```

**`resultado` cubre dos dimensiones con un campo**, porque la ficha de hoy registra
principalmente *qué se testeó* y no *qué resultó*:

| Valor | Significa |
|---|---|
| *(vacío)* | todavía sin responder — impide confirmar |
| **No aplica** | el equipo no lleva ese componente o no puede hacer eso |
| OK / No OK | se revisó, con resultado |

**«No aplica» afirma algo sobre el equipo, no sobre lo que hizo el técnico** — no todos los
ROV llevan joystick, y el «cilindro fuente» solo existe en los que tienen **dos e-pods en
vez de uno**. *No lo revisamos* no compite con este valor porque no es un valor: es el campo
vacío, que impide confirmar. Por eso el denominador de las estadísticas queda intacto: *de
los equipos que sí tienen joystick, ¿cuántos llegaron con corrosión?* sigue siendo
calculable. Ver § 1.4 para por qué este documento defendía antes lo contrario.

> **Refinamiento posible más adelante, no ahora:** si la ficha de fabricación registrara
> cuántos e-pods lleva el equipo y si tiene joystick, la revisión podría generar solo las
> líneas que corresponden, en vez de generarlas todas y hacer que alguien marque «No aplica»
> cada vez. Es mejor a la larga —el dato se declara una vez y no en cada visita— pero exige
> campos nuevos en la ficha de fabricación y que estén bien llenos. Con «No aplica» el
> análisis ya es correcto; esto solo ahorraría clics.

Las líneas se generan solas al crear la revisión, con todos los chequeos activos, y **el
técnico no las puede crear ni borrar**: se responden. Si pudiera agregar filas, la ausencia
de una fila dejaría de significar algo, que es todo lo que un checklist viene a garantizar —
*la cámara estaba bien* tiene que ser distinguible de *nadie miró la cámara*. El catálogo se
administra por fuera, en `Reparaciones → Configuración → Catálogos ROV → Pasos de testeo`.

`resultado` no es `required` en el campo — lo valida el paso a `confirmado`, para poder
guardar a medio llenar sin poder cerrar incompleto.

**Las líneas se copian del catálogo una sola vez, cuando la revisión nace.** Eso deja un
hueco que no es obvio: la revisión nace al salir la orden de borrador, o sea apenas el
equipo entra al taller, así que **todo equipo que hoy esté en el taller ya tiene su ficha**.
Un chequeo agregado al catálogo un martes no le llega a ninguno de ellos — solo a los que
entren después — y quien lo agregó no tiene cómo enterarse. Para eso está el botón
**«Actualizar checklist»** en la revisión en borrador, que trae las líneas que falten.

No se actualiza solo, a propósito. Una ficha a medio llenar que cambia de contenido sin que
nadie la toque es peor que una desactualizada: el técnico ya la recorrió entera y no la
vuelve a leer, así que la línea nueva es justo la que no va a ver. Que lo pida una persona
fija el momento en que la ficha cambia, y queda anotado en el chatter. El botón solo agrega
—`_generar_chequeos` nunca borra respuestas— y una revisión confirmada lo rechaza: una ficha
cerrada que crece deja de ser el registro de lo que se revisó ese día.

### 5.4.1 La pantalla se arma por secciones

`mc.rov.revision` expone **siete one2many hacia esta misma tabla**, uno por valor de
`seccion`, diferenciados solo por el dominio. No agregan columnas: son vistas de
`chequeo_ids`.

Existen porque la hoja de papel viene en bloques con título —*Prueba de video* con cámara y
tilt, *Prueba de navegación* con hélices y los dos movimientos— y se llena de arriba abajo.
La alternativa era una sola lista agrupada por sección, descartada porque un grupo hay que
desplegarlo antes de escribir dentro, y un checklist que exige clics previos se llena a
medias.

Cada bloque se esconde cuando su sección no trae chequeos para ese tipo de revisión: un
título con una lista vacía debajo se lee como algo roto.

**La sección `luces` es el caso especial:** no lleva chequeos de OK / No OK porque la prueba
de luces es un conteo —cuántas encienden—, y eso ya son `luces_internas`, `luces_externas` y
el total, que se compara solo contra la ficha del equipo. La sección existe para que el
bloque tenga título como los demás, y para dejar el catálogo abierto por si aparece algo que
un número no conteste.

Un test verifica que la unión de los siete campos sea exactamente `chequeo_ids`: una línea
que no caiga en ninguna sección es un chequeo que el técnico no ve nunca y que sin embargo
le impide confirmar.

### 5.5 `mc.rov.hallazgo` — catálogo de hallazgos

```
name       Char       required
familia    Selection  terceros | estanqueidad | estructura | electrico | funcional | otro
sequence   Integer
active     Boolean    default True
```

Este catálogo **es la pieza que falta hoy** y la razón de todo el diseño.

### 5.6 `mc.rov.revision.hallazgo` — línea de hallazgo

```
revision_id    M2o mc.rov.revision      required, ondelete cascade
sequence        Integer
componente_id   M2o mc.rov.componente     REQUERIDO
subtipo_id      M2o mc.rov.subtipo        domain [('componente_id','=',componente_id)]
hallazgo_id       M2o mc.rov.hallazgo     REQUERIDO
severidad         Selection  informativo | atencion | impide_operar   required, default atencion
chequeo_origen_id M2o mc.rov.revision.chequeo   opcional: qué chequeo lo destapó
detalle           Text                    complemento, nunca sustituto
```

**`chequeo_origen_id` es el que hace medible la detección** (§ 16.2). Sin él no se puede
saber si un hallazgo lo reveló un chequeo de la revisión o si alguien lo vio de casualidad —
y esa diferencia es la que dice si a la revisión le falta un chequeo. Cuesta un campo ahora y
es imposible de reconstruir después.

**Apunta solo a las líneas del checklist, y la inspección de sellos queda deliberadamente
afuera.** Un sello contesta *si alguien más abrió el equipo*, no *qué está fallando*, y además
ya registra su propio resultado en cada fila (`estado_sello`, `manipulacion_externa`), o sea
que es contable sin este puntero. Las líneas de chequeo son las que lo necesitan: por sí solas
dicen OK / No OK y nunca qué se encontró.

> **Consecuencia que hay que respetar al consultar:** los hallazgos de familia **`terceros`**
> —marca de plumón, sello no original, tornillería cambiada, componente no original— salen de
> la inspección física, así que van a tener este campo vacío casi siempre. Contados sin
> filtrar parecen un hueco en la batería, y no lo hay: los detectó la inspección de sellos.
> **La consulta de «chequeos que faltan» tiene que excluir esa familia.**
>
> No lleva una casilla propia en el catálogo de hallazgos para marcarlo: la respuesta ya vive
> en `familia`, y agregar un booleano que dice lo mismo es el patrón que este módulo ya se
> corrigió varias veces.

Reusa `mc.rov.componente` y `mc.rov.subtipo`, los mismos catálogos de las líneas de trabajo.
Eso es lo que permite correlacionar: *dónde* se encuentran los hallazgos y *dónde* se hacen
los trabajos hablan el mismo idioma.

### 5.7 Cambios en `mc.rov.linea.falla`

```
hallazgo_origen_id   M2o mc.rov.revision.hallazgo   opcional
responsable_id       M2o hr.employee                 quién hizo este trabajo
causa_raiz           Selection                       baja desde repair.order (§ 9)
```

**`responsable_id` en la línea y no solo en la cabecera**, porque dos técnicos pueden
trabajar la misma orden y cada línea ya lleva sus horas. Con él, las HH quedan atribuidas y
se puede costear por técnico o ver quién concentra qué tipo de trabajo. Se propone desde el
responsable de la revisión o el de la orden.

Es el único de los campos discutidos que **no se puede retrofitear**: agregarlo después deja
todas las líneas anteriores sin atribuir para siempre.

`hallazgo_origen_id` cierra el circuito:

```
revisión de recepción → hallazgo → línea de trabajo (acción + HH) → revisión de entrega
```

Se deja opcional: un trabajo puede surgir sin hallazgo previo, y un hallazgo puede quedar
sin resolver — que también es un dato.

---

## 6. Cómo se evita que el texto libre se coma los hallazgos

La estructura no gana por existir. Gana cuando el texto libre deja de ser el camino fácil.
Si se deja una caja de texto grande donde la costumbre pone los hallazgos, ahí van a seguir.

1. **`hallazgo_id` y `componente_id` son obligatorios.** Escribir un párrafo no es una
   opción disponible: no se puede guardar un hallazgo sin elegir del catálogo.
2. **`detalle` es complemento.** Existe para el matiz —"la trizadura arranca en el
   penetrador de babor"— no para el hallazgo. Siempre hay algo contable al lado.
3. **Cuando el catálogo no alcanza, se agrega al catálogo, no al detalle.** Se administra
   desde `Reparaciones → Configuración` sin tocar código, igual que componentes y acciones.
   Esa es la diferencia entre un catálogo vivo y uno decorativo.
4. **`observaciones_salida` deja de ser la caja de los hallazgos.** Hoy es un `Text` sin
   propósito declarado, justo donde la costumbre los pone. Pasa a tener destino explícito:
   **lo que se le informa al cliente en la entrega**, y sale en el PDF. Los hallazgos
   internos no van ahí.
5. **El uso de "Otro" es la señal de qué le falta al catálogo**, y es medible. Con texto
   libre no hay señal de nada.

---

## 7. Catálogos semilla

### Chequeos

| Sección | Chequeo | Por componente |
|---|---|---|
| Presión | Estanqueidad bajo presión | no |
| Leak | El sensor de leak responde | no |
| Navegación | Hélices en posición correcta | no |
| Navegación | Movimiento vertical | no |
| Navegación | Movimiento horizontal | no |
| Video | Imagen de cámara | no |
| Video | Tilt | no |

**Ninguno se hace por componente, y la sección «Inspección física» quedó vacía.** Las tres
entradas que tenía —marcas de plumón, sellos antiguos, sellos nuevos— se fueron por dos
caminos distintos:

- **Los dos de sellos** se reemplazaron por `mc.rov.revision.inspeccion` (§ 5.8): el sello
  tiene continuidad y estados, y eso necesita un modelo, no dos casillas.
- **Las marcas de plumón salieron de la batería en `19.0.12.0.0`.** Preguntarlas en los cinco
  componentes de toda revisión costaba cinco respuestas obligatorias por ficha y casi nunca
  decía nada. Ver una marca sigue siendo registrable como **hallazgo** —el catálogo lo
  conserva— que es lo que corresponde a algo que ocurre a veces.

La sección se queda en `SECCIONES` porque el bloque de la pantalla es lo que se llena
primero cuando el taller quiera volver a poner algo ahí, y porque el mecanismo
`por_componente` sigue existiendo para ese caso.

### Componentes que se agregan

`mc.rov.componente` hoy tiene Motor, Umbilical, Electrónica/Software, Estructura/Chasis,
Consola, Cámara, Sensor, Otro. La inspección física necesita además:

- **E-pod**
- **Cilindro fuente**
- **Joystick** — hoy existe solo como subtipo de Consola; sube a componente porque se
  inspecciona por separado

### Hallazgos

| Familia | Hallazgos |
|---|---|
| Intervención de terceros | Marca de plumón · Sello no original · Tornillería cambiada · Componente no original |
| Estanqueidad | Filtración · Sello vencido · O-ring dañado · Penetrador suelto |
| Estructura | Corrosión · Trizadura · Deformación · Soldadura rota |
| Eléctrico | Cable pellizcado · Conector dañado · Aislación deteriorada · Falso contacto |
| Funcional | No responde · Intermitente · Fuera de rango · Ruido anormal |

**No hay un hallazgo "Sin hallazgos".** Una revisión sin líneas de hallazgo ya significa que
no se encontró nada, y los chequeos respondidos son la prueba de que se miró. Tener las dos
formas de decirlo crearía registros ambiguos: una línea "sin hallazgos" junto a otra con un
hallazgo real no querría decir nada.

---

## 8. Vistas y navegación

| Dónde | Qué |
|---|---|
| `Reparaciones → Revisiones técnicas` | Lista y formulario (sin las de fabricación) |
| `Reparaciones → Configuración → Catálogos ROV` | Componentes, Acciones, Tipos de intervención, Pasos de testeo, Hallazgos |
| `Inventario → Configuración → Catálogos ROV` | Software de superficie y Controladores de vuelo — vocabulario de la ficha de **fabricación**, que vive en el número de serie |
| Botón inteligente en `stock.lot` | "Revisiones" con contador → el historial del equipo. **Único cambio en el lote, y es de solo lectura** |
| Página en `repair.order` | Las revisiones de esa visita, con `open_form_view` para poder abrirlas y seguir llenándolas |
| Reporte QWeb sobre `mc.rov.revision` | La versión digital de la hoja de papel, imprimible y adjuntable |

**Los dos «Catálogos ROV» son deliberadamente dos.** Los de reparación cuelgan de
Reparaciones y los de fabricación de Inventario, porque colgarlos todos del mismo menú
obligaba a manufactura a entrar al módulo de reparaciones para agregar un software.

El reporte también tapa un hueco actual: el técnico llena trabajos, causa raíz y
observaciones, y **nada de eso sale en un PDF** — el único documento imprimible es el
presupuesto por defecto de Odoo.

### 8.1 Las pestañas son el orden del trabajo *(19.0.14.0.0)*

Salió de mirar las dos pantallas juntas: **la barra de pestañas es lo que le dice al usuario
cuál es el proceso**, así que tiene que leerse de izquierda a derecha en el orden en que las
cosas ocurren. Donde no lo hacía, era porque las pestañas se habían agregado en el orden en
que se fueron implementando.

En la revisión pasan de cinco a tres:

| Antes | Ahora | Por qué |
|---|---|---|
| Corridas · Sellos · Pruebas · Hallazgos · Condiciones | **Sellos · Pruebas · Hallazgos** | |

- **Sellos va primera** porque se inspecciona **antes de tocar el equipo** — lo dice el aviso
  de esa misma pestaña. Estaba segunda, contradiciendo su propia instrucción.
- **Corridas se fusiona dentro de Pruebas.** La corrida no es una prueba: es *la condición
  bajo la cual se probó* —qué cable, qué alimentación, cuánto aguantó el esfuerzo—. Pero
  ocurre en la misma sesión, con el equipo encendido, y tenerlas separadas obligaba a saltar
  de pestaña en medio del trabajo. Adentro: las corridas arriba, las siete secciones del
  checklist debajo, y el bloque de terreno cuando el tipo lo pide.
- **Condiciones desaparece** como pestaña. Ver § 8.2.

En la orden de reparación, las pestañas pasan a ser los cuatro momentos del diagnóstico de
fallas, más las dos nativas:

> **Recepción · Diagnóstico · Reparación · Repuestos · Cierre · Notas**

- **Recepción** es nueva y se lleva los cuatro campos que estaban sueltos en la cabecera
  —falla reportada, síntomas, sospecha, equipos recibidos—, que además estaban repartidos
  entre las dos columnas y mezclados con los campos nativos de Odoo.
- **Diagnóstico** era *Revisiones*. Nombra el paso en vez del artefacto; la lista de adentro
  sigue diciendo «Revisión» en cada fila. **Es impreciso a propósito:** esa pestaña también
  guarda la segunda revisión, la de después de reparar, que no diagnostica sino que verifica.
  Se aceptó la imprecisión porque el 90% de las visitas lleva una sola revisión y es la
  diagnóstica, y porque la legibilidad del proceso vale más que el caso raro.
- **Reparación** era *Trabajos realizados*. Es la palabra del taller; «Corrección» se lee como
  corregir un error propio.
- **Cierre** era *Resultado*. Con el origen y el análisis adentro dejó de ser solo el
  resultado: es el acto de cerrar.

**Repuestos no se fusiona con Reparación**, aunque sean el mismo momento. Son dos modelos
haciendo dos cosas: uno es el *relato* del trabajo (componente, acción, horas), el otro el
*consumo material* que descuenta inventario y se factura. Meter la lista nativa de Odoo dentro
de una pestaña propia arrastra comportamientos que se rompen en la próxima actualización. Lo
que los ata de verdad no es el layout sino la validación del § 8.3.

**La regla que concilia las dos pantallas**, y que conviene tener escrita para no
«arreglarla» mal después: *lo derivado se lee arriba de las pestañas; lo que se llena va
adentro de una.* Por eso el `resultado` de la revisión —que se calcula solo— está en la
cabecera, y el cierre de la orden —donde se escribe el origen— es una pestaña.

### 8.2 La temperatura es de la corrida, no de la revisión *(19.0.14.0.0)*

`temperatura_interior` y `temperatura_exterior` estaban en `mc.rov.revision`, listadas en el
§ 5.1 bajo «mediciones que no dependen del cable». **Nunca hubo un argumento escrito para
ponerlas ahí**: se arrastraron, y la revisión de este diseño no encontró ninguna línea que las
justificara.

Ahora hay dos datos que sí deciden:

1. **Se mide una vez por corrida, no una por sesión** (confirmado por Marine Connection). Si
   se corre con el umbilical propio y después con el de prueba, son dos lecturas. Guardarlas
   en la revisión obligaría a elegir una o a promediarlas, y las dos cosas pierden justamente
   la comparación que hace útil la segunda corrida.
2. La temperatura **depende del cable**, que es lo contrario de lo que decía el § 5.1: la
   caída de tensión en un umbilical largo calienta. Estaba clasificada al revés.

Pasan a `mc.rov.revision.corrida`. En `odoo_prod` no había ninguna lectura registrada al
migrar, así que no hubo nada que repartir.

> **Restricción para el reporte PDF, y hay que respetarla:** la temperatura vuelve a medirse
> como **dato interno** y **no debe salir impresa**. Antes se le entregaba al cliente y el
> cliente la usó en contra. Es el primer caso concreto de lo que el § 12.1 anticipaba en
> abstracto — que el reporte obliga a decidir campo por campo qué es interno y qué se
> entrega.

### 8.3 Que no se registre el repuesto es un modo de falla, no un descuido *(19.0.14.0.0)*

Una línea de trabajo con acción «Cambio completo» y ninguna línea de producto significa que se
cambió una pieza y no quedó registrada: se pierde el vínculo con el lote y se corta el
análisis de fallas por componente. Hoy la orden se cierra igual.

`mc.rov.accion` gana un booleano **`consume_repuesto`**, marcado en las acciones de cambio, y
el cierre lo valida. **No se hardcodean los nombres de las acciones**: el catálogo es
configurable y mañana aparece «Reemplazo de sello».

**Alcance declarado:** exige *al menos una* línea de producto, no una por cada cambio. Una
orden con tres cambios y un repuesto registrado pasa. Es un piso y no una garantía; la
correspondencia uno a uno obligaría a decir qué repuesto va con qué trabajo, que es otro campo
y otra decisión.

### 8.4 La revisión sin confirmar se muestra, no bloquea *(19.0.14.0.0)*

Hoy la orden se cierra con la revisión en borrador y medio checklist sin responder: los dos
ciclos de estado corren en paralelo sin tocarse. Se evaluó exigir la revisión confirmada para
cerrar y **se descartó**, por dos razones que apuntan al mismo lado:

- La revisión se crea sola en **toda** orden de ROV, así que bloquear obligaría a recorrer los
  veinte chequeos incluso cuando el equipo entró a cambiar un conector. **Y cuando responder
  cuesta, se marca «No aplica» en cadena para pasar el trámite** — que envenena el dato mucho
  más que una revisión en borrador. Es el mismo argumento por el que el análisis del origen no
  es obligatorio.
- El vacío acá **no es ambiguo**, y la regla es bloquear solo cuando lo sería. Una revisión en
  *Borrador* dice literalmente que está sin terminar; el estado ya es la señal.

Entra como filtro **«Revisión sin confirmar»** en la lista de órdenes. A diferencia de «Sin
síntoma registrado», este sí puede llegar a cero: la revisión se confirma cualquier día, el
equipo no se fue a ninguna parte.

**Si en unos meses ese filtro muestra una pila, ahí está la evidencia para bloquear** — y
recién entonces se sabrá cuánto cuesta de verdad, que hoy es una suposición.

### 8.5 La batería se ordena por área, y crece hasta cubrir los síntomas *(19.0.14.1.0)*

Salió de contar la batería contra el catálogo de síntomas del diagnóstico de fallas. Los siete
chequeos originales salieron de la hoja de papel y cubrían cuatro áreas —presión, leak,
navegación, video—. **El catálogo de síntomas tiene nueve familias**, y para tres de ellas no
había ninguna prueba: un ROV que no enciende, que pierde conexión con la superficie o al que no
le responde una luz se iba a diagnosticar mirando.

Eso no rompía nada, pero se leía mal en el único análisis que importa: el hallazgo quedaría con
`chequeo_origen_id` vacío, o sea contado como *«ningún chequeo lo detectó»* — indistinguible de
un hueco en la batería. Y el hueco existía de verdad.

Entran dos secciones nuevas en código —**Energía** y **Comunicación**— y nueve chequeos como
datos semilla. La sección **Inspección física**, que había quedado vacía en `19.0.12.0.0` al
salir las marcas de plumón, vuelve a tener contenido.

**Lo que deliberadamente no se agrega es todo lo que la corrida ya mide.** Que el equipo se
apague solo lo dice `esfuerzo_resultado` junto con su duración; que se caliente, las
temperaturas; el ancho de banda son `subida` y `bajada`. Registrar el mismo hecho como número y
como casilla deja dos versiones del mismo dato y ninguna confiable — y además **un número le
gana a una casilla**: «aguantó 90 minutos» dice más que «OK».

**Los umbrales se contestan a mano, no se derivan.** Decir si 8 Mbps está bien exige un umbral
que hoy nadie definió, y uno inventado en el código marcaría «No OK» según un número sin
significado — el mismo defecto que hizo descartar el «nivel de confianza» en el diseño del
diagnóstico. Por eso el ancho de banda entra como chequeo contestado por el técnico, que sabe
qué da su modelo. **El día que la ficha técnica declare el valor esperado, puede pasar a
derivarse solo**, exactamente como ya lo hace `luces_difieren` contra `mc_cantidad_luces`.

**No hay sección «Sensores»** porque el sensor de profundidad se verifica probando depth hold.

**Segunda pasada, `19.0.14.2.0`.** La primera cerró los huecos **entre** familias de síntoma;
contarlas no muestra los huecos **dentro** de una familia que ya tenía alguna prueba, y ahí
estaban los dos más grandes:

- **«Un motor no gira» no tenía chequeo.** Es de los síntomas que más se reportan, y «Hélices
  en posición correcta» mira la posición, no que giren.
- **La inspección física no miraba el umbilical.** Revisaba chasis, penetradores y hélices —o
  sea el vehículo— y el cable es el componente del que más se sospecha.

Entran también **acro** —que aísla el giróscopo de la parte que nivela, un escalón por debajo
de la separación entre depth hold y stabilize—, «sin ruido ni vibración anormal», y una sección
**Accesorios** con manipulador y sonar. La batería queda en 22.

Que manipulador y sonar los lleve una minoría de los equipos **no es razón para no
preguntarlos**: «No aplica» afirma que el equipo no lo tiene, que es distinto de que nadie lo
haya mirado — la misma razón por la que las líneas del checklist se generan siempre.

Y se retiró un síntoma: **«Fuga de aceite»**, porque estos ROV no usan aceite. Estaba por
analogía con equipos submarinos que sí llevan, y era un síntoma que nadie podía reportar
ocupando lugar en el mesón.

### 8.6 Una corrida por revisión *(19.0.15.0.0)*

`mc.rov.revision.corrida` era un modelo de línea: una revisión podía llevar varias corridas,
una por umbilical, para comparar cables dentro de la misma ficha. **Desaparece.** Sus campos
suben a la revisión y una revisión pasa a tener un solo cable.

**La premisa que lo separaba resultó ser falsa a medias.** El § 5.2 decía que «lo que no
depende del cable —inspección física, presión, leak, luces, video— vive en la revisión y se
hace una sola vez aunque haya dos corridas». Pero varios chequeos **sí** dependen del cable:
responde a comandos, el ancho de banda, probablemente el video. Y las dos corridas compartían
**un solo juego de respuestas**:

> Cualquier chequeo que cambiara entre un cable y otro se perdía en silencio. La comparación
> que justificaba la segunda corrida quedaba visible en cuatro números y en nada más.

Ahora la regla es una sola y no necesita convenciones:

| Qué cambia | Qué se hace |
|---|---|
| Solo los números —ancho de banda, esfuerzo, temperatura— | *(ya no existe: siempre se corre el esfuerzo completo, así que siempre es una revisión)* |
| Cualquier cosa que se responda | **Una segunda revisión**, con su batería completa |

Marine Connection confirmó el dato que lo decide: **al cambiar de cable siempre se corre el
esfuerzo completo**, nunca se cambia solo para medir ancho de banda. O sea que una segunda
pasada con otro cable siempre fue una prueba entera, y modelarla como una línea dentro de la
misma ficha era describirla más chica de lo que es.

**Lo que esto retira, todo de una vez:** la convención de «los chequeos son de la primera
corrida», el campo «batería corrida con» que se llegó a proponer para registrarla, y el
`por_corrida` que iba a partir tres chequeos por cable. Ninguno hace falta cuando la revisión
tiene un solo umbilical.

**El precio, dicho de frente:** comparar dos cables ahora cuesta responder los 22 chequeos dos
veces. Es el mismo precio que ya tenía el re-test tras reparación, y es lo que compra que la
comparación sea completa — media comparación no sirve.

### 8.7 Por qué existe la segunda revisión *(19.0.15.0.0)*

Colapsar la corrida tiene una consecuencia que hay que pagar: **antes, dos corridas dentro de
una revisión solo podían significar «comparación de cables»** — la estructura codificaba la
intención. Ahora dos revisiones en la misma visita pueden ser eso o un re-test tras reparación,
y son indistinguibles.

Mezclarlas corrompe la pregunta que justifica el segundo pase: *«¿cuántas veces la revisión
posterior todavía muestra la falla?»* no significa nada si la mitad de esos segundos pases eran
comparaciones de cable.

Se evaluó inferirlo del umbilical —si difiere, es comparación— y se descartó: miente cuando un
re-test usa otro cable por casualidad. Entra como campo **`motivo`**: *re-test tras reparación*
/ *comparación de cable* / *otro*.

Se pide **a partir de la segunda revisión de la visita** y se exige para confirmar. En la
primera no se pregunta: `numero_en_visita` ya dice que es la primera, y un campo que se
contesta siempre igual deja de leerse.

### 8.8 El software entra a la batería, y nada más que eso *(19.0.15.2.0)*

Faltaban dos cosas distintas y las dos se resuelven con chequeos de catálogo.

**La primera es un hueco de cobertura.** El catálogo de síntomas tiene «El software de
superficie falla» y la batería no tenía ninguna prueba que lo verificara. Es el mismo conteo
—síntomas contra pruebas— que en `19.0.14.1.0` hizo aparecer las secciones de energía y
comunicación. Un síntoma sin prueba que lo cubra significa que el técnico lo va a encontrar
mirando, y entonces el hallazgo queda sin `chequeo_origen_id`.

**La segunda es una falla observada:** el equipo se autoformatea y vuelve al software instalado
de fábrica. Normalmente ROVControl vuelve a QGroundControl, o QGroundControl baja a una versión
más vieja; ArduSub podría revertir también pero no está confirmado. Se detecta comparando
contra la ficha, que ya guarda las tres versiones con `tracking`.

Los dos van en la sección `comunicacion` y no en una sección propia, porque el catálogo de
síntomas ya clasificó esa falla ahí. Una sección nueva costaba un valor de `SECCIONES`, un
one2many filtrado y un bloque de vista para dos preguntas.

**Lo único que se agregó en código son cinco `related` de solo lectura** con lo que la ficha
declara instalado, al lado del chequeo que los usa. No son modelo, son pantalla: un chequeo que
para responderse obliga a abrir el número de serie y volver se responde «OK» sin mirar, y eso
es un dato falso donde antes había un vacío honesto. Se esconden cuando la ficha no declara
nada —hoy, todos los equipos anteriores a Odoo— porque cinco etiquetas vacías se leen como algo
roto.

#### Lo que se descartó, y con qué regla vuelve

Un borrador anterior tenía un modelo `mc.rov.revision.software` con ranuras
—superficie / vehículo / controlador / otro—, valor esperado derivado de la ficha, líneas
generadas al abrir la revisión y un `difiere` con comparación normalizada.

Se descartó porque **el instrumento salía más caro que lo que iba a medir**. Cuál software
revierte y cada cuánto no se sabe todavía, y `detalle` acepta cualquier combinación sin
inventarle casilleros. Estructurarlo ahora es adivinar la forma del dato antes de tener el
dato — el mismo error que este documento evita en el ancho de banda (§ arriba: no se deriva
porque nadie definió el umbral).

**Vuelve a la mesa cuando el `detalle` de estos dos chequeos muestre un patrón**: qué ranura
revierte, con qué frecuencia. Ahí la comparación automática se justifica con evidencia.

Tampoco lleva un booleano `difieren` como el de las luces, y por una razón que no es de
alcance: con el nombre del software escrito a mano, «QGround» y «QGroundControl» son la misma
cosa y darían falso positivo. Un conteo de luces es un entero y no tiene ortografía; el nombre
de un programa sí. Tres líneas lado a lado las compara el ojo sin equivocarse.

**Solo `aplica_reparacion`.** Encender las otras dos por costumbre es exactamente la omisión
que dejó la batería de fabricación sin definir: en fabricación el software lo instala uno
mismo, así que compararlo contra la ficha no afirma lo mismo.

---

## 9. Qué cambia en `repair.order`

Poco, y nada de lo que se usa a diario cambia de significado.

| Cambio | Por qué |
|---|---|
| Se eliminan `item_2` … `item_5` | 0 de 10 órdenes los usaron; la etiqueta original ya era "Ítem 2" |
| Nuevo `mc_items_recibidos_ids` (M2m a `stock.lot`) | Reemplaza la necesidad real: los equipos que llegan junto al ROV. Sin tope, y **trazable** — el E-pod tiene serie propia |
| `causa_raiz` baja a `mc.rov.linea.falla` | Una orden puede tener tres causas distintas; hoy hay que elegir una |
| Nueva pestaña con las revisiones de la visita | La primera se abre sola al salir la orden de borrador; el botón es para el segundo pase |
| `tag_ids` (etiquetas nativas de `repair`) se esconde | `tipo_intervencion_ids` ya clasifica la orden y es lo que leen los reportes. Dos campos de tags idénticos uno al lado del otro solo consiguen que se llene el equivocado |
| La pestaña `parts` pasa a llamarse **«Repuestos»** | "Piezas" no dice de qué; la pestaña admite tanto lo que se le pone al equipo como lo que se le retira |
| `mc_propietario_lot_id` y `mc_items_recibidos_ids` se anclan antes de `under_warranty` | En el arch base `lot_id` va dentro de un `div`, así que un `position="after"` sobre el campo los metía adentro del mismo div: salían en línea, sin etiqueta y pegados al número de serie, donde se leían como una repetición de él |

---

## 10. Migración `19.0.6.0.0`

Mucho más corta que la del diseño anterior, porque **no se mueve ninguna medición**.

1. **Sembrar catálogos** — chequeos, hallazgos, componentes nuevos (vía `data/`, no SQL).
2. **`causa_raiz`**: copiar el valor de cada orden a sus líneas de trabajo antes de eliminar
   la columna. Las órdenes sin líneas pierden el valor — hay que contarlas antes.
3. **Eliminar** `item_2` … `item_5`.

`stock.lot` no aparece en la migración.

---

## 11. Contrato del pipeline

`docs/integrations/pipeline.md` exige coordinar por PR antes de cambiar cualquier campo
listado. Esta versión toca:

- **`item_2..5` se eliminan** y **`causa_raiz` cambia de modelo.**
- **Modelos nuevos**: `mc.rov.revision` y sus tres modelos de línea son, de aquí en
  adelante, **la fuente principal del análisis de fallas** — el insumo del dashboard.
- **Los 48 campos `mc_*` de `stock.lot` no cambian.** El contrato los cubre con una línea
  genérica y sigue siendo válida.

**Además hay que corregir el contrato, que ya está desactualizado:** lista `estado_final`,
`garantia_reparacion` y `fecha_garantia` en `repair.order`, y esos tres campos **no existen
en el código** — solo en ese documento.

---

## 12. Fase posterior: fotos de los hallazgos

**Decidido, pero fuera del alcance inicial.**

Estado del VPS al 2026-08-11: disco de 75 GB con 50 GB libres, 1.037 adjuntos que suman
86 MB, y `ir_attachment.location` vacío ⇒ **van a disco, no a la base**, así que no inflan
los backups de PostgreSQL.

Cuando se implemente, el campo va en la **línea de hallazgo** y debe ser
`fields.Image(max_width=1920, max_height=1920)`, **no `fields.Binary`**. `Image` redimensiona
al guardar y deja una foto de celular de 4 MB en 300-500 KB. Con `Image` caben unas 125.000
fotos antes de que el disco importe.

---

## 12.1 El reporte no es el adorno final

**La ficha de reparación existe, entre otras cosas, para entregársela al cliente.** Eso
convierte al reporte QWeb en un requisito del entregable, no en un extra que se agrega si
sobra tiempo. Lo mismo aplica a la ficha de fabricación, que hoy tampoco imprime nada.

La consecuencia de diseño es que **cada dato tiene una audiencia**. La tabla incorpora los
acuerdos de las notas del 27–28 de agosto, ratificados por Paulo el 9 de septiembre:

| Va al cliente | Se queda interno |
|---|---|
| Chequeos ejecutados y su resultado | Horas de trabajo por línea y por técnico |
| Mediciones aplicables, salvo temperatura | Temperaturas, veredicto global y severidad |
| Técnico en la cabecera, según la maqueta ratificada | Horas internas de trabajo |
| `observaciones_salida` — definido en § 6.4 como *lo que se le informa al cliente* | `detalle` de cada hallazgo |
| Hallazgos, con criterio | La lectura del horómetro |

### Base de impresión ratificada — septiembre de 2026

- Variante C, papel carta. Referencia: [maqueta recuperada](referencias/ficha-impresa-rov.html).
  Sus datos son de ejemplo. El logo tipográfico es provisional: usar el logo configurado de
  la compañía en Odoo cuando exista.
- Ficha de equipo reparado y ficha de equipo nuevo. La primera implementación imprime una
  revisión por documento: `reparacion`, `rendimiento` o `terreno`, con su número real.
  `fabricacion` ya no es un tipo vigente. No consolida rendimiento y terreno ni incluye
  toda la ficha técnica de `stock.lot`; las notas no especifican ese consolidado.
- Hallazgos solo en reparación, sin severidad ni detalle interno. La ficha muestra, en su
  orden real, hasta siete líneas simples. Para evitar que textos largos dominen la hoja, el
  reporte calcula un presupuesto visual de 7,60 unidades: la primera línea vale 1 y cada línea
  estimada adicional 0,52, usando el mayor wrapping entre componente/subtipo y descripción.
  Luego muestra «y N hallazgos más · ver en el sistema». Las líneas completas permanecen en Odoo
  y el bloque puede ocultarse completo; no hay filtro por familia ni priorización por severidad.
  La regla se validó en Letter con catálogo real y con textos de estrés que envuelven,
  observaciones, diferencias, chequeos, firmas, pie y BORRADOR. Chequeos dinámicos, incluidos
  los nuevos del catálogo, con distinción entre pendiente y no aplica.
- Conservar fuga de corriente y funcionamiento continuo donde correspondan. En terreno,
  no imprimir mediciones eléctricas o de presión de taller. Cero no significa automáticamente
  «sin medir»: los campos numéricos actuales no distinguen ambos casos.
- Opciones de firmas, sellos, hallazgos y diferencias para la copia impresa. No modifican ni
  confirman la revisión. Identificar expresamente los borradores.
- Bloques modulares con IDs estables para personalizar mediante vistas heredadas. Las notas
  mencionan Studio, controles de visibilidad y cinco maquetas con `noupdate`, pero no definen
  esos parámetros por completo. La edición desde Studio aún requiere validación; no congelar
  todas las plantillas base con `noupdate` por inferencia de ese resumen.
- Usar los valores congelados disponibles en la revisión para comparaciones históricas.
  El reporte no constituye un archivo inmutable: contactos, catálogos y algunos datos de
  la orden siguen vinculados a registros actuales.

El estado de implementación y las verificaciones pendientes se mantienen exclusivamente
al inicio de [pendientes.md](../pendientes.md).

## 13. Fuera de alcance

- **`stock.lot` y su ficha técnica de fabricación.** Ver § 1.1 y § 2.
- **`tracking=True` en los campos de configuración del lote.** Sigue siendo una buena idea
  —la ficha técnica se puede actualizar cuando se modifica un equipo preexistente, y hoy ese
  cambio no deja rastro— pero es trabajo del lado de manufactura, no de este diseño. Anotado
  para cuando se aborde esa hoja.
- **El dashboard de patrones de fallas.** Es el destino de estos datos, pero se construye
  después de que existan.

---

## 14. Qué campos son obligatorios

**Propuesta con criterio propio, pendiente de que Paulo consulte en el taller.**

El principio: **se exige lo que hace inútil al registro si falta, y se exige al confirmar, no
al escribir.** Cada campo obligatorio es fricción, y la fricción donde no hace falta enseña a
la gente a esquivarla — con lo cual deja de servir donde sí hace falta.

### 14.1 Ficha de reparación (la revisión)

**Siempre, no se puede ni guardar el borrador:**

| Campo | Por qué |
|---|---|
| `lot_id` | Sin equipo el registro no es de nadie |
| `tipo` | Recepción y entrega significan cosas opuestas; sin él el registro es ambiguo |
| `fecha` | Trae default de hoy, así que en la práctica no cuesta nada |

**Para pasar a `confirmado`:**

| Regla | Por qué | Origen |
|---|---|---|
| `responsable_id` | Sin atribución, todo el trabajo de poner empleados no sirve de nada | **Confirmado**: la ficha la llena el técnico que hizo el trabajo, así que es una firma real y no la memoria de quien transcribe |
| Al menos **una corrida**, con `esfuerzo_resultado` y `esfuerzo_duracion` | Una revisión sin corridas dice que no se probó nada | **Confirmado**: la prueba de esfuerzo siempre se hace |
| En cada corrida: `alimentacion` y `tension_salida` | Son las condiciones del banco; sin ellas no hay comparación entre visitas | **Confirmado**: se anotan siempre en la ficha de reparación |
| En cada corrida: `umbilical` y `largo` | Sin saber con qué cable se midió, las mediciones no se pueden interpretar ni comparar | Criterio propio |
| **Todos** los chequeos con `resultado`, incluido *No lo tiene* | Es el punto del checklist: probar que se miró | **Confirmado**: la inspección no siempre recorre los cinco componentes, así que *No lo tiene* es un valor de uso corriente y no una excepción |
| Pares coherentes: si hay `subida` hay `bajada` | Media medición es peor que ninguna — parece un dato y no lo es | Criterio propio |

**Confirmado por el taller: todas las pruebas se hacen siempre.** Así que exigir todos los
chequeos respondidos no impone nada que no ocurra ya — solo obliga a dejar constancia.

El único caso en que un chequeo no se responde con OK o No OK es cuando **el equipo no lleva
ese componente**: no todos los ROV tienen joystick, y el «cilindro fuente» solo existe en
los que tienen dos e-pods. Para eso está *No lo tiene* (§ 5.4), que afirma algo sobre el
equipo y no sobre lo que hizo el técnico.

**Deliberadamente NO obligatorios:**

- `repair_id` — la fabricación no tiene orden.
- Cero hallazgos es legal: significa que el equipo llegó limpio, y los chequeos lo prueban.
- Las pruebas que no se hicieron. Se puede confirmar una revisión parcial siempre que cada
  chequeo diga explícitamente *no aplica*; lo que no se puede es dejarlo en blanco.
- Temperaturas, y los campos de terreno cuando el tipo no es terreno.

### 14.2 Ficha de fabricación (`stock.lot`)

**Ningún campo pasa a `required` a nivel de modelo.** Un número de serie lo crea la orden de
fabricación **antes** de que nadie llene la ficha: exigir campos al guardar rompería
manufactura, y además los lotes de componentes no tienen ninguno de estos datos.

En su lugar, un indicador derivado y un filtro:

```
mc_ficha_completa   Boolean   computed, store   solo tiene sentido si es_un_rov
```

Y un filtro **"Ficha incompleta"** en la lista de números de serie. Es visible sin bloquear,
y convierte "hay que acordarse de llenarla" en una lista concreta.

Lo que propongo contar como completa, con la justificación de cada uno:

| Campo | Por qué es esencial |
|---|---|
| `mc_fecha_puesta_servicio` | **Sin ella no hay reloj de mantención** y el equipo no aparece nunca en la lista de vencidos |
| `mc_chasis`, `mc_modelo_motores`, `mc_n_motores`, `mc_posicion_motores` | La identidad física del equipo; sin ella no se puede agrupar fallas por configuración |
| `mc_controlador_vuelo` y la versión que corresponda | Para correlacionar fallas con firmware, que es media razón del análisis |
| `mc_n_serie_umbilical` y `mc_longitud` | **La revisión de reparación compara contra `mc_longitud`**; sin ella la comparación no existe |
| `mc_cantidad_luces` | **La revisión compara el conteo de la prueba contra este número** |

Los últimos dos grupos son el caso más claro: no son obligatorios por sí mismos, sino porque
**hay otra ficha que los lee**. Si están vacíos, dos de las verificaciones automáticas de la
reparación quedan mudas.

Lo que **no** propongo exigir: pesos, temperaturas, tarjetas de comunicación, dispositivos
extra, brazo. Son descriptivos y nada depende de ellos.

> Esto es lo único de este diseño que toca `stock.lot`, y no cambia ni un dato: agrega un
> campo derivado y un filtro. Si prefieren que la ficha de fabricación quede completamente
> intacta, se cae sin afectar nada más.

---

## 15. Verificación

1. **Tests** — clases nuevas: `TestMcRovRevisión` (cabecera, derivados, `resultado`
   calculado, generación automática de líneas), `TestMcRovRevisiónCorrida` (una y dos
   corridas, esfuerzo), `TestMcRovRevisiónChequeo` (validación al confirmar),
   `TestMcRovRevisiónHallazgo` (severidad y precedencia), `TestMcRovLineaFallaHallazgo`
   (el enlace y la baja de `causa_raiz`).
2. **Auditoría previa al deploy** — cuántas órdenes tienen `causa_raiz` sin líneas de
   trabajo, que son las que perderían el valor:
   ```sql
   SELECT count(*) FROM repair_order ro
    WHERE ro.causa_raiz IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM mc_rov_linea_falla lf WHERE lf.repair_id = ro.id);
   ```
3. **Manual, en staging** — crear una revisión de recepción sobre una serie ROV; confirmar
   que las líneas de chequeo se generan solas, que no deja confirmar con chequeos sin
   responder, que dos corridas con distinto umbilical se pueden comparar, que `resultado`
   reacciona a un hallazgo `impide_operar`, y que el reporte imprime.
4. **Rollback** — según `docs/runbooks/deploy.md`. La ficha técnica de fabricación no se
   toca, así que un rollback no arriesga nada de manufactura.

---

## 16. Para qué sirven estos datos

Esta sección existe para que ningún campo del modelo parezca gratuito. Cada uno de los que
cuestan discusión —`severidad`, `chequeo_origen_id`, `horas_operacion`, `esfuerzo_duracion`—
está aquí porque habilita algo concreto.

Ordenado por **cuándo empieza a servir**, no por lo impresionante que suena. La mitad de las
metodologías de confiabilidad necesitan un volumen de datos que Marine Connection no va a
tener por años, y prometerlas antes de tiempo es vender humo.

### 16.1 Desde el primer mes

| Qué | Con qué datos |
|---|---|
| **Pareto de fallas** — qué componentes concentran hallazgos, horas y visitas | `componente_id` + `horas` de las líneas de trabajo |
| **Análisis de garantía** — qué falla dentro de garantía (costo propio) y qué después | `repair.order.under_warranty` × hallazgos. Los de familia *intervención de terceros* son evidencia directa para invalidarla |

### 16.2 Con un año de datos

**Tabla de fallas — que es un FMEA, y armado al revés del habitual.** El FMEA clásico lo
arman ingenieros *imaginando* modos de falla en una sala de reuniones. Aquí se arma **desde
el historial real**, que es estrictamente mejor y que casi ningún taller puede hacer porque
no guarda los datos. Sus tres ejes salen del modelo:

| Eje del FMEA | De dónde sale |
|---|---|
| **Severidad** | `severidad` del hallazgo |
| **Ocurrencia** | Cuántas veces aparece ese hallazgo en la flota |
| **Detección** | `chequeo_origen_id`: ¿lo agarró un chequeo, o se vio de casualidad? |

**La detección es el eje que casi nadie puede calcular**, y de ahí sale el resultado más
útil de todos: *un hallazgo que aparece seguido y que ningún chequeo detecta es un chequeo
que falta*. Y al revés, un chequeo que sale OK siempre, en toda la flota, durante un año, o
no mide nada o mide algo que no falla — se elimina. **La revisión se audita a sí mismo.**

**Degradación por equipo.** Subida, bajada y `esfuerzo_duracion` de cada visita, en serie.
Un equipo cuyo enlace cae visita tras visita se está deteriorando antes de fallar. Es lo
único de toda la lista que hoy es *literalmente imposible*, porque no existe la segunda
medición.

**Cohortes por configuración.** Como la revisión guarda la versión de firmware del día de
la prueba, se puede preguntar *"¿las fallas de motor aparecieron después de ArduSub 4.1?"*.
Para un fabricante es de lo más accionable que hay: dice si el problema lo introdujo uno
mismo.

### 16.3 Con volumen — y con una condición

**MTBF y análisis de supervivencia (Weibull).** La curva de bañera distingue falla infantil
—defecto de fabricación, problema propio— de desgaste normal, que es problema del cliente.
Esa distinción vale dinero.

Pero **necesita horas de uso, no de calendario.** Un ROV que bucea ocho horas diarias y uno
guardado en bodega acumulan el mismo tiempo de calendario, así que un MTBF calculado sobre
fechas favorece a los equipos que nadie usa.

De ahí `horas_operacion`. Y como **solo algunos ROV traen horómetro**, la flota se parte en
dos poblaciones: los que dan confiabilidad real y los que dan aproximaciones por calendario.
No es un problema —tener datos buenos de una parte es muchísimo mejor que nada— pero
**cualquier dashboard tiene que declarar de qué población sale cada número**, o alguien va a
promediar los dos.

Dos decisiones que se derivan de eso y que no son técnicas:

1. **`mc_tiene_horometro` en la ficha de fabricación**, para que una lectura vacía no
   confunda *"el equipo no tiene"* con *"nadie lo anotó"* — la misma distinción que se
   resolvió al retirar «Desconocido». Y de una consulta dice qué porcentaje de la flota es
   analizable.
2. **Que los equipos nuevos salgan todos con horómetro**, si el análisis de confiabilidad
   les importa. Es lo único que hace crecer esa población.
