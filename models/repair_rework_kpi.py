"""Consulta Q3 sobre cierres F4 y líneas nativas autorizadas."""

from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError

from .mc_rov_componente import ORIGENES
from .production_kpi_metrics import local_day, period_bounds
from .repair_rework_metrics import summarize_rework


class RepairReworkKPI(models.AbstractModel):
    """Separa los casos acreditados de visitas y horas sin cobertura."""

    _name = "mc.rov.repair.rework.kpi"
    _description = "Retrabajo y causas en Reparación"

    def _closed_repairs(self, companies, start, end):
        events = (
            self.env["mc.rov.production.event"]
            .sudo()
            .search(
                [
                    ("company_id", "in", companies),
                    ("kind", "=", "repair_done"),
                    ("at", "!=", False),
                ]
            )
        )
        events = events.filtered(
            lambda row: (not start or local_day(row.at) >= start)
            and (not end or local_day(row.at) <= end)
        )
        visible = (
            self.env["repair.order"]
            .with_context(active_test=False)
            .search([("id", "in", events.repair_id.ids), ("company_id", "in", companies)])
        )
        visible_ids = set(visible.ids)
        return {
            event.repair_id.id
            for event in events
            if event.repair_id.id in visible_ids
            and event.lot_id.with_env(self.env).has_access("read")
            and event.product_id.with_env(self.env).has_access("read")
            and event.move_id.with_env(self.env).has_access("read")
            and event.repair_id.lot_id == event.lot_id
        }

    @api.model
    def get_summary(self, date_from=False, date_to=False):
        companies = self.env["mc.rov.kpi.dashboard"]._check_caller()
        if not all(
            self.env[model].has_access("read")
            for model in ("repair.order", "mc.rov.linea.falla", "stock.lot", "stock.move")
        ):
            raise AccessError(_("Se requiere lectura de Reparación e Inventario."))
        try:
            start, end = period_bounds(date_from, date_to)
        except (TypeError, ValueError) as error:
            raise ValidationError(_("Seleccione un período válido.")) from error
        visits = {repair_id: [] for repair_id in self._closed_repairs(companies, start, end)}
        lines = (
            self.env["mc.rov.linea.falla"]
            .sudo()
            .search([("repair_id", "in", list(visits))])
            .with_env(self.env)
        )
        lines.check_access("read")
        latest = self.env["mc.rov.repair.rework.event"]._latest(lines)
        for line in lines:
            event = latest.get(line.id)
            state = event.state if event and event.state != "proposal" else "pending"
            visits[line.repair_id.id].append((state, line.horas, line.origen))
        summary = summarize_rework(visits)
        labels = dict(ORIGENES, unknown=_("Sin causa registrada"))
        summary["causes"] = [
            {"key": key, "label": labels[key], **values}
            for key, values in sorted(
                summary["causes"].items(), key=lambda item: (-item[1]["hours"], item[0])
            )
        ]
        return summary
