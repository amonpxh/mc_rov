# Runbook: Running mc_rov tests

**Audience:** anyone validating changes before merging or deploying.

**Time:** ~1-2 minutes for the full test suite (34 tests).

---

## Test environment

| Resource | Value |
|---|---|
| Test database | `odoo_test` |
| Config | `/etc/odoo/odoo.conf` |
| Test runner | Odoo's native test framework |
| Total tests | 34 (8 `stock.lot` + 10 `repair.order` + 16 `mc.rov.componente`) |

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

Available test classes (as of v19.0.2.0.0):

| Class | Tests | Coverage |
|---|---|---|
| `TestStockLotRov` | 14 | `es_un_rov` (derived from category), `mc_repair_count`, `ultima_mantencion` |
| `TestRepairOrder` | 7 | defaults, selections, `fecha_entrega_real`, `linea_falla_ids` |
| `TestMcRovComponente` | 18 | all four custom models (`componente`, `subtipo`, `accion`, `linea.falla`) |

> Copy the class names from this table, not from memory. `--test-tags` silently matches
> nothing and exits green when the class name is wrong.

## Expected output

All 39 tests should pass. Look for `0 failed, 0 error(s) of 39 tests` in the output (exact format depends on Odoo verbosity).

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
