"""Choose explicit draft protocols for a genuinely manufactured serial."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class NewAcceptanceWizard(models.TransientModel):
    """The dialog delegates capture to the authorized joint-start service, without sudo."""

    _name = "mc.rov.new.acceptance.wizard"
    _description = "Iniciar aceptación de equipo nuevo"

    production_id = fields.Many2one(
        "mrp.production", string="Fabricación", required=True, readonly=True
    )
    lot_id = fields.Many2one("stock.lot", string="Equipo / serie", required=True)
    rnd_id = fields.Many2one("mc.rov.revision", string="Prueba de rendimiento", required=True)
    trn_id = fields.Many2one("mc.rov.revision", string="Prueba en terreno", required=True)
    eligible_lot_ids = fields.Many2many("stock.lot", compute="_compute_eligible_lots")

    @api.depends("production_id")
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_eligible_lots(self):
        # Domains guide selection; the service revalidates every source on submission.
        for wizard in self:
            wizard.eligible_lot_ids = (
                wizard.production_id._new_acceptance_output_lots()
                if wizard.production_id
                else False
            )

    @api.onchange("lot_id")
    def _onchange_lot_id(self):
        # Never carry protocols from the previously selected serial into another unit.
        self.rnd_id = self.env["mc.rov.revision"]
        self.trn_id = self.env["mc.rov.revision"]

    def action_start(self):
        self.ensure_one()
        self.check_access("write")
        self.env["mc.rov.new.acceptance"].start_attempt(
            self.production_id.id, self.lot_id.id, self.rnd_id.id, self.trn_id.id
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Prueba de rendimiento"),
            "res_model": "mc.rov.revision",
            "res_id": self.rnd_id.id,
            "view_mode": "form",
            "target": "current",
        }


class NewAcceptanceManufacturingEntry(models.Model):
    """Expose the explicit acceptance dialog only from an authorized finished production."""

    _inherit = "mrp.production"

    def _new_acceptance_output_lots(self):
        self.ensure_one()
        if self.env.user.share or self.env.user._is_public():
            raise AccessError(_("La aceptación requiere una cuenta interna."))
        if not isinstance(self.id, int) or isinstance(self.id, bool) or self.id <= 0:
            raise UserError(_("Guarde la fabricación antes de iniciar aceptación."))
        self.check_access("read")
        self.check_access("write")
        if self.company_id.id not in self.env.companies.ids:
            raise AccessError(_("La fabricación no pertenece a una empresa activa autorizada."))
        self.product_id.check_access("read")
        if self.state != "done":
            raise UserError(_("La aceptación se inicia desde una fabricación terminada."))
        lots = self.env["mc.rov.acceptance.activity.automation"]._produced_lots(self)
        if not lots:
            raise UserError(_("La fabricación no tiene series realmente producidas para aceptar."))
        lots.check_access("read")
        lots.check_access("write")
        return lots

    def action_open_new_acceptance(self):
        self.ensure_one()
        lots = self._new_acceptance_output_lots()
        return {
            "type": "ir.actions.act_window",
            "name": _("Iniciar aceptación de equipo nuevo"),
            "res_model": "mc.rov.new.acceptance.wizard",
            "view_mode": "form",
            "views": [(self.env.ref("mc_rov.view_mc_rov_new_acceptance_wizard_form").id, "form")],
            "target": "new",
            "context": {
                "default_production_id": self.id,
                "default_lot_id": lots.id if len(lots) == 1 else False,
            },
        }
