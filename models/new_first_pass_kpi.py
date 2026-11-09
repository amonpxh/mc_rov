"""Read the first formal joint outcome of actually manufactured ROV serials."""

from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError

from .business_kpi_metrics import first_pass_status


class NewFirstPassKPI(models.AbstractModel):
    """An explicit current manufacturing selection, never a fabricated reporting cohort."""

    _name = "mc.rov.new.acceptance.kpi"
    _description = "Primera aceptación conjunta de equipo nuevo"

    def _check_caller(self):
        user = self.env.user
        if (
            user.share
            or user._is_public()
            or not user.has_group("base.group_user")
            or not user.has_group("mc_rov.group_work_assignment_team")
        ):
            raise AccessError(_("Se requiere consulta del trabajo del equipo."))
        return self.env.companies.ids

    def _selected_productions(self, production_ids, companies):
        if not isinstance(production_ids, list) or any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in production_ids
        ):
            raise ValidationError(_("Seleccione identificadores válidos de fabricación."))
        productions = (
            self.env["mrp.production"]
            .with_context(active_test=False)
            .browse(sorted(set(production_ids)))
        )
        if len(productions.exists()) != len(productions):
            raise AccessError(_("La selección contiene fabricaciones no autorizadas."))
        productions.check_access("read")
        if any(row.company_id.id not in companies for row in productions):
            raise AccessError(_("La selección contiene fabricaciones no autorizadas."))
        productions.product_id.check_access("read")
        return productions

    def _produced_units(self, productions):
        if not productions:
            return {}
        root = self.env["stock.lot"]._get_rov_root_category()
        if not root or len(root) != 1 or not root.exists():
            raise ValidationError(
                _("Configure la categoría raíz de vehículos antes de calcular el KPI.")
            )
        root.with_user(self.env.uid).check_access("read")
        categories = productions.product_id.categ_id
        categories.check_access("read")
        eligible = self.env["product.category"].search(
            [("id", "in", categories.ids), ("id", "child_of", root.id)]
        )
        units = {}
        for production in productions:
            if production.product_id.categ_id not in eligible:
                continue
            for lot in self.env["mc.rov.acceptance.activity.automation"]._produced_lots(
                production
            ):
                lot.product_id.check_access("read")
                if not production.production_group_id:
                    raise ValidationError(
                        _("La fabricación debe conservar su grupo nativo de origen.")
                    )
                key = (production.company_id.id, lot.id)
                unit = {
                    "company_id": production.company_id.id,
                    "lot_id": lot.id,
                    "product_id": lot.product_id.id,
                    "production_group_id": production.production_group_id.id,
                }
                if key in units and units[key] != unit:
                    raise ValidationError(
                        _("La serie tiene orígenes de fabricación incompatibles.")
                    )
                units[key] = unit
        return units

    def _authorized_attempts(self, units, companies):
        # A hidden historical source rejects the whole episode, rather than dropping
        # an inconvenient first failure or returning misleading partial aggregates.
        episodes = (
            self.env["mc.rov.new.acceptance.episode"]
            .sudo()
            .search(
                [
                    ("lot_id", "in", [unit["lot_id"] for unit in units.values()]),
                    ("company_id", "in", companies),
                ]
            )
            .filtered(lambda row: (row.company_id.id, row.lot_id.id) in units)
        )
        originals = self.env["mrp.production"].browse(episodes.production_id.ids)
        originals.check_access("read")
        originals.product_id.check_access("read")
        for episode in episodes:
            unit = units[(episode.company_id.id, episode.lot_id.id)]
            if (
                episode.product_id.id != unit["product_id"]
                or episode.production_group_id.id != unit["production_group_id"]
                or episode.production_id.company_id != episode.company_id
            ):
                raise AccessError(
                    _("La identidad histórica no corresponde a la unidad seleccionada.")
                )
        attempts = (
            self.env["mc.rov.new.acceptance.attempt"]
            .sudo()
            .search([("episode_id", "in", episodes.ids)], order="episode_id, ordinal")
        )
        revisions = self.env["mc.rov.revision"].browse((attempts.rnd_id | attempts.trn_id).ids)
        revisions.check_access("read")
        revisions.lot_id.check_access("read")
        revisions.product_id.check_access("read")
        for attempt in attempts:
            for source, kind in ((attempt.rnd_id, "rendimiento"), (attempt.trn_id, "terreno")):
                if (
                    source.tipo != kind
                    or source.lot_id != attempt.episode_id.lot_id
                    or source.repair_id
                ):
                    raise AccessError(
                        _("La prueba histórica no corresponde a la unidad fabricada.")
                    )
        return attempts

    def _normalized_attempt(self, attempt):
        # Only sealed outcome fields participate. Current answers and reminder
        # policies cannot retroactively change the first formal presentation.
        row = {"ordinal": attempt.ordinal, "validity": "valid"}
        if attempt.state == "failed" or attempt.first_pass_snapshot == "failed":
            return {**row, "verdict": "failed", "required_failure": True}
        if attempt.state == "pending":
            return {**row, "verdict": "pending"}
        if attempt.state == "confirmed" and attempt.first_pass_snapshot == "passed":
            return {
                **row,
                "verdict": "passed",
                "required_passed": True,
                "correction_required": False,
                "retest_required": False,
            }
        return {**row, "verdict": None}

    @api.model
    def get_summary(self, production_ids):
        companies = self._check_caller()
        productions = self._selected_productions(production_ids, companies)
        units = self._produced_units(productions)
        attempts = self._authorized_attempts(units, companies)
        grouped = {key: [] for key in units}
        for attempt in attempts:
            grouped[(attempt.company_id.id, attempt.episode_id.lot_id.id)].append(
                self._normalized_attempt(attempt)
            )
        episodes = []
        for key, unit in sorted(units.items()):
            rows = grouped[key]
            episodes.append(
                {
                    "company_id": unit["company_id"],
                    "lot_id": unit["lot_id"],
                    "production_group_id": unit["production_group_id"],
                    "status": first_pass_status(rows),
                    "first_ordinal": min((row["ordinal"] for row in rows), default=False),
                }
            )
        counts = {
            key: sum(row["status"] == key for row in episodes)
            for key in ("passed", "failed", "pending", "unknown")
        }
        evaluated = counts["passed"] + counts["failed"]
        return {
            "basis": "selected_productions_new_units_current",
            "population": len(episodes),
            **counts,
            "evaluated": evaluated,
            "value": 100 * counts["passed"] / evaluated if evaluated else None,
            "coverage_percent": 100 * evaluated / len(episodes) if episodes else None,
            "episodes": episodes,
        }
