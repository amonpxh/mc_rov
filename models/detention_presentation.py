"""Acciones de registro e historial de detenciones en la orden autorizada."""

from markupsafe import Markup

from odoo import _, Command, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import format_datetime

from .detention_capture import OPEN
from .detention_history import CAUSE_LABELS


class DetentionOrderPresentation(models.AbstractModel):
    """Muestra la evidencia y abre asistentes sin elevar los permisos del origen."""

    _name = "mc.rov.detention.order.presentation"
    _description = "Presentación de detenciones en órdenes ROV"

    mc_detention_history_html = fields.Html(compute="_compute_detention_history")
    mc_detention_can_start = fields.Boolean(compute="_compute_detention_controls")
    mc_detention_can_finish = fields.Boolean(compute="_compute_detention_controls")

    @api.depends_context("uid", "company")
    def _compute_detention_controls(self):
        service = self.env["mc.rov.detention.service"]
        root = self.env["stock.lot"]._get_rov_root_category()
        for order in self:
            order.mc_detention_can_start = order.mc_detention_can_finish = False
            if not isinstance(order.id, int) or not order.has_access("write"):
                continue
            try:
                source = service._source(order._name, order.id, "write")
                order.mc_detention_can_start = bool(
                    root
                    and source.state in OPEN[source._name]
                    and self.env["product.category"].search_count(
                        [
                            ("id", "=", source.product_id.categ_id.id),
                            ("id", "child_of", root.id),
                        ]
                    )
                )
                order.mc_detention_can_finish = any(
                    not row.ended_at for row in service._rows(source)
                )
            except AccessError:
                continue

    @api.depends_context("uid", "company", "tz", "lang")
    def _compute_detention_history(self):
        service = self.env["mc.rov.detention.service"]
        for order in self:
            if not isinstance(order.id, int):
                order.mc_detention_history_html = False
                continue
            rows = service.get_intervals(order._name, order.id)
            employees = self.env["hr.employee.public"].search(
                [("id", "in", [row["responsible_employee_id"] for row in rows])]
            )
            labels = {employee.id: employee.name for employee in employees}
            items = []
            for row in reversed(rows):
                start = format_datetime(self.env, fields.Datetime.to_datetime(row["started_at"]))
                end = (
                    format_datetime(self.env, fields.Datetime.to_datetime(row["ended_at"]))
                    if row["ended_at"]
                    else _("En curso")
                )
                outcome = {
                    "resumed": _("Trabajo reanudado"),
                    "source_closed": _("Fin por cierre de orden"),
                }.get(row["end_kind"], "")
                items.append(
                    Markup(
                        "<li><strong>{}</strong> · {} → {} {}<div>{}</div><div>{}</div><div>{}</div></li>"
                    ).format(
                        _(CAUSE_LABELS[row["cause"]]),
                        start,
                        end,
                        outcome,
                        labels.get(row["responsible_employee_id"], ""),
                        row["explanation"],
                        row["closing_explanation"],
                    )
                )
            order.mc_detention_history_html = (
                Markup("<ul>{}</ul>").format(Markup("").join(items))
                if items
                else Markup("<p>{}</p>").format(_("Sin detenciones registradas."))
            )

    def _open_detention(self, decision):
        self.ensure_one()
        service = self.env["mc.rov.detention.service"]
        source = service._source(self._name, self.id, "write")
        context = {
            "default_repair_id": source.id if source._name == "repair.order" else False,
            "default_production_id": (source.id if source._name == "mrp.production" else False),
            "default_decision": decision,
        }
        action = {
            "type": "ir.actions.act_window",
            "res_model": "mc.rov.detention.wizard",
            "name": (
                _("Registrar detención") if decision == "start" else _("Registrar reanudación")
            ),
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": context,
        }
        if decision == "start":
            if source.state not in OPEN[source._name]:
                raise UserError(_("La orden debe estar confirmada y abierta."))
        else:
            rows = service._rows(source).filtered(lambda row: not row.ended_at)
            if not rows:
                raise UserError(_("La orden no tiene detenciones abiertas."))
            wizard = (
                self.env["mc.rov.detention.wizard"]
                .with_context(**context)
                .create(
                    {
                        "option_ids": [
                            Command.create(
                                {
                                    "name": _(CAUSE_LABELS[row.cause]),
                                    "interval_key": str(row.id),
                                }
                            )
                            for row in rows
                        ],
                    }
                )
            )
            action["res_id"] = wizard.id
        return action

    def action_open_detention_start(self):
        return self._open_detention("start")

    def action_open_detention_finish(self):
        return self._open_detention("finish")


class RepairDetentionPresentation(models.Model):
    """Integra la pestaña F2 en Reparación."""

    _name = "repair.order"
    _inherit = ["repair.order", "mc.rov.detention.order.presentation"]


class ProductionDetentionPresentation(models.Model):
    """Integra la pestaña F2 en Fabricación."""

    _name = "mrp.production"
    _inherit = ["mrp.production", "mc.rov.detention.order.presentation"]
