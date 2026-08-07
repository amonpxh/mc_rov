# Changelog

All notable changes to the `mc_rov` Odoo module are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this module adheres to [semantic versioning](https://semver.org/) within the constraints of Odoo's version scheme: `19.0.X.Y.Z` where `19.0` is the Odoo major, `X` is breaking-change/migration, `Y` is feature, `Z` is bugfix.

## [19.0.2.0.0] — 2026-08-07

### Changed
- **`es_un_rov` is now derived from the product category, not set by hand.** A serial number is flagged as ROV when its product's category sits anywhere under the ROV vehicle branch (`child_of`), covering both `ROV-MC` and `ROV-XX`. The field is stored, computed and read-only.
- The root category is resolved from the `mc_rov.rov_category_id` system parameter, falling back to the `__import__.cat_ROV` external ID left by the category tree import. The parameter lets the tree be reorganised without a deploy.
- `es_un_rov` is part of the pipeline contract (see `docs/integrations/pipeline.md`). Its name and type are unchanged; its semantics are not.

### Added
- `product.category.write` override that recomputes affected serials when a category is re-parented — `@api.depends("product_id.categ_id")` does not cover that case.
- 5 tests on `es_un_rov` (both ROV branches, nested subcategory, unrelated category, re-parenting).

### Migration
- `migrations/19.0.2.0.0/post-migrate.py` seeds the system parameter and recomputes `es_un_rov` for every existing serial. **Serials flagged by hand whose product is outside the ROV branch lose the flag**, which hides their four ficha-técnica tabs until the product is recategorised. The script logs how many were affected and aborts without touching data if the root category cannot be resolved.

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
