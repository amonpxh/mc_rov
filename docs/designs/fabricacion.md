# Fabricación

> Estado: **diseño acordado y aprobado por el supervisor, sin implementar.** Salido de dos días
> de conversación (2026-08-17 y 18), de verificar `odoo_prod` en vez de suponer, y de correr el
> flujo completo en `odoo_staging` — § 2.1, donde tres hallazgos contradicen lo que este mismo
> documento decía antes. Lo que queda sin decidir está en § 10.

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
- `mrp` asigna el número de serie por su cuenta (`mrp.production.lot_producing_ids`, **Many2many**
  y no Many2one: en Odoo 19 una orden puede producir varias series. Esta línea decía
  `lot_producing_id` hasta el 2026-08-20, y el campo con ese nombre no existe). Hacen falta
  dos configuraciones y cero código: *Inventario → Trazabilidad → Lotes y números de serie*, y
  en el producto *Trazabilidad → Por número de serie único*.
- Tipos de punto de calidad disponibles: `passfail`, `measure`, `instructions`, `picture`,
  `print_label`, `register_byproducts`, `register_consumed_materials`, `register_production`,
  `spreadsheet`.
- `quality.alert` trae `product_tmpl_id`, `lot_ids`, `reason_id`, `action_corrective`,
  `action_preventive`, `check_id`, `production_id`, `stage_id`, `team_id` y chatter.
- **`mrp.eco` no tiene ningún campo hacia `quality.alert`, ni al revés.**
- **`product.template` no tiene ninguna relación con `quality.alert`.** Trae `eco_ids` y los
  conteos de chequeos, y nada de alertas.
- **`stock.lot` tiene los conteos y ninguna vista los usa.** `quality_control` le pone
  `quality_alert_qty` y `quality_check_qty`, computados y restringidos a
  `quality.group_quality_user`. Se supuso que existían para sostener botones inteligentes
  nativos; **verificado en pantalla el 2026-08-20 sobre `odoo_prod`: no hay ninguno.** El
  número de serie muestra «Por reparar / Hecho», «Ubicación» y «Trazabilidad», y nada de
  calidad. El lado del lote hubo que escribirlo (`19.0.15.4.0`), y quedó como pestaña y no
  como botón inteligente porque este formulario no declara un `oe_button_box` con nombre
  estable — la misma razón que ya está escrita en `views/stock_lot_views.xml`.
- `repair.order` **sí** tiene `quality_alert_ids` y `quality_check_ids`, nativos.
- Filas afectadas por la migración de pruebas de terreno: **cero**. Cuatro lotes ROV, ninguno
  con datos de prueba.

### 2.1 El experimento en staging *(2026-08-18)*

Media hora de hacer clic sobre `odoo_staging` con MRP y Calidad reales. **Tres de los siete
hallazgos contradicen lo que este documento decía antes**, y por eso están escritos acá.

1. **Calidad pisa el chequeo.** Se falló y se volvió a aprobar el mismo control: la fila cambió
   de `fail` a `pass` y `control_date` se sobrescribió. Ni fila nueva ni encadenamiento —
   `previous_check_id` y `next_check_id` quedaron vacíos, o sea que sirven para ordenar
   chequeos dentro de una operación, no para reintentos.
2. **La alerta no se crea sola al fallar.** Hay un botón «Crear alerta» y alguien tiene que
   apretarlo. Este documento daba por hecho que se acumulaban solas.
3. **Un chequeo fallido no impide cerrar la orden.** Verificado: `quality_state = fail` junto a
   `state = done`.
4. **La alerta llena `product_tmpl_id` sola.** Nace apuntando al modelo sin que nadie lo diga,
   que es lo que la vuelve una lección y no un incidente suelto.
5. **No hay ningún puente al ECO**, confirmado en pantalla además de en `ir_model_fields`: la
   pestaña «Misceláneo» trae Proveedor, Fecha asignada y Fecha de cierre, y el menú ⚙ solo
   Duplicar y Eliminar.
6. **`quality.reason` trae cuatro valores por defecto** —Falla en el centro de trabajo, Calidad
   de las piezas, Operación de trabajo, Otros— y **le falta «Diseño o especificación»**.
7. **La orden creó el número de serie sola** (`0000011`), con trazabilidad y movimientos.
   También produjo con los componentes en «No disponible», dejando stock negativo.

#### Los tres primeros, juntos, describen cómo se borra lo que veníamos a capturar

> El técnico marca **Fallido** → no se crea nada → nada lo detiene → arregla el equipo → marca
> **Aprueba** → **el fallo se sobrescribe** → la orden cierra impecable.

Al final, esa orden se ve perfecta: el chequeo dice `pass`, no hay ninguna alerta, y lo único
que queda es una línea de chatter — prosa, por registro, no consultable.

**Y no es un defecto de Odoo: Calidad responde otra pregunta.** Está hecho para contestar *«¿esta
unidad quedó buena?»*, no *«¿qué aprendimos armándola?»*. Para la primera, pisar el estado es lo
correcto — lo que importa es el veredicto final.

Que no bloquee (hallazgo 3) es **bueno**: si bloqueara, la salida cómoda sería marcar «Aprueba»
para poder avanzar, y eso es un dato falso donde antes había un vacío honesto. Pero la otra cara
es que nada obliga a cerrar el ciclo.

#### Y validó por contraste la decisión del § 4.5

La recomendación inicial era poner las pruebas de aceptación como puntos de calidad. **Si se
hubiera hecho, el caso «probar hasta que quede bueno» habría perdido todos los intentos menos el
último.** Están en `mc.rov.revision` porque ahí sí hay historial, y eso resultó ser lo que las
salva.

## 3. El reparto: qué módulo hace qué

| Qué | Módulo | Modelo |
|---|---|---|
| Ficha técnica de la unidad | `stock` + `mc_rov` | `stock.lot` |
| Historial de cambios de la unidad | `mail` | chatter, ya existe |
| Lista de materiales | `mrp` | `mrp.bom` |
| Evento de armado | `mrp` | `mrp.production` |
| N° de serie del equipo armado | `mrp` | `lot_producing_ids` |
| Qué piezas entraron en esta unidad | `stock` | `stock.move.line` |
| Verificación del armado | `quality_control` | `quality.point` → `quality.check` |
| **Pruebas de aceptación** | **`mc_rov`** | **`mc.rov.revision`** |
| Lección aprendida | `quality_control` | `quality.alert` |
| Cambio de BoM | `mrp_plm` | `mrp.eco` |

**La regla que ordena esto:** *los chequeos pertenecen al proceso que los define; las alertas son
el idioma común.*

### 3.1 El flujo completo, de punta a punta

Las secciones siguientes están organizadas por tema. Esto es el proceso, que es lo que hay que
digitalizar.

> **La versión para usuarios, con ejemplos y sin razones de diseño, está en
> [`flujo-de-trabajo.md`](../flujo-de-trabajo.md).** Este documento explica por qué; ése explica
> qué app abrir.

1. **Se crea la orden de fabricación** desde el BoM del modelo.
2. **Se arma.** Durante el armado se responden los puntos de calidad: sellos y o-rings,
   penetradores, cableado, foto del interior. **Antes de cerrar el casco**, porque después no se
   ven.
3. **Se cierra el casco** y se responden estanqueidad y leak.
4. **Se termina la MO y ahí nace el número de serie** (`lot_producing_ids`). Los componentes
   rastreados por lote quedan registrados contra esta unidad.
5. **Se llena la ficha técnica** del número de serie.
6. **Prueba de rendimiento**, desde un botón en el número de serie: mediciones de banco, corrida
   de resistencia, y las versiones de software instaladas — **que son las que alimentan la
   ficha**, porque acá el software se instala, no se compara.
7. **Prueba en terreno**, desde el mismo lugar: condiciones del sitio y batería reducida.
8. **Si alguna de las dos falla, se ajusta y se hace otra.** Las dos quedan en el historial;
   solo la aprobada satisface el requisito (§ 4.4).
9. **Se entrega**, con el indicador diciendo si las dos están.
10. Si en cualquier punto aparece un problema **del modelo y no de la unidad**: alerta de
    calidad con su acción preventiva, y si cambia el BoM, un ECO enlazado (§ 6).

## 4. Las pruebas de aceptación

### 4.1 Por qué `tipo` y no un modelo nuevo

Una prueba de fabricación no es una revisión de reparación: no lleva sellos, no busca desgaste,
y no la origina una visita. El instinto correcto es separarlas.

**Pero `mc.rov.revision` ya contiene la prueba de rendimiento.** La sección que llamamos «la
corrida» —`esfuerzo_duracion`, `esfuerzo_resultado`, `subida`, `bajada`, `alimentacion`,
`tension_salida`, `temperatura_interior`, `temperatura_exterior`— **es** una prueba de
banco, campo por campo. Un modelo nuevo duplicaría ocho campos, y el día que cambie uno
habrá que acordarse de los dos.

Se resuelve con **dos vistas filtradas del mismo modelo**: la pestaña del número de serie se
parte en *Pruebas de fabricación* y *Revisiones de reparación*, cada una con su dominio sobre
`tipo`. Visualmente quedan tan separadas como si fueran modelos distintos, sin duplicar nada.

Es el mismo mecanismo que usan los `chequeo_<seccion>_ids`: un solo `One2many`, nueve vistas por
dominio.

**El precio, declarado, y contando los dos lados.** Un modelo nuevo duplicaría ocho campos; el
`tipo` compartido arrastra los que **no** aplican. Una prueba de rendimiento hereda `umbilical`
—«del equipo» / «del taller» no significa nada en un ROV recién armado—, `motivo` (re-test /
comparación de cable), `horas_operacion` (que es 0 en un equipo nuevo), y `repair_id` y
`partner_id` vacíos. Esconderlos es una visibilidad más que mantener por cada uno.

La decisión sigue siendo el `tipo` compartido, porque **ocho campos duplicados se desincronizan
solos y cuatro campos escondidos no**: el primero es un error silencioso, el segundo es
disciplina verificable con un test. Pero la comparación no es «duplicar contra no duplicar».

Ya se hace hoy con `lugar` y `profundidad`, y hay tests que fijan que una revisión de fabricación
no genera inspección de sellos.

### 4.2 Los tres tipos

`tipo` queda en **`reparacion`**, **`rendimiento`** y **`terreno`**. El valor `fabricacion` se
retira: era genérico y nunca tuvo justificación escrita, y además dejó de describir una sola
cosa — lo que pasa al armar son puntos de calidad, lo que pasa después es la prueba de
banco.

**Se llama `rendimiento` y no `rendimiento`, decidido el 2026-08-20 al implementarlo.** El diseño había
elegido `rendimiento` y tampoco lo justificó, que es exactamente el defecto por el que se retiró
`fabricacion`. Y el problema no es que sea impreciso —la prueba sí mide rendimiento: ancho de
banda, consumos, pilot gain— sino que **`rendimiento` y `terreno` no contrastan en el mismo
eje**: uno nombra qué se mide y el otro dónde se hace, así que el desplegable deja abierta la
pregunta *«¿y la de terreno no mide rendimiento?»*.

El eje verdadero es el lugar, y este documento lo delata solo: las tablas del § 5.2 definen las
dos por dónde ocurren, y el caso que ilustra su diferencia es **la presión verificada por dos
medios según dónde estés**. Se descartaron `laboratorio` —no hay ningún lugar del taller que se
llame así, sería vocabulario importado— y `taller`, porque la revisión de reparación también se
hace en el taller y reintroduce la misma colisión. La etiqueta es **«Prueba de rendimiento»** y nunca
«Banco» a secas, que se leería como *bank*.

**Y `terreno` no es solo prueba de aceptación.** A veces un cliente pide, después de una
reparación, comprobar que el equipo sigue respetando su profundidad máxima. Es poco frecuente
pero ocurre, y el modelo lo aguanta sin cambios porque `repair_id` es opcional:

| Revisión de terreno | Qué es |
|---|---|
| **sin** orden de reparación | Prueba de aceptación de un equipo nuevo |
| **con** orden de reparación | Prueba extra pedida dentro de una reparación |

Por eso el botón *«Nueva prueba en terreno»* existe en **dos lugares**: el número de serie y la
orden de reparación. La batería es la misma en los dos casos — no hay una cuarta.

Vale la pena notar lo que eso significa: **cuando un cliente pide comprobar la profundidad
después de una reparación, está pidiendo exactamente la prueba de aceptación, años después.**
Misma batería, mismo criterio. Que la pregunta *«¿este equipo aguanta lo que dice aguantar?»* se
conteste igual el día 1 que el día 1.500 es señal de que el modelo quedó en el lugar correcto.

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
`mc_ficha_completa`— más un filtro **«Sin pruebas de aceptación»** en la lista. Eso convierte
«hay que acordarse» en «hay una lista de los que todavía no se pueden entregar».

**No bloquea nada, se comporta como el aviso amarillo de la ficha.** Misma decisión que retirar
el `required` en `19.0.15.2.1`: bloquear empuja a inventar, y lo que encuentra los incompletos es
una lista, no un candado. Además no hay dónde bloquear — **el módulo no tiene una acción de
«entregar»**, así que un requisito de entrega no tiene punto de verificación. Afirmar lo
contrario sería inventar una compuerta que no existe.

#### A qué equipos se les exige

**Solo a los que salieron de una orden de fabricación.** Es el criterio preciso y se deriva del
dato, no de que alguien haya categorizado bien.

Resuelve de una vez dos casos que un criterio por categoría dejaba roto:

- **Los ROV de terceros.** `es_un_rov` cubre `ROV-MC` y `ROV-XX` por igual, así que derivarlo de
  ahí habría dejado a todos los equipos de clientes marcados como pendientes **para siempre**. Un
  indicador permanentemente en rojo para media flota se aprende a ignorar en una semana.
- **Los ROV-MC anteriores a Odoo.** Son de marca propia, así que la categoría diría «nuestro», y
  nunca van a tener estas pruebas porque se armaron antes de que existieran. **Decidido: se dan
  por buenos** — están en terreno funcionando y no se prueban retroactivamente. Sin MO no se les
  exige nada, y eso sale gratis del mismo criterio.

#### Qué cuenta como «hecha»

**Confirmada y con resultado *Aprobado* o *Aprobado con observaciones*.** Una prueba
**Rechazada** no cumple el requisito.

La distinción importa, y son dos cosas separadas:

> **El historial registra todos los intentos. El indicador refleja si el requisito está
> cumplido.**

Una prueba que falló existe, queda fechada y con su resultado, y el equipo **sigue apareciendo
como pendiente** hasta que se repita y pase. Es exactamente la secuencia «falló → se ajustó →
pasó» que la foto de un solo valor borraba (§ 4.5).

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

### 4.7 Duración y texto libre: un estándar, no dos

Hoy las **líneas** de una revisión tienen texto libre —`detalle` en cada chequeo, `observacion`
en cada sello— y la **cabecera** no. Es una inconsistencia real, y las pruebas de aceptación la
destapan porque necesitan las dos cosas.

Se resuelve con una regla que vale para todo el módulo:

> **Texto libre para el contexto. Catálogo para el contenido.**

**`duracion` (h)** entra en la cabecera: cuánto duró la prueba. **No es `esfuerzo_duracion`** —
esa es la corrida de resistencia *dentro* de la prueba. Una prueba en terreno de tres horas puede
no tener corrida de resistencia; una de banco tiene las dos, y son números distintos.

**Un texto libre en la cabecera**, y el nombre es parte del diseño: se llama **«Condiciones y
notas de la prueba»** y **no «Observaciones»**. *Observaciones* es una invitación a escribir ahí
los hallazgos, y eso mataría el catálogo que costó dos versiones construir. La ayuda del campo lo
dice explícito: lo que hace falta para interpretar los resultados y no cabe en ningún chequeo —
la marea, que el cliente pidió cortarla antes, que el generador andaba justo. **Los hallazgos van
en su pestaña.**

Entra a la lista de revisar en seis meses junto a `analisis_causa`: un campo «por si acaso» o no
se usa o se abusa, y las dos cosas hay que medirlas.

#### Un defecto que esto destapa

`_compute_resultado` exige `esfuerzo_resultado` para dar cualquier resultado. **Si una prueba en
terreno no lleva corrida de resistencia, esa revisión no podría quedar aprobada nunca** — se
quedaría en blanco para siempre, que es justo el modo de falla que `19.0.15.1.0` vino a arreglar
del otro lado.

El esfuerzo tiene que exigirse **solo donde es parte de la batería**, no siempre.

### 4.8 La numeración, y por qué obliga a congelar el tipo

Las pruebas de aceptación **son documentos que ve el cliente**, así que no deberían salir
numeradas dentro de la serie de reparaciones: una ficha de equipo nuevo llamada `REV/00042`,
intercalada entre reparaciones de otros equipos, se lee como un trámite interno.

Tres secuencias: **`REV/`** se queda con reparación —los registros existentes no cambian de
significado— y las de aceptación estrenan **`RND/`** y **`TRN/`**.

> **`RND/` y `TRN/`, y no `BAN/` y `TER/`**, que es lo que decía este párrafo. `BAN/` cayó
> con el nombre del tipo: se llamaba `banco` cuando esto se escribió y volvió a llamarse
> `rendimiento` en `19.0.18.0.0`. Y las tres letras son sin vocales a propósito: `REN/` se
> lee tan bien como *renting*, y esta empresa arrienda equipos — un prefijo ambiguo en un
> documento que ve el cliente es exactamente lo que la numeración por tipo viene a evitar.
> `TER/` cambió por simetría: tres consonantes las tres, para que se lean como una familia.

**Implementado en `19.0.19.0.0`, y con una corrección de este § :** congelar el tipo al
confirmar **no alcanza**. Entre crear y confirmar, el tipo se cambia —es lo corriente, porque
el botón del número de serie crea la prueba y recién ahí el técnico ve cuál era— y ahí el
prefijo asignado al crear queda mintiendo igual. Así que **el número se rehace cuando el tipo
cambia en borrador**, con nota en el chatter, y el correlativo viejo queda con un hueco: lo
mismo que ya pasa al borrar un borrador, y mucho mejor que un `TRN/` que es una reparación.

Y el candado no cuelga de `estado` sino de un campo propio, **`documento_emitido`**, que se
enciende al confirmar por primera vez y no se apaga. Colgarlo de `estado` dejaba abierta la
puerta obvia: devolver a borrador una prueba entregada, cambiarle el tipo y renumerarla.

**Y eso obliga a algo que hace falta igual:** hoy `tipo` es editable después de crear —hay tests
que cubren que cambiarlo ajusta el checklist—, así que un prefijo asignado al crear podría quedar
mintiendo, y renombrar rompería una referencia ya entregada. **`tipo` se congela al confirmar.**

No es un parche de la numeración: **cambiarle el tipo a una revisión confirmada no debería poder
hacerse de todos modos.** Es un documento emitido. Que hoy se pueda es un hueco que existe con o
sin las secuencias.

Queda anotado en el contrato del pipeline aunque `name` no sea clave ahí, porque el formato
cambia.

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

### 5.2 Cuatro baterías, y el criterio que las separa

Hay **cuatro**, no tres, porque el armado se verifica en un sistema distinto:

| Batería | Módulo | Se llena en | Cuándo |
|---|---|---|---|
| **Armado** | Calidad | Dentro de la orden de fabricación | Mientras se arma, antes de cerrar el casco |
| **Rendimiento** | mc_rov | N° de serie → botón | Equipo armado, en el banco |
| **Terreno** | mc_rov | N° de serie **o** orden de reparación → botón | En agua |
| **Reparación** | mc_rov | Orden de reparación | Cada vez que el equipo vuelve |

**El armado va en puntos de calidad** porque hay cosas que solo se pueden verificar antes de
cerrar el casco: sellos, o-rings, torque de penetradores, cableado interno. Un punto de calidad
se engancha a la operación; una batería plana no. Si el control no está amarrado al momento, se
responde después, de memoria, mirando un equipo cerrado.

**Y el criterio que ordena la de terreno no es la relevancia, es la física:**

> **Qué se puede medir efectivamente estando ahí.**

Ése es el corte, y lo aportó Paulo. No es «qué importa en terreno» —importa casi todo— sino qué
se puede hacer sin el taller detrás. De ahí salen las tres diferencias reales de esa batería, y
ninguna es arbitraria.

#### El caso que lo ilustra: la presión se verifica por dos medios

La misma pregunta —*¿se mantiene estanco?*— se responde con instrumentos distintos según dónde
estés:

| | Cómo se presuriza | Qué se mide |
|---|---|---|
| **Rendimiento** (taller) | Máquina de presión | bar + tiempo |
| **Terreno** | Descenso real | profundidad alcanzada |
| **Reparación** (taller) | Máquina de presión | bar + tiempo |

Por eso **el chequeo de estanqueidad está en las tres** y lo que cambia son las mediciones. La
profundidad en terreno **no es contexto: es la verificación de presión hecha por otro medio.**

### 5.3 Los chequeos

Los 24 del catálogo, más los 6 del armado. **Solo se listan las diferencias respecto de cómo
está hoy** — los otros 18 aplican a las cuatro baterías tal como ya están configurados.

| Chequeo | Hoy | Queda en | Por qué |
|---|---|---|---|
| Hélices en posición correcta | Fab · Rep · Terr | **Rep** | En rendimiento la posición ya se verifica funcionalmente: si una hélice está al revés, fallan los chequeos de movimiento |
| Chasis y estructura sin daño visible | Fab · Rep · Terr | **Rep** | Busca daño de uso |
| Penetradores y conectores sin daño | Fab · Rep · Terr | **Rep** | Ídem |
| Umbilical sin cortes ni aplastamientos | Fab · Rep · Terr | **Rep** | Ídem |
| Hélices sin daño ni desgaste | Fab · Rep · Terr | **Rep** | Busca desgaste |
| El software de superficie inicia y opera | Rep | **Rend · Terr · Rep** | Se acotó de más en 19.0.15.2.0 |
| *(nuevos)* Sellos y o-rings · Penetradores apretados · Cableado interno · Foto del interior · Registrar N° de serie | — | **Armado** | Solo verificables antes de cerrar el casco |

**Totales: Armado 5 · Rendimiento 18 · Terreno 17 · Reparación 24.**

Terreno es rendimiento **menos estanqueidad**, porque no hay máquina de presión en el muelle.

> **Los cinco chequeos de armado no salieron del taller: los escribió el diseño.** Razonados
> desde el principio de «antes de cerrar el casco», pero sin conocer cómo se arma. **Son la parte
> más débil de este documento** y deben ser lo primero que se corrija con retroalimentación real.
> Quedan porque tener algo que corregir es mejor que tener nada que mirar.

### 5.4 Las mediciones

Solo las diferencias respecto de hoy. **No cambian:** alimentación, temperaturas interior y
exterior, lugar, velocidad de la corriente y horómetro.

| Medición | Rend. | Terr. | Rep. |
|---|---|---|---|
| **Fecha de la prueba** | ✗ → **✓** | ✓ | ✓ |
| Duración de la prueba | ✓ | ✓ | ✗ → **✓** |
| Modelo de fuente | ✓ | ✗ → **✓** | ✗ → **✓** |
| Tensión de salida (V) | ✓ | ✗ → **✓** | ✓ |
| Umbilical usado *(y largo solo si es del taller)* | ✗ → **✓** | ✗ → **✓** | ✓ |
| **Presión alcanzada (bar) + tiempo** | ✗ → **✓** | ✗ *(va profundidad)* | ✗ → **✓** |
| Profundidad alcanzada (m) | ✗ | ✓ | ✗ |
| **Fuga de corriente (A)** — nueva | ✗ → **✓** | ✗ *(no hay instrumento)* | ✗ → **✓** |
| Consumo en reposo | ✓ | ✗ | ✗ → **✓** |
| Consumo bajo carga *(era «esfuerzo»)* | ✓ | ✗ | ✗ → **✓** |
| Funcionamiento continuo: duración + resultado | ✗ → **✓** | ✗ | ✓ |
| Ancho de banda subida / bajada | ✓ | ✗ → **✓** | ✓ |
| Conteo de luces internas / externas | ✗ → **✓** | ✗ → **✓** | ✓ |
| Limitación pilot gain (%) | ✓ | ✗ → **✓** | ✗ → **ficha** |
| Ganancia luz (%) | ✓ | ✗ → **✓** | ✗ → **ficha** |
| Versiones de software instaladas | ✗ → **✓** | ✗ | ficha |
| Condiciones y notas de la prueba | ✗ → **✓** | ✓ | ✗ → **✓** |

**Tres cosas que la comparación deja en evidencia**, y ninguna es de diseño — son huecos de hoy:

1. **La prueba de rendimiento no tiene fecha.** No se puede saber cuándo se probó un equipo en el
   banco. La de terreno sí la tiene.
2. **La presión no se registra en ninguna parte** —ni bar ni tiempo— aunque el estándar existe:
   2 h a 30 bar, 50 en algunos modelos, eventualmente hasta 100.
3. **La prueba de rendimiento no guarda la corrida de funcionamiento continuo**, que sí guarda la
   de reparación.

#### Ficha y prueba no compiten: dicen cosas distintas

Tres campos parecían duplicados y no lo son. La regla que los ordena:

> **La ficha guarda lo que el equipo *debería* tener. La prueba anota lo que *se encontró*.**

- Ficha: 6 luces. Prueba: se encendieron 4. `luces_difieren` lo marca solo.
- Ficha: ArduSub 4.1.0. Prueba: se encontró 4.0.2. Igual.
- Ficha: umbilical de 200 m con su número de serie. Prueba: se usó ése, o uno del taller.

**En fabricación va al revés:** ahí la prueba **determina** el valor y la ficha lo recibe. Por eso
las versiones de software se anotan en rendimiento y no se comparan.

Y donde dice **ficha**: no se vuelve a medir, se muestra el valor registrado para que el técnico
vea si cambió — el mismo bloque que ya funciona con las versiones de software desde
`19.0.15.2.0`.

**Consecuencia de agregar pilot gain y ganancia luz a terreno:** si se ajustan ahí, el valor de la
ficha queda viejo. **Quien ajusta, actualiza.**

### 5.5 Se retira la palabra «esfuerzo»

Significaba tres cosas a la vez: el consumo bajo carga en kWh de la ficha, la corrida de hora y
media en el bin, y todo el conjunto al hablar. **Asignársela a una de las tres deja a las otras
sin nombre**, así que se retira entera:

| Antes | Ahora |
|---|---|
| «Esfuerzo» (kWh, ficha) | **Consumo bajo carga** |
| `esfuerzo_duracion` / `esfuerzo_resultado` | **Prueba de funcionamiento continuo** |

*Funcionamiento continuo* y no *resistencia*, porque va a quedar al lado de «fuga de corriente» y
ahí resistencia se lee como ohmios. Y describe exactamente lo que pasa: el ROV anda hora y media
seguida a ver si aguanta.

Las tres mediciones eléctricas quedan como bloque: **fuga de corriente (A) · consumo en reposo ·
consumo bajo carga**.

### 5.6 Dos umbrales que se descartaron a propósito

El § 5.1 dice que en fabricación los umbrales existen. **Eso es cierto y aun así se descartaron
dos**, por razones que conviene dejar escritas o alguien los va a agregar creyendo que faltaban.

**La profundidad en terreno no se compara contra la profundidad máxima del modelo.** Existe el
dato —100, 250, 300, 500, 600, hasta 1000 según el modelo— y vive en la hoja de cotización. Pero
un umbral ahí **no mediría mejor: empujaría a arriesgar más.** Alguien bajaría un ROV a 250 m para
satisfacer al sistema cuando el trabajo pedía 40. Es la misma familia que el `required` de la
ficha — la restricción no mejora el dato, cambia la conducta, y para peor.

**La presión de taller tiene estándar** —2 h a 30 bar, 50 en algunos modelos, eventualmente hasta
100— **y aun así no se declara en la ficha ni se deriva.** Se evaluó pedir una «presión de prueba»
por modelo para poder derivar el chequeo, y **se descartó: los técnicos saben a cuánto va cada
equipo**, y exigir el valor por adelantado es agregarle trámite a algo que ya funciona.

Se registran los bar y el tiempo alcanzados; quien dice si aprobó es la persona. Es exactamente
el mismo trato que el ancho de banda, y por la misma razón: **el sistema guarda la medición y no
opina sobre ella mientras no tenga con qué.**

### 5.7 Un arreglo que viene gratis

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

### 6.1 Los huecos, revisados después del experimento

1. **Nadie ve las lecciones en el momento de armar, y ése es el riesgo del cementerio.**

   `product.template` y `stock.lot` no tienen ninguna relación con las alertas. Pero **el que
   arma un ROV no está en la ficha del producto: está en la orden de fabricación.** Ponerlas solo
   en el producto es casi tan inútil como dejarlas en la app de Calidad — las dos exigen que
   alguien se acuerde de ir a mirar.

   Y `mrp.production.quality_alert_ids` **no sirve para esto**: son las alertas *de esa MO*, no
   las lecciones históricas del modelo. Justo lo contrario de lo que hace falta.

   Lo que hay que construir es **la MO mostrando las alertas anteriores de su modelo**, y ahí una
   decisión de alcance: **solo las cerradas que tengan acción preventiva escrita.** Todas las
   alertas del modelo sería ruido; las que produjeron una acción preventiva son exactamente las
   lecciones.

   El producto y el lote también las llevan, pero como consulta de referencia. **La que importa
   es la de la MO**, porque es la única que aparece sin que nadie la busque.
2. **No hay puente alerta ↔ ECO.** «Cambiamos el BoM por esto» no queda registrado. Un campo.
3. **De la línea de trabajo a la alerta** falta un botón que la pre-llene desde `origen`. El
   puente ya está a medio construir: `repair.order.quality_alert_ids` existe de fábrica.

4. **La alerta no se crea sola al fallar un chequeo, y ése es el hueco que hace fallar todo lo
   demás.** Sin ella, el § 6 completo es un archivador que nadie llena.

   **Fallar un chequeo debe crear la alerta automáticamente**, en borrador, enlazada y sin
   título — visiblemente a medio llenar. Una alerta vacía en la lista es una deuda evidente; una
   lección que nunca se escribió es invisible.

   La objeción razonable es que fallar el chequeo también es manual, así que no se elimina la
   dependencia humana. Pero hay una asimetría que decide: **marcar el chequeo como fallido es
   obligatorio para avanzar; crear la alerta no lo pide nadie.** El primero está en el camino, el
   segundo es un desvío — y los desvíos no se toman a las siete de la tarde con un equipo a medio
   armar.

   **Y resuelve dos problemas con una sola pieza:** si la alerta nace en el momento del fallo, el
   fallo queda registrado ahí para siempre, así que **la alerta se vuelve el historial de
   intentos** que el chequeo no guarda (§ 2.1, hallazgo 1).

   **Acotado a los ROV, decidido el 2026-08-20 al implementarlo.** Este párrafo no lo
   calificaba, y así se implementó primero: cualquier chequeo fallado de la base abría su
   alerta. Se restringe a los productos de la rama de categorías ROV —la misma que resuelve
   `es_un_rov`— porque el costo se paga en la dirección equivocada: un punto de calidad en
   recepción de compras llenaría la lista de borradores vacíos, y **una lista larga de alertas
   que nadie salda destruye justamente la señal en que se apoya este párrafo**, que una alerta a
   medio llenar se lee como deuda pendiente.

   Si la raíz de categorías no resuelve, no se crea ninguna alerta y queda un WARNING en el log.
   Callar es la dirección segura del fallo, pero es silenciosa, así que tiene que avisar.

5. **`lot_ids` no se llena solo.** Es el campo que se destacó como «el alcance del daño», y en la
   prueba quedó vacío: cuando se creó la alerta, la orden todavía no tenía número de serie.
   Poblarlo tiene que ocurrir al terminar la orden, no al crear la alerta.

6. **La etapa «Resuelto» es ambigua.** Las etapas son *Nueva → Confirmado → Acción propuesta →
   Resuelto*, y la última no distingue «lo arreglamos en este equipo» de «lo cambiamos para todos
   los que vengan» — que es exactamente la distinción unidad/modelo sobre la que se construyó este
   diseño. Hace falta una etapa más, o una casilla.

7. **`quality.reason` tiene que alinearse con `ORIGENES`.** Le falta «Diseño o especificación»,
   que es uno de los dos orígenes que convierten una línea de reparación en una lección de
   manufactura. Sin esa opción, una falla de diseño se registra como «Operación de trabajo» y el
   cruce entre los dos lados miente.

   **La alineación no es por estadística, es por recuperación.** Con el volumen de fabricación el
   cruce numérico va a ser flaco; lo que se gana es que un mismo filtro encuentre las dos cosas.
   Cuesta un desplegable de seis valores y son datos, no código.

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

### 6.3 Por qué reparación lleva catálogo y fabricación texto libre

**Esto va escrito porque parece una inconsistencia y no lo es.** Sin la razón registrada, alguien
va a «arreglarlo» unificando los dos vocabularios, y va a romper justo lo que sigue.

Las fallas no desaparecen cuando un diseño madura: **se mudan.** La misma población de defectos
aparece en un sistema o en el otro según cuándo se manifieste.

| | Diseño inmaduro | Diseño maduro |
|---|---|---|
| Dónde aparece | Armando | En terreno, con los años |
| Volumen | Ráfaga sobre **un** modelo | Goteo sobre **toda** la flota |
| Cómo se lee | De corrido, en el momento | Estadísticamente, después |
| Forma correcta | **Texto libre** | **Catálogo** |

Un catálogo vale en proporción a las repeticiones. Con del orden de diez equipos al año, un
catálogo de fabricación da conteos de 1 y 2, y leer diez descripciones toma cinco minutos. En
reparación es al revés: el volumen crece con la flota y con los años, y la prosa se vuelve
ilegible.

Además, **en fabricación no importa la frecuencia sino no repetir**: una sola vez basta para que
valga escribirlo. Eso no necesita taxonomía, necesita que el registro exista y cuelgue del modelo.

Lo que sí se estructura en fabricación es **la forma del registro, no el vocabulario**: que
exista como registro y no como conversación, que apunte a `product_tmpl_id`, y que **la acción
correctiva esté separada de la preventiva** — esa separación es toda la estructura necesaria,
porque es la diferencia entre *arreglamos este equipo* y *cambiamos cómo se arman todos*.

**Y el remate:** una línea de reparación con `origen = falla_fabricacion` o `= diseno` **es un
patrón de fabricación descubierto tarde**. Los patrones de manufactura sí se detectan — pero en
los datos de reparación, con el volumen de la flota entera y años de exposición, que es
justamente lo que a fabricación le falta.

> **Fabricación no necesita detectar sus propios patrones, porque reparación se los detecta.**

Eso le da su lugar definitivo al puente del § 6.1.3: no es trazabilidad decorativa, es **el canal
por el que vuelve el patrón que fabricación no podía ver**. Y sube la importancia de `origen`,
que por suerte es obligatorio al cerrar la orden desde `19.0.13.0.0`.

**Cuándo revisitarlo:** probablemente nunca. Y si alguna vez, la señal no es un número sino que
alguien diga *«ya no me acuerdo de todas»* — ahí leerlas dejó de funcionar, y para entonces las
categorías salen de mirar las descripciones escritas en vez de adivinarlas.

### 6.4 La curva de maduración, y cuándo se pasa de MRP a PLM

Los hallazgos de fabricación no llegan a tasa constante: **llegan en ráfaga durante los primeros
equipos de un modelo y después bajan casi a cero.** Es la misma forma que la revisión técnica ya
razona para las unidades —falla infantil contra desgaste, § 16.3 de `revision-tecnica.md`— pero
aplicada **al diseño en vez de al equipo**.

De ahí sale algo que nadie pidió y que vale la pena: **contar alertas por modelo y por trimestre
dice cuándo un diseño maduró.** No hacen falta categorías, solo fecha y producto, que ya vienen
con la alerta. Y tiene plata detrás — no se puede cotizar a precio fijo ni comprometer plazos en
un modelo que todavía tira sorpresas. Da una regla operativa que hoy no existe: *«el MK3 lleva dos
trimestres sin alertas, se puede cotizar como producto maduro»*.

#### El punto de cambio

**El primer BoM se crea directo en MRP. Desde el primer cambio en adelante, todo es ECO.**

La línea no está entre inmaduro y maduro, está **entre crear y cambiar**. El primer BoM no es un
cambio: es escribir de qué quedó hecho lo que se acaba de armar.

El ECO vale por razones distintas en cada fase, y conviene no confundir la ceremonia con el
propósito:

- **Madurando:** es un **cuaderno**. Registra la secuencia de intentos, que es exactamente el
  historial de maduración. La ceremonia estorba.
- **Ya maduro:** es un **control**. Un cambio ahora hace que los equipos en terreno dejen de ser
  iguales a los que salen hoy, con consecuencias en repuestos, reparaciones y documentación. La
  ceremonia se justifica.

PLM soporta esa diferencia sin código: `mrp.eco.type` permite dos tipos con etapas y aprobaciones
distintas — uno *Maduración*, rápido y sin aprobación, y otro *Cambio en producto en producción*,
con aprobación.

> **Disciplina que hay que respetar o no sirve de nada:** desde que un modelo usa ECOs, su BoM no
> se edita nunca más a mano. PLM no lo impide, y **el uso mixto es peor que cualquiera de los dos
> puros**, porque la comparación entre versiones queda con agujeros y miente en silencio.

Y un matiz que evita una preocupación falsa: **de qué está hecho realmente un equipo no vive en el
BoM, vive en sus movimientos de stock.** El BoM versionado registra la *intención*; la
trazabilidad registra el *hecho*. Dos preguntas distintas, las dos respondidas.

#### Y con eso, las lecciones aprendidas dejan de ser un modelo

> **El historial de maduración de un diseño es la cadena de alertas y ECOs de ese modelo, en
> orden:** qué encontramos → qué cambiamos → qué encontramos después.

Ya está casi todo modelado. Falta el campo que los une.

## 7. Qué se retira

- **`tipo = fabricacion`** de la revisión, reemplazado por `rendimiento` — hecho en `19.0.16.0.0`.
- **La pestaña «Prueba en Terreno»** del número de serie, y sus columnas:
  `mc_fecha_prueba`, `mc_lugar`, `mc_profundidad`, `mc_velocidad_corriente`, `mc_alimentacion`,
  `mc_tiempo_prueba_terreno`, `mc_temperatura_interior_terreno`,
  `mc_temperatura_exterior_terreno`, `mc_observacion`.
- Las columnas de prueba de laboratorio del lote, una vez que la prueba de rendimiento las
  reemplace.

Y **`observacion` en la línea de inspección de sellos pasa a `detalle`.** Hoy hay tres nombres
para la misma idea: `detalle` en la línea de chequeo, `detalle` en la de hallazgo, y
`observacion` en la de sellos. Es el mismo «dos nombres para una cosa» que ya se corrigió en la
pestaña de la revisión y en el chequeo de acro. Como esta versión lleva migración de todos modos,
sale gratis; si no, dentro de un año alguien escribe un reporte y se pregunta por qué ese campo
se llama distinto.

Y un renombre que no es cosmético: **«En reposo» / «Esfuerzo» del lote pasan a «Consumo en
reposo» / «Consumo bajo carga».** Hoy la palabra *esfuerzo* significa dos cosas distintas en el
módulo: en la ficha del lote es **un consumo en kWh bajo carga** —hace pareja con el consumo en
reposo, por eso están uno debajo del otro—, y en la revisión es **la corrida de resistencia**, el
ROV andando una hora y media en un bin con agua.

**Este renombre se aplazó al implementar (2026-08-20), por una razón que el diseño no había
visto:** «En reposo» y «Esfuerzo» son dos de las columnas de laboratorio del lote, o sea que la
misma tanda de trabajo las borra. Renombrarlas antes es trabajo que se elimina un PR después, y
la ambigüedad que evitan solo existe en la ventana entre los dos. **La decisión de vocabulario
sigue en pie para los campos nuevos de la revisión**, que es donde de verdad importa.

Sin este renombre, una revisión de `tipo = banco` tendría adentro un campo «esfuerzo» que
significa distinto del «Esfuerzo» que hoy vive dentro de la prueba de rendimiento. Se renombra el
del lote y no el de la revisión porque *prueba de esfuerzo* es el término estándar para una
corrida de resistencia, y porque «consumo en reposo / bajo carga» es lo que el par realmente
mide.

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
  son pruebas de rendimiento sucesivas. **Vuelve cuando tres o cuatro rediseños muestren qué
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

1. ~~**Si Calidad guarda el historial de intentos.**~~ — **resuelto el 2026-08-18: pisa.** Ver
   § 2.1, hallazgo 1, y su efecto sobre el diseño en § 6.1.4. Se probó en `odoo_staging` y no hizo
   falta `odoo_lab`: los módulos ya estaban instalados en producción, así que la copia los trae.
2. ~~**El contenido exacto de las dos baterías nuevas.**~~ — **cerrado el 2026-08-19**, § 5.2 a
   § 5.6. Lo único que queda de ese punto son **los cinco chequeos de armado**, que los escribió
   el diseño y no el taller: se implementan y se corrigen con la primera retroalimentación real.
3. ~~**Si la revisión de terreno necesita un tiempo de prueba propio y un texto libre.**~~ —
   **resuelto el 2026-08-18: las dos, sí.** Ver § 4.7. Mi preliminar era que el texto libre no, y
   estaba mal: las líneas ya tenían texto libre y la cabecera no, así que el estándar estaba roto
   de antes. Lo que faltaba no era prohibirlo sino nombrarlo bien.
4. **Los mínimos y máximos por modelo.** No bloquean esto —§ 9— pero si no existen escritos, eso
   mismo es el hallazgo.
5. **Empezar con un solo modelo de ROV** y una MO completa de punta a punta antes de escribir
   código. Se está digitalizando un proceso hoy físico: no hay costumbre que aprovechar, hay
   costumbre que cambiar, y eso se descubre haciendo una.

### Lo que se decidió el 2026-08-18, y no vuelve a discusión

Todo esto lo revisó y aprobó el supervisor.

- **Fabricación registra en texto libre, reparación con catálogo** — § 6.3, con su porqué, que
  hay que conservar o alguien va a «arreglar» la asimetría.
- **La causa raíz sí se alinea** con `ORIGENES`, por recuperación y no por estadística. Con esa
  lista basta para cubrir el origen de las fallas; el texto libre conserva el detalle del oficio
  de madurar un diseño.
- **Fallar un chequeo crea la alerta automáticamente**, en borrador — § 6.1.4.
- **El primer BoM se crea en MRP; desde el primer cambio, todo es ECO** — § 6.4, con dos tipos de
  ECO según la fase, y la disciplina de no volver a editar el BoM a mano.
- **Se cuentan alertas por modelo y por trimestre** para saber cuándo un diseño maduró.
- **Las cuatro baterías**, con el criterio de terreno —*qué se puede medir efectivamente estando
  ahí*— y la presión verificada por dos medios según dónde se esté (§ 5.2).
- **Se retira la palabra «esfuerzo»** del vocabulario (§ 5.5).
- **Dos umbrales descartados a propósito**: la profundidad en terreno y la presión de taller
  (§ 5.6).


- **`tipo` compartido**, no modelo nuevo (§ 4.1).
- **Solo se exige a los equipos con MO**; los ROV-MC anteriores a Odoo se dan por buenos.
- **«Hecha» = confirmada y aprobada**; una prueba rechazada se registra y no cumple el requisito.
- **No se bloquea nada**: indicador y filtro, como el aviso amarillo de la ficha.
- **Tres secuencias** `REV/` · `RND/` · `TRN/`, y `tipo` congelado una vez emitido el documento.
- **Las lecciones se muestran en la MO**, filtradas a las cerradas con acción preventiva.
- **El par «En reposo» / «Esfuerzo» del lote se renombra** para que *esfuerzo* signifique una
  sola cosa.
