"""Confirma la llegada al taller con una recepción válida de la misma serie."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..models.production_kpi_event import lock_source
from ..models.repair_arrival import _ARRIVAL_CAPTURE


class RepairArrivalWizard(models.TransientModel):
    """Distingue recepción validada al llegar de registro posterior."""

    _name = "mc.rov.repair.arrival.wizard"
    _description = "Acreditar llegada al taller"

    repair_id = fields.Many2one("repair.order", required=True, readonly=True, string="Visita")
    picking_id = fields.Many2one("stock.picking", required=True, string="Recepción validada")
    delayed = fields.Boolean(string="La validación se hizo después de la llegada")
    arrived_at = fields.Datetime(string="Fecha y hora efectivas de llegada")
    reason = fields.Text(string="Motivo")

    @api.constrains("repair_id", "picking_id")
    def _check_sources(self):
        # El ORM eleva las restricciones, pero los documentos se leen como el operador.
        for wizard in self.with_user(self.env.uid):
            wizard.repair_id.check_access("read")
            wizard.picking_id.check_access("read")

    def _check_receipt(self, repair, picking):
        repair.lot_id.check_access("read")
        if not repair.lot_id.es_un_rov or repair.state == "cancel":
            raise UserError(_("Seleccione una visita activa de un ROV."))
        if (
            repair.company_id not in self.env.companies
            or picking.company_id != repair.company_id
            or (repair.picking_id and repair.picking_id != picking)
        ):
            raise UserError(_("La recepción debe corresponder a la visita del ROV."))
        if (
            picking.state != "done"
            or picking.picking_type_code != "incoming"
            or not picking.date_done
            or not repair.partner_id
            or picking.partner_id.commercial_partner_id != repair.partner_id.commercial_partner_id
        ):
            raise UserError(_("Seleccione una recepción validada del cliente de la visita."))
        lines = picking.move_line_ids
        lines.check_access("read")
        if not lines.filtered(
            lambda line: line.lot_id == repair.lot_id
            and line.product_id == repair.product_id
            and line.quantity > 0
            and line.move_id.state == "done"
            and line.location_id.usage == "customer"
            and line.location_dest_id.usage == "internal"
        ):
            raise UserError(_("La transferencia no acredita el ingreso de la serie de la visita."))

    def action_apply(self):
        self.ensure_one()
        self.check_access("write")
        repair, picking = self.repair_id, self.picking_id
        if not self.env.user.has_group("stock.group_stock_user"):
            raise AccessError(_("Se requiere acceso a Inventario."))
        repair.check_access("read")
        picking.check_access("read")
        lock_source(repair)
        lock_source(picking)
        self._check_receipt(repair, picking)
        arrived = self.arrived_at if self.delayed else picking.date_done
        reason = (self.reason or "").strip() if self.delayed else False
        if self.delayed and (not arrived or arrived >= picking.date_done or not reason):
            raise UserError(_("Registre una llegada anterior a la validación y su motivo."))
        if picking.date_done > fields.Datetime.now():
            raise UserError(_("La fecha de validación aún no ha ocurrido."))
        ledger = (
            self.env["mc.rov.repair.arrival"]
            .sudo()
            .with_context({}, _mc_arrival_capture=_ARRIVAL_CAPTURE)
        )
        existing = ledger.search(
            [
                "|",
                ("repair_id", "=", repair.id),
                "&",
                ("picking_id", "=", picking.id),
                ("lot_id", "=", repair.lot_id.id),
            ],
            limit=1,
        )
        if existing:
            if (
                (existing.repair_id, existing.picking_id, existing.lot_id)
                == (repair, picking, repair.lot_id)
                and existing.validated_at == picking.date_done
                and existing.arrived_at == arrived
                and existing.reason == reason
            ):
                return {"type": "ir.actions.act_window_close"}
            raise UserError(
                _("La visita o la recepción de esta serie ya tiene evidencia registrada.")
            )
        ledger.create(
            {
                "repair_id": repair.id,
                "picking_id": picking.id,
                "lot_id": repair.lot_id.id,
                "company_id": repair.company_id.id,
                "actor_id": self.env.uid,
                "arrived_at": arrived,
                "validated_at": picking.date_done,
                "reason": reason,
            }
        )
        repair.invalidate_recordset(["mc_arrived_at", "mc_arrival_validated_at"])
        return {"type": "ir.actions.act_window_close"}
