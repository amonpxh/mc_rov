# Changelog

All notable changes to the `mc_rov` Odoo module are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this module adheres to [semantic versioning](https://semver.org/) within the constraints of Odoo's version scheme: `19.0.X.Y.Z` where `19.0` is the Odoo major, `X` is breaking-change/migration, `Y` is feature, `Z` is bugfix.

## [19.0.8.0.0] — 2026-08-12

**The repair sheet becomes a record instead of a paragraph.** Design and rationale:
[`docs/designs/protocolo-de-pruebas.md`](docs/designs/protocolo-de-pruebas.md).

### The problem

The workshop fills a repair sheet by hand. It records **what was tested** reasonably well;
what it records badly is the findings, which all land in one free-text observations field.
That makes pattern analysis impossible without reading the paragraphs one by one — you
cannot ask *what is the most common motor failure* or *how many units arrive with
third-party intervention*.

The module already had half the answer: `mc.rov.linea.falla` records component + subtype
against configurable catalogues. What was missing is a single thing — the model stores
`accion_id`, which is **what was done**, and has no field for **what was found**. It is
called a failure line and holds no failure.

### Added

Six models. One header, three line models, two catalogues.

- **`mc.rov.protocolo`** — one test session. It hangs off the **serial number, not the
  repair order**: a new ROV goes through the same battery before shipping, and there is no
  order then. Hanging it off the order would leave all of manufacturing out of the analysis.

  `tipo` (fabricación / recepción / entrega / terreno) lets the same visit produce two
  protocols — test on arrival, fix, test again before delivery — and the comparison between
  them is the evidence that the work helped.

  `horas_operacion` records the hour-meter reading. Only some ROVs have one, and what
  matters analytically is **the delta between consecutive protocols**: the hours the unit
  actually flew between visits. It is the denominator every reliability calculation needs,
  because a unit diving eight hours a day and one sitting in a warehouse accumulate the
  same calendar time.

- **`mc.rov.protocolo.corrida`** — one pass with one umbilical. It exists because **the
  umbilical is a condition of the run, not a datum of a test**. Usually one; two when the
  standard test cable is used as a control sample, and then the comparison isolates the
  cable as a fault source: same ROV, same bench, different cable. If bandwidth only drops
  with the unit's own umbilical, the problem is the cable and not the vehicle.

  `esfuerzo_duracion` is the field that did not exist and is worth the most. The result is
  binary — the ROV runs 1 to 1½ hours in a water bin and either holds up or does not — but
  *how long it held* is different, comparable information. "Held 90 minutes" and "failed at
  15" are recorded identically today, which is to say not recorded.

- **`mc.rov.chequeo`** and **`mc.rov.protocolo.chequeo`** — the standard test steps and the
  checklist lines generated from them. Adding *yaw*, *roll* or *pitch* for a 6-DOF unit is
  creating catalogue records, not deploying code.

  `resultado` covers two dimensions with one value, because the paper sheet mainly records
  *what was tested* rather than *what came out*: empty blocks confirmation, and **`No lo
  tiene`** is a first-class answer. It is deliberately not called *No aplica* — the physical
  inspection does not always cover all five components, since not every ROV has a joystick
  and the "cilindro fuente" only exists on units with two e-pods. *No aplica* would leave
  the record saying both *the unit doesn't have it* and *we didn't check*, and with that the
  denominator of any statistic is lost.

- **`mc.rov.hallazgo`** and **`mc.rov.protocolo.hallazgo`** — the missing vocabulary.
  `componente_id`, `hallazgo_id` and `severidad` are all required, so **writing a paragraph
  is not an available option**. `detalle` stays as a complement, never as the record.

  `chequeo_origen_id` makes the FMEA's **detection** axis measurable — whether a checklist
  step revealed the finding or someone spotted it by chance. That is the axis almost no
  workshop can compute, and it yields the most useful result of all: *a frequent finding
  that no check detects is a check that is missing*, and a check that comes out OK across
  the whole fleet for a year can be retired. **The protocol audits itself.**

- **Manufacturing and repair do not run the same battery.** The check catalogue declares
  which protocol types each step belongs to. The case that justifies it is the physical
  inspection: it exists to detect whether someone else opened the unit, which means nothing
  on a ROV the workshop built itself last week.

- `mc_tiene_horometro` on the spec sheet, as a **Sí/No `Selection` and not a checkbox**. A
  boolean is never empty, so `False` would mean both *no hour meter* and *nobody checked* —
  and this field decides which part of the fleet can be measured in operating hours rather
  than calendar time.

- `es_inspeccionable` on `mc.rov.componente`. Without it a per-component check would
  generate one line for every catalogue entry — umbilical and sensor included, which nobody
  inspects looking for third-party seals.

### Changed

- **`causa_raiz` moved from `repair.order` down to `mc.rov.linea.falla`.** One value per
  order forced a choice when a visit had several causes: an umbilical cut by accident and a
  motor worn by use are two different things.
- **`responsable_id` on the work line**, not only on the protocol header. Two technicians
  can work the same order and each line already carries its hours. Adding it later would
  leave every prior line unattributed — the one field here that cannot be retrofitted.
- **`item_2` … `item_5` removed**, replaced by `mc_items_recibidos_ids`, a Many2many to
  `stock.lot`. No fixed arity, and traceable: e-pods carry their own serial, so the record
  shows which e-pod arrived with which ROV on which visit.
- **`mc_total_horas` moved to the foot of the hours column** with `sum`, instead of a
  detached field at the bottom of the tab.

### Migration
`19.0.8.0.0/post-migrate.py`, in order of increasing risk: copy `causa_raiz` down to each
order's work lines (orders with a root cause and **no** lines lose it — the script counts
and logs how many), drop `item_2` … `item_5`, and finally force a recompute of
`mc_ficha_completa`.

That last step is mandatory and is the module's recurring trap: **the ORM only fills new
columns.** `mc_ficha_completa` has existed since `19.0.6.0.0`, so adding `mc_tiene_horometro`
to its list of essential fields triggers no recompute on its own — sheets currently marked
complete would stay marked complete forever, without the hour meter.

- 25 tests (106 → 131).

## [19.0.7.0.1] — 2026-08-12

### Changed
- **`Cantidad de luces` moved from *Periféricos* to *Especificaciones*.** It is a count of
  the unit's own components, like `N° de motores`, not an accessory.

  The point is the rule it makes possible. It was the only required field outside
  *Especificaciones*, so the rule read *"everything in Especificaciones, plus one field on
  another tab"*. It now reads *"everything in Especificaciones"* — which the form states
  by itself, without anyone having to explain it.

  View-only change. The field keeps its name and its place in `mc_ficha_completa`; nothing
  in the database moves.

## [19.0.7.0.0] — 2026-08-12

Both changes come from using `19.0.6.0.0` in production for half an hour.

### Removed
- **`Desconocido` is gone from every `Selection` in the spec sheet.** It was added one
  version earlier so that pre-Odoo field units could be saved without inventing data. Two
  problems, one cosmetic and one not:

  Six of those fields render as radio buttons, and **a radio makes every option cost the
  same** — which is the opposite of what an escape hatch should do. And more importantly,
  the call is to make people go and find out the unit's actual specs rather than accept a
  non-answer.

  The trade-off, stated plainly because it is real: **a presumed value is now
  indistinguishable from a verified one.** Someone types `4.1.0` from memory and the sheet
  reports as complete. That is the price of forcing the investigation.

### Added
- **`mc_ficha_faltantes`**, shown as a banner at the top of the serial form.

  The browser does reject a save when a numeric field is zero — but **it does not
  highlight the field**, so the user sees a save that fails with no visible cause, which
  trains people to guess. Naming the fields is more reliable than fighting Odoo's
  highlighting, and it covers two cases the red dots never could: fields that live on
  another notebook page (*Cantidad de luces* is under *Periféricos*) and records created
  by import, where there is no form at all.

### Migration
`19.0.7.0.0/post-migrate.py` clears any `Desconocido` left in the eight affected columns.
Odoo does not fail on a stored value its `Selection` no longer offers — it renders the
field blank — but the value stays in the database, invisible, and would resurface in any
export or pipeline query. Emptying it makes it what it actually is: an unfilled field,
which is exactly what the *Ficha incompleta* filter should catch. On a database where
nobody used it, the script touches nothing.

- 3 tests net (103 → 106).

## [19.0.6.0.0] — 2026-08-12

The manufacturing spec sheet becomes mandatory for ROVs, and the two flight/surface
software fields stop having one column per product.

### Changed
- **Every field in *Especificaciones*, plus *Cantidad de luces*, is now required for ROV
  serials** — via `required="es_un_rov"` **in the view**, not `required=True` on the model.

  The distinction matters. A model-level `required` puts `NOT NULL` on the column and
  applies everywhere: to component lots, which have none of these fields and never will,
  and to the moment a manufacturing order creates the serial, which happens before anyone
  fills the sheet. Either would break manufacturing. A view-level rule blocks nobody from
  creating a serial by code, and blocks everybody from saving an incomplete ROV sheet by
  hand.

- **`mc_version_px4` and `mc_version_navigator` collapse into `mc_version_controlador`;
  `mc_version_qground` becomes `mc_software_superficie` + `mc_version_software`.**

  Both pairs had one column per product, which means a deploy every time the product
  landscape moves — and it is moving: ROVControl is temporary and will be replaced by
  Crabby, PX4 is nearly gone in favour of Navigator, and Navigator is itself slated for
  replacement. The two version columns also never coexisted: a unit has a Pixhawk or a
  Navigator, so one of them was always empty. Retiring or adding a product is now a list
  edit.

  `mc_version_ardusub` stays on its own, because it is the one thing that genuinely does
  coexist with either controller.

  A side effect worth noting: this **removes the conditional show/hide** the design
  originally called for. With a single version field per slot there is nothing to hide.

### Added
- **`Desconocido` as an explicit option in every `Selection` of the spec sheet.** An empty
  field cannot tell *nobody filled it in* from *nobody knows*, and for units that predate
  Odoo the second is the honest answer. It is what makes the strict requirement liveable:
  a field unit can be saved without inventing data.

- **`mc_ficha_completa`**, a stored computed flag, and a **"Ficha incompleta"** filter on
  the serials list.

  The two mechanisms are complementary rather than redundant. The view rule only reaches
  whoever opens the form — a serial created by a manufacturing order or by import never
  passes through it. This flag is what finds those. And **`Desconocido` counts as
  missing**: it unblocks saving without emptying the to-do list.

  Numeric fields are checked with `> 0`, not "is filled". In Odoo an `Integer` or a `Float`
  is never empty — it reads as `0` — so `required` cannot tell *nobody filled it* from
  *they typed zero*. A ROV with zero motors or zero kilos does not exist, which makes zero
  exactly the right signal.

### Migration
`19.0.6.0.0/post-migrate.py`, in strict order: merge the two controller versions into one
(keeping the one matching the selected controller, falling back to the other rather than
losing a value), move `mc_version_qground` into the new pair seeding `QGroundControl` only
where a version was actually recorded, and **only then** drop the three old columns.

`mc_ficha_completa` is not touched there: it is a new column, and the ORM computes new
columns on its own after the script runs.

- 7 tests (96 → 103).

## [19.0.5.2.0] — 2026-08-11

### Added
- **An order can no longer be closed without a type of intervention.** Without one it was invisible to everything derived from it: it counted as neither maintenance nor repair, did not restart the unit's cycle, did not reach the counters, and never appeared in `ultima_mantencion` or `ultima_reparacion`. Nothing warned. It is the same silent failure `fecha_entrega_real` had, with the same delayed symptom — months later the unit still shows as overdue.

  The check runs **before** `super().write()` so the state never lands, and it covers only the transition to `done` rather than being an `@api.constrains`. That way it never blocks editing an order that predates the rule — the same reasoning that keeps the delivery-date seal out of `create`.

### Changed
- **Notebook pages reordered to the workshop's actual sequence:** Trabajos realizados → Piezas → Resultado → Notas de reparación.

  The previous order was not a decision. `<notebook position="inside">` appends, so Odoo's own two pages sat in front by default and *Notas de reparación* landed **between** Trabajos realizados and Piezas — the two pages that have to be filled consistently with each other, since a "cambio" line implies the corresponding part. Notes go last because `internal_notes` is a scratchpad, not a step in the process.

- **`mc_total_horas` is now stored.** It is a column in the order list, and an unstored computed column can be displayed but not sorted, filtered or grouped — which is most of what one asks of an hours total. The column is new, so the ORM fills it on creation and no migration is needed.

### Fixed
- **`mc.rov.linea.falla` lines could reshuffle between reads.** `_order` was `sequence` alone and every line is created at `sequence = 10`, so the order among them was left to PostgreSQL unless someone dragged the handle. Now `sequence, id`.
- **`fecha` on a work line now defaults to today.** With no default it was left blank almost always, and with it went the ability to place each piece of work in time.

### Note
The corresponding search view for `repair.order` — filters by intervention type, group by root cause — is deliberately **not** in this release. It needs the base search view's arch to anchor its group-by section without producing a second "Group By" heading, and guessing at an inherited view's internals is what caused the defects in 19.0.5.0.1 and 19.0.5.1.0.

- 7 tests (89 → 96).

## [19.0.5.1.0] — 2026-08-11

### Fixed
- **Decommissioned units still had a maintenance clock**, so they kept showing up under "Mantención vencida". Sales would have called a customer to offer maintenance on a unit that no longer exists. `proxima_mantencion` is now null once `mc_fecha_baja` is set — the same principle as "no service date, no clock", taken to the other end of the unit's life.
- **The description block never actually moved into its tab.** `position="move"` only runs when it is a direct child of a position operation; nested deeper it is ignored silently, which left an empty tab with the note editor still sitting above the tabs. It is now its own operation.

### Changed
- **Decommissioning moved to a dialog reached from the ⚙ actions menu**, replacing the form button and its "are you sure?" confirmation.

  **The reason is now required, and it replaces the confirmation.** A confirm dialog gets answered yes without reading; having to write *why* is what actually prevents the distracted click — you can fat-finger a button, not a sentence. And unlike a confirmation, the reason is kept and is worth something later.

  One menu entry covers both directions: it offers to decommission an in-service unit, and shows since when plus a revert for one already out. The ⚙ menu is where Odoo puts Duplicate and Delete — the lifecycle family this belongs to, and it stops competing for attention with the fields people read every day.

- `stock.lot.action_dar_de_baja` / `action_reactivar` renamed to `dar_de_baja(fecha, motivo)` / `reactivar()`. No view calls them any more; the wizard does.

### Documentation
- **Corrected a wrong justification recorded in 19.0.5.0.0.** `CHANGELOG`, `CLAUDE.md` and `pipeline.md` all said Odoo's archiving was "deliberately not used", as though an available option had been weighed and rejected. It was never available: `stock.lot` has no `active` field in Odoo 19, so serials cannot be archived at all.

  This matters beyond pedantry. The original wording sent the next reader looking for a trade-off that does not exist, and it obscured the actually useful fact for the pipeline: since there is no archiving, decommissioned units stay visible to ordinary ORM reads and cannot silently vanish from an export.

- 6 tests.

## [19.0.5.0.2] — 2026-08-11

### Changed
- **The decommission buttons moved to a form header.** The lot form ships without one, so this view adds it. It is where a user already looks for actions that change a record's state, without being told.
- **A red "De baja" ribbon** now appears on decommissioned units. A ribbon is seen on opening the record; a status field has to be gone and read.
- **Odoo's description block moved into a notebook page.** Loose in the sheet, its empty text area left a large gap between the fields and the tabs — which is its normal state, since the note is rarely filled. The whole `group[@name='description']` is moved, so its title travels with it and nothing is orphaned; the title is then cleared, being redundant inside a page of the same name.

  That page is **not** hidden for non-ROV lots, unlike the rest: it is the only place the field lives, and hiding it would make notes unreachable on component lots.

### Note
Moving a node out of the inherited view couples this module to `group[@name='description']` existing in `stock.view_production_lot_form`. It is a named group, which is the stable kind of anchor, but if a future Odoo release drops it the view will fail to load. Same class of dependency the module already accepts for `//field[@name='product_id']` and `//sheet`.

## [19.0.5.0.1] — 2026-08-11

### Fixed
- **The decommissioning buttons broke the serial form's field alignment.** They were placed inside the `<group>`, and a group is a table of label/field pairs: a button takes a lone cell and desynchronises the pairing for everything after it. The visible symptom was `ref` ("Referencia") showing its label with no input, and an orphan unlabelled input box appearing at the bottom of the other column — an empty field inviting someone to type into it without knowing what it was.

  The buttons now sit in their own `<div>` between the field groups and the notebook. No data or computation was affected; the fields were always correct.

### Note
This shipped broken in 19.0.5.0.0 and was not caught before deploy, because the view renders without error — Odoo has no way to know that a button in a group is not what you meant. Only opening the form shows it.

## [19.0.5.0.0] — 2026-08-07

### Added
- **Ownership of the unit.** `mc_propietario_id` on `stock.lot` — who owns the ROV today. Until now the customer only existed on the repair order, tied to that one job, so "whose serial is this?" and "show me every unit belonging to this client" had no answer at all.

  Fleet units sit under the company's own partner rather than being left empty: empty is indistinguishable from "nobody filled it in".

  Hand-maintained, and Odoo leaves no choice — `stock.lot` in 19 has no ownership concept whatsoever. `last_delivery_partner_id` is gone, and `delivery_ids` is neither stored nor usable for this: returning a repaired ROV also produces a delivery, so it overwrites itself.

- **Ownership history.** New model `mc.rov.propietario.historial`, one row per *period* (`fecha_desde` / `fecha_hasta`), written by `stock.lot.write` and never by hand. Only ROV serials get rows.

  It exists for analysis: how long each unit spent with each client, how many hands it passed through, whether resold units come back to the workshop more often.

- **Resale detection at intake.** Nobody tells us when a customer resells their ROV; the symptom is the unit coming back billed to someone else. The repair order now shows the registered owner, warns when it differs from the order's customer, and offers a transfer button that records which order revealed the change (`repair_id` on the history row).

- **Decommissioning.** "Dar de baja" / "Reactivar" buttons, backed by `mc_fecha_baja` and `mc_motivo_baja`. A date rather than a boolean, because *when* a unit left service is analysis-relevant.

  Archiving is not an alternative: `stock.lot` has no `active` field in Odoo 19, so serial numbers cannot be archived at all. *(This sentence originally claimed archiving was rejected on merit — corrected in 19.0.5.1.0.)*

- Group-by owner and by commercial status on the serial number list, a "Dados de baja" filter, and both fields as optional columns.
- 17 tests.

### Changed
- **`mc_estado_comercial` is now derived** from the owner, from open rentals and from the decommissioning date, in that order of precedence: decommissioned beats sold, and a sold unit does not go back to saying "Disponible" just because no rental is active. Same field, same four values, same place in the form — it simply can no longer lie. It was the last hand-maintained field of its family.

  "En arriendo" comes from `sale.order.line.pickedup_lot_ids` minus `returned_lot_ids`. There is no relation to traverse from `stock.lot` to `sale.order.line`, so `@api.depends` cannot see it; a `write` override on `sale.order.line` triggers the recompute, the same role `product.category` plays for `es_un_rov`. The intermediate table names are never hardcoded — the compute searches by field name, and the migration reads them from `ir_model_fields`.

  **Note for the pipeline:** the field keeps its name and type but changes meaning. Do not read a change in it as a human decision. See `docs/integrations/pipeline.md`.

### Migration
- `migrations/19.0.5.0.0/post-migrate.py`. The step order is the fragile part and is not interchangeable:

  1. **Rescue the existing `"Baja"` values into `mc_fecha_baja` first.** The recompute derives the status *from* that date, so running it first would turn every decommissioned unit back into "Disponible" with nothing left to reconstruct it from.
  2. Seed owners, so step 4 can tell "Vendido" from fleet.
  3. Open the first ownership period of every existing ROV.
  4. Recompute `mc_estado_comercial` — the ORM does not recompute a field that becomes computed+stored when the column already existed with data.

  Step 1 invents a date (the record's `write_date`), which this module otherwise refuses to do. It is the lesser evil here: *that* a unit is decommissioned matters more than the exact day, and losing it would be irreversible. `mc_motivo_baja` says the date is approximate so nobody reads it as recorded fact.

  No abort gate as in 19.0.2.0.0 — nothing unreconstructable is at stake once the date is saved.

## [19.0.4.2.0] — 2026-08-07

### Added
- **Maintenance clock.** `proxima_mantencion` on `stock.lot`, computed as the cycle length added to `ultima_mantencion`, or to `mc_fecha_puesta_servicio` when the unit has never been serviced. A unit serviced at 18 months restarts its cycle there, not on the theoretical anniversary — what counts is when it was actually worked on.
- `mc_fecha_puesta_servicio` — delivery to the customer if the unit was sold, or first availability for rental if it belongs to the fleet. Manual on purpose: units delivered before Odoo existed have no stock move to derive it from, and rentals go in and out repeatedly.

  **No service date means no clock.** Units sitting in the warehouse stay out of the overdue list.

- "Mantención vencida" and "Mantención en 60 días" filters on the serial number list, plus `proxima_mantencion` as a column. No new menu: sales already reaches equipment through *Inventario → Números de serie*, and the call list is that same list filtered.
- Cycle length is read from the `mc_rov.meses_ciclo_mantencion` system parameter, defaulting to 12. A non-numeric value falls back to the default with a log warning rather than breaking every unit's form.
- 7 tests.

### Changed
- `ultima_mantencion` and `ultima_reparacion` are now stored. A stored field cannot depend on a non-stored one, and `proxima_mantencion` has to be stored for the overdue filter to work. The `repair_ids` relation added in 19.0.3.0.0 is what lets the ORM know when to recompute them. New columns, so Odoo fills them on upgrade — no migration script.

### Deliberately not built
No stored "overdue" boolean. A unit falls overdue through the passage of time, not because someone edits it, so a stored flag would go stale in silence. The filter compares `proxima_mantencion` against today's date, which is always current.

## [19.0.4.1.0] — 2026-08-07

### Fixed
- **Closing a repair order now seals `fecha_entrega_real` if it is empty**, using the closing date. `ultima_mantencion` depends on that field, so leaving it blank meant the maintenance did not count and the unit's clock never restarted — with no warning of any kind. The technician closed the order and the serial went on looking overdue forever. The field stays editable for when the handover happened on a different day.

  Only `write` is covered, not `create`: an order born already closed comes from a historical import, and stamping today's date there would invent a worse figure than leaving it blank.

- **`mc_repair_count` counted maintenances as repairs.** Three repairs and two maintenances showed as "5 Reparaciones". It now counts only types flagged as repairs.

### Added
- `es_reparacion` on `mc.rov.tipo.intervencion`, symmetric to `es_mantencion`. The two are independent on purpose: a visit can be both, and a diagnosis or an upgrade is neither. Seeded on *Reparación correctiva*.
- `ultima_reparacion` on `stock.lot` — last closed repair, mirroring `ultima_mantencion`.
- `mc_mantencion_count` on `stock.lot`.
- 9 tests. `TestStockLotEstado` was split into `TestStockLotContadores`, `TestStockLotFechas` and `TestStockLotEstadoOperativo` over a shared `StockLotOrdenesCommon` base — it had grown past pylint's public-method limit, which was right: it held three separate concerns.

### Note for the pipeline
`mc_repair_count` keeps its name and type but now excludes maintenances. Counts taken before this version are not comparable with counts taken after.

## [19.0.4.0.0] — 2026-08-07

### Changed
- **`repair.order.tipo_intervencion` (Selection) → `tipo_intervencion_ids` (Many2many).** A single visit to the workshop can be more than one thing: a ROV comes in for scheduled maintenance and turns out to need a repair too. The Selection forced a choice, and picking "repair" silently discarded the maintenance that was actually performed — along with the reset of the unit's maintenance clock.

  **Breaking for the pipeline:** the field is renamed and its type changed. See `docs/integrations/pipeline.md`.

- `ultima_mantencion` and `mc_estado_operativo` no longer compare against the literal `"mantencion_preventiva"`. They read the `es_mantencion` flag on the intervention type, so adding a type like "Mantención mayor" is a checkbox in the UI, not a code change. Same principle already recorded for `mc.rov.accion` in `docs/pendientes.md`.

### Added
- Model `mc.rov.tipo.intervencion` — configurable catalogue under *Reparaciones → Configuración*, alongside components and actions. Fields: `name`, `sequence`, `es_mantencion`, `active`.
- Four seeded types: Diagnóstico, Reparación correctiva, Mantención preventiva (`es_mantencion`), Conversión / Upgrade.
- 4 tests, including the mixed visit (maintenance + repair in one order) for both `ultima_mantencion` and `mc_estado_operativo`.

### Migration
- `migrations/19.0.4.0.0/post-migrate.py` maps each old Selection value to its catalogue record and drops the old column, following the pattern of `19.0.1.3.0` (which did the same for `linea_falla.accion`). No-op on fresh installs.

## [19.0.3.0.0] — 2026-08-07

### Fixed
- **`ultima_mantencion` counted any repair as a maintenance.** It returned the delivery date of the latest `done` order regardless of `tipo_intervencion`, so a corrective repair updated the "last maintenance" date and made an overdue unit look serviced. It now filters on `mantencion_preventiva`. This matters for customers on an annual maintenance contract.
- `ultima_mantencion` ordered by `id desc` rather than by date, so an old order closed late returned the wrong date. Orders with no delivery date are now excluded — in PostgreSQL a `DESC` sort puts NULLs first and they were winning the `limit=1`.

### Changed
- **`mc_estado_operativo` is now derived from the unit's open repair orders**, not typed in by hand. Open non-draft order → *En reparación*; open order of type `mantencion_preventiva` → *En mantención*; otherwise *Operativo*. The field is stored, computed and read-only.

  It was a plain manual Selection that nothing read and that recorded no history: a technician could open a repair order and the serial would keep saying *Operativo* with the unit dismantled on the bench. The state already lived in `repair.order`; keeping a second copy by hand only allowed the two to disagree.

### Added
- `repair_ids` One2many on `stock.lot` (inverse of `repair.order.lot_id`), so the ORM knows when to recompute `mc_estado_operativo`.
- 7 tests: 2 on the `ultima_mantencion` fix, 5 on `mc_estado_operativo`.

### Migration
- `migrations/19.0.3.0.0/post-migrate.py` recomputes `mc_estado_operativo` for every existing serial, overwriting hand-entered values. No gate is needed here: unlike `es_un_rov`, nothing is lost that cannot be rebuilt — the repair orders are the source.

## [19.0.2.0.0] — 2026-08-07

### Changed
- **`es_un_rov` is now derived from the product category, not set by hand.** A serial number is flagged as ROV when its product's category sits anywhere under the ROV vehicle branch (`child_of`), covering both `ROV-MC` and `ROV-XX`. The field is stored, computed and read-only.
- The root category is resolved from the `mc_rov.rov_category_id` system parameter, falling back to the `__import__.cat_ROV` external ID left by the category tree import. The parameter lets the tree be reorganised without a deploy.
- `es_un_rov` is part of the pipeline contract (see `docs/integrations/pipeline.md`). Its name and type are unchanged; its semantics are not.

### Added
- `product.category.write` override that recomputes affected serials when a category is re-parented — `@api.depends("product_id.categ_id")` does not cover that case.
- 5 tests on `es_un_rov` (both ROV branches, nested subcategory, unrelated category, re-parenting).

### Migration
- `migrations/19.0.2.0.0/post-migrate.py` seeds the system parameter and recomputes `es_un_rov` for every existing serial. **Serials flagged by hand whose product is outside the ROV branch lose the flag**, which hides their four ficha-técnica tabs until the product is recategorised. The script logs how many were affected. If the root category cannot be resolved it aborts without touching data — but only when serials are currently flagged, since on a database with no flagged ROVs there is nothing to lose.

## [19.0.1.5.0] — 2026-05-12

### Removed
- 90 orphan `x_studio_*` columns deleted from `stock_lot` via SQL — leftovers from Odoo Studio that were not migrated to the proper module fields.

### Fixed
- Duplicate-label WARNING in Odoo logs resolved.

## [19.0.1.4.0]

### Added
- `mc_total_horas` computed field on `repair.order` summing `horas` from `linea_falla_ids`.
- Total horas displayed at the bottom of the "Trabajos realizados" tab.

## [19.0.1.3.0]

### Added
- `fecha` and `horas` fields on `mc.rov.linea.falla`.
- New columns in the "Trabajos realizados" view: Componente, Subtipo, Acción, Fecha, HH., Detalle.
- HH. column left-aligned (value and header).

### Verified
- 43 tests passing in production.

## [19.0.1.2.0]

### Changed
- `mc_` prefix added to the 48 ROV ficha técnica fields on `stock.lot`.
- `mc_repair_count` field added to `stock.lot`.

### Verified
- 48 `mc_*` columns confirmed in production DB.

## [19.0.1.1.0]

### Added
- 48 custom fields on `stock.lot` for ROV ficha técnica (especificaciones, periféricos, umbilical, prueba en terreno), migrated from Odoo Studio into the module.
- Post-migrate script `migrations/19.0.1.1.0/post-migrate.py` to preserve data during migration.

### Removed
- Studio view eliminated from DB. All visibility logic now controlled by `es_un_rov` in the module.
- Duplicate "reparaciones" button (the standard `repair` module already provides one).

### Fixed
- Migration `19.0.1.1.0`: second guard added to prevent failure in `odoo_test` and reinstallations where intermediate non-prefixed columns don't exist.

## [19.0.1.0.0] — initial release

### Added
- Base module structure (`__manifest__.py`, `__init__.py`, dependencies: `stock`, `repair`, `sale`, `sale_renting`).
- Custom models:
  - `mc.rov.componente` — catalog of ROV components (Motor, Umbilical, Electrónica, etc.) with subtypes.
  - `mc.rov.subtipo` — subtypes per component.
  - `mc.rov.accion` — catalog of repair actions (Reparación, Limpieza, Soldadura, etc.).
  - `mc.rov.linea.falla` — work lines registered in a repair order.
- Inheritance of `repair.order`: `tipo_intervencion`, system items, `falla_reportada`, "Trabajos realizados" and "Resultado" tabs.
- Inheritance of `stock.lot`: smart button for repairs, `ultima_mantencion`, history action.
- Views for components (list + form with inline subtypes), inherited repair.order and stock.lot forms.
- Menu "Componentes ROV" under Reparaciones > Configuración.
- Access rules for the 3 custom models (CRUD, no group restriction).
- Master data: 8 components, ~40 subtypes, 10 actions predefined.
- Custom CSS for editable field visibility.
- GitHub Flow with `develop` branch documented.
- Complete `.gitignore`.
- pre-commit with `pylint-odoo` configured.
- GitHub Actions CI: lint on push to `main`/`develop`.
- Semantic versioning convention documented.
- Docstrings and inline comments on the three core models.
- Field `es_un_rov` (replaces Studio's `x_studio_es_un_rov`).
- Tests for `stock.lot` (8 tests covering `es_un_rov`, `mc_repair_count`, `ultima_mantencion`).
- Tests for `repair.order` (10 tests covering defaults, selections, `fecha_entrega_real`, `linea_falla_ids`).
- Tests for `mc.rov.componente` and related models (16 tests covering all four custom models).
- Robust XPaths in `stock_lot_views.xml` (`//field[@name='product_id']`, `//sheet` instead of fragile internal-structure anchors).

### Fixed
- `ultima_mantencion` now uses `fecha_entrega_real` (custom field) instead of `create_date`.
