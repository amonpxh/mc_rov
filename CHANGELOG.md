# Changelog

All notable changes to the `mc_rov` Odoo module are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this module adheres to [semantic versioning](https://semver.org/) within the constraints of Odoo's version scheme: `19.0.X.Y.Z` where `19.0` is the Odoo major, `X` is breaking-change/migration, `Y` is feature, `Z` is bugfix.

## [19.0.19.0.0] — 2026-08-21

### Added

- **The acceptance tests get their own numbering: `REN/` and `TER/`.** `REV/` stays with
  repairs, so no existing record changes its number or its meaning. The reason is that
  acceptance tests are **documents the customer sees**: a spec sheet for a brand-new unit
  called `REV/00042`, interleaved with other machines' breakdowns, reads as internal
  paperwork — numbering a machine's birth inside the series of its failures says the opposite
  of what the document is for. Design in `designs/fabricacion.md` § 4.8.

- **`documento_emitido`**, a flag that turns on the first time a revision is confirmed and
  never turns off. It is what freezes `tipo`.

### Changed

- **A draft that changes type is renumbered**, with a note in the chatter naming the old
  number and the new one. The design said freezing the type at confirmation was enough, and
  it isn't: the type gets changed *between* create and confirm — that is the normal case,
  because the serial's button creates the test and only then does the technician see which
  kind it was — so a prefix assigned at creation would still end up lying. The old counter is
  left with a gap, which is what already happens when a draft is deleted, and is far better
  than a `TER/` that is actually a repair.

- **The type of an issued document cannot be changed**, in the model and not only in the view:
  an import, a server action or a `write` from another module never passes through the view.

  The lock hangs on `documento_emitido` and **not on `estado`**, and that distinction is the
  whole point. A confirmed revision sent back to draft to fix a typo has already gone out with
  its number on it; if the type reopened there, the document the customer is holding would be
  renumbered.

### Migration

`19.0.19.0.0/post-migrate.py` backfills `documento_emitido` on everything already confirmed.
Without it, every existing confirmed revision would come back with its type unlocked.

## [19.0.16.1.0] — 2026-08-20

### Changed

- **The serial's «Revisiones» tab is now «Pruebas», and it moves ahead of Propietarios and
  Alertas de calidad.** The first three tabs say what the equipment *is*; this one says what
  happened to it; the rest is ancillary. It sat last because the quality-alerts tab was
  anchored in front of it, which was the anchor talking, not a decision.

  The rename is for **discoverability, not taxonomy**. «Revisiones» is the model's name and the
  family's name, and the argument for keeping it was that each row already says which kind it
  is — *Prueba de banco*, *Prueba en terreno*, *Reparación*. But a tab label is the only sign
  the user gets, and «Revisiones» does not tell anyone that this is where the equipment gets
  tested. Nobody mistakes a repair row for a test.

## [19.0.16.0.1] — 2026-08-20

Two things `19.0.16.0.0` left half-done, both found by Paulo asking where the two tests that
used to live on the serial had gone.

### Added

- **«Nueva prueba en terreno» on the serial number.** `19.0.16.0.0` retired the field-test tab
  because it stored the result of an *event* as if it were a spec sheet — but its new home,
  a revision of type `terreno`, **had no door from the serial**. The only button read «Nueva
  prueba de banco». The old home was removed before the new one had an entrance.

  One button per type rather than a generic one with a dropdown (§ 4.3): whoever is about to
  test knows which of the two they are running.

### Changed

- **The serial's «PRUEBA DE RENDIMIENTO» section is now «PRUEBA DE BANCO».** `19.0.16.0.0`
  retired that word from the revision type and the label kept it, so the form showed a section
  named with a word the module no longer uses, next to a revision type named otherwise. It was
  claimed during that work that A1 would resolve this; it did not — those are the *lab*
  columns, and they leave in block A2. The section disappears entirely then.

## [19.0.16.0.0] — 2026-08-20

Block A1 of the fabrication design: the schema move that has to happen **before the system
goes into real use**, because it is the only one carrying a migration. § 8 puts it plainly —
*the window is now; with real equipment loaded, each of those three questions comes back*.

### Changed

- **The revision type `fabricacion` becomes `banco`.** The old value was generic and never had
  a written justification, and it had stopped describing one thing: what happens while
  assembling are quality points, what happens afterwards is this test.

  **It is `banco` and not `rendimiento`** — the name the design had picked, and equally
  unjustified, which is precisely the defect that retired `fabricacion`. Not because
  «rendimiento» is inaccurate: the test does measure performance. Because **`rendimiento` and
  `terreno` do not contrast on the same axis** — one names what is measured, the other where it
  happens — so the dropdown leaves open the question *«doesn't the field test measure
  performance too?»*.

  The real axis is place, and the design gives itself away: its tables define both by where they
  happen, and the case it uses to illustrate their difference is **pressure verified by two
  means depending on where you are**. `laboratorio` was rejected — nowhere in the workshop is
  called that, it would be imported vocabulary — and so was `taller`, since the repair revision
  also happens there and brings the collision back. The label is always «Prueba de banco», never
  a bare «Banco».

- **`aplica_fabricacion` becomes `aplica_banco`** across the model, the 24 catalogue records,
  the view and the tests.

- **`observacion` becomes `detalle` on the seal inspection line.** There were three names for
  one idea — `detalle` on the check line, `detalle` on the finding line, `observacion` here. This
  version carries a migration anyway, so unifying it was free.

### Fixed

- **A field revision could never be approved.** `_compute_resultado` demanded
  `esfuerzo_resultado` before returning any result at all, and the endurance run is not part of
  the field battery — the criterion is not relevance but physics: there is nowhere to leave a
  ROV running for ninety minutes off a boat. So a field test sat blank forever, which is the
  same failure mode `19.0.15.1.0` fixed from the other side. The run is now demanded only where
  it belongs, driven by a list beside `CAMPO_APLICA` rather than by a condition buried in the
  compute.

### Removed

- **The field-test columns leave `stock.lot`**, along with their tab: `mc_fecha_prueba`,
  `mc_lugar`, `mc_profundidad`, `mc_velocidad_corriente`, `mc_alimentacion`,
  `mc_tiempo_prueba_terreno`, both `_terreno` temperatures and `mc_observacion`.

  They were the result of an *event* stored as if it were a spec sheet, so running the test
  twice overwrote the first one in silence — `mc_fecha_prueba` even had a date, so somebody
  understood it was an event, but there was only room for one. It is now a revision of type
  `terreno`, which keeps history.

  **The migration counts and dumps whatever it is about to drop**, even though § 8 verified zero
  affected rows: what held on 2026-08-18 may not hold the day it runs, and the lesson of
  `19.0.15.0.0` is that the warning about what is lost has to arrive *before* the rows go.

  **And rehearsing it on staging immediately proved the dump wrong.** Against a copy of
  production it reported three serials as losing field-test data; reading the values, the only
  real one was `mc_alimentacion = 'Generador'` on a test serial. The rest were zeros — because
  Odoo stores `0`, not `NULL`, in an Integer or Float nobody filled, so `IS NOT NULL` cannot
  tell an untouched column from a measured zero. It is the same «zero of the numeric fields»
  the spec sheet already has identified and tested. Emptiness is now judged per type, because
  **a warning that cries wolf is worse than no warning**: the next time there is real data,
  nobody will read it.

- **The unused «Revisiones de fabricación» action.** No menu referenced it — bench tests are
  created from the serial's button — and after the rename its domain would have matched nothing.

## [19.0.15.5.0] — 2026-08-20

The repair → lesson bridge, redesigned. § 6.1.3 asked for «a button», and that does not
survive the question that undid it: *how does the user know what it does, and why would they
press it?*

### Added

- **`Reparaciones → Lecciones pendientes`.** The work lines whose origin points inward —
  design, own manufacturing, supplier part — that have neither fed a lesson nor been
  dismissed, grouped by model.

  **No threshold, no parameter.** Each group's count *is* the evidence; where the line falls
  between anecdote and pattern is a judgement, so no number is hardcoded.

  The technician already does the observation: origin is mandatory at close and «why it
  happened» is written down. What was missing was who harvests it — and that is not the
  person closing a repair, because the conclusion is an engineering judgement with
  consequences in spares and warranties. **The system detects, the person concludes or
  dismisses.**

- **The lesson is written from several work lines at once**, and that is the substantive
  change. One line is an anecdote; repetition is what makes it a lesson. All the units land
  in the alert's damage scope — *«these three carry the old o-ring»*, not just *«we changed
  the o-ring»* — and every «why it happened» goes into the description with its serial in
  front, because with several units you need to know which one said what.

  Refuses to mix models in one lesson, and only proposes a root cause when the lines agree on
  the origin: picking one of two would be inventing the datum.

- **Dismissing is writing why**, in an editable column of the same list, with a filter to
  revisit what was dismissed — a judgement gets reviewed.

  **This is the only thing stored of the whole mechanism.** The pattern is not: it exists
  because the lines exist, and materialising it would recreate the defect `CLAUDE.md` already
  named — *no stored «maintenance overdue» boolean, because it would go stale in silence*.
  What is stored is the human decision, which derives from nothing.

### Removed

- **The button on the repair order's work line**, added in `19.0.15.3.0`. Not for noise: it
  did harm. The queue lists lines with an empty `mc_alerta_id`, so **a technician's stray
  click hid the evidence from the supervisor, silently.** The field stays as a read-only
  column showing which lesson a work fed.

## [19.0.15.4.0] — 2026-08-20

Corrections found by walking `19.0.15.3.0` on screen in production.

### Added

- **The serial number lists the quality alerts that name it.** `quality_control` puts
  `quality_alert_qty` on `stock.lot` and no view uses it — verified on screen against
  `odoo_prod`, where the form shows *Por reparar / Hecho*, *Ubicación* and *Trazabilidad* and
  nothing from Quality. So the lot side of § 6.1.1 had to be written after all; the design said
  it was probably native and it is not.

  **A tab, not a smart button**, for the reason already written in `views/stock_lot_views.xml`:
  this form declares no `oe_button_box` with a stable name, and guessing at the internals of an
  inherited view is what caused the defects in `19.0.5.0.1` and `19.0.5.1.0`.

  It does **not** filter by stage, unlike the model's tab. The model answers «what did we change
  for everyone», so only closed lessons belong there. This one answers «what happened to this
  unit», and an open alert naming it is exactly what you want to know before delivering it.

### Changed

- **The repair order tab goes back to «Trabajos realizados» from «Reparación».** The rename in
  `19.0.14.0.0` was meant to make the tab bar read as the process, moment by moment — but a tab
  called *Reparación* inside the Repair module distinguishes nothing. Same symptom that already
  sent *Diagnóstico* back to *Revisiones*: the label fought with what was inside. Label only;
  the internal name was `trabajos_realizados` all along.

## [19.0.15.3.0] — 2026-08-20

Block B of the fabrication design: the bridges to `quality.alert`. See
`docs/designs/fabricacion.md` § 6 and the split in `docs/pendientes.md`.

### Added

- **A failed quality check now opens its quality alert by itself, in draft and untitled.**
  This is the gap that made everything else in § 6 an empty filing cabinet. The staging
  experiment of 2026-08-18 showed how the record disappears: the technician marks Failed,
  nothing is created, nothing stops them, they fix the unit, mark Passed — and Quality
  overwrites the check's state, so the order closes looking spotless with no trace beyond
  one chatter line.

  The asymmetry that justifies automating it: marking the check as failed is *mandatory to
  move on*, and creating the alert is a detour nobody asks for — and detours are not taken
  at seven in the evening with a half-built ROV on the bench.

  **Restricted to products in the ROV category branch**, the same one `es_un_rov` resolves.
  § 6.1.4 did not qualify it, and the cost of not qualifying it lands in the wrong direction: a
  quality point on incoming purchases would fill the list with empty drafts, and a long list of
  alerts nobody clears destroys the very signal the design leans on — that a half-filled alert
  reads as a pending debt. If the root category does not resolve, nothing is created and a
  WARNING goes to the log.

  **Idempotent per check, and that is half the value.** Fail → adjust → fail again produces
  one alert with the retry in its chatter, not two alerts. That is what turns the alert into
  the history of attempts the check itself cannot keep. A *closed* alert is never reopened:
  the same control failing months later is a new finding about a lesson already learnt.

- **The manufacturing order shows the lessons of its model**, in a banner above the tabs and
  a tab of its own. This is the cementerio risk pinned to a screen: a lessons register nobody
  reads while building the equipment is a graveyard, and worse than usual, because this one
  *will* get filled — writing the lesson is satisfying — and will not get read. The product
  form is not enough; whoever builds a ROV is looking at the order, not at the product.

  **Only closed alerts with a preventive action written.** Every alert of the model would be
  noise: it would include the ones still open and the ones closed by fixing one unit without
  changing anything. The ones that produced a preventive action are exactly the lessons.

  Alerts born in a *repair* order are included, and that is the point rather than a side
  effect: a work line with origin «design» or «own manufacturing» is a manufacturing pattern
  found late, and this is the channel that carries it back (§ 6.3).

- **`quality.alert.mc_eco_id`** — the alert now points at the engineering change it produced,
  and `mrp.eco` lists the lessons behind it. Verified on production that no such link existed
  in either direction, so «we changed the BoM because of this» was recorded nowhere. Chained
  in order, alerts and ECOs are the maturity history of a design (§ 6.4).

- **A button on the repair work line raises the quality alert**, pre-filled from `origen`,
  the affected unit and the written root-cause analysis. It lives on the line you are already
  looking at so that whoever repairs never has to learn that the Quality app exists. The line
  keeps the alert in `mc_alerta_id`, so a second click opens the existing one instead of
  inflating the per-model count that tells us when a design matured.

- **The serial number is written into the order's alerts when the MO is finished.** `lot_ids`
  is the scope of the damage — «we changed the o-ring» is the lesson, «these 7 units carry the
  old one» is the action — and it came out empty in the experiment, because when the alert is
  created the order has no serial yet (§ 6.1.5). Alerts whose scope was set by hand are left
  alone.

### Changed

- **`mrp`, `quality_control`, `mrp_plm`, `quality_mrp` and `quality_repair` join the module's
  dependencies**, so `mc_rov` no longer installs without Enterprise. A separate bridge module
  (`mc_rov_quality`) was considered and rejected: too much infrastructure for four fields in a
  single-company module. The CI runner's `addons_path` and the state of `odoo_test` were both
  verified before this landed.

  `quality_mrp` and `quality_repair` were not in the design and are needed: they define
  `quality.alert.production_id` and `quality.alert.repair_id`, which is where the bridges
  attach. Both are `auto_install`, so they were already there — declaring them fixes the load
  order.

## [19.0.15.2.2] — 2026-08-17

### Changed

- **«Responde en acro» becomes «Responde en modo acrobático (acro)».** The two neighbouring
  checks name the mode in Spanish and keep the technical term in parentheses — «Se estabiliza
  (stabilize)», «Mantiene profundidad (depth hold)» — and this one broke the pattern by using
  the technical term as if it were the description.

- **The incomplete-ficha banner now shows progress: «Faltan 3 de 16 datos…».** Without a count
  it said exactly the same thing with one field empty as with sixteen — one yellow bar — so
  filling fifteen of sixteen looked identical to not having started. It matters since
  `19.0.15.2.1`, when the view's `required` came out and the banner became the only signal:
  filling the ficha in parts is now visible progress instead of a warning that never moves.

  **The total is computed, not written into the view.** Adding a specification to
  `CAMPOS_FICHA` is a one-line change, and a hardcoded «de 16» would go stale with nothing to
  announce it. There is a test pinning the total to the tuple.

- **The revision header goes to two titled blocks**, *Equipo y visita* and *Esta revisión*, and
  `repair_id` moves to the left one. It read as four fields against seven, which looks like
  carelessness. The real split is not by count but by what each column describes — which unit
  and which visit, against what this particular revision is — and the repair order is the
  visit, so it belongs beside the order's customer and evens the blocks to five and six. Same
  treatment «Con qué se probó» / «Qué dio» got in `19.0.15.1.0`.

## [19.0.15.2.1] — 2026-08-17

Screen fixes on the tests tab, from looking at `19.0.15.2.0` deployed. Carries a migration.

### Fixed

- **The checklist was shown in creation order, not catalog order.** `mc.rov.revision.chequeo`
  declared `sequence = fields.Integer(default=10)` — **the same value on every line** — so
  `_order = "revision_id, sequence, id"` fell through to `id`. Two consequences that were
  visible on screen and that nobody connected to this:

  1. A check added to the catalog later stayed **last forever**, whatever its sequence.
     «Movimiento horizontal» (sequence 66) rendered after «Sin ruido ni vibración» (77).
  2. **Re-sequencing the catalog had no effect on revisions that already existed.**
     `19.0.14.2.0` moved *stabilize* ahead of *depth hold* so the battery would tell a story —
     stabilizes but will not hold depth points at the pressure sensor — and that change never
     reached a single existing record.

  `sequence` becomes a stored `related` of `chequeo_id.sequence`, so re-ordering the catalog
  now re-orders every ficha, past ones included. The migration backfills existing lines:
  **Odoo does not recompute an existing stored field just because its definition changed**, so
  without the script only new revisions would come out right — the worst of both worlds, since
  the defect would disappear exactly where it gets tested.

- **Every section sized its columns differently.** Each section is an independent `<list>`, and
  an HTML table sizes itself to its content: «Estanqueidad bajo presión» and «Tilt» are not the
  same width, so the radios of «Resultado» ended up staggered across nine blocks. Fixed widths
  in the module CSS, with `table-layout: fixed` — without it the browser treats percentages as
  suggestions and measures by the longest string again. «Chequeo» deliberately keeps under half
  the width: leaving it wide pushed the answer, which is what the technician came to click, to
  the far edge of the screen.

- **An incomplete ficha said so twice.** The banner named the missing fields *and* every field
  was `required="es_un_rov"`, so the same thing arrived as a list of names at the top and as red
  boxes below. **One standard, and it is the banner** — it is the one that covers the three
  cases the red never reached: numerics at zero (which the browser rejects but does not paint,
  so the save failed with no visible cause), fields living on another tab, and records created
  by import or by code, where there is no form to look at.

  The `required` was not merely redundant, it was **all-or-nothing**: someone who knows 12 of
  the 14 specifications could not save the 12, and the way out was to invent the other 2. A
  supposed value is indistinguishable from a verified one — the exact failure this module has
  been avoiding since «Desconocido» was retired in `19.0.7.0.0`. No pressure is lost: the
  banner shows on every open and the **«Ficha incompleta»** filter still finds every one of
  them. What is lost is the block, which was protecting the form at the cost of rewarding
  invented data.

- **«Componente» is hidden in the physical-inspection list too.** No catalog check is
  `por_componente` — there is a test that pins it — so the column is guaranteed empty, and
  showing it stole width from the other three in that one block. Still available from the ⚙.

## [19.0.15.2.0] — 2026-08-17

Software enters the repair battery. Rationale in
[`docs/designs/revision-tecnica.md`](docs/designs/revision-tecnica.md) § 8.8.

### Added

- **Two checks in the `comunicacion` section**, repair battery only:
  «El software de superficie inicia y opera» and «El software instalado corresponde a la
  ficha».

  The first closes a hole counted against the symptom catalog: [«El software de superficie
  falla»](data/mc_rov_sintoma_data.xml) existed as a symptom with **no test that verified
  it**, so a technician found it by looking and the finding had no originating check.

  The second catches an observed failure: the unit reformats itself and reverts to the
  factory software — usually ROVControl back to QGroundControl, or QGroundControl down to an
  older release. It is answered by comparing against the ficha, which already keeps the three
  versions with `tracking`.

- **Five `related` fields on the revision**, read-only, showing what the ficha declares
  installed: `software_ficha_id`, `version_software_ficha`, `version_ardusub_ficha`,
  `controlador_ficha_id`, `version_controlador_ficha`. They exist for the screen, not the
  model — **a check that forces the technician to open another view to answer it gets answered
  «OK»**, which is a false datum where an honest blank used to be. The block hides itself when
  the ficha declares nothing, which today is every pre-Odoo unit.

### Notes

- **This is deliberately as small as it gets: no new model, no computed `difieren`, no
  migration.** An earlier draft had a `mc.rov.revision.software` line model with slots, a
  derived expected value and a normalized comparison. It was dropped because **the instrument
  cost more than what it measures**: which software reverts, and how often, is not known yet,
  and `detalle` accepts any combination without inventing boxes for it. Structuring it now
  would be guessing the shape of the data before having the data. The rule for revisiting is
  written down: when these two checks show a pattern — which slot, how often — a model with an
  automatic comparison can be justified on evidence.

- **No `difieren` boolean, unlike `luces_difieren`.** With the software name typed by hand,
  «QGround» and «QGroundControl» are the same thing and would raise a false positive. Three
  lines side by side are compared correctly by eye, and the eye does not trip on spelling.

- **Only `aplica_reparacion`.** Turning the other two on out of habit is exactly the omission
  that left the manufacturing battery undefined (see [`docs/pendientes.md`](docs/pendientes.md)):
  in manufacturing you install the software yourself, so comparing it against the ficha does
  not mean the same thing.

## [19.0.15.1.0] — 2026-08-17

Screen fixes from looking at the deployed revision form.

### Fixed

- **A half-filled revision said «Aprobado».** `resultado` fell through to *approved* by
  elimination, so a freshly created record — 22 checks unanswered, nothing tested — declared
  the unit fine. It is the empty-indistinguishable-from-a-datum failure, on the optimistic
  side, which is the worse of the two. It now stays **blank** until every check is answered
  and the stress test has a result.

- **«Equipos recibidos» accepted other ROVs.** With no domain, a second vehicle could be added
  as if it were an accessory — and that unit would then have no revision, no checks and no
  history: invisible to every analysis. Restricted to `es_un_rov = False`, which also excludes
  the order's own unit.

### Changed

- **The tab goes back to «Revisiones».** It was «Diagnóstico» for a few hours so the tab bar
  would read as the process, and that left **two names for one thing**: the tab said
  Diagnóstico and every record inside said `REV/00006 — Revisión técnica`.

  «Revisión» is also the precise one: a manufacturing revision diagnoses nothing, and the
  second one of a visit verifies rather than diagnoses. What names the *step* is now a muted
  line inside the tab, which the technician reads where the work happens — more than a
  three-word label ever said.

- **`motivo` gains «Primer diagnóstico» as an explicit, default value.** Empty used to mean
  "this is the first one", which is inferring from an absence. Now the field is self-describing
  and countable without joining to `numero_en_visita`, and it costs no clicks: the revision
  auto-created on order confirmation arrives already marked. **The «Nueva revisión» button
  creates it empty on purpose**, to force the choice exactly where it matters. Only asked when
  there is a visit — a manufacturing revision has no repair to verify and no cable to compare.

- **«Condiciones de la prueba» becomes two titled blocks** — *Con qué se probó* and *Qué dio* —
  instead of two uneven columns. Four rows against six reads as a decision when each block says
  what it holds, and as sloppiness when it does not.

  The three Selections go to **horizontal radio**: they hold two and three values, and a
  dropdown to choose between two hides half the answer behind a click. **Units move out of the
  labels** and sit beside the input — `m`, `V`, `h`, `Mbps`, `°C`.

## [19.0.15.0.0] — 2026-08-17

One run per revision. Rationale in
[`docs/designs/revision-tecnica.md`](docs/designs/revision-tecnica.md) §§ 8.6–8.7.

### Removed

- **`mc.rov.revision.corrida` is gone.** Its fields move up onto `mc.rov.revision` under the
  same names: `umbilical`, `largo`, `alimentacion`, `tension_salida`, `esfuerzo_duracion`,
  `esfuerzo_resultado`, `subida`, `bajada`, `temperatura_interior`, `temperatura_exterior`.

  **The premise that split them turned out to be half false.** The design said "what does not
  depend on the cable lives on the revision and is done once even when there are two runs".
  But several checks *do* depend on the cable — responds to commands, bandwidth, probably
  video — and the two runs shared **one set of check answers**:

  > Any check that differed between one cable and the other was lost silently. The very
  > comparison that justified the second run was visible in four numbers and nothing else.

  Marine Connection confirmed the fact that settles it: **changing cables always means running
  the full stress test again**, never a quick swap to read bandwidth. So a second pass with
  another cable was always a whole test, and modelling it as a line inside the same record
  described it as smaller than it is.

  **This retires three things at once:** the convention that "checks belong to the first run",
  the «batería corrida con» field proposed to record that convention, and the `por_corrida`
  mechanism that was going to split three checks per cable. None are needed when a revision has
  one cable.

  **The price, stated plainly:** comparing two cables now costs answering the 22 checks twice.
  That is the same price the post-repair retest already had, and it is what makes the
  comparison complete — half a comparison is worth nothing.

### Added

- **`mc.rov.revision.motivo`** — `retest` | `comparacion_cable` | `otro`. Collapsing the run
  costs something that has to be paid back: **two runs inside one revision could only ever mean
  "cable comparison"** — the structure encoded the intent. Two revisions in a visit can be that
  or a post-repair retest, and they look identical.

  Mixing them destroys the question that justifies a second pass: *"how often does the later
  revision still show the fault"* means nothing if half those second passes were cable
  comparisons. Inferring it from the umbilical was considered and rejected — it lies when a
  retest happens to use a different cable.

  Asked **from the second revision of a visit onward** and required to confirm. Not asked on
  the first: `numero_en_visita` already says it is the first, and a field that is always
  answered the same way stops being read.

### Migration

`19.0.15.0.0/pre-migrate.py` lifts each revision's **first** run onto the header and drops the
model, its table and its ORM metadata.

**Runs beyond the first are discarded, and every one is dumped to the log in full first.** They
could not become extra revisions: each would need its own 22 answers, and those answers never
existed — precisely the defect this change fixes.

## [19.0.14.2.1] — 2026-08-17

### Fixed

- **Navigation checks were out of order, and the previous version caused it.** The six checks
  added in 19.0.14.1.0 and 19.0.14.2.0 landed *between* «Movimiento vertical» (70) and
  «Movimiento horizontal» (80), splitting a pair that belongs together.

  The section is now sequenced by **increasing dependency**, which fixes a second thing that
  was wrong on its own: hélices → thrusters → vertical → horizontal → acro → **stabilize** →
  **depth hold** → ruido. Stabilize now comes *before* depth hold, because depth hold includes
  stabilize — testing them the other way round means testing the compound before the part.

### Changed

- **«Prueba de luces» moves last, and its checklist now sits above the counters.** It is the
  only section that also asks for numbers, so it is the only one shaped differently. Put last
  and starting like every other section — a list — that difference stops interrupting the
  rhythm of the other eight.

  The count stays with the light check rather than moving up beside the runs: the technician
  does the three things in one go — switch the lights on, count how many lit, check they
  respond.

## [19.0.14.2.0] — 2026-08-17

Second pass over the battery. The first one closed the gaps **between** symptom families; this
one closes the gaps **inside** families that already had some coverage — the ones counting
families does not reveal.

### Added

- **Section `accesorios`**, plus six checks. The battery goes from 16 to 22.

  | Section | Check | The gap it closes |
  |---|---|---|
  | Navegación | **Todos los thrusters responden** | *«Un motor no gira»* is one of the most reported symptoms and had **no** check — "Hélices en posición correcta" looks at position, not rotation |
  | Navegación | **Responde en acro** | Acro holds angular rate on the **gyro**; stabilize levels using accelerometer and compass. Acro working while stabilize fails means the gyro is sound and the levelling half is not |
  | Navegación | Sin ruido ni vibración anormal | Symptom with no check; observed under power, hence navigation and not the intake inspection |
  | Inspección física | **Umbilical sin cortes ni aplastamientos** | The inspection covered chassis, penetrators and propellers — the vehicle, never the cable. And the umbilical is the single most suspected component |
  | Accesorios | Manipulador responde | Symptom with no check |
  | Accesorios | Sonar funciona | Symptom with no check |

  Manipulator and sonar are carried by a minority of the units, and that is **not** a reason
  to skip asking: "No aplica" asserts the unit does not have one, which is different from
  nobody having looked.

### Removed

- **The symptom «Fuga de aceite».** Marine Connection's ROVs do not use oil. It was in the list
  by analogy with subsea equipment that does — a symptom nobody could ever report, taking up
  space at the counter. The symptom catalogue goes from 27 to 26.

## [19.0.14.1.0] — 2026-08-17

The test battery grows to cover what customers actually report. Rationale in
[`docs/designs/revision-tecnica.md`](docs/designs/revision-tecnica.md) §§ 8.5–8.6.

### Added

- **Two new check sections, `energia` and `comunicacion`**, and **nine seed checks** — the
  battery goes from 7 to 16.

  This came from counting the battery against the symptom catalogue. The original seven came
  off the paper sheet and covered four areas; the symptom catalogue has **nine families**, and
  three of them had no check at all. A ROV that won't power up, that loses its surface link, or
  whose lights don't respond was going to be diagnosed by looking at it.

  That reads badly in the one analysis that matters: the finding would carry an empty
  `chequeo_origen_id`, counted as *no check detected this* — indistinguishable from a gap in
  the battery. And the gap was real.

  | Section | New checks |
  |---|---|
  | Energía *(new)* | Enciende y arranca correctamente |
  | Comunicación *(new)* | Responde a comandos desde superficie · El ancho de banda es el esperado |
  | Inspección física *(was empty)* | Chasis · Penetradores y conectores · Hélices |
  | Navegación | Mantiene profundidad (depth hold) · Se estabiliza (stabilize) |
  | Luces | Las luces responden al control desde superficie |

  **Depth hold and stabilize are two checks, not one**, for the same reason they are two
  symptoms: they point at different parts — the pressure sensor and the IMU/compass. That gives
  a deduction available no other way: *if depth hold fails but stabilize works, the problem is
  the depth sensor*, since one depends on the other. Until now that could be **reported** as a
  symptom but never **verified**. It also removes any need for a "Sensores" section: the depth
  sensor is tested by testing depth hold.

  **Nothing the run already measures was added.** Shutting off on its own is
  `esfuerzo_resultado` plus its duration; heating is the temperatures; bandwidth is `subida` /
  `bajada`. Recording the same fact as a number *and* a checkbox leaves two versions and no
  reliable one — and a number beats a checkbox anyway: "held 90 minutes" says more than "OK".

  **Thresholds are answered by hand, not derived.** Saying whether 8 Mbps is good needs a
  threshold nobody has defined, and one invented in code would flag "No OK" against a
  meaningless number — the same defect that sank the "confidence level" field in the
  diagnostics design. The technician knows what their model delivers. **When the spec sheet
  declares an expected value, this can become derived**, exactly as `luces_difieren` already
  does against `mc_cantidad_luces`.

### Changed

- **The umbilical option «De prueba (control)» is now «Del taller».** The old label sometimes
  lied: the workshop cable is a control sample when there are two runs, but it is also used
  **because the ROV arrived without its own** — rare, but it happens. In that case it is not a
  control of anything, it is the only cable. Whether it serves as a comparison depends on there
  being two runs, which is visible by counting runs. **The `prueba` key is unchanged, so no
  query breaks.**

  > **A revision with a single run, and that run `prueba`, means the unit arrived with no
  > umbilical of its own.** Exclude those from any umbilical failure analysis: that ROV can
  > never carry a cable finding — not because the cable was sound, but because it was not
  > there. Without the exclusion, the statistics say umbilicals fail less than they do.

### Documented

- **Checks are answered with the equipment's own umbilical.** Some depend on the cable and the
  checklist is answered once per revision. The convention survives all three scenarios — the
  only ambiguous one is *two runs*, and there the convention decides; a lone workshop-cable run
  means there was no other cable. A per-run checklist was considered and rejected: a new model
  with a migration for a minority of visits, when the difference between cables is already
  captured by the run's own numbers.

### Note for deploy

Existing revisions keep their seven lines — the checklist is copied when the revision is
created. **The «Actualizar checklist» button on a draft revision brings the nine new ones in.**
It only adds; it never touches an answer.

## [19.0.14.0.2] — 2026-08-17

### Fixed

- **Naming the records was not enough — they could not be *searched*.** 19.0.14.0.1 gave the
  two link models a readable `display_name`, but typing in either dropdown still matched
  nothing: Odoo searches on `_rec_name`, which neither model has. The only way through was
  "Search more", which opened a dialog listing **the ID column and nothing else**, because a
  model with no `name` field gets an auto-generated list view that has nothing to show.

  So the fix shipped half the problem: you could read the options once they appeared, but not
  find them. Both models now override `_search_display_name` (on the check name or the
  component, and on the finding name or the component), and both get a real list view for the
  "Search more" dialog.

  The component only joins the search under positive operators — under `not ilike` an OR
  returns too much, since one half failing to match is enough.

### Changed

- **«Detectado por» → «Prueba que lo detectó».** The old label read as if it were asking *who*
  found it. The new one names the answer it expects. Its help text now also says what the
  field is for, which is the least obvious and most valuable thing about it: *a finding that
  recurs and that no test detects is a check missing from the battery*.

### Documented

- **The seal inspection is deliberately not reachable from that field, and findings of family
  `terceros` will therefore sit there empty.** A seal answers *did somebody else open this
  unit*, not *what is failing*, and it already records its own outcome per row (`estado_sello`,
  `manipulacion_externa`). Checklist lines needed the pointer because on their own they only
  say ok / no_ok and never what was found.

  The consequence has to be respected when querying: marca de plumón, sello no original,
  tornillería cambiada and componente no original come from the physical inspection, so they
  carry a null here. **Counted naively they look like a gap in the battery, and there is
  none** — the inspection did detect them. The "missing check" query must exclude that family.

  No flag was added to the finding catalogue to mark this, because the answer already lives in
  `familia` — duplicating it in a boolean is the pattern this module has had to undo several
  times.

## [19.0.14.0.1] — 2026-08-17

### Fixed

- **The two link fields that close the analysis circuit showed a technical id instead of a
  name.** «Detectado por» offered `mc.rov.revision.chequeo,50` and «Resuelve el hallazgo»
  offered `mc.rov.revision.hallazgo,12`. Neither model has a `name` field or a `_rec_name`, so
  Odoo falls back to `model,id` — and both are dropdowns where a human has to pick a row.

  These are not cosmetic fields. `chequeo_origen_id` records **which check revealed the
  finding**, which is the detection axis of an FMEA and yields the most useful result the data
  can give: *a finding that recurs and that no check detects is a check missing from the
  battery*. `hallazgo_origen_id` is what ties a repair back to what was found. **Nobody links
  a row they cannot read**, and an unlinked row leaves a work line with "why it happened" and
  no "what was found".

  Line checks now read `«Estanqueidad bajo presión»`, or `«Marcas de plumón · E-pod»` when the
  check is generated per component — without the component, five rows of the same check would
  be indistinguishable. Findings read `«Motor / Rotor · Corrosión»`.

  Same bug and same fix as `mc.rov.linea.falla` in 19.0.13.0.0. That one was fixed because a
  `UserError` had to name the line; its two siblings were not checked at the time. Spotted on
  screen after deploying 19.0.14.0.0.

## [19.0.14.0.0] — 2026-08-17

The tabs become the process. Rationale in
[`docs/designs/revision-tecnica.md`](docs/designs/revision-tecnica.md) §§ 8.1–8.4.

### Changed

- **Repair order tabs are now the four moments, left to right: Recepción · Diagnóstico ·
  Reparación · Repuestos · Cierre · Notas.** Three of the four moments were already tabs and
  the first one was not — it lived loose in the header, split across both columns and
  interleaved with Odoo's native fields, so the tab bar did not tell you what the process was.

  *Recepción* is new and takes the four intake fields. *Revisiones* → **Diagnóstico**,
  *Trabajos realizados* → **Reparación**, *Resultado* → **Cierre**. Field names and model
  names are unchanged; only the labels moved.

  **«Diagnóstico» is deliberately imprecise:** that tab also holds the *second* revision, the
  one run after repairing, which verifies rather than diagnoses. Accepted because the vast
  majority of visits carry a single, diagnostic revision, and process legibility beats
  precision on the rare case.

  **Repuestos stays a separate tab** although it is the same moment as Reparación. They are
  two models doing two things — the *narrative* of the work versus the *material* consumed
  from stock and invoiced — and pulling Odoo's native parts list into a custom page drags
  behaviour that breaks on the next upgrade. What ties them is the validation below, not the
  layout.

- **Revision tabs go from five to three: Sellos · Pruebas · Hallazgos.** *Sellos* moves first
  because seals are inspected **before touching the equipment** — its own banner says so, and
  it was second. *Corridas* folds into *Pruebas*: a run is not a test, it is the **condition**
  the tests ran under, but it happens in the same session, and keeping them apart forced a tab
  jump mid-work. *Condiciones* disappears with the temperature move below.

- **`temperatura_interior` / `temperatura_exterior` move from `mc.rov.revision` to
  `mc.rov.revision.corrida`.** Both halves of the claim that filed them under "measurements
  that do not depend on the cable" were wrong: they are taken **once per run**, so two
  umbilicals give two readings — and storing them on the header forced picking one or
  averaging, both of which destroy the very comparison that makes the control run useful.
  And they *do* depend on the cable: a long umbilical drops voltage and heats.

  The original design listed these two fields with **no recorded justification**. They were
  inherited, not decided.

  > **Report constraint, recorded now so it is not lost:** temperature is being measured again
  > as an **internal** figure and **must not be printed**. It used to be handed to the
  > customer and the customer used it against Marine Connection. It is the first concrete case
  > of what the PDF report will have to decide field by field.

### Added

- **`mc.rov.accion.consume_repuesto`** and a close-time check. A work line with action "Cambio
  completo" and no product line means a part was swapped and never recorded — what is lost is
  the link to the part's lot, and with it any later answer to *which component fails most* or
  *how long one lasts*. Marked on the two change actions; which actions require it is read
  from the flag, never from comparing names, because the catalogue is configurable.

  **Declared scope:** it demands *at least one* product line, not one per change. An order
  with three changes and one part recorded passes. That is a deliberate floor — one-to-one
  correspondence would require saying which part goes with which job, which is a field that
  does not exist.

- **`repair.order.mc_revision_pendiente`** (stored) and a **«Revisión sin confirmar»** filter.
  Closing an order with its revision still in draft was possible and invisible. Blocking it
  was considered and **rejected**: a revision is auto-created on every ROV order, so blocking
  would force walking twenty checks even when the unit came in to swap a connector — and when
  answering costs, people tick "No aplica" down the list to get through, which poisons the
  data far worse than a draft revision does. The empty here is also not ambiguous: the state
  literally reads *Borrador*.

  Unlike «Sin síntoma registrado», this filter **can** reach zero — the revision can be
  confirmed any day. If it accumulates a pile over the coming months, that is the evidence to
  revisit blocking, with a real cost instead of a guess.

### Migration

`19.0.14.0.0/pre-migrate.py` drops the two temperature columns from `mc_rov_revision`; the ORM
recreates them on `mc_rov_revision_corrida`. `odoo_prod` had **no revision with a temperature
recorded**, which is what made this clean — a per-session reading cannot be split across two
runs without inventing the second.

**If it finds data, it drops nothing** and logs a warning instead, leaving two inert orphan
columns rather than losing measurements silently.

### Documentation

- `docs/runbooks/deploy.md` gains the browser-cache trap: Odoo's web client serves cached view
  definitions for as long as the tab stays loaded, so a tab open from before the deploy shows
  the **old** form while everything server-side is correct. Hard-refresh before trusting any
  on-screen check. This cost fifteen minutes on 2026-08-14, with the combined view arch
  verified correct and the fields still missing from the screen.

## [19.0.13.0.0] — 2026-08-14

Failure diagnostics. Design in
[`docs/designs/diagnostico-de-fallas.md`](docs/designs/diagnostico-de-fallas.md).

### Added

- **`mc.rov.sintoma`** — catalogue of what the customer *reports*, 27 seed entries across
  nine families. The module could already record what the workshop *finds*
  (`mc.rov.revision.hallazgo`); what someone *says* went into a free-text paragraph and could
  not be counted. Without both halves you lose the one analysis a workshop can produce and a
  manufacturer cannot: **how often what the customer thought was broken was not what was
  broken.**

- **`repair.order.sintoma_ids`** and **`repair.order.componente_sospechado_ids`** — what the
  customer *saw* and what the customer *deduces*, kept apart. The test for which list
  something belongs in is "did they see it, or are they inferring it?": *a motor doesn't spin*
  is a symptom, *I think it's the umbilical* is a suspicion. The suspicion field reuses
  `mc.rov.componente`, the same catalogue as findings and work lines, so
  "suspected the umbilical, turned out to be the connector" is a query rather than a read.

  Both live on the order and not on the revision because they are captured in a window that
  does not come back: **intake is the only time there is anyone to ask.** Neither is required
  — an empty symptom is honestly empty, and forcing it would produce inventions. Both go with
  `no_create`: at the counter with the customer waiting is exactly where four spellings of
  "won't turn on" appear and the count dies.

- **`mc.rov.linea.falla.analisis_causa`** (*Por qué pasó*) — free text next to `origen`,
  never required. Between the finding ("O-ring damaged") and the origin ("design") sits the
  reasoning, and in a field that is a self-assessment in three of its six values, that
  reasoning is what makes the value auditable six months later. **Text and not five numbered
  fields**: the number of links varies — sometimes three, sometimes eight — and forcing five
  produces filler. It is also the cheap thing to retire if it turns out to be filled only in
  complex cases, which is what is expected.

- **Search view for `repair.order`** — the module had none. Adds a **"Sin síntoma
  registrado"** filter, scoped to orders that are not yet done or cancelled, plus search and
  group-by on intervention type. The scoping is not cosmetic: an incomplete serial can be
  completed any day, but an order closed a year ago cannot — the customer is gone. Unscoped,
  the filter would drag the whole history forever, never reach zero, and stop being looked at.

  It does **not** group by origin, although that was on the pending list: since 19.0.8.0.0
  the field lives on the work line. An order with three jobs has three origins, and grouping
  it by one would need the derived field that silently drops the other two.

- `sum` on the `mc_total_horas` column, which the field was stored for in 19.0.5.2.0.

### Changed

- **`causa_raiz` → `origen`, a breaking rename with new keys.** The old field mixed two
  questions — *what physically happened* and *whose problem is it* — and two of its six values
  are the proof: `corrosion` is a mechanism (it exists **as a finding** in
  `mc.rov.hallazgo`) and `accidente` is a circumstance. Neither answers whose problem it is.

  New keys: `diseno` · `falla_fabricacion` · `pieza_proveedor` · `mal_uso` · `desgaste` ·
  `desconocida`. Four are reused verbatim; `corrosion` and `accidente` are migrated.

  **The parentheses are in the label, not the tooltip** — the field is a list column, so the
  chosen value gets cut off, but the open dropdown shows the options in full, which is exactly
  when the clarification is needed.

- **`origen` is required to close the order, not to save the line.** A model-level `required`
  would demand it while the technician is still repairing, when the answer is speculation —
  and would produce "No determinado" ticked to get past the dialog, indistinguishable from a
  real one. It is validated on the transition to `done`, next to `_validar_tipo_intervencion`.
  **"No determinado" closes the order**: forcing an accusation produces false accusations.

  An order with **no** work lines closes fine — a pure diagnostic visit records none.

- `mc.rov.linea.falla` gained `_compute_display_name` (component · action). Without it the
  close-time error would name the line `mc.rov.linea.falla,42`.

- The intake block (symptoms, suspicion) sits next to `falla_reportada` on the main form, not
  in a tab: it is filled with the customer standing there.

- **Origin and its written analysis are answered in the *Resultado* tab**, through a second
  one2many over the same relation — the pattern the revision already uses for its seven
  `chequeo_*_ids` fields. "Trabajos realizados" is where you write *while* working, and its
  list already carries ten columns. The closing list is `create="0" delete="0"`.

- Three new components: **Luces**, **Manipulador**, **Sonar**. Three symptoms named
  components that did not exist, and the reported-vs-real crossing broke exactly there. A
  fourth candidate, "Software de superficie", was dropped on writing the data: `comp_electronica`
  is already named "Electrónica / Software".

### Documented (not a code change)

- **Archiving a catalogue entry hides it from history, it does not preserve it.** Retiring an
  entry is meant to be a flag rather than a deletion — but reading an x2many applies
  `active_test`, so an order that reported a now-archived symptom comes back with one symptom
  fewer, silently. The relation row survives; you need `active_test=False` to see it.

  The consequence is analytical, not cosmetic: **archive a commonly used entry and its
  historical count drops to zero, which looks exactly like it having stopped occurring.**
  Applies to every catalogue with `active` reached through an x2many. Not new here — it had
  never been written down. Surfaced by a test that asserted the opposite.

### Migration

`19.0.13.0.0/pre-migrate.py`. `corrosion` → `desconocida`, with the old value appended to
`detalle` so it is not lost; `accidente` → `mal_uso`, which the new label absorbs explicitly
("Uso del cliente (mal uso o accidente)").

**And rows with no `causa_raiz` at all → `desconocida`.** The old field was never required, so
production has work lines with no cause; leaving them NULL would make them indistinguishable
from a value lost in the migration.

Pre-migrate and not post-migrate so the new column is written before the ORM processes the
model, with no window in which the old value is gone and the new one is not there yet.

### Removed

- **`mc.rov.causa.sistemica`** — designed and cut before implementation. Linking the second
  occurrence to the first requires a person to remember the first, months later. That is
  pattern memory across time, which a person does not have and a query does: once symptom,
  suspected component, finding, component and origin are all structured, `GROUP BY origen,
  componente_id` finds the repeats on its own. A hand-maintained catalogue adds no query
  power — it adds a label someone has to remember to apply, and a forgotten label makes the
  query lie.

- **`momento_falla`** — designed and cut before implementation. Temporality passes the design's
  own test for what a symptom is (the customer *saw* the fault come and go), and as a separate
  field it carried a default "No se sabe" that made the very distinction it existed for —
  "doesn't know" versus "nobody asked" — impossible. It enters as three catalogue entries in a
  `temporalidad` family instead.

## [19.0.12.1.1] — 2026-08-14

### Fixed

- **Nine blank rows in the *Pruebas* tab.** Odoo pads every editable list to a minimum of
  four rows (`web/static/src/views/list/list_renderer.js`, `getEmptyRowIds`), minus one when
  the "Add a line" link is shown. The tests tab is the worst possible case for that rule:
  seven sections, one to three checks each, all with `create="0"` — so nothing is subtracted
  and four blocks carry nine blank rows between them.

  Dropping `editable` would remove them and cost far more: every check would move to a modal
  dialog, seven windows to fill what the paper sheet answers in seven consecutive marks.

  The rule is structural because Odoo leaves no alternative — the filler `<tr>` is rendered
  with no class and no identifying attribute, just a `<td>` holding a zero-width space. Data
  rows do carry `o_data_row`. If a future Odoo version gives them a class, the rule stops
  applying and the rows come back: it looks odd, nothing breaks.

## [19.0.12.1.0] — 2026-08-14

### Added

- **«Actualizar checklist» button** on a draft revision. The checklist is copied from the
  catalog when the revision is created, and the revision is created when the repair order
  leaves draft — that is, the moment the unit enters the workshop. So every unit already in
  the workshop has its sheet, and a check added to the catalog on a Tuesday reaches none of
  them: only units arriving afterwards. The button pulls in the missing lines on demand.

  It is a button and not automatic on purpose. A half-filled sheet that changes content
  without anyone touching it is worse than a stale one, because the technician already read
  it end to end and will not read it again. Asking for it fixes the moment.

  It only adds — `_generar_chequeos` never deletes answers — so pressing it twice costs
  nothing, and a confirmed revision refuses: a closed sheet that grows stops being the
  record of what was checked that day.

### Fixed

- **The test blocks used half the width of the page.** Each section of the *Pruebas* tab is a
  `<group>`, which Odoo renders as a two-column table, so a list placed in it without
  `colspan="2"` gets one of those two columns. The visible symptom was the check name cut
  short — `Estanqueid…` for "Estanqueidad bajo presión" — with a different width per section,
  because each list sized its own columns. The luces block already carried the `colspan`; the
  other six did not.

  The empty rows below each block are not this bug and are not fixable from the view: Odoo
  pads every editable list to a minimum of four rows.

## [19.0.12.0.0] — 2026-08-14

### Changed — breaking

- **One revision per visit, not two.** `mc.rov.revision.tipo` lost `recepcion` and
  `entrega`, which collapsed into a single `reparacion`. The type is now
  `fabricacion` | `reparacion` | `terreno`.

  The split assumed both sheets would be filled. The paper sheet it replaces is *one* per
  repaired unit, so asking for two does not produce two records: it produces one filled and
  one blank, with no way to tell which visit left which blank. Before/after comparison moves
  to **between visits** — the interval the failure analysis wanted anyway, because that is
  the one the unit spent flying. The "test, fix, retest" case is still supported, now
  through the **Nueva revisión** button rather than by system-wide obligation, with
  `numero_en_visita` telling the two apart.

  **What to watch:** seal state must now be recorded as *how the unit arrived*, guaranteed
  by the field label ("Estado del sello al recibir") and a banner rather than by the record
  type. A seal the workshop itself broke during the work, entered here, would count as
  third-party tampering.

- **`mc.rov.chequeo.aplica_recepcion` and `aplica_entrega` merged into `aplica_reparacion`**;
  both columns dropped. Existing rows migrate as `recepcion OR entrega`, because losing a
  check from the battery is worse than running one too many.

- **Pipeline contract breaks on both counts** — see `docs/integrations/pipeline.md`. A query
  filtering the old `tipo` keys returns nothing rather than erroring, which is the more
  dangerous kind of break.

### Changed

- **The checks tab is now laid out like the paper sheet.** Seven one2many views of the same
  lines, one per section, each rendered as a titled block — *Prueba de video* with camera and
  tilt, *Prueba de navegación* with the propellers and both movements. A single list grouped
  by section was rejected: a group has to be expanded before you can type in it, and a
  checklist that demands clicks up front gets filled halfway. Empty sections hide themselves.

- **The technician can no longer add or delete check lines**, only answer them. This reverses
  an earlier call ("an extra check is still information"): if rows can be added, the absence
  of a row stops meaning anything, and telling *checked and clean* from *never occurred to me
  to look* is the entire point of a checklist. The catalogue is administered from
  `Reparaciones → Configuración → Catálogos ROV → Pasos de testeo ROV`.

- **The light counts moved into the checks tab**, under a *Prueba de luces* heading, together
  with the mismatch warning against the unit's spec sheet. They were in a separate
  *Mediciones* tab, away from the rest of the battery, and got lost. That tab is now
  *Condiciones* and holds temperatures and the field-test fields.

- **«No lo tiene» is now labelled «No aplica»**, in both checks and seals. The stored key did
  not change, so there is no data migration and no query breaks. The old label existed to
  keep *the unit lacks it* apart from *we did not check it* — but the latter was never a
  value, it is the empty field, which blocks confirmation. The distinction was guaranteed
  elsewhere all along.

- **Repair order form:** the owner and received-equipment fields moved out of the `div` that
  wraps `lot_id` in the base arch, where they rendered inline and unlabelled and read as a
  duplicate of the serial number. The native `tag_ids` field is hidden — `tipo_intervencion_ids`
  already classifies the order and two identical tag widgets side by side only get the wrong
  one filled. The `parts` tab is now **Repuestos**.

- **Revisions can be opened from the repair order again.** The one2many is read-only, so
  clicking a row used to open a read-only dialog: a revision could be filled when created and
  never again. `open_form_view` adds the link to its real form.

- **`Inventario → Configuración → Catálogos ROV`** now groups the surface-software and
  flight-controller catalogues, mirroring the Repair-side menu instead of leaving them loose
  among Odoo's own settings.

### Removed

- **The "Marcas de plumón" check.** Asking it across five components on every revision cost
  five mandatory answers per sheet and almost never said anything. Seeing a felt-tip mark
  remains recordable as a **finding** — the catalogue entry stays — which is the right shape
  for something that happens sometimes. Its check lines are deleted by the migration, since
  `chequeo_id` is `ondelete="restrict"` and Odoo's obsolete-data cleanup would have given up
  silently.

  Nothing in the seed catalogue uses `por_componente` any more. The mechanism is kept: it is
  what makes "this has to be answered component by component" possible without a deploy.

### Migration

`19.0.12.0.0` — `pre-migrate.py` does all three data jobs, deliberately: data files load
between pre and post, so what runs first is what the XML finds, and the values declared in
XML win. `post-migrate.py` recomputes `manipulacion_externa`, whose rule changed and whose
column already exists with data.

### Tests

150 (was 144). The type filter and the per-component generation are now covered with a check
created inside the test rather than with catalogue records, because the seed catalogue runs
in all three types and the catalogue changes without a deploy.

## [19.0.11.1.0] — 2026-08-13

### Added
- **The intake revision is now created automatically** when a repair order leaves draft,
  instead of waiting for someone to press a button.

  It always happens — every workshop visit starts by checking how the unit arrived — and
  the module's rule is that **what always happens gets created automatically; what
  sometimes happens gets a button.** Depending on memory for a mandatory step is how a step
  gets skipped in silence, and months later nobody understands why there is no data. The
  manufacturing revision keeps its button, because that one genuinely does not always
  happen.

  Three conditions, and all three matter: **on leaving draft** and not on creation, since a
  draft is a quotation and the unit may not have arrived; **ROVs only**, since a component
  repair carries no revision; and **only if none exists**, so bouncing between states does
  not duplicate.

### Documentation
- **The pipeline contract listed `mc.rov.protocolo` and its line models, which no longer
  exist.** Same class of breakage as the one corrected on 2026-08-12, committed again by the
  rename. It now documents `mc.rov.revision` and its five models in full — including the
  warning that **`numero_en_visita` must be read before aggregating**, because counting
  findings per revision rather than per visit drops a rate to a third when a visit held
  three of them.
- `designs/protocolo-de-pruebas.md` renamed to `designs/revision-tecnica.md` and brought up
  to date, with § 1.2 recording why the name changed — beside § 1.1, which records the scope
  error. Both are kept rather than erased: the next reader needs to know those questions
  exist.
- `pendientes.md` rewritten. It described a state three versions old.

- 5 tests (139 → 144).

## [19.0.11.0.1] — 2026-08-13

### Fixed
- **The button that replaced the manufacturing-revision menu was never added.**
  `19.0.11.0.0` removed the menu on the grounds that a button on the serial number is the
  right place — and shipped the model method with nothing calling it. Manufacturing was
  left with no way to create a revision at all, which is worse than the menu it replaced.
- **The revisions tab on a repair order without a serial looked broken.** The buttons hide
  when there is no `lot_id`, since a revision needs a unit — but the result was an empty tab
  with no explanation. It now says what to fill in first.
- `action_nuevo_revision_*` renamed to `action_nueva_revision_*`. The bulk rename in
  `19.0.11.0.0` left the article disagreeing with the noun in the method names.

## [19.0.11.0.0] — 2026-08-13

### Changed
- **`Protocolo` is renamed to `Revisión técnica`.** "Protocolo" means *procedure*, and the
  record is not the procedure — the procedure is the check catalogue. What gets created on
  every visit is the result of running it.

  The name had already caused a real misunderstanding: *"shouldn't it always be the same
  one?"*. It should — the **procedure** is always the same. The filled-in record is not.

  `Revisión técnica` was chosen because in Chile everyone already knows what one is: a
  periodic, standardised battery of tests on a vehicle, whose outcome is *approved /
  approved with observations / rejected* and which leaves a document and a history per
  unit. That is what this is, down to the three outcome values, which were already
  implemented under those names. The long form names the model and the menu; `Revisión`
  alone is used in buttons and columns, where it is unambiguous.

- **`numero_en_visita`, and it is what protects the analysis.** Several revisions in one
  visit are legitimate — test, fix, retest — but they poison statistics if you cannot tell
  which is which: *"share of units arriving with a broken motor"* falls to a third if one
  visit had three revisions and the finding sits in one.

  **The rule is that the unit of analysis is the visit, not the revision.** This field
  makes "the first" and "the last" unambiguous: #1 says what the unit arrived with, the
  last says how it left. Ordering by date is not enough — several on the same day do not
  order themselves.

- **Manufacturing revisions lose their menu** and are created with a button on the serial
  number, which is where manufacturing already works. A global menu would only serve to see
  all of them together, and nobody has that question.

  It is a button and not automatic because a manufacturing revision **does not always
  happen** — a unit is built once and at most modified a few times — and because the system
  cannot detect a modification: a spec-sheet change is a write, and so is fixing a typo. The
  module's rule: create automatically what always happens, by hand what sometimes happens.

- **The five repair catalogues now sit under one `Catálogos ROV` entry** instead of five
  loose ones. For daily use nobody needs that menu anyway: typing a name into a catalogue
  field offers *Create* inline. The menu is for **maintaining** the catalogue.

### Added
- **`tracking=True` on fifteen spec-sheet fields** — the re-engineering history. A ROV gets
  modified over its life (T200 → T500 motors, Pixhawk → Navigator, a new umbilical) and
  until now the change left no trace. Each one now lands in the chatter with a date and
  old → new value, with no model and no migration.

  It does not cover the *why* — that lives in a *Conversión / Upgrade* order — nor how the
  unit measured afterwards, which is a manufacturing revision.

### Migration
`19.0.11.0.0/pre-migrate.py` **discards the old models and lets the ORM create the new
ones**. The rename is of name, not of structure, so keeping the data would mean rewriting
six system tables — and missing one leaves invisible debris: orphaned chatter, attachments
pointing at a model that no longer exists.

Production held **1 test record with 22 checklist lines and no findings** when this
shipped, created the same day to look at the screen. **Anyone deploying this with real
revisions will lose them**; the script logs the row count of every table it drops.

## [19.0.10.0.0] — 2026-08-13

### Changed
- **The physical inspection was modelled wrong and is rebuilt.** It shipped as three
  independent checkboxes per component — *marcas de plumón*, *sellos antiguos*, *sellos
  nuevos* — which cannot express the process they describe.

  A seal has **continuity**: the one placed today is the one inspected on the next visit.
  If it is intact it stays; if it is broken a new one goes on, and *that* becomes the old
  one next time. Three booleans say nothing about whether it was broken, and "sello antiguo
  ✓ / sello nuevo ✓" is not an answer to the question the inspection exists to ask — *has
  anyone else opened this unit?*

  It is now **one row per sealed component** with a single field: the state the seal was
  found in. Five rows instead of fifteen, one click each.

  One field is enough because the protocol's `tipo` supplies the context: at intake the
  state is *how it arrived*, at delivery it is *how we left it*. And **no field records who
  broke it**, because the ambiguity does not exist — the workshop never breaks a seal
  without recording it, and its own breakages happen during the work, after intake. So a
  seal found broken at intake is third-party manipulation, full stop. `manipulacion_externa`
  is stored and derived from exactly that.

- **`Marcas de plumón` stays in the check catalogue** rather than moving into the new model.
  It may stop being used in favour of seals only; as a catalogue check it retires by
  unticking `active`, whereas as a model field it would need a deploy. That is the line
  worth drawing: **what has continuity and states needs a model; a yes/no that may disappear
  belongs in the configurable catalogue.**

- **The check list now allows adding rows, but still not deleting them.** Blocking creation
  protected nothing — an extra check a technician performed is still information. Blocking
  deletion is what matters: removing a row hides that something went unchecked, which is
  precisely what a checklist exists to prevent.

- **Answers are radio buttons instead of dropdowns**, on both the checks and the seals. The
  manufacturing sheet is filled with one click per field; the checklist took two per row
  across fifteen-plus rows for the same kind of task.

- **The surface-software and flight-controller catalogues moved to
  `Inventario → Configuración`.** They are vocabulary of the **manufacturing** spec sheet,
  which lives on the serial number — leaving their menus under Repairs forced manufacturing
  into the wrong app to add a software.

- 7 tests (132 → 139).

## [19.0.9.0.0] — 2026-08-13

### Changed
- **`mc_software_superficie` and `mc_controlador_vuelo` become catalogues** —
  `mc.rov.software.superficie` and `mc.rov.controlador.vuelo`, both manageable from
  *Reparaciones → Configuración*.

  The reason is not being able to **add** options; a `Selection` allows that too, at the
  cost of a deploy. It is being able to **retire** them. Removing a value from a `Selection`
  orphans every unit that has it stored, which needs a cleanup migration each time — the
  same one `19.0.7.0.0` had to run for `Desconocido`. With `active`, the historical record
  still resolves and the option simply stops being offered.

  That matters because the landscape is already moving: ROVControl is temporary and Crabby
  replaces it, and Navigator is itself slated for replacement.

  *An earlier justification in `19.0.6.0.0` argued a `Selection` was fine here because
  "unlike `tipo_intervencion`, only one value applies at a time". That was true about
  cardinality and said nothing about changeability, which is the axis that actually
  mattered.*

- **Both fields render as radio buttons**, consistent with the other choices in
  *Especificaciones*. Odoo's radio widget works on a Many2one, so the catalogue change costs
  nothing visually.

- **The protocols tab is now first on the repair order**, ahead of *Trabajos realizados* and
  *Piezas*. The intake protocol is step one of the actual process — the unit arrives, it is
  tested, findings are recorded — and it was sitting behind two tabs that cover what happens
  afterwards. The tab order was reordered to the workshop's sequence in `19.0.5.2.0`; adding
  protocols at the end contradicted that same criterion.

### Added
- **Two buttons on the protocols tab** — *Nuevo protocolo de recepción* and *Nuevo protocolo
  de entrega* — that create the record already linked to the order and the serial.

  Without them the protocol could be seen from the order but not created there: you had to
  leave for the menu, find the serial and come back. That turned the first real step of the
  process into a separate errand behind a navigation nobody was going to perform.

### Migration
`19.0.9.0.0` needs **two scripts**, because Odoo does not convert a column's type when a
field goes from `Selection` to `Many2one` — it finds a `varchar` where it expects an
`integer`, logs a warning and leaves the column, which would leave the field permanently
broken.

`pre-migrate` renames the text columns aside; the module load then creates clean integer
columns; `post-migrate` translates each stored string to its catalogue record, matching by
name — which is exactly what the `Selection` stored, since its keys were the visible
strings. **A value with no match is created in the catalogue rather than dropped**: it may
have arrived by import, and deleting it would assert the unit had nothing.

- 1 test (131 → 132).

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
