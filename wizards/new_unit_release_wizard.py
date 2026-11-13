"""Revisión explícita de liberación; no emite documentos ni valida stock."""

from odoo import api, fields, models


class NewUnitReleaseWizard(models.TransientModel):
    """Conserva la decisión de Supervisor y sus evidencias en el hito privado."""

    _name = "mc.rov.unit.release.wizard"
    _description = "Validar liberación de unidad ROV"

    production_id = fields.Many2one(
        "mrp.production", string="Fabricación", required=True, readonly=True
    )
    lot_id = fields.Many2one("stock.lot", string="Unidad / serie", required=True)
    fen_id = fields.Many2one(
        "mc.rov.ficha.equipo.nuevo", string="Ficha de Equipo Nuevo", required=True
    )
    no_blocking_nc = fields.Boolean(
        string="He revisado las no conformidades y no hay bloqueantes pendientes"
    )
    eligible_lot_ids = fields.Many2many("stock.lot", compute="_compute_eligible_lots")

    @api.depends("production_id")
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_eligible_lots(self):
        for wizard in self:
            wizard.eligible_lot_ids = (
                self.env["mc.rov.acceptance.activity.automation"]._produced_lots(
                    wizard.production_id
                )
                if wizard.production_id
                else False
            )

    def action_release(self):
        self.ensure_one()
        self.check_access("write")
        self.production_id._release_rov_unit(self.lot_id, self.fen_id, self.no_blocking_nc)
        return {"type": "ir.actions.act_window_close"}
