from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL, float_compare


class AcceptanceActivityAutomation(models.AbstractModel):
    """Inicia aceptación por serie realmente producida, sin generar pruebas ficticias."""

    _name = "mc.rov.acceptance.activity.automation"
    _description = "Automatización de aceptación"

    def _capture(self, productions):
        ids = sorted(
            {record.id for record in productions if isinstance(record.id, int) and record.id > 0}
        )
        if not ids:
            return {}
        self.env.cr.execute(
            SQL("SELECT id FROM mrp_production WHERE id IN %s ORDER BY id FOR UPDATE", tuple(ids))
        )
        records = self.env["mrp.production"].sudo().browse(ids).exists()
        records.invalidate_recordset(["state"])
        return {record.id: record.state for record in records}

    def _produced_lots(self, production):
        production.ensure_one()
        production = production.with_user(self.env.uid)
        production.check_access("read")
        lots = self.env["stock.lot"].with_user(self.env.uid)
        if production.state != "done" or production.product_id.tracking != "serial":
            return lots.browse()
        moves = production.move_finished_ids.filtered(
            lambda move: move.state == "done"
            and move.product_id == production.product_id
            and not move.byproduct_id
        )
        lines = moves.move_line_ids.filtered(
            lambda line: line.lot_id
            and line.lot_id.product_id == production.product_id
            and (not line.lot_id.company_id or line.lot_id.company_id == production.company_id)
            and float_compare(line.quantity, 0, precision_rounding=line.product_uom_id.rounding)
            > 0
        )
        result = lots.browse(sorted(set(lines.lot_id.ids)))
        result.check_access("read")
        return result

    def _after_completion(self, previous):
        instant = fields.Datetime.now()
        productions = self.env["mrp.production"].browse(sorted(previous)).exists()
        productions.invalidate_recordset(["state"])
        for production in productions:
            if previous[production.id] != "done" and production.state == "done":
                for lot in self._produced_lots(production):
                    self._start(production, lot, instant)

    def _start(self, production, lot, started_at):  # pylint: disable=too-many-return-statements
        production.ensure_one()
        lot.ensure_one()
        production = production.with_user(self.env.uid)
        lot = lot.with_user(self.env.uid)
        production.check_access("write")
        lot.check_access("write")
        self._capture(production)
        self.env.cr.execute(SQL("SELECT id FROM stock_lot WHERE id = %s FOR UPDATE", lot.id))
        cycles = self.env["mc.rov.acceptance.activity.cycle"].sudo()
        if production.state != "done" or lot not in self._produced_lots(production):
            return cycles.browse()
        root = self.env["stock.lot"]._get_rov_root_category()
        if not root or not self.env["product.category"].search_count(
            [("id", "=", production.product_id.categ_id.id), ("id", "child_of", root.id)]
        ):
            return cycles.browse()
        existing = cycles.search(
            [("production_id", "=", production.id), ("lot_id", "=", lot.id)], limit=1
        )
        if existing:
            return existing
        policy = (
            self.env["mc.rov.acceptance.activity.policy"]
            .sudo()
            .search([("company_id", "=", production.company_id.id)], limit=1)
        )
        if not self.env["mc.rov.automation.control"]._creation_enabled(production.company_id) or (
            policy and not policy.enabled
        ):
            return cycles.browse()
        reason = (
            policy._configuration_error(lot)
            if policy
            else _("Configure cuenta y calendario en Seguimiento de aceptación.")
        )
        if reason:
            production.message_post(body=_("Seguimiento de aceptación no generado: %s", reason))
            return cycles.browse()
        with self.env.cr.savepoint():
            cycle = cycles.create(
                {
                    "company_id": production.company_id.id,
                    "production_id": production.id,
                    "lot_id": lot.id,
                    "started_at": started_at,
                }
            )
            self._start_stage(cycle, "performance", started_at)
            self._start_stage(cycle, "field", started_at)
        return cycle

    def _start_stage(self, cycle, stage, started_at, occurrence=1):
        cycle.ensure_one()
        stages = {
            "performance": ("performance_days", _("Realizar prueba de rendimiento")),
            "field": ("field_days", _("Realizar prueba en terreno")),
            "rejection_performance": ("rejection_days", _("Resolver rechazo de rendimiento")),
            "rejection_field": ("rejection_days", _("Resolver rechazo de terreno")),
            "fen": ("fen_days", _("Preparar y emitir ficha de equipo nuevo")),
        }
        if stage not in stages:
            raise ValidationError(_("Etapa de aceptación inválida."))
        lot = cycle.lot_id.with_user(self.env.uid)
        lot.check_access("write")
        # La MO autorizó el inicio; las etapas posteriores pertenecen al equipo probado.
        self._capture(cycle.production_id)
        runs = self.env["mc.rov.acceptance.activity.run"].sudo()
        existing = runs.search(
            [("cycle_id", "=", cycle.id), ("stage", "=", stage), ("occurrence", "=", occurrence)],
            limit=1,
        )
        if existing:
            return existing
        policy = (
            self.env["mc.rov.acceptance.activity.policy"]
            .sudo()
            .search([("company_id", "=", cycle.company_id.id)], limit=1)
        )
        if (
            not policy
            or not policy.enabled
            or not self.env["mc.rov.automation.control"]._creation_enabled(cycle.company_id)
        ):
            return runs.browse()
        reason = policy._configuration_error(lot)
        if reason:
            lot.message_post(body=_("Seguimiento de aceptación no generado: %s", reason))
            return runs.browse()
        days_field, summary = stages[stage]
        deadline = policy._deadline(started_at, policy[days_field])
        activity = (
            self.env["mail.activity"]
            .sudo()
            .with_company(cycle.company_id)
            .create(
                {
                    "res_model_id": self.env["ir.model"]._get_id("stock.lot"),
                    "res_id": lot.id,
                    "activity_type_id": self.env.ref(
                        "mc_rov.activity_type_acceptance_" + stage
                    ).id,
                    "summary": summary,
                    "note": Markup('<p><a href="/odoo/stock.lot/%s">%s</a></p>')
                    % (lot.id, lot.display_name),
                    "user_id": policy.user_id.id,
                    "mc_employee_id": policy.employee_id.id or False,
                    "date_deadline": deadline,
                }
            )
        )
        return runs.create(
            {
                "company_id": cycle.company_id.id,
                "cycle_id": cycle.id,
                "stage": stage,
                "occurrence": occurrence,
                "activity_id": activity.id,
                "started_at": started_at,
                "original_deadline": deadline,
                "current_deadline": deadline,
                "calendar_id": policy.calendar_id.id,
                "calendar_tz": policy.calendar_id.tz,
            }
        )


class AcceptanceProductionAutomation(models.Model):
    """Observa eventos persistidos conservando asistentes y retornos de MRP."""

    _inherit = "mrp.production"

    def write(self, values):
        service = self.env["mc.rov.acceptance.activity.automation"]
        previous = service._capture(self) if "state" in values else {}
        result = super().write(values)
        if previous:
            service._after_completion(previous)
        return result

    def button_mark_done(self):
        service = self.env["mc.rov.acceptance.activity.automation"]
        previous = service._capture(self)
        result = super().button_mark_done()
        service._after_completion(previous)
        return result

    def _post_inventory(self, *args, **kwargs):
        service = self.env["mc.rov.acceptance.activity.automation"]
        previous = service._capture(self)
        result = super()._post_inventory(*args, **kwargs)
        service._after_completion(previous)
        return result


class AcceptanceStockMoveAutomation(models.Model):
    """El cierre desde movimientos también respeta la transición efectiva de MRP."""

    _inherit = "stock.move"

    def _action_done(self, *args, **kwargs):
        service = self.env["mc.rov.acceptance.activity.automation"]
        previous = service._capture(self.production_id | self.raw_material_production_id)
        result = super()._action_done(*args, **kwargs)
        service._after_completion(previous)
        return result
