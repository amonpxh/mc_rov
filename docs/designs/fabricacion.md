# Fabricación

> Estado: **diseño acordado, sin implementar.** Salido de dos días de conversación (2026-08-17
> y 18) y de verificar `odoo_prod` en vez de suponer. Lo que quedó sin decidir está en § 10.

## 1. Qué problema resuelve

Del lado de la reparación el módulo cerró el ciclo completo: qué se encontró, por qué pasó, qué
se hizo. **Del lado de la manufactura no hay nada de eso.** Concretamente:

1. **No existe el evento de armado.** Un ROV aparece como número de serie sin que nada registre
   que se armó, cuándo, ni con qué piezas.
2. **Las pruebas de aceptación son una foto de un solo valor.** Viven como columnas en
   `stock.lot` —la de laboratorio y la de terreno— así que **repetir una prueba pisa la
   anterior en silencio**. `mc_fecha_prueba` tiene fecha, o sea que alguien entendió que era un
   evento, pero solo cabe uno.
3. **Las lecciones aprendidas se pierden.** Se hacen fabricaciones y modificaciones de
   fabricación a partir de errores detectados al armar, y ese aprendizaje no queda en ninguna
   parte. Es el mismo hueco que el diagnóstico de fallas cerró en reparación.
4. **Lo que ya se sabe en reparación no llega a fabricación.** Una línea de trabajo con
   `origen = diseno` («lo pensamos mal») o `= falla_fabricacion` («lo hicimos mal») **es una
   lección de manufactura ya escrita**, y muere donde nace.

El punto 2 tiene un agravante que decide buena parte del diseño: **normalmente se prueba una
sola vez, salvo cuando hay que ajustar el diseño y se repite hasta que quede bueno.** O sea que
el caso raro es el informativo, y es justo el que la foto destruye.

## 2. Lo verificado, no lo supuesto

Todo esto se comprobó contra `odoo_prod` el 2026-08-18:

- `mrp`, `mrp_plm`, `quality`, `quality_control` y `web_enterprise` están **instalados**. Es una
  instancia Enterprise y nadie los usa.
- `mrp` asigna el número de serie por su cuenta (`mrp.production.lot_producing_id`). Hacen falta
  dos configuraciones y cero código: *Inventario → Trazabilidad → Lotes y números de serie*, y
  en el producto *Trazabilidad → Por número de serie único*.
- Tipos de punto de calidad disponibles: `passfail`, `measure`, `instructions`, `picture`,
  `print_label`, `register_byproducts`, `register_consumed_materials`, `register_production`,
  `spreadsheet`.
- `quality.alert` trae `product_tmpl_id`, `lot_ids`, `reason_id`, `action_corrective`,
  `action_preventive`, `check_id`, `production_id`, `stage_id`, `team_id` y chatter.
- **`mrp.eco` no tiene ningún campo hacia `quality.alert`, ni al revés.**
- **`product.template` y `stock.lot` no tienen ninguna relación con `quality.alert`.**
- `repair.order` **sí** tiene `quality_alert_ids` y `quality_check_ids`, nativos.
- Filas afectadas por la migración de pruebas de terreno: **cero**. Cuatro lotes ROV, ninguno
  con datos de prueba.

## 3. El reparto: qué módulo hace qué

| Qué | Módulo | Modelo |
|---|---|---|
| Ficha técnica de la unidad | `stock` + `mc_rov` | `stock.lot` |
| Historial de cambios de la unidad | `mail` | chatter, ya existe |
| Lista de materiales | `mrp` | `mrp.bom` |
| Evento de armado | `mrp` | `mrp.production` |
| N° de serie del equipo armado | `mrp` | `lot_producing_id` |
| Qué piezas entraron en esta unidad | `stock` | `stock.move.line` |
| Verificación del armado | `quality_control` | `quality.point` → `quality.check` |
| **Pruebas de aceptación** | **`mc_rov`** | **`mc.rov.revision`** |
| Lección aprendida | `quality_control` | `quality.alert` |
| Cambio de BoM | `mrp_plm` | `mrp.eco` |

**La regla que ordena esto:** *los chequeos pertenecen al proceso que los define; las alertas son
el idioma común.*

## 4. Las pruebas de aceptación

### 4.1 Por qué `tipo` y no un modelo nuevo

Una prueba de fabricación no es una revisión de reparación: no lleva sellos, no busca desgaste,
y no la origina una visita. El instinto correcto es separarlas.

**Pero `mc.rov.revision` ya contiene la prueba de rendimiento.** La sección que llamamos «la
corrida» —`esfuerzo_duracion`, `esfuerzo_resultado`, `subida`, `bajada`, `alimentacion`,
`tension_salida`, `temperatura_interior`, `temperatura_exterior`— **es** una prueba de
rendimiento, campo por campo. Un modelo nuevo duplicaría ocho campos, y el día que cambie uno
habrá que acordarse de los dos.

Se resuelve con **dos vistas filtradas del mismo modelo**: la pestaña del número de serie se
parte en *Pruebas de fabricación* y *Revisiones de reparación*, cada una con su dominio sobre
`tipo`. Visualmente quedan tan separadas como si fueran modelos distintos, sin duplicar nada.

Es el mismo mecanismo que usan los `chequeo_<seccion>_ids`: un solo `One2many`, nueve vistas por
dominio.

**El precio, declarado:** son el mismo modelo, así que la separación depende de la disciplina de
las visibilidades por `tipo`. Ya se hace hoy con `lugar` y `profundidad`, y hay tests que fijan
que fabricación no genera inspección de sellos.

### 4.2 Los tres tipos

`tipo` queda en **`reparacion`**, **`rendimiento`** y **`terreno`**. El valor `fabricacion` se
retira: era genérico y nunca tuvo justificación escrita.

| Tipo | Cuándo | Origen | Lleva |
|---|---|---|---|
| `rendimiento` | Equipo armado, en banco | Número de serie | Mediciones, esfuerzo, batería de fabricación |
| `terreno` | Antes de entregar, en agua | Número de serie | Condiciones del sitio, batería de terreno |
| `reparacion` | Visita al taller | Orden de reparación | Sellos, batería de reparación, hallazgos |

Las dos primeras son **pruebas de aceptación**: parte del nacimiento del equipo, no de su vida
posterior. Por eso el historial de revisiones queda **solo de reparación**, y vive en el módulo
de Reparaciones, que es donde ya está.

### 4.3 Se crean desde el número de serie, y el botón es específico

Una prueba de aceptación no nace de una orden de reparación, así que la crea un botón en la
pestaña del número de serie.

**El botón es por tipo —«Nueva prueba de rendimiento», «Nueva prueba en terreno»— y no uno
genérico.** No es cosmética: un «Nueva revisión» genérico dejaría crear revisiones de
reparación **huérfanas**, sin orden, sin cliente y sin motivo, que después no encuentra nadie.
La especificidad del botón es lo que impide crear el registro equivocado.

### 4.4 Obligatorias, y por lo tanto visibles

Las dos son obligatorias antes de entregar. **Un requisito que el sistema no muestra es un
requisito que se olvida**, así que se deriva en el número de serie —igual que
`mc_ficha_completa`— si cada una está hecha, más un filtro **«Sin pruebas de aceptación»** en la
lista de números de serie.

Eso convierte «hay que acordarse» en «hay una lista de los que todavía no se pueden entregar».

**No bloquea nada.** Es la misma decisión que se tomó al retirar el `required` de la ficha en
`19.0.15.2.1`: bloquear empuja a inventar, y lo que encuentra los incompletos es una lista, no
un candado.

### 4.5 Historial, no foto

Las dos guardan historial por la razón del § 1: el caso «probar hasta que quede bueno» es donde
está la información, y hoy cada repetición borra la anterior. Es la misma corrección que
`19.0.15.0.0` le hizo a la corrida.

### 4.6 La forma visual se conserva

Las pestañas actuales *Umbilical* y *Prueba en Terreno* se ven como un formulario agrupado
**porque hay exactamente una**. Al pasar a historial ese layout no se pierde: se muda al
registro. La pestaña muestra la lista de pruebas y cada una se abre en su formulario de bloques.

Y la forma corresponde al contenido: **las mediciones se leen mejor en formulario, y los
pasa/falla en lista.** Por eso la prueba de rendimiento tiene bloques con títulos y la batería
es una lista de chequeos. Cada cosa con su forma.

## 5. Las baterías

Hoy los 22 chequeos tienen las tres casillas `aplica_*` encendidas por omisión, así que un ROV
recién armado recibe las mismas preguntas que uno que llegó roto, incluidas las que buscan
desgaste. **El mecanismo para separarlas existe y está probado: son datos, no código.**

### 5.1 Dos cosas hacen distinta a la de fabricación

1. **Los umbrales existen.** Se construye contra una especificación. En reparación se decidió no
   derivar el ancho de banda porque nadie los había definido; fabricando, la especificación *es*
   el umbral.
2. **El software se mide al revés.** En reparación se compara contra la ficha. En fabricación
   **se instala**, así que la fabricación es la *fuente* de la ficha. Registrar las versiones al
   armar es lo que haría que la ficha dejara de nacer vacía — que es el problema que hoy
   arrastran todos los equipos anteriores a Odoo.

### 5.2 El armado va en puntos de calidad, no en la revisión

Y hay una razón que solo aparece cuando el proceso es físico: **hay cosas que solo se pueden
verificar antes de cerrar el casco.** Sellos, o-rings, torque de penetradores, cableado interno.
Si el control no está amarrado a la operación de armado, se responde después, de memoria,
mirando un equipo cerrado.

Los puntos de calidad se enganchan a la operación; una batería plana no. Por eso el armado va
ahí y la prueba de aceptación va en la revisión.

| Momento | Qué | Dónde | Tipo |
|---|---|---|---|
| Antes de cerrar | Sellos y o-rings instalados y lubricados | Punto de calidad | Pass-Fail |
| | Penetradores y conectores apretados | Punto de calidad | Pass-Fail |
| | Cableado interno ordenado y asegurado | Punto de calidad | Pass-Fail |
| | Foto del interior armado | Punto de calidad | Picture |
| Cerrado | Estanqueidad · Leak | Punto de calidad | Pass-Fail |
| Cierre | Registrar número de serie | Punto de calidad | Register Production |
| **Banco** | Tensión, consumo en reposo y bajo carga | **Revisión `rendimiento`** | Medición |
| | Ancho de banda subida / bajada | **Revisión `rendimiento`** | Medición |
| | Thrusters, movimientos, *stabilize*, *depth hold* | **Revisión `rendimiento`** | Chequeo |
| | Imagen, tilt, luces, ganancia | **Revisión `rendimiento`** | Chequeo + medición |
| | Esfuerzo: duración y temperaturas | **Revisión `rendimiento`** | Medición |
| | Versiones de software instaladas | **Revisión `rendimiento`** | **Alimentan la ficha** |
| **Terreno** | Lugar, profundidad, corriente, alimentación | **Revisión `terreno`** | Condiciones |
| | Batería reducida de navegación, video y comunicación | **Revisión `terreno`** | Chequeo |

Casi la mitad de las mediciones ya se toman hoy: son las columnas del número de serie
convertidas en un evento repetible.

### 5.3 Un arreglo que viene gratis

`mc_ancho_banda` y `mc_consumo_corriente` son `Char` hoy, así que no se pueden promediar,
comparar ni graficar. Al pasar a la revisión se declaran como numéricos con unidad, y recién ahí
sirven para el pipeline.

## 6. Lecciones aprendidas: ya existen y se llaman `quality.alert`

El diseño del 2026-08-17 proponía construir un modelo de lecciones sobre `product.template`.
**No hay que construirlo.** `quality.alert` trae más de lo que se iba a escribir:

| Lo que pedía el diseño | Campo |
|---|---|
| Lección **del modelo**, no de la unidad | `product_tmpl_id` |
| Qué unidades quedaron afectadas | `lot_ids` |
| Por qué pasó | `reason_id` (catálogo) |
| Qué se corrigió | `action_corrective` |
| **Qué hacemos para que no se repita** | `action_preventive` |
| De dónde salió | `check_id`, `production_id` |
| Flujo e historial | `stage_id`, `team_id`, chatter |

`lot_ids` es el que más importa y no estaba en el diseño anterior: **es el alcance del daño.**
«Cambiamos el o-ring» es la lección; «estas 7 unidades llevan el viejo» es la acción.

### 6.1 Los tres huecos, y son chicos

1. **`product.template` no tiene relación con las alertas.** O sea que el que arme el próximo
   ROV **no las va a ver** salvo que se acuerde de ir a la app de Calidad. Es el riesgo del
   cementerio localizado en un campo que falta. **Dos `One2many` —producto y lote— y es el
   trabajo más valioso de todo el bloque.**
2. **No hay puente alerta ↔ ECO.** «Cambiamos el BoM por esto» no queda registrado. Un campo.
3. **De la línea de trabajo a la alerta** falta un botón que la pre-llene desde `origen`. El
   puente ya está a medio construir: `repair.order.quality_alert_ids` existe de fábrica.

### 6.2 Por qué la revisión no se reemplaza por chequeos de calidad

`repair.order` ya trae `quality_check_ids`, o sea que Odoo tenía un mecanismo de chequeos sobre
reparaciones cuando se construyó `mc.rov.revision`. **No se cambia**, y no por costo hundido:

- La revisión hace cosas que un `quality.check` no hace: inspección de sellos, catálogo de
  hallazgos por familia, y **«No aplica» como respuesta válida** —un `passfail` es binario—.
- Y sobre todo: **la revisión es un entregable al cliente.** Un chequeo de calidad es un control
  interno.

Ese mismo criterio es el que deja las pruebas de aceptación en la revisión y no en puntos de
calidad: **también son entregables** — la ficha que recibe el cliente lleva sus resultados.

`repair.order.quality_check_ids` se esconde de la vista: dos mecanismos de chequeo visibles en
la misma pantalla es una invitación a llenar el equivocado.

## 7. Qué se retira

- **`tipo = fabricacion`** de la revisión, reemplazado por `rendimiento`.
- **La pestaña «Prueba en Terreno»** del número de serie, y sus columnas:
  `mc_fecha_prueba`, `mc_lugar`, `mc_profundidad`, `mc_velocidad_corriente`, `mc_alimentacion`,
  `mc_tiempo_prueba_terreno`, `mc_temperatura_interior_terreno`,
  `mc_temperatura_exterior_terreno`, `mc_observacion`.
- Las columnas de prueba de laboratorio del lote, una vez que la prueba de rendimiento las
  reemplace.

## 8. Migración

**Cero filas afectadas**, verificado: ningún lote ROV tiene datos de prueba. La migración se
reduce a borrar columnas y a mapear `tipo = fabricacion` → `rendimiento` si existiera alguna
fila.

Eso hace desaparecer tres problemas que había que resolver si hubiera habido datos: dónde poner
`mc_observacion` (texto libre que el módulo lleva dos versiones reemplazando por hallazgos), qué
significa `mc_tiempo_prueba_terreno` frente a `esfuerzo_duracion`, y qué hacer con una revisión
migrada sin chequeos respondidos, que quedaría en borrador para siempre.

**Es un bump `X`** por las columnas que se borran, con riesgo prácticamente nulo. La ventana
para hacerlo es ahora: con equipos reales cargados, cada una de esas tres preguntas vuelve.

## 9. Lo que NO se hace, y con qué regla vuelve

- **El re-test tras rediseño no se modela.** Ocurre pocas veces al año, con enfoque de
  troubleshooting, y nadie sabe describir su forma. Modelarlo ahora es inventar la forma del
  dato antes de tener el dato — el mismo error que se evitó con el software en `19.0.15.2.0`.
  Mientras tanto cae en su lugar natural: un prototipo se arma con una MO, y las repeticiones
  son revisiones de rendimiento sucesivas. **Vuelve cuando tres o cuatro rediseños muestren qué
  les falta.**
- **No se rastrea todo por lote.** La trazabilidad es configuración *por producto*: un BoM de 40
  líneas puede tener 4 rastreadas —o-rings, thrusters, tarjetas, controlador— y el resto
  consumido automáticamente. Eso convierte «registrar 40 piezas» en «elegir el lote de 4», y
  deja intacto lo único que hoy no se puede responder: **qué otras unidades llevan la pieza que
  salió mala.**
- **No se derivan tolerancias.** Las mediciones se guardan como números y quien dice si pasó es
  el técnico, igual que hoy con el ancho de banda. El día que la ficha declare el valor esperado
  por modelo, se deriva solo — como ya lo hace `luces_difieren`.
- **El reporte PDF va al final**, decidido explícitamente. Con una restricción ya fijada: **la
  temperatura no se imprime**. Se le entregaba al cliente y el cliente la usó en contra.

## 10. Lo que sigue sin decidir

1. **Si Calidad guarda el historial de intentos** cuando un chequeo falla y se repite, o si el
   último pisa al anterior. Si lo pisa, el caso «probar hasta que quede bueno» tiene el mismo
   defecto del snapshot dentro del armado. **Es lo primero que hay que probar en `odoo_lab`.**
2. **El contenido exacto de las dos baterías nuevas** — qué se pregunta en rendimiento y qué en
   terreno. La tabla del § 5.2 es una propuesta para llevar al taller, no una decisión.
3. **Si la revisión de terreno necesita un tiempo de prueba propio y un texto libre.** Dejaron de
   ser preguntas de migración al no haber datos, pero vuelven antes de la primera prueba real.
   Preliminar: el texto libre no, por lo mismo que se retiró de todas partes.
4. **Los mínimos y máximos por modelo.** No bloquean esto —§ 9— pero si no existen escritos, eso
   mismo es el hallazgo.
5. **Empezar con un solo modelo de ROV** y una MO completa de punta a punta antes de escribir
   código. Se está digitalizando un proceso hoy físico: no hay costumbre que aprovechar, hay
   costumbre que cambiar, y eso se descubre haciendo una.
