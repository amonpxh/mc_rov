# Cómo se sigue el trabajo entre los módulos

**Para quién:** cualquiera que trabaje con ROVs en Odoo — taller, fabricación, comercial.

**Para qué:** son varios módulos y ninguno cuenta la historia completa. Esto dice **qué app
abrir en cada momento y qué queda registrado**, sin entrar en cómo está construido.

> Si buscas las razones de diseño, están en [`designs/fabricacion.md`](designs/fabricacion.md) y
> [`designs/revision-tecnica.md`](designs/revision-tecnica.md). Este documento es el mapa, no el
> plano.

---

## Mapa rápido

| Quiero… | Abro |
|---|---|
| Armar un ROV | **Fabricación** → Órdenes de fabricación |
| Verificar el armado paso a paso | **Calidad** → aparece dentro de la orden |
| Registrar un problema que va a repetirse | **Calidad** → Alertas |
| Probar el equipo terminado | **Inventario** → N° de serie → *Nueva prueba de rendimiento* |
| Probarlo en agua antes de entregar | **Inventario** → N° de serie → *Nueva prueba en terreno* |
| Ver o llenar la ficha técnica de un equipo | **Inventario** → Números de serie |
| Recibir un equipo con falla | **Reparaciones** → Órdenes |
| Diagnosticar qué le pasa | **Reparaciones** → dentro de la orden, pestaña Revisiones |
| Cambiar cómo se fabrica un modelo | **PLM** → ECO sobre la lista de materiales |

---

## No es una sola línea, son tres

Los procesos no van uno detrás de otro. Corren en paralelo y a ritmos distintos:

```
UNIDAD     fabricar → aceptar → entregar → operar → mantener/reparar → baja
                                                          │
                                                          ↓ origen = diseño / manufactura
MODELO     diseñar → madurar (ECO tras ECO) ─────────→ maduro
                        ↑
COMERCIAL  cotizar → vender/arrendar → facturar
```

- **La unidad** sí es secuencial: un equipo pasa por sus etapas en orden.
- **El modelo** corre en paralelo y abarca muchas unidades — el MK3 madura mientras se arman el
  tercero, el cuarto y el quinto.
- **Lo comercial** tiene su propio ritmo y toca a la unidad en dos puntos: al cotizarla y al
  entregarla.

La flecha que sube de reparación al modelo es la importante: **un defecto de fabricación
descubierto dos años después vuelve a la línea del modelo** y cambia cómo se arman los que vengan.

### Qué módulo usa cada proceso

| Proceso | Abre | Y toca sin darse cuenta |
|---|---|---|
| Fabricar | Fabricación | Calidad, Inventario |
| Aceptar | **Inventario** | — |
| Entregar / arrendar | Ventas, Alquiler | Inventario |
| Mantener | Reparaciones | — |
| Reparar | Reparaciones | **Calidad** (para la alerta) |
| Cambiar el diseño | **PLM** | Calidad, Fabricación |
| Dar de baja | Inventario | — |
| Cotizar | Ventas / Reparaciones | — |

**Ahí están las dos fricciones que más van a perder a la gente**, y no son las obvias:

1. **Aceptar se hace en «Inventario».** El técnico piensa *«voy a probar el equipo»*, no *«voy a
   inventario»*. Es el proceso con peor nombre de puerta de todos.
2. **Reparar termina en «Calidad»**, un módulo que esa persona no abre nunca. Justo el paso que
   cierra el círculo con fabricación es el que exige saltar a una app ajena.

## 1. Un ROV nuevo: del armado a la entrega

### Paso 1 — La orden de fabricación

**Fabricación → Órdenes de fabricación → Nuevo.** Se elige el modelo y su lista de materiales.

### Paso 2 — Se arma, y se verifica mientras se arma

Dentro de la orden, el botón **Controles de calidad** trae las verificaciones del armado: sellos
y o-rings, penetradores, cableado, foto del interior.

**Estos controles están puestos en el momento en que se pueden hacer.** Los del interior hay que
responderlos **antes de cerrar el casco**, porque después no se ven — y un control respondido de
memoria mirando un equipo cerrado no verifica nada.

### Paso 3 — Si algo falla

El control se marca **Fallido** y se abre una **alerta de calidad**. Ahí se escribe:

| Campo | Qué va |
|---|---|
| **Título** | Qué pasó, en una línea |
| **Descripción** | El detalle, en texto libre |
| **Causa raíz** | De dónde vino: diseño, manufactura propia, pieza de proveedor… |
| **Acciones correctivas** | Qué se hizo **con este equipo** |
| **Acciones preventivas** | **Qué cambiamos para que no se repita** ← lo que de verdad importa |

**La diferencia entre esas dos últimas es la que da valor a todo el sistema.** «Se reconectó y
quedó bien» arregla un equipo. «Subir el cable del E-pod a 40 cm» arregla todos los que vengan.

Un control fallido **no impide cerrar la orden**, a propósito: nadie debería tener que marcar
«Aprueba» mintiendo para poder avanzar.

### Paso 4 — Nace el número de serie

Al terminar la orden, Odoo crea el número de serie del equipo. **A partir de aquí ese número es
el equipo**: su ficha, sus pruebas, sus dueños y sus reparaciones cuelgan de él por el resto de
su vida.

### Paso 5 — La ficha técnica

**Inventario → Números de serie → el que acaba de nacer.** Se llenan chasis, motores, pesos,
tarjetas, controlador y luces.

Las **versiones de software** las aporta el paso siguiente: en fabricación el software se
instala, así que la prueba de rendimiento es la que dice qué quedó puesto.

El aviso amarillo de arriba dice cuántos datos faltan de cuántos. **No bloquea** — se puede
guardar una ficha a medias, y es mejor guardar 12 de 14 datos verdaderos que inventar los 2 que
faltan. Para encontrarlas después está el filtro **«Ficha incompleta»**.

### Paso 6 — Prueba de rendimiento

Desde el número de serie, botón **Nueva prueba de rendimiento**. Es la prueba de banco:
tensión, consumo en reposo y bajo carga, ancho de banda, corrida de resistencia con sus
temperaturas, y las versiones de software instaladas.

### Paso 7 — Prueba en terreno

Botón **Nueva prueba en terreno**. Lugar, profundidad, velocidad de la corriente, alimentación,
y una batería reducida.

### Paso 8 — Entrega

Las dos pruebas anteriores son **obligatorias antes de entregar o arrendar**. El número de serie
muestra si cada una está hecha, y hay un filtro **«Sin pruebas de aceptación»** con los equipos
que todavía no se pueden entregar.

**Una prueba que se hizo y salió mal no cuenta como hecha.** Queda registrada —con su fecha y su
resultado— y el equipo sigue apareciendo como pendiente hasta que se repita y pase.

> **Todos los intentos quedan guardados.** Si un equipo hubo que probarlo tres veces mientras se
> ajustaba, las tres pruebas están ahí. Ésa es la parte que más sirve después.

---

## 2. Un ROV que vuelve al taller

### Paso 1 — La orden de reparación

**Reparaciones → Órdenes → Nuevo.** Se elige el equipo y se anotan los **síntomas** que reporta
el cliente y los **componentes que se sospechan**.

Al confirmar la orden, la revisión técnica se crea sola.

### Paso 2 — La revisión

Dentro de la orden, pestaña **Revisiones**. Tres pestañas, en el orden en que ocurren las cosas:

1. **Sellos** — ¿alguien abrió este equipo antes de que llegara?
2. **Pruebas** — la batería completa, por áreas, más las condiciones de la corrida.
3. **Hallazgos** — qué se encontró, elegido de un catálogo.

Cada chequeo se responde **OK / No OK / No aplica**. «No aplica» es una respuesta válida y dice
algo del equipo — no es lo mismo que dejarlo en blanco.

### Paso 3 — Los trabajos

Por cada cosa que se arregla se registra **qué se hizo** y **por qué pasó** (el origen). El
origen es obligatorio al cerrar.

### Paso 4 — Cuando la culpa es nuestra

Si el origen es **«Diseño o especificación»** o **«Manufactura propia»**, eso **no es solo una
reparación: es una lección de fabricación descubierta tarde**.

Desde la línea de trabajo se levanta una **alerta de calidad** apuntando al modelo, y ahí vuelve
al circuito del punto 3.

> Ésta es la parte que cierra el círculo. Un defecto de fabricación puede tardar dos años en
> aparecer, y cuando aparece lo hace en el taller de reparación, no en el de armado. **Si no se
> devuelve, se vuelve a fabricar igual.**

---

## 3. Cuando hay que cambiar cómo se fabrica un modelo

### La regla

**La primera lista de materiales se crea directo en Fabricación. Desde el primer cambio en
adelante, todo pasa por PLM.**

Crear no es cambiar. La primera lista documenta lo que se acaba de armar; desde la primera
modificación se está cambiando algo que ya existe.

> **Y una vez que un modelo usa ECOs, su lista de materiales no se edita nunca más a mano.**
> Odoo lo permite, pero mezclar las dos formas deja la historia con agujeros y la comparación
> entre versiones deja de servir.

### Un ejemplo completo

**Enero.** Se arma el primer MK3. Se crea su lista de materiales directo: o-ring 235, cilindro
Petrohue, seis thrusters.

**Febrero, tercer equipo.** Se suelta un conector del E-pod en el banco. Falla el control →
alerta `QA00007` → acción preventiva: *«el cable del E-pod queda corto, subir a 40 cm»*.

**Ahí entra PLM.** Se abre un **ECO de tipo Maduración** enlazado a esa alerta, se cambia el
largo del cable, se aplica. La lista pasa a la versión 2 y queda escrito **qué cambió y por
qué**.

**Marzo, mayo y agosto.** Tres ECOs más, cada uno con su alerta. Eso es la maduración del MK3,
registrada en vez de recordada.

**Al año siguiente.** Dos trimestres sin ninguna alerta: el diseño maduró. Se puede cotizar a
precio fijo y comprometer plazos.

**En 2028** alguien propone cambiar el o-ring. Ese ECO **ya no es de Maduración**: es de *Cambio
en producto en producción*, con aprobación — porque hay cuarenta equipos en terreno que
quedarían distintos a los que salen mañana, con lo que eso implica en repuestos y reparaciones.

**Y si alguien pregunta** *«¿por qué el MK3 lleva el cable de 40 y no de 30?»*, la respuesta está
a dos clics: ECO → alerta → *«se soltaba en el banco»*.

### Los dos tipos de ECO, y por qué

| Tipo | Cuándo | Ceremonia |
|---|---|---|
| **Maduración** | El modelo todavía se está afinando | Mínima — la ceremonia estorba |
| **Cambio en producto en producción** | Ya hay equipos entregados | Con aprobación — el cambio tiene consecuencias afuera |

El ECO vale por razones distintas en cada fase: mientras se madura es un **cuaderno**, y una vez
maduro es un **control**.

---

## Dos cosas que confunden seguido

**«¿Por qué hay dos sistemas de checklist?»** Porque responden preguntas distintas.

| | Controles de calidad | Revisión técnica |
|---|---|---|
| Pregunta | ¿Se armó bien? | ¿Cómo está el equipo? |
| Cuándo | Durante el armado | Al probarlo y en cada reparación |
| Respuestas | Aprueba / Falla | OK / No OK / **No aplica** |
| Historial | Solo el último resultado | **Todos los intentos** |
| ¿Se imprime? | No, es interno | **Sí, se le entrega al cliente** |

**«¿Por qué en fabricación se escribe libre y en reparación se elige de una lista?»** Porque el
volumen es distinto. En fabricación los problemas llegan en ráfaga sobre un modelo y se leen de
corrido mientras se está afinando. En reparación llegan de a poco sobre toda la flota durante
años, y sin catálogo no habría forma de contarlos.
