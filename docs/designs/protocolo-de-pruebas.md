# Diseño: protocolo de pruebas y análisis de fallas

**Versión objetivo:** `19.0.6.0.0` (segmento `X`: mueve datos y requiere migración)
**Estado:** propuesta, pendiente de aprobación
**Fecha:** 2026-08-11

---

## 1. El problema

En el taller llenan a mano una *ficha de equipo reparado*: responsable, fecha, modelo, serie,
cliente, inspección física, pruebas de esfuerzo / presión / leak / navegación / sistema /
luces, y observaciones al final. Nada de eso existe en Odoo como tal.

Lo que sí existe es peor que nada: **24 campos de `stock.lot` que parecen ficha técnica pero
son el resultado de una sola prueba.**

| En `stock.lot` hoy | Lo que realmente es |
|---|---|
| `mc_fuente_energia`, `mc_tension_salida`, `mc_modelo_fuente` | Con qué se alimentó *una* prueba |
| `mc_consumo_corriente`, `mc_en_reposo`, `mc_esfuerzo` | Medición de *una* prueba de esfuerzo |
| `mc_prueba_leak` | Resultado de *una* prueba de leak |
| `mc_ancho_banda`, `mc_subida`, `mc_bajada` | Medición de *una* prueba de sistema |
| `mc_limitacion_pilot_gain`, `mc_ganancia_luz` | Ajustes con los que se corrió *una* prueba |
| `mc_tiempo_prueba_lab`, `mc_temperatura_interior_lab`, `mc_temperatura_exterior_lab` | Condiciones de *una* prueba |
| Página *Prueba en Terreno* completa (9 campos) | *Una* salida a terreno |

Como viven en el lote hay **un solo valor por equipo**. Cuando el ROV vuelva el próximo año y
se le repitan las pruebas, los números del año pasado se sobrescriben. El ancho de banda que
bajó de 90 a 40 Mbps, la corriente en reposo que subió, el leak que empezó a fallar
intermitente — **la degradación se destruye en cada escritura, y es exactamente el análisis
que se quiere hacer.** Nada avisa.

Es el patrón recurrente del módulo (`es_un_rov`, `mc_estado_operativo`) llevado un paso más
allá: no es que el dato se desincronice, es que se borra.

Segundo problema: las observaciones son texto libre (`observaciones_salida`,
`mc_observacion`, `detalle` en las líneas de trabajo). Un historial de fallas construido
sobre texto libre no se puede agregar, contar ni comparar.

---

## 2. Decisiones tomadas

| Decisión | Elección | Quién |
|---|---|---|
| Dónde viven los resultados de prueba | Modelo nuevo, N por equipo | — |
| Relación con la orden de reparación | `repair_id` **opcional** | Paulo: "técnico que fabrica y/o repara" |
| Responsable | `hr.employee`, no `res.users` | Paulo: 3-4 logins para no pagar suscripciones |
| Historial de configuración | `tracking=True` + snapshot de versiones en el protocolo | Paulo preguntó; no se construye modelo SCD-2 |
| Pilot gain y ganancia de luz | Se mueven al protocolo | Paulo: "se pueden mover en cada prueba" |
| `item_2` … `item_5` | Se eliminan | 0 de 10 órdenes los usan; etiqueta original ya era "Ítem 2" |
| Observaciones | Catálogo de hallazgos, no texto libre | Paulo |
| Chequeos que crecen (6DOF, sonar…) | Catálogo configurable | Paulo preguntó por 6DOF |
| Cliente vs dueño en el protocolo | Ninguno propio: ambos derivados | Cierra la separación de `19.0.5.0.0` |
| Firma / aprobación con nombre | Se posterga; `estado: confirmado` es la aprobación por sistema | Paulo: "lo vemos luego" |
| Fotos de hallazgos | Se implementan al final, con `fields.Image` (§ 12) | Paulo: "dejémoslo para el final" |
| Ficha de papel como fuente | **No.** El diseño se hizo sin verla a propósito | Paulo: "mi trabajo es mejorarlo, no replicarlo" |

---

## 3. Los tres tipos de dato

| Qué | Dónde | Cardinalidad |
|---|---|---|
| **Configuración del equipo** — chasis, motores, tarjetas, versiones, sensor de presión, umbilical propio, cantidad de luces | `stock.lot` (donde ya está) | 1 por equipo; cambia si lo modifican |
| **Protocolo de pruebas** — la ficha de papel | `mc.rov.protocolo` (nuevo) | N por equipo, 1 por sesión de pruebas |
| **Hallazgos** — qué se encontró | Líneas del protocolo, contra catálogo | N por protocolo |

---

## 4. Modelo de datos

Cinco modelos nuevos: una cabecera, dos modelos de línea, dos catálogos.

### 4.1 `mc.rov.protocolo` — cabecera

```
name                    Char       secuencia PROT/00001, readonly
lot_id                  M2o stock.lot        required, index
repair_id               M2o repair.order     opcional, index, ondelete set null
tipo                    Selection  fabricacion | recepcion | entrega | terreno   required
fecha                   Date       required, default hoy
responsable_id          M2o hr.employee      default env.user.employee_id
estado                  Selection  borrador | confirmado                          default borrador
```

**`repair_id` es opcional a propósito.** Un ROV nuevo pasa por el mismo protocolo antes de
despacharse y ahí no hay orden de reparación. Si el protocolo colgara de la orden, toda la
fabricación quedaría fuera del análisis.

**`tipo` con recepción y entrega** permite lo que ya hacen: probar al recibir, arreglar, y
volver a probar antes de entregar. Dos protocolos, misma visita. La comparación entre ambos
es la evidencia de que el trabajo sirvió.

**El protocolo de recepción es la actividad de diagnosticar**, y ahí es donde este modelo se
une con el registro de fallas. Conviene no confundir dos niveles:

- `tipo_diagnostico` (tipo de intervención) sigue siendo lo que ya es: el tipo de **visita**.
  No cambia nada de él.
- El **protocolo de recepción** es el paso de diagnóstico, y ocurre en toda visita — sea
  reparación, mantención o diagnóstico puro.
- Una visita de solo diagnóstico produce un protocolo de recepción con hallazgos y **cero
  líneas de trabajo**. Ese es su resultado completo, y hoy no queda registrado en ninguna
  parte: el diagnóstico termina en el texto libre de observaciones y se pierde.

**`estado`** existe para que el protocolo se pueda llenar por partes. En `borrador` se guarda
incompleto; al confirmar se valida que todos los chequeos estén respondidos y el registro
queda en solo lectura. Sin eso, un checklist a medio llenar no se distingue de uno completo.

**`responsable_id` no es `required` a nivel de modelo, sí en la vista.** Los registros que
cree la migración no tienen a quién atribuirse, y un empleado ficticio tipo "Sin registrar"
ensuciaría la lista de empleados para siempre. Un protocolo migrado se reconoce porque el
responsable está vacío, que es la verdad.

Derivados, sin columna propia:

```
product_id       related lot_id.product_id            readonly   el modelo del ROV
propietario_id   related lot_id.mc_propietario_id     readonly   el dueño registrado
partner_id       related repair_id.partner_id         readonly   quién paga esta visita
es_un_rov        related lot_id.es_un_rov             readonly
```

**Sobre la nomenclatura cliente/dueño:** el protocolo no lleva contacto propio. `propietario_id`
es de quién es el equipo (dura años); `partner_id` es a quién se le factura esta visita (dura
lo que dura la orden). Agregar un tercer contacto aquí reabriría justo la confusión que se
cerró en `19.0.5.0.0`.

Configuración al momento de la prueba — las cuatro versiones que más cambian:

```
version_qground     Char
version_px4         Char
version_navigator   Char
version_ardusub     Char
```

Se proponen desde el lote al crear el protocolo. Se duplican **solo estas cuatro** porque son
las únicas que se quieren leer *en la misma fila* que las mediciones: el ancho de banda de esa
prueba junto a la versión de firmware de esa prueba. El resto de la configuración se resuelve
con `tracking` (§ 6).

Mediciones — los campos que bajan de `stock.lot`:

```
--- esfuerzo ---
umbilical_prueba          Boolean    ¿se usó umbilical de prueba en vez del propio?
umbilical_prueba_largo    Float m    largo del umbilical de prueba
umbilical_equipo_largo    Float m    propuesto desde lot_id.mc_longitud, editable
umbilical_difiere         Boolean    computed, largo medido != el de la ficha
alimentacion              Selection  UPS | Generador | Transformador
modelo_fuente             Char
tension_salida            Integer V
consumo_corriente         Char
consumo_reposo            Float kWh
consumo_esfuerzo          Float kWh

--- parámetros de trabajo ---
limitacion_pilot_gain     Integer %
ganancia_luz              Integer %

--- sistema ---
ancho_banda               Char
subida                    Float Mbps
bajada                    Float Mbps

--- luces ---
luces_internas            Integer
luces_externas            Integer
luces_total               Integer    computed, internas + externas
luces_ficha               Integer    related lot_id.mc_cantidad_luces, readonly
luces_difieren            Boolean    computed, total != ficha

--- condiciones ---
tiempo_prueba             Float h
temperatura_interior      Float °C
temperatura_exterior      Float °C

--- solo cuando tipo = terreno ---
lugar                     Char
profundidad               Integer m
velocidad_corriente       Float knots
```

Dos comparaciones automáticas que hoy nadie hace:

- **`umbilical_difiere`** compara el largo medido contra el de la ficha. El campo se propone
  desde el lote pero **queda editable**: en el papel anotan los dos largos, y si lo anotan es
  porque puede no coincidir con lo registrado. De solo lectura, el sistema impediría anotar
  la verdad.
- **`luces_difieren`** compara el conteo de la prueba contra la especificación del equipo. Si
  el ROV debería tener 6 luces y se contaron 4, el sistema lo dice. Es una de las cosas que
  la inspección busca.

Resultado del protocolo, derivado (no editable, igual que `mc_estado_comercial` y
`mc_estado_operativo`):

```
resultado   Selection  aprobado | aprobado_con_observaciones | rechazado   computed, store
```

Regla, en orden de precedencia:

1. Algún chequeo en `no_ok`, o algún hallazgo con severidad `impide_operar` → **rechazado**
2. Algún hallazgo → **aprobado con observaciones**
3. Si no → **aprobado**

### 4.2 `mc.rov.chequeo` — catálogo de chequeos

```
name             Char       required
sequence         Integer
seccion          Selection  inspeccion_fisica | presion | leak | navegacion | otro
por_componente   Boolean    si la línea debe indicar sobre qué componente se hizo
active           Boolean    default True
```

**Aquí se contesta la pregunta del 6DOF.** Agregar *lateral*, *yaw*, *roll* o *pitch* es crear
cuatro registros desde `Reparaciones → Configuración`, no tocar código ni desplegar. Lo mismo
para sonar, USBL o cualquier chequeo que aparezca en un modelo nuevo.

`seccion` sí es un `Selection`, o sea que agregar una **sección** nueva requiere código. Es un
límite deliberado: las secciones son la estructura de la ficha y son estables; los chequeos
dentro de ellas son operativos y cambian. Un catálogo de secciones sería un catálogo de
catálogos para resolver un problema que no existe.

### 4.3 `mc.rov.protocolo.chequeo` — línea de chequeo

```
protocolo_id    M2o mc.rov.protocolo      required, ondelete cascade
sequence        Integer
chequeo_id      M2o mc.rov.chequeo        required
componente_id   M2o mc.rov.componente     required si chequeo_id.por_componente
resultado       Selection  ok | no_ok | na
detalle         Char
```

Las líneas se generan solas al crear el protocolo, con todos los chequeos activos de la
sección que corresponda al `tipo`. **La inspección física es un checklist, no una lista de
excepciones:** se recorren los cinco componentes siempre y "revisado y limpio" queda
registrado. Si solo se anotaran los hallazgos, *el joystick estaba limpio* sería
indistinguible de *nadie miró el joystick*.

`resultado` no es `required` en el campo — lo valida el paso a `confirmado`. Así se puede
guardar a medio llenar sin poder cerrar incompleto.

### 4.4 `mc.rov.hallazgo` — catálogo de hallazgos

```
name       Char       required
familia    Selection  terceros | estanqueidad | estructura | electrico | funcional | otro
sequence   Integer
active     Boolean    default True
```

Este catálogo es **lo que falta hoy**. `mc.rov.linea.falla` ya es estructurado (componente +
subtipo + acción), pero `accion_id` es *lo que se hizo*, no *lo que se encontró*. No existe
vocabulario de hallazgos, y sin él el análisis de fallas se apoya en el `detalle` de texto
libre.

### 4.5 `mc.rov.protocolo.hallazgo` — línea de hallazgo

```
protocolo_id    M2o mc.rov.protocolo      required, ondelete cascade
sequence        Integer
componente_id   M2o mc.rov.componente     required
subtipo_id      M2o mc.rov.subtipo        domain [('componente_id','=',componente_id)]
hallazgo_id     M2o mc.rov.hallazgo       required
severidad       Selection  informativo | atencion | impide_operar   required, default atencion
detalle         Text                      complemento, no reemplazo
```

Reusa `mc.rov.componente` y `mc.rov.subtipo`, los mismos catálogos de las líneas de trabajo.
Eso es lo que permite correlacionar: *dónde* se encuentran los hallazgos y *dónde* se hacen
los trabajos hablan el mismo idioma.

`detalle` sigue existiendo, pero **como complemento del hallazgo, no en su lugar**. Sin la
parte estructurada el técnico escribe "se vio raro el motor" y no hay nada que agregar.

### 4.6 Cambio en `mc.rov.linea.falla`

```
hallazgo_origen_id   M2o mc.rov.protocolo.hallazgo   opcional
```

Es el campo que cierra el circuito:

```
protocolo de recepción → hallazgo → línea de trabajo (acción + HH) → protocolo de entrega
```

Con eso se puede preguntar: *de los hallazgos de recepción, cuántos se cerraron*; *qué
componente concentra los hallazgos*; *cuántos equipos llegan con intervención de terceros*;
*cuánto demora en promedio cada acción*; *qué hallazgo predice una falla posterior*.

Se deja opcional: un trabajo puede surgir sin hallazgo previo, y un hallazgo puede quedarse
sin resolver — que también es un dato.

---

## 5. Qué sale de `stock.lot`

**Se van al protocolo (24 campos):**

`mc_modelo_fuente`, `mc_fuente_energia`, `mc_tension_salida`, `mc_consumo_corriente`,
`mc_en_reposo`, `mc_esfuerzo`, `mc_limitacion_pilot_gain`, `mc_ganancia_luz`,
`mc_tiempo_prueba_lab`, `mc_prueba_leak`, `mc_ancho_banda`, `mc_subida`, `mc_bajada`,
`mc_temperatura_interior_lab`, `mc_temperatura_exterior_lab`, `mc_fecha_prueba`, `mc_lugar`,
`mc_profundidad`, `mc_velocidad_corriente`, `mc_alimentacion`, `mc_tiempo_prueba_terreno`,
`mc_temperatura_interior_terreno`, `mc_temperatura_exterior_terreno`, `mc_observacion`

`mc_fuente_energia` (página Umbilical) y `mc_alimentacion` (página Prueba en Terreno) eran la
**misma selección con los mismos tres valores, duplicada**. Colapsan en un solo
`alimentacion` en el protocolo, distinguidas por el `tipo`.

**Se queda como especificación:** chasis, modelo / N° / posición de motores, pesos, sensor de
presión, tarjetas de comunicación, versiones de software, controlador de vuelo, brazo y salida
de brazo, cantidad de luces, dispositivos extra, N° de serie / longitud / diámetro / peso del
umbilical.

**Desaparecen del formulario del lote:** la sección *Prueba de rendimiento*, la sección
*Parámetros de trabajo* y la pestaña *Prueba en Terreno* completa.

---

## 6. Historial de configuración

La configuración también cambia: las versiones de software se actualizan en cada upgrade
—*Conversión / Upgrade* es un tipo de intervención existente—, los motores pasan de T200 a
T500, el umbilical se reemplaza por otro con distinto número de serie. Sin historial no se
puede preguntar *"¿con qué versión de ArduSub estaba corriendo cuando falló el motor?"*.

**Solución: `tracking=True` en los campos de configuración de `stock.lot`.** `stock.lot`
hereda `mail.thread` —por eso funciona el `message_post` de la baja—, así que cada cambio
queda en el chatter con fecha y valor anterior → valor nuevo, en `mail_tracking_value`,
consultable por SQL. Cero modelos nuevos, cero migración, una palabra por campo.

**No se construye** un `mc.rov.configuracion.historial` estilo el de propietarios. Veinte
campos por períodos es caro, y entre el `tracking` y el snapshot de versiones del protocolo
quedan cubiertas todas las preguntas planteadas hasta ahora. Si aparece una que ninguno
responde, se construye entonces — con la pregunta en la mano.

**Dos límites, dichos explícitamente:**

- `tracking` registra **desde que se activa**. Lo anterior se perdió. Hoy no cuesta nada
  porque no hay datos reales.
- Con logins compartidos, el *quién* del chatter va a decir "Trabajadores". El *cuándo* y el
  *de qué a qué* —la parte que importa— quedan igual. Y el quién que de verdad interesa
  —quién hizo el trabajo físico— es `responsable_id`, que es un dato distinto del autor del
  registro y haría falta aunque cada técnico tuviera su propio login.

---

## 7. Catálogos semilla

### Chequeos

| Sección | Chequeo | Por componente |
|---|---|---|
| Inspección física | Marcas de plumón | sí |
| Inspección física | Sellos antiguos | sí |
| Inspección física | Sellos nuevos | sí |
| Presión | Estanqueidad bajo presión | no |
| Leak | El sensor de leak responde | no |
| Navegación | Hélices en posición correcta | no |
| Navegación | Movimiento vertical | no |
| Navegación | Movimiento horizontal | no |

### Componentes que se agregan al catálogo

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
| Otro | Sin hallazgos |

---

## 8. Vistas y navegación

| Dónde | Qué |
|---|---|
| `Reparaciones → Protocolos de prueba` | Lista y formulario |
| `Reparaciones → Configuración` | Chequeos ROV, Hallazgos ROV (junto a Componentes y Acciones) |
| Botón inteligente en `stock.lot` | "Protocolos" con contador → **el historial del equipo; esta es la serie de tiempo** |
| Página en `repair.order` | Los protocolos de esa visita |
| Reporte QWeb sobre `mc.rov.protocolo` | La versión digital de la hoja de papel, imprimible y adjuntable |

El reporte también tapa un hueco que existe hoy: el técnico llena trabajos, causa raíz y
observaciones de salida, y **nada de eso sale en un PDF** — el único documento imprimible es
el presupuesto por defecto de Odoo.

---

## 9. Migración `19.0.6.0.0`

Pasos en orden estricto. El orden importa: los valores se leen **antes** de borrar las
columnas, igual que `_convertir_bajas` en `19.0.5.0.0`.

1. **Sembrar catálogos** — chequeos, hallazgos, componentes nuevos (vía `data/`, no SQL).
2. **Rescatar mediciones** — por cada lote con al menos un valor no vacío, crear un
   `mc.rov.protocolo`:
   - `tipo` = `terreno` si hay datos de terreno, si no `recepcion`
   - `fecha` = `mc_fecha_prueba`, o `write_date::date` si está vacía
   - `responsable_id` vacío, con `mc_observacion` volcado a un hallazgo de familia *Otro* y
     detalle con el texto original
   - Motivo en el chatter indicando que es un registro migrado y que la fecha es aproximada

   **Cuidado con `mc_prueba_leak`.** Hoy ese booleano significa **"se hizo la prueba"**, no
   **"la prueba pasó"** — el resultado siempre terminó en el texto libre de observaciones.
   La migración no debe convertirlo en `resultado = ok`, porque el dato de si pasó nunca
   existió. Se convierte en una línea de chequeo con el resultado sin responder.
3. **Eliminar columnas** — los 24 campos movidos más `item_2` … `item_5`.
4. **Activar `tracking`** — no requiere migración, pero conviene registrar en el log desde qué
   fecha hay historial.

**En su base de datos hoy esto produce como mucho 3 protocolos desechables**, porque las tres
series de producción son de prueba. El paso 2 se escribe igual, para que el módulo sea correcto
para cualquiera que despliegue después con datos reales.

**Este es el momento más barato para hacerlo.** Hecho después de cargar la flota, hay que
reconstruir a mano de qué visita venía cada medición, y en la mayoría de los casos no se va a
poder.

---

## 10. Contrato del pipeline

`docs/integrations/pipeline.md` exige coordinar por PR antes de cambiar cualquier campo
listado. Esta versión toca varios:

- **`item_2..5` se eliminan.**
- **24 campos `mc_*` salen de `stock.lot`.** El doc los cubre con una línea genérica
  *(48 ficha técnica `mc_*` fields — TBD list in Phase 1)*, así que hay que enumerar los que se
  van.
- **Modelos nuevos** que el pipeline va a querer: `mc.rov.protocolo` y sus dos modelos de
  línea son, de aquí en adelante, **la fuente principal del análisis de fallas**.

**Además hay que corregir el contrato, que ya está desactualizado:** lista `estado_final`,
`garantia_reparacion` y `fecha_garantia` en `repair.order`, y esos tres campos **no existen en
el código** — solo en ese documento.

---

## 11. Correcciones que se arrastran

Salieron de la revisión del módulo de reparación y tocan los mismos archivos. Se pueden
separar en su propio PR si este crece demasiado.

| Corrección | Por qué ahora |
|---|---|
| Reordenar pestañas: Trabajos realizados → Piezas → Resultado → Notas | Ya se va a agregar una pestaña de protocolos; se ordena todo de una vez |
| `mc_total_horas` a `store=True` | Hoy está en la lista y no se puede ordenar, filtrar ni agrupar. Columna nueva ⇒ **sin migración** |
| Constraint: no cerrar una orden sin `tipo_intervencion_ids` | Sin tipo, la orden no cuenta para mantención, reparación, contadores ni reloj. Falla silenciosa idéntica a la de `fecha_entrega_real` |
| `_order = "sequence, id"` en `mc.rov.linea.falla` | Todas las líneas nacen en `sequence = 10`; hoy el orden lo decide PostgreSQL |
| `fecha` con default hoy en `mc.rov.linea.falla` | Se deja en blanco casi siempre |
| Vista de búsqueda para `repair.order` | No se puede filtrar por tipo ni agrupar por causa raíz |
| `causa_raiz` baja a la línea | Una orden puede tener tres causas distintas; hoy hay que elegir una |

---

## 12. Fase posterior: fotos de los hallazgos

**Decidido, pero fuera del alcance inicial** (Paulo, 2026-08-11: "dejémoslo para el final").

El almacenamiento resultó no ser un problema. Estado del VPS al 2026-08-11:

| Dato | Valor |
|---|---|
| Disco | 75 GB, 50 GB libres (32% usado) |
| Adjuntos actuales | 1.037 archivos, 86 MB |
| `ir_attachment.location` | vacío ⇒ **van a disco, no a la base** |

Que no vayan a la base es lo que más importa: no inflan los backups de PostgreSQL.

Cuando se implemente, el campo va en la **línea de hallazgo** y debe ser
`fields.Image(max_width=1920, max_height=1920)`, **no `fields.Binary`**. `Image`
redimensiona al guardar y deja una foto de celular de 4 MB en 300-500 KB; `Binary` guarda el
original completo. Con `Image` caben unas 125.000 fotos antes de que el disco importe.

## 13. Preguntas abiertas

1. **¿El responsable va también en la línea de trabajo?** Si quieren costear HH por técnico,
   sí: dos técnicos pueden trabajar la misma orden. Hoy el diseño lo pone solo en la cabecera
   del protocolo.
2. **¿`resultado` debe poder forzarse?** El diseño lo deriva de chequeos y hallazgos. Si un
   técnico necesita rechazar un protocolo por algo que el catálogo no captura, hace falta un
   override — pero eso rompe la regla de "derivado no editable" que rige el resto del módulo.
3. **¿Qué chequeos de navegación aplican a cada modelo?** El catálogo permite agregarlos; falta
   saber si un ROV de 4 grados debería mostrar los chequeos de 6DOF como *no aplica* o no
   mostrarlos.

---

## 14. Verificación

1. **Tests** — clases nuevas: `TestMcRovProtocolo` (cabecera, derivados, `resultado` calculado,
   generación automática de líneas), `TestMcRovProtocoloChequeo` (validación al confirmar),
   `TestMcRovProtocoloHallazgo` (severidad y precedencia), `TestMcRovLineaFallaHallazgo` (el
   enlace). Más los casos de las correcciones del § 11.
2. **Auditoría previa al deploy** — cuántos lotes tienen mediciones que la migración va a
   convertir:
   ```sql
   SELECT count(*) FROM stock_lot
    WHERE mc_ancho_banda IS NOT NULL OR mc_subida <> 0 OR mc_bajada <> 0
       OR mc_fecha_prueba IS NOT NULL OR mc_tension_salida <> 0;
   ```
3. **Manual, en staging** — crear un protocolo de recepción sobre una serie ROV, confirmar que
   las líneas de chequeo se generan solas, que no deja confirmar con chequeos sin responder,
   que `resultado` reacciona a un hallazgo `impide_operar`, y que el reporte imprime.
4. **Rollback** — según `docs/runbooks/deploy.md`. **Volver atrás el código no restaura los 24
   campos borrados**; para eso está el backup de la base.
