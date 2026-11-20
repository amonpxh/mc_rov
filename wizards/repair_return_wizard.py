"""Diálogo para vincular la visita o emitir su dictamen técnico."""

from odoo import fields, models

from ..models.repair_return import VERDICTS


class RepairReturnWizard(models.TransientModel):
    """Recoge valores de Taller o Supervisor y delega su autorización."""

    _name = "mc.rov.repair.return.wizard"
    _description = "Registrar un retorno de reparación"

    return_id = fields.Many2one(
        "repair.order", required=True, readonly=True, string="Visita de retorno"
    )
    lot_id = fields.Many2one(related="return_id.lot_id", compute_sudo=False)
    company_id = fields.Many2one(related="return_id.company_id", compute_sudo=False)
    original_id = fields.Many2one("repair.order", string="Reparación anterior")
    decide = fields.Boolean(readonly=True)
    relation = fields.Selection(VERDICTS, string="Dictamen")
    reason = fields.Text(string="Fundamento")

    def action_link(self):
        self.ensure_one()
        self.check_access("write")
        self.env["mc.rov.repair.return"]._link(self.return_id, self.original_id)
        self.return_id.invalidate_recordset(
            ["mc_return_relation", "mc_return_original_id", "mc_return_reason"]
        )
        return {"type": "ir.actions.act_window_close"}

    def action_decide(self):
        self.ensure_one()
        self.check_access("write")
        self.env["mc.rov.repair.return"]._decide(self.return_id, self.relation, self.reason)
        self.return_id.invalidate_recordset(
            ["mc_return_relation", "mc_return_original_id", "mc_return_reason"]
        )
        return {"type": "ir.actions.act_window_close"}
