# Runbook: Running mc_rov tests

**Audience:** anyone validating changes before merging or deploying.

**Time:** ~1-2 minutes for the full test suite (153 tests).

---

## Test environment

| Resource | Value |
|---|---|
| Test database | `odoo_test` |
| Config | `/etc/odoo/odoo.conf` |
| Test runner | Odoo's native test framework |
| Total tests | 168 (73 `stock.lot` + 16 `repair.order` + 18 `mc.rov.componente` + 46 `mc.rov.revision` + 15 diagnóstico de fallas) |

## Running all tests

```bash
sudo -u odoo odoo \
  -d odoo_test \
  -u mc_rov \
  --test-tags /mc_rov \
  --stop-after-init \
  --no-http \
  --config /etc/odoo/odoo.conf
```

**Important gotchas:**

1. **The `-u mc_rov` flag is required** — otherwise the test framework doesn't discover the module's tests.
2. **`--test-tags` syntax in Odoo 17+** is `/module:Class` with forward slash and colon. Not `module.Class`.

## Running a specific test class

```bash
sudo -u odoo odoo \
  -d odoo_test \
  -u mc_rov \
  --test-tags /mc_rov:TestMcRovComponente \
  --stop-after-init \
  --no-http \
  --config /etc/odoo/odoo.conf
```

Available test classes (as of v19.0.12.0.0):

| Class | Tests | Coverage |
|---|---|---|
| `TestStockLotRov` | 6 | `es_un_rov`, derived from the product category |
| `TestStockLotContadores` | 7 | `mc_repair_count`, `mc_mantencion_count` |
| `TestStockLotFechas` | 13 | `ultima_mantencion`, `ultima_reparacion`, sealing of `fecha_entrega_real` |
| `TestStockLotEstadoOperativo` | 6 | `mc_estado_operativo`, derived from open orders |
| `TestStockLotCicloMantencion` | 8 | `proxima_mantencion`, the configurable cycle length, and no clock once decommissioned |
| `TestStockLotPropiedad` | 6 | `mc_propietario_id` and the ownership history written by `write` |
| `TestStockLotEstadoComercial` | 7 | `mc_estado_comercial`, rentals, decommissioning |
| `TestStockLotTraspasoDesdeOrden` | 4 | resale detected at intake, transfer from the repair order |
| `TestStockLotFichaCompleta` | 11 | `mc_ficha_completa`, `mc_ficha_faltantes` y el cero de los numéricos |
| `TestMcRovBajaWizard` | 5 | the decommission dialog, including the required reason |
| `TestRepairOrder` | 16 | defaults, `tipo_intervencion_ids`, `fecha_entrega_real`, `linea_falla_ids`, `mc_total_horas`, the close-without-type block |
| `TestMcRovRevision` | 9 | secuencia, derivados, el filtro por tipo y el reparto por sección |
| `TestMcRovRevisionResultado` | 6 | `resultado` derivado: hallazgos, chequeos fallados y esfuerzo |
| `TestMcRovRevisionConfirmacion` | 7 | qué se exige para confirmar |
| `TestMcRovRevisionLuces` | 3 | la comparación contra la ficha técnica |
| `TestMcRovRevisionSellos` | 9 | la inspección de sellos y la evidencia de manipulación |
| `TestMcRovRevisionAutomatica` | 6 | la revisión que se abre sola, y el botón del segundo pase |
| `TestMcRovRevisionTrazabilidad` | 3 | el circuito hallazgo → trabajo |
| `TestMcRovComponente` | 18 | all four custom models (`componente`, `subtipo`, `accion`, `linea.falla`) |
| `TestDiagnosticoFallas` | 15 | síntoma y sospecha, `origen` exigido al cerrar, el análisis escrito |

Two shared fixture bases declare no tests — do not target them with `--test-tags`:
`StockLotOrdenesCommon` (classes that need repair orders), `RevisionCommon` (revision
classes) and `StockLotPropiedadCommon`
(classes that need a real ROV, i.e. the category tree, because ownership history is only
written for units with `es_un_rov` on).

> Copy the class names from this table, not from memory. `--test-tags` silently matches
> nothing and exits green when the class name is wrong.

## Expected output

All 153 tests should pass. Look for `0 failed, 0 error(s) of 153 tests` in the output (exact format depends on Odoo verbosity).

## When tests fail

1. **Read the failure output.** Odoo prints stack traces and assertion errors at the end of the test phase.
2. **If the failure is in code you changed:** fix and re-run.
3. **If the failure is in code you didn't touch:**
   - Check `git log` for recent changes nearby.
   - Could be a flaky test (rare in this suite).
   - Could be a schema drift from `data/mc_rov_data.xml`.
   - Could be a side-effect from a migration that didn't run cleanly.
4. **Never merge a PR with red tests.** Branch protection on `main` enforces this, but be vigilant in any case.

## CI test runs

CI runs the same suite automatically on every PR (see `.github/workflows/test.yml`). You can rely on green CI as evidence that tests pass in a clean environment with no local state contamination.

## Test maintenance discipline

- Every new feature should ship with at least one test.
- Every bug fix should ship with a test that reproduces the bug (would have caught it).
- Test files live in `tests/test_<model>.py` following Odoo's `TransactionCase` / `SavepointCase` patterns.
