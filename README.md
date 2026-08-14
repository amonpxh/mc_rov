# mc_rov — Marine Connection ROV Management

Odoo 19 module for ROV (Remotely Operated Vehicle) inventory and repair tracking. Extends Odoo's standard `stock` and `repair` modules, plus introduces a custom `mc.rov.componente` model family for component-level tracking.

## Status

- **Odoo version:** 19
- **Module version:** 19.0.12.0.0 (see `__manifest__.py`)
- **Tests:** 150
- **License:** LGPL-3
- **Maintenance:** active. See `CODEOWNERS`.

## Quick links

- **Module encyclopedia** (models, fields, conventions, gotchas) → [`CLAUDE.md`](CLAUDE.md)
- **Inventory design context** (category tree, traceability chain, taxonomy boundaries) → [`INVENTARIO.md`](INVENTARIO.md)
- **Deploy procedure** → [`docs/runbooks/deploy.md`](docs/runbooks/deploy.md)
- **Running tests** → [`docs/runbooks/testing.md`](docs/runbooks/testing.md)
- **Pipeline integration** (how this module exposes data to the analytics pipeline) → [`docs/integrations/pipeline.md`](docs/integrations/pipeline.md)
- **Version history** → [`CHANGELOG.md`](CHANGELOG.md)

## Installing

In a fresh Odoo 19 environment:

```bash
# 1. Copy or symlink this folder into your Odoo addons path
# Example: /opt/odoo/custom-addons/mc_rov

# 2. Update Odoo's apps list
odoo-bin -c /etc/odoo/odoo.conf -u base -d <database> --stop-after-init

# 3. Install the module
odoo-bin -c /etc/odoo/odoo.conf -i mc_rov -d <database> --stop-after-init
```

Or via the Odoo UI: Apps → Update Apps List → search "Marine Connection" → Install.

## Contributing

Follow the GitHub Flow described in [`CLAUDE.md` § "Flujo de trabajo con git"](CLAUDE.md#flujo-de-trabajo-con-git). Commits use Conventional Commits format. PRs to `main` require ≥ 1 review and green CI (lint + tests).

## Owners

See `CODEOWNERS`.
