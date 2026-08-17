# Pipeline integration

This module is the **source of truth** for ROV data at Marine Connection. It is consumed (read-only) by the ROV Operations Data Pipeline.

- **Pipeline repo:** `marine-connection/mc-rov-pipeline` *(TBD — will exist after pipeline Phase 0)*
- **Pipeline purpose:** automated Excel reports + real-time Grafana dashboards + analytical lakehouse (S3 + Iceberg + Athena)

## Architectural pattern

```
mc_rov (source of truth, writeable)
   │
   ▼  read-only access
ROV Operations Pipeline
   │
   ▼
Reports · Dashboards · Analytics · Predictive maintenance
```

The pipeline **never writes back** to this module. `mc_rov` is canonical; the pipeline is a downstream consumer.

## Touchpoints in this module

| Touchpoint | Lives in | Added in |
|---|---|---|
| Custom REST controller | `controllers/api.py` | Pipeline Phase 1 *(not yet built)* |
| Pipeline Odoo user | `pipeline@marine-connection` | Phase 1 *(not yet created)* |
| Pipeline security group | `Pipeline API (Read-Only)` (rows in `security/ir.model.access.csv`) | Phase 1 |

## How the pipeline reads from this module

1. **JSON-RPC** against Odoo's native endpoint — used for most queries (stable across Odoo versions, ORM-respecting).
2. **Custom REST endpoints** at `/api/v1/*` — used for pipeline-shaped contracts not ergonomic via JSON-RPC.

The pipeline authenticates as `pipeline@marine-connection` using an API key stored in AWS SSM Parameter Store on the pipeline side. The user belongs to the `Pipeline API (Read-Only)` group, which has `perm_read=True` and everything else `False` on the relevant models.

## Pipeline-relevant models and fields

The pipeline consumes data from these models. **Treat fields listed here as a stable contract** — coordinate via PR review before changing or removing any of them.

### `stock.lot` (ROV instances)

Standard Odoo fields used by pipeline:
- `id`, `name`, `ref`, `product_id`, `create_date`, `write_date`

Custom mc_rov fields used:
- `es_un_rov` — **derived, not curated.** Since 19.0.2.0.0 this is a stored computed
  boolean: true when the product's category sits under the ROV vehicle branch. Same name,
  same type, different meaning — do not read it as an operator's judgement call. It flips
  on its own when a product is recategorised.
- `mc_estado_comercial` — **derived since 19.0.5.0.0.** Same name, same four values,
  different meaning: it is computed from `mc_propietario_id`, from open rentals
  (`sale.order.line.pickedup_lot_ids` minus `returned_lot_ids`) and from `mc_fecha_baja`,
  in that order of precedence. It is no longer an operator's assertion and cannot diverge
  from those three. Do not treat a change in it as a human decision.
- `mc_propietario_id` — **new in 19.0.5.0.0.** Current owner of the unit. Fleet units are
  held under the company's own partner, never null: an empty value would be
  indistinguishable from "nobody filled it in". Hand-maintained, for the same reason as
  `mc_fecha_puesta_servicio` — Odoo 19 has no ownership concept on `stock.lot` to derive
  it from, and units sold before Odoo existed have no stock move either.
- `mc_fecha_baja`, `mc_motivo_baja` — **new in 19.0.5.0.0.** Decommissioning. A date and
  not a boolean, because *when* a unit left service is analysis-relevant. Rows migrated
  from the old `"Baja"` value carry an **approximate** date (the record's `write_date`) and
  say so in `mc_motivo_baja`.

  **This is the only way a unit is taken out of service** — `stock.lot` has no `active`
  field in Odoo 19, so serials cannot be archived and no second mechanism can disagree with
  this one. Concretely for the pipeline: decommissioned units stay visible to ordinary ORM
  reads. There is no `active_test` context to remember, and no silent row loss on export.
  Filter on `mc_fecha_baja IS NOT NULL` when you want to exclude them.

  Since 19.0.5.1.0, `proxima_mantencion` is null on decommissioned units, so they drop out
  of overdue-maintenance figures on their own.

### `mc.rov.propietario.historial` (new in 19.0.5.0.0)

One row per **ownership period**, not per change: `lot_id`, `partner_id`, `fecha_desde`,
`fecha_hasta` (null on the current period), `repair_id`.

Written entirely by `stock.lot.write` — never by hand. Only ROV serials get rows; component
lots are excluded on purpose. `repair_id` records the repair order that revealed the change,
which distinguishes a resale detected at intake from a manual correction.

This is the intended source for ownership analysis. Do **not** reconstruct ownership from
`repair.order.partner_id`: that field is who pays a given job, which is sometimes an insurer
or a distributor, and the original sale never produces a repair order at all.
- `mc_estado_operativo` — **derived since 19.0.3.0.0**, computed from the unit's open repair
  orders. Same name and type, different meaning: it is no longer an operator's assertion
  and cannot diverge from the orders. Do not treat a change in it as a human decision.
- `mc_repair_count` (computed)
- `ultima_mantencion` (computed) — **narrowed in 19.0.3.0.0** to preventive maintenance only
  (`tipo_intervencion = mantencion_preventiva`). It previously returned the date of any
  closed order, so pipeline history built before that version overstates maintenance.
- `mc_ficha_completa` — **new in 19.0.6.0.0.** Stored computed boolean: true when the unit's
  spec sheet carries every field considered essential. False on component lots too, so
  always pair it with `es_un_rov` when looking for ROVs with an incomplete sheet.

  Numeric fields are checked with `> 0`, not "is set". In Odoo an `Integer` or a `Float` is
  never empty — it reads as `0` — so a zero motor count means *nobody filled it in*, not
  *zero motors*. The pipeline should read this field rather than re-deriving the rule.

- *(the remaining ficha técnica `mc_*` fields — pipeline consumes a subset; TBD list in
  Phase 1)*

#### Breaking field changes in 19.0.6.0.0

Three columns were **dropped**, not renamed in place. A pipeline query naming them errors
out rather than returning empty:

| Removed | Replaced by | Why |
|---|---|---|
| `mc_version_qground` | `mc_software_superficie` (Selection) + `mc_version_software` | QGroundControl stopped being the only surface software. Crabby and ROVControl exist, and ROVControl is temporary |
| `mc_version_px4`, `mc_version_navigator` | `mc_controlador_vuelo` (already existed) + `mc_version_controlador` | A unit has a Pixhawk **or** a Navigator, never both, so one column was always empty. And Navigator is itself slated for replacement |

The pattern in both cases is the same and worth knowing for anything built on top: **one
column per product means a schema change every time the product landscape moves.** These
are now a selector plus a single version field, so adding or retiring a product is a list
edit.

Migration merged the two controller versions by preferring the one matching the selected
controller, falling back to the other rather than dropping a value, and seeded
`mc_software_superficie` as `QGroundControl` only on rows that actually had a version
recorded.

> `19.0.6.0.0` briefly shipped a `Desconocido` option on eight spec-sheet `Selection`
> fields; `19.0.7.0.0` removed it and cleared any stored value. If anything read those
> columns during that window, treat `Desconocido` as null.

### `repair.order`

Standard fields:
- `id`, `name`, `product_id`, `lot_id`, `state`, `create_date`, `schedule_date`

Custom mc_rov fields:
- `tipo_intervencion_ids` — **breaking change in 19.0.4.0.0.** Was `tipo_intervencion`, a
  Selection holding one of four string keys. It is now a Many2many to
  `mc.rov.tipo.intervencion`, because one workshop visit can be several things at once.
  Pipeline queries reading the old name will return nothing. Read `name` for the label, or
  `es_mantencion` to identify maintenance visits — do not match on the label text.
- `falla_reportada`
- `linea_falla_ids` (one2many)
- `causa_raiz` — **moved to `mc.rov.linea.falla` in 19.0.8.0.0, then replaced by `origen` in
  19.0.13.0.0 (see that model below).** It was one value per order, which forced a choice
  when a visit had several: an umbilical cut by accident and a motor worn by use are two
  different root causes. Migration copied each order's value down to its work lines; orders
  that had a root cause and **no** work lines lost it, and the migration logs how many.
- `sintoma_ids` — **new in 19.0.13.0.0.** Many2many to `mc.rov.sintoma`: what the customer
  **reports**, as opposed to what the workshop finds. Optional by design, so an empty value
  means "nobody was asked", never "no symptoms". Do not treat it as a denominator without
  first measuring how often it is filled.
- `componente_sospechado_ids` — **new in 19.0.13.0.0.** Many2many to `mc.rov.componente`:
  which component the customer *suspects*, as opposed to saw. It deliberately reuses the same
  catalogue as findings and work lines, which is what makes **reported-vs-real** a join and
  not a text comparison: suspicion (order) against `mc.rov.revision.hallazgo.componente_id`.
  There is **no link between an individual symptom and an individual suspicion** — if a
  customer reports two of each, which goes with which is not recorded. That is a deliberate
  trade, not missing data.
- `fecha_entrega_real`
- `observaciones_salida`
- `mc_total_horas` — **stored since 19.0.5.2.0.** It was an unstored computed field, which
  meant it could be read per record but not sorted, filtered or aggregated in a query. It
  is now a real column. Same name, same value; what changed is that you can `GROUP BY` it.
- `mc_propietario_lot_id`, `mc_propietario_difiere` — related/computed from the unit's
  registered owner. `mc_propietario_difiere` is the resale signal: it fires when the order's
  customer is not the unit's registered owner.
- `item_2..5` — **removed in 19.0.8.0.0.** Four unlabelled `Char` fields left over from
  Studio; zero of the ten orders in production ever used them. Replaced by
  `mc_items_recibidos_ids`, a Many2many to `stock.lot` — no fixed arity, and traceable,
  since e-pods carry their own serial.
- `revision_ids` — **new in 19.0.8.0.0 as `protocolo_ids`, renamed in 19.0.11.0.0.** The
  technical revisions of this visit. Since 19.0.11.0.1 the intake one is **created
  automatically** when the order leaves draft, so from that version on every ROV repair
  order has at least one — but orders confirmed before it may have none.

**A semantic guarantee that only holds going forward:** since `19.0.5.2.0` an order cannot
be closed without at least one `tipo_intervencion_ids`. Before that it could, and such an
order counted as neither maintenance nor repair, never restarted the unit's cycle and never
reached the counters — silently. **Orders closed before that version may still have none**,
so do not assume the field is populated when reading history.

> An earlier version of this document also listed `estado_final`, `garantia_reparacion` and
> `fecha_garantia` on `repair.order`. **Those three fields have never existed in the code**
> — they were only ever in this file. Removed 2026-08-12.

### `mc.rov.revision` and its lines (new in 19.0.8.0.0, renamed in 19.0.11.0.0)

**This is the intended source for failure analysis** — the thing the whole module was
building towards. One record per test session on one unit.

> **Breaking rename in 19.0.11.0.0.** These models shipped as `mc.rov.protocolo` and were
> renamed to `mc.rov.revision`, along with `protocolo_id` → `revision_id` on every line.
> The old models were **dropped, not migrated**: a pipeline query naming them errors out.
> "Protocolo" means *procedure*, and the record is the result of running one — the procedure
> is the check catalogue.

> **Breaking change in 19.0.12.0.0: `tipo` lost two of its four values.** `recepcion` and
> `entrega` collapsed into a single `reparacion`; the migration rewrote every existing row.
> A query filtering on the old keys returns nothing — it does **not** error out, which makes
> this the more dangerous kind of break.
>
> The split assumed both sheets would be filled. In practice a visit is one paper sheet, so
> asking for two produced one filled and one blank, with no way to tell which. Before/after
> comparison now happens **between visits**, which is the interval the failure analysis
> wanted anyway.

- `mc.rov.revision`: `lot_id`, `repair_id` (nullable — manufacturing revisions have no
  order), `tipo` (`fabricacion` | `reparacion` | `terreno`), `fecha`,
  `responsable_id` (`hr.employee`), `estado`, `horas_operacion`, `resultado`,
  `numero_en_visita`, plus the light counts and field-test fields.

  **`numero_en_visita` is not decoration — read it before aggregating.** A visit usually
  holds one revision, created automatically when the order leaves draft, but may hold
  several (test, fix, retest). **The unit of analysis is the visit, not the revision**:
  counting findings per revision drops a rate to a third if one visit had three of them. Use
  `numero_en_visita = 1` for *what the unit arrived with*, and the maximum per `repair_id`
  for *how it left*.

  `resultado` is derived and stored: `rechazado` if any check is `no_ok`, any run's stress
  test has problems, or any finding is `impide_operar`; `aprobado_con_observaciones` if
  there are findings; `aprobado` otherwise.

  `horas_operacion` is the hour-meter reading, **only present on units that have one**
  (`stock.lot.mc_tiene_horometro`). What is analytically useful is the **delta between
  consecutive revisions** — the hours the unit actually flew. Reliability figures computed
  on calendar time flatter units that nobody uses.

- `mc.rov.revision.corrida`: one pass with one umbilical — `umbilical` (`equipo` |
  `prueba`), `largo`, `alimentacion`, `tension_salida`, `esfuerzo_duracion`,
  `esfuerzo_resultado`, `subida`, `bajada`. Two rows when the standard test cable is used
  as a **control sample**; comparing them isolates the cable as a fault source.

  > **Moved in 19.0.14.0.0: `temperatura_interior` and `temperatura_exterior` came down from
  > `mc.rov.revision`,** where the columns were dropped. A query naming them on the revision
  > errors out. They are measured **once per run**, so a revision with two runs has two
  > readings and they are meant to be compared, not averaged. No production row had a value at
  > migration time, so there is no pre-19.0.14.0.0 history to reconcile.
  >
  > **Internal figure — never expose it in anything customer-facing.** It used to be given to
  > the customer and was used against Marine Connection; it is being measured again on the
  > explicit condition that it stays inside.

- `mc.rov.revision.chequeo`: `chequeo_id`, `componente_id`, `seccion` (stored related),
  `resultado` (`ok` | `no_ok` | `no_lo_tiene`), `detalle`. **`no_lo_tiene` means the unit
  lacks that component** — not that it went unchecked. Empty means unanswered, which blocks
  confirmation. Its **label** became "No aplica" in 19.0.12.0.0; the stored key did not
  change, so queries are unaffected.

  Since 19.0.12.0.0 the technician can neither add nor delete lines: the battery is
  generated from the catalogue. That makes the absence of a line meaningful — it means the
  step is not in the battery for that revision type, never that someone skipped it.

- `mc.rov.revision.hallazgo`: `componente_id`, `subtipo_id`, `hallazgo_id`, `severidad`,
  `chequeo_origen_id`, `detalle`, `lot_id` (stored). Reuses the same component and subtype
  catalogues as the work lines, which is what makes findings and work correlatable.

  `chequeo_origen_id` is the **detection** axis of an FMEA: whether a checklist step
  revealed the finding or someone spotted it otherwise. A frequent finding that no check
  detects is a check that is missing.

- `mc.rov.revision.inspeccion`: `componente_id`, `estado_sello`, `observacion`,
  `manipulacion_externa` (stored, derived). **One row per sealed component**, replacing what
  had been three independent checkboxes. Generated only on `reparacion` revisions.
  `manipulacion_externa` fires when a seal arrived broken or absent **at intake** —
  unambiguous, because the workshop never breaks a seal without recording it and its own
  breakages happen during the work.

  **Since 19.0.12.0.0 that "at intake" is a data-entry convention, not a structural
  guarantee.** It used to be enforced by the record's type (an intake revision was filled on
  arrival); with one revision per visit it rests on the field label and a banner. Treat a
  sudden rise in `manipulacion_externa` as possibly procedural before treating it as a rise
  in third-party tampering.

- `mc.rov.chequeo` (catalogue): `name`, `seccion` (`inspeccion_fisica` | `presion` | `leak` |
  `navegacion` | `video` | `luces` | `otro`), `por_componente`, and three booleans declaring
  which revision types it applies to — `aplica_fabricacion`, `aplica_reparacion`,
  `aplica_terreno`. **`aplica_recepcion` and `aplica_entrega` were merged into
  `aplica_reparacion` in 19.0.12.0.0 and the columns dropped.** `mc.rov.hallazgo`
  (catalogue): `name`, `familia`.

- `mc.rov.sintoma` (catalogue, **new in 19.0.13.0.0**): `name`, `familia` (`energia` |
  `movimiento` | `video` | `comunicacion` | `sensores` | `accesorios` | `fisico` |
  `temporalidad` | `otro`), `sequence`, `active`. This is the **reported** side of the
  chain — the counterpart to `mc.rov.hallazgo`, which is the **observed** side. Retirement is
  a flag, not a deletion.

  The `temporalidad` family carries what a `momento_falla` Selection would have held; that
  field was designed and cut before implementation, so **it never existed in any released
  version** and no data was ever stored under it.

  > **Archiving a catalogue entry hides history from the ORM.** Reading an x2many applies
  > `active_test`, so an order that reported a now-archived symptom comes back with one
  > symptom fewer — silently. The relation row is still there: read with `active_test=False`,
  > or read `mc_rov_repair_order_sintoma_rel` directly.
  >
  > **This is a live trap for any count over time.** Archive a commonly used symptom and its
  > historical count drops to zero, which looks exactly like the symptom having stopped
  > occurring. The same applies to every catalogue with `active` reached through an x2many —
  > `mc.rov.hallazgo`, `mc.rov.componente`, `mc.rov.tipo.intervencion`. Not new in
  > 19.0.13.0.0; it had simply never been written down.

### `mc.rov.componente` and related

- `mc.rov.componente`: `id`, `name`, `active`
- `mc.rov.subtipo`: `id`, `name`, `componente_id`, `active`
- `mc.rov.accion`: `id`, `name`, `active`, and **`consume_repuesto` (new in 19.0.14.0.0)** —
  whether the action necessarily consumes a part. It drives a close-time check, so **from that
  version on, a closed order with a `consume_repuesto` work line has at least one product
  line**. Orders closed before it may have none; and even after, the guarantee is *at least
  one part per order*, not one per change.
- `mc.rov.chequeo`, `mc.rov.hallazgo`, `mc.rov.software.superficie`,
  `mc.rov.controlador.vuelo`: catalogues added in 19.0.8.0.0 and 19.0.9.0.0, all with
  `active`. **Retirement is a flag, not a deletion** — a unit that referenced a retired
  option still resolves it.
- `mc.rov.linea.falla`: `id`, `repair_id`, `componente_id`, `subtipo_id`, `accion_id`, `fecha`, `horas`, `detalle`
  - **New in 19.0.8.0.0**: `hallazgo_origen_id` (which finding this work resolves — the
    link that closes the circuit), `responsable_id` (`hr.employee`), and `causa_raiz`,
    which moved down from `repair.order`.
  - `mc.rov.componente` gained `es_inspeccionable`, which drives the seal inspection rows.

  > **Breaking change in 19.0.13.0.0: `causa_raiz` was dropped and replaced by `origen`.** The
  > column no longer exists — a query naming it errors out, which is the safer kind of break.
  >
  > The old field mixed *what physically happened* with *whose problem it is*; `origen`
  > answers only the second. New keys: `diseno` · `falla_fabricacion` · `pieza_proveedor` ·
  > `mal_uso` · `desgaste` · `desconocida`. Four are the old keys unchanged, so **their
  > meaning is stable across the boundary**. Two are not: `corrosion` became `desconocida`
  > (it was a mechanism, and `mc.rov.hallazgo` already has a "Corrosión" entry — the old value
  > is appended to `detalle`), and `accidente` became `mal_uso`, whose label now reads "Uso
  > del cliente (mal uso o accidente)".
  >
  > **Rows that had no `causa_raiz` at all are now `desconocida`.** The old field was never
  > required. Do not read a pre-19.0.13.0.0 `desconocida` as "the workshop investigated and
  > could not tell" — a share of them mean "nobody filled it in". The distinction is not
  > recoverable; the migration logs the counts.
  >
  > **`origen` is enforced at order close, not by the model.** Lines can exist without it
  > while the order is open, and lines on orders closed before this version keep whatever the
  > migration gave them. Treat the field as reliably populated only on orders closed from
  > 19.0.13.0.0 onward.

  - **New in 19.0.13.0.0**: `analisis_causa`, free text — the reasoning behind the chosen
    origin. Never required and expected to be sparse, so it is a field to *read*, not to
    aggregate.

  **On joining findings to origins.** The design's unit of analysis is the work line, but the
  line has no finding of its own — only `hallazgo_origen_id`, which is **optional** and
  requires that someone recorded the finding on the revision. So "why it happened" without
  "what was found" on the same row is expected, especially early. Primary join is
  `linea.hallazgo_origen_id → hallazgo_id`; when it is null, fall back to the line's own
  `componente_id` + `accion_id`, which are required but say where work happened, not what was
  found. **Measure the fill rate of that pointer before trusting any analysis built on it** —
  a crossing over 20% of the lines is a bias, and it looks exactly like a result.

## Contract stability rules

Before changing or removing **any** of the following, coordinate via PR review:

- An endpoint URL or response shape in `controllers/api.py`
- Any field listed in "Pipeline-relevant models and fields" above
- Permissions on the `Pipeline API (Read-Only)` group

The pipeline has its own tests that exercise these contracts; breaking them is detectable but better avoided.

## When changing pipeline-consumed fields

If you must change a field consumed by the pipeline:

1. Open a PR in `mc_rov` describing the change.
2. Tag the pipeline maintainer for review.
3. Coordinate the change in the pipeline (extractor update) to ship before or alongside the mc_rov change.
4. Update this document to reflect the new contract.

## Future enhancements

- *(To be tracked here as the pipeline evolves.)*
