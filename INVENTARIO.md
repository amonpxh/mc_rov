# Inventario — contexto de dominio para `mc_rov`

Este documento describe el diseño de inventario de Marine Connection en Odoo y las
restricciones que el módulo `mc_rov` debe respetar. No documenta el módulo — para eso
está [`CLAUDE.md`](../CLAUDE.md).

**Fuente de verdad del árbol:** `Arbol_Categorias_ROV_Odoo_FINAL.xlsx` (fuera del repo).
**Estado:** 164 categorías cargadas en producción vía importación.

---

## La cadena de trazabilidad

El análisis de fallas que el negocio necesita —*"esta placa falló, ¿de qué lote vinieron
sus componentes y qué otros equipos lo llevan?"*— depende de una cadena de cuatro
eslabones:

```
ROV            serie
  └─ e-pod     serie
      └─ placa LOTE      ← se rastrea la tirada, no la unidad
          └─ componente  LOTE solo en transistores y conversores DC-DC
```

**Dos consecuencias que el módulo tiene que asumir:**

1. **Las placas se rastrean por lote, no por serie.** No existe historial de una placa
   individual. Si alguien pide *"cuántas veces se reparó esta fuente específica"*, la
   respuesta es que no se puede: se conoce la tirada de fabricación. Cambiar esto exige
   dejar el stock de esos productos en cero (Odoo bloquea el cambio de seguimiento con
   existencias).

2. **Solo dos familias de componentes llevan lote:** transistores/MOSFET/IGBT y módulos
   DC-DC. El resto de la electrónica quedó sin seguimiento. Una falla causada por un
   capacitor o un integrado no se puede rastrear hasta su compra.

**El lote es el número de la orden de compra**, no el date code del fabricante. Un lote
lleva al proveedor y a la fecha a través de la recepción.

---

## Las dos taxonomías

Conviven dos clasificaciones de los mismos objetos físicos, **y así deben quedar**:

| | Qué responde | Tamaño |
|---|---|---|
| `product.category` | ¿Dónde guardo esto y cómo lo valorizo? | 164 |
| `mc.rov.componente` + `mc.rov.subtipo` | ¿Qué falló y qué hicimos? | 8 + ~40 |

**No fusionarlas.** Las granularidades no calzan: el árbol incluye materia prima,
consumibles y servicios que nunca se reparan; los subtipos incluyen distinciones que al
inventario no le importan. Fusionarlas obligaría al técnico a elegir entre 164 opciones
cuando solo 40 le sirven.

**No mapearlas tampoco.** El mapeo subtipo → categoría es ambiguo: *"Fuente de poder"*
apunta a `PCBA-PSU`, `CTRL-PSU` o `CNSL-PSU` según dónde estuviera montada, y eso el
técnico no lo sabe al elegir el subtipo.

### El puente es la orden de reparación

Una `repair.order` tiene dos capas:

- **`linea_falla_ids`** — la narrativa: componente, subtipo, acción, horas, detalle.
- **Líneas estándar de la orden** — el inventario: producto, cantidad y **lote**.

El cruce falla ↔ lote sale de la orden, no de hacer coincidir las taxonomías. Por eso no
hay mapeo que mantener.

**Donde se rompe:** si el técnico llena "Trabajos realizados" pero no agrega el repuesto
como línea de producto, el vínculo con el lote se pierde y el análisis de fallas se corta.
Ver la entrada correspondiente en `CLAUDE.md` § Pendiente.

---

## Reconciliación periódica de subtipos

Cruzar los subtipos de `mc.rov.subtipo` contra el árbol de categorías es barato y rinde:
en la primera pasada (mayo 2026) reveló **siete categorías faltantes** y confirmó **dos
que no hacen falta**.

Los subtipos son historial de reparación, no memoria — por eso encuentran huecos que
ninguna entrevista encuentra.

**Agregadas al árbol a partir de ese cruce:** `THR-PARTS-BUJE`, `CTRL-MEM` (micro SD),
`IMG-PARTS` (base/máscara, domo/lente, cable interno de cámara). Y el domo entró en
`FRAME-EPOD-PARTS`, las mangueras en `FRAME-PARTS`, el teclado en `CNSL-HMI`.

**Confirmadas como innecesarias, porque vienen integradas:**

| Subtipo | Dónde vive realmente |
|---|---|
| Sensor de temperatura | Integrado en el sensor de presión (`SENS-DEPTH`) |
| Compás / IMU | Integrado en la controladora de vuelo (`CTRL-BOARD`) |

Ambas categorías lo dicen en su nota. **No basta con una regla que diga "no se crea"**:
alguien que busque "IMU" tiene que encontrar dónde está, no la negación de que exista.

Repetir el cruce una o dos veces al año, o cada vez que se agreguen subtipos.

---

## Vocabulario de la casa

Siete términos resultaron ambiguos durante el diseño del árbol. El módulo ya usa el
vocabulario correcto en sus subtipos (mufa, domo, buje), pero conviene tenerlos presentes:

| Término | Significa | No confundir con |
|---|---|---|
| **Botella** | Carcasa del e-pod | — (no se dice "carcasa de presión") |
| **Regleta** | Bornera de riel DIN de la consola | Enchufe múltiple, que también se dice regleta |
| **Abrazadera** | Anillo que fija la tapa a la botella | Amarra plástica (que algunos llaman brida) |
| **Stencil** | Plantilla para perforar cilindros de PLA | Stencil de pasta de soldar (no lo usan aún) |
| **Pasta** | De soldar, al poblar placas | Pasta térmica, del e-pod |
| **Switch** | Interruptor de encendido | Switch de red (no tienen) |
| **Tapón** | Tres cosas: protección fuera del agua, dummy submarino, y locking sleeve | — |

---

## Procesos de los que depende la trazabilidad

Dos disciplinas operativas sostienen todo lo anterior. Ninguna es configuración: son
hábitos que, si se rompen, dejan datos silenciosamente incorrectos.

1. **Cada ensamble pasa por una Orden de Fabricación.** La OF es lo que graba qué lotes
   se consumieron en cada unidad. Si alguien arma una placa en el banco y ajusta el
   inventario a mano, ese eslabón se pierde y no se puede reconstruir.

2. **El material se entrega desde bodega a la OF**, o se mantiene un solo lote abierto por
   componente. Si el técnico saca libremente del cajón habiendo dos bolsas abiertas, lo
   que Odoo registró como consumido puede no ser lo que se soldó — y falla en silencio.

---

## Equipos de clientes

Un ROV que Marine Connection fabricó y vendió sigue siendo `ROV-MC`, pero **ya no es
activo de la empresa**. Al volver para servicio se recibe **en consignación**, con el
cliente como propietario: Odoo no lo valoriza, pero le mantiene ubicación, número de serie
e historial.

Lo mismo aplica a `ROV-XX` (equipos de otras marcas), que **nunca** entran como stock
propio.

**La categoría dice qué es el equipo; la propiedad se maneja con el propietario y la
ubicación.** Confundir ambas cosas lleva a valorizar equipos ajenos en el balance.
