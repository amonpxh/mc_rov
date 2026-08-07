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
- `mc_estado_comercial` — still hand-maintained
- `mc_estado_operativo` — **derived since 19.0.3.0.0**, computed from the unit's open repair
  orders. Same name and type, different meaning: it is no longer an operator's assertion
  and cannot diverge from the orders. Do not treat a change in it as a human decision.
- `mc_repair_count` (computed)
- `ultima_mantencion` (computed) — **narrowed in 19.0.3.0.0** to preventive maintenance only
  (`tipo_intervencion = mantencion_preventiva`). It previously returned the date of any
  closed order, so pipeline history built before that version overstates maintenance.
- *(48 ficha técnica `mc_*` fields — pipeline consumes a subset; TBD list in Phase 1)*

### `repair.order`

Standard fields:
- `id`, `name`, `product_id`, `lot_id`, `state`, `create_date`, `schedule_date`

Custom mc_rov fields:
- `tipo_intervencion`, `item_2..5`
- `falla_reportada`
- `linea_falla_ids` (one2many)
- `estado_final`, `causa_raiz`
- `garantia_reparacion`, `fecha_garantia`
- `fecha_entrega_real`
- `observaciones_salida`
- `mc_total_horas` (computed)

### `mc.rov.componente` and related

- `mc.rov.componente`: `id`, `name`, `active`
- `mc.rov.subtipo`: `id`, `name`, `componente_id`, `active`
- `mc.rov.accion`: `id`, `name`, `active`
- `mc.rov.linea.falla`: `id`, `repair_id`, `componente_id`, `subtipo_id`, `accion_id`, `fecha`, `horas`, `detalle`

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
