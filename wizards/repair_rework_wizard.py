"""Recoge una clasificación o confirma la propuesta vista por Supervisor."""

from odoo import fields, models

from ..models.repair_rework import KINDS


class RepairReworkWizard(models.TransientModel):
    """Delega las comprobaciones de rol, orden y evidencia al historial."""

    _name = "mc.rov.repair.rework.wizard"
    _description = "Clasificar el trabajo de una reparación"

    line_id = fields.Many2one("mc.rov.linea.falla", required=True, readonly=True, string="Trabajo")
    repair_id = fields.Many2one(related="line_id.repair_id", compute_sudo=False)
    lot_id = fields.Many2one(related="repair_id.lot_id", compute_sudo=False)
    review = fields.Boolean(readonly=True)
    proposal_id = fields.Integer(readonly=True)
    kind = fields.Selection(KINDS, required=True, string="Clasificación")
    previous_line_id = fields.Many2one("mc.rov.linea.falla", string="Trabajo anterior")
    finding_id = fields.Many2one("mc.rov.revision.hallazgo", readonly=True, string="Hallazgo")
    alert_id = fields.Many2one("quality.alert", readonly=True, string="Alerta de calidad")
    reason = fields.Text(string="Fundamento")

    def action_record(self):
        self.ensure_one()
        self.check_access("write")
        self.env["mc.rov.repair.rework.event"]._record_classification(
            self.line_id, self.kind, self.previous_line_id, self.reason
        )
        self.line_id.invalidate_recordset(["mc_rework_state"])
        return {"type": "ir.actions.act_window_close"}

    def action_confirm(self):
        self.ensure_one()
        self.check_access("write")
        self.env["mc.rov.repair.rework.event"]._confirm_classification(
            self.line_id, self.proposal_id
        )
        self.line_id.invalidate_recordset(["mc_rework_state"])
        return {"type": "ir.actions.act_window_close"}
