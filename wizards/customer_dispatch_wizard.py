"""Captura el día o instante que respalda una constancia de salida."""

from odoo import api, fields, models

from ..models.customer_dispatch import DISPATCH_KINDS, DISPATCH_MODES


class CustomerDispatchWizard(models.TransientModel):
    """Confirma, corrige o invalida una constancia sin editar la transferencia."""

    _name = "mc.rov.customer.dispatch.wizard"
    _description = "Registrar constancia de salida al cliente"

    picking_id = fields.Many2one(
        "stock.picking", string="Transferencia", required=True, readonly=True
    )
    # El id vigente al abrir el formulario evita aceptar cambios sobre un historial obsoleto.
    expected_event_id = fields.Integer(readonly=True)
    kind = fields.Selection(DISPATCH_KINDS, string="Acción", required=True, readonly=True)
    mode = fields.Selection(DISPATCH_MODES, string="Modalidad")
    precision = fields.Selection(
        [("date", "Solo día"), ("datetime", "Día y hora")], string="Precisión", default="date"
    )
    effective_date = fields.Date(string="Día de salida")
    effective_at = fields.Datetime(string="Fecha y hora de salida")
    attachment_id = fields.Many2one("ir.attachment", string="Constancia")
    repair_candidate_ids = fields.Many2many("repair.order", compute="_compute_repair_candidates")
    repair_ids = fields.Many2many(
        "repair.order",
        relation="mc_rov_customer_dispatch_wizard_repair_rel",
        string="Visitas de reparación",
    )
    reason = fields.Text(string="Motivo")

    @api.depends("picking_id", "kind")
    @api.depends_context("uid", "company")
    def _compute_repair_candidates(self):
        repairs = self.env["repair.order"]
        for wizard in self:
            picking = wizard.picking_id
            if (
                wizard.kind != "invalidated"
                and picking
                and picking.has_access("read")
                and picking.company_id in self.env.companies
                and repairs.has_access("read")
            ):
                wizard.repair_candidate_ids = repairs.search(picking._dispatch_repair_domain())
            else:
                wizard.repair_candidate_ids = repairs

    @api.constrains("picking_id", "attachment_id", "repair_ids")
    def _check_document_references(self):
        # Las referencias se validan con el acceso real del usuario que las registra.
        for wizard in self.with_user(self.env.uid):
            wizard.picking_id._check_dispatch_capture()
            wizard.attachment_id.check_access("read")
            wizard.repair_ids.check_access("read")

    def action_apply(self):
        self.ensure_one()
        self.check_access("write")
        self.env["mc.rov.customer.dispatch"]._append_from_wizard(self)
        return {"type": "ir.actions.act_window_close"}
