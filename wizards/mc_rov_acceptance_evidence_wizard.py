from odoo import _, api, fields, models


class AcceptanceEvidenceWizard(models.TransientModel):
    """Selecciona evidencia de la aceptación abierta del equipo, no la última revisión."""

    _name = "mc.rov.acceptance.evidence.wizard"
    _description = "Pruebas de aceptación"

    lot_id = fields.Many2one("stock.lot", string="Equipo", required=True)
    rnd_id = fields.Many2one("mc.rov.revision", string="Prueba de rendimiento")
    trn_id = fields.Many2one("mc.rov.revision", string="Prueba en terreno")
    reason = fields.Text(string="Motivo del cambio")
    summary = fields.Text(string="Aceptación", readonly=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        summary = {"rnd_id": False, "trn_id": False, "summary": False}
        lot_id = values.get("lot_id") or self.env.context.get("default_lot_id")
        if lot_id:
            summary = self.env["mc.rov.acceptance.activity.automation"]._evidence_summary(
                self.env["stock.lot"].browse(lot_id)
            )
        values.update({key: value for key, value in summary.items() if key in fields_list})
        return values

    @api.onchange("lot_id")
    def _onchange_lot_id(self):
        # Solo cambia caché del asistente; seleccionar o crear pruebas requiere botón explícito.
        self.rnd_id = False
        self.trn_id = False
        self.summary = False
        lot = self.lot_id
        if lot and isinstance(lot.id, int) and lot.id > 0:
            summary = self.env["mc.rov.acceptance.activity.automation"]._evidence_summary(lot)
            self.rnd_id = summary["rnd_id"]
            self.trn_id = summary["trn_id"]
            self.summary = summary["summary"]

    def action_apply(self):
        self.ensure_one()
        self.env["mc.rov.acceptance.activity.automation"]._select_evidence(
            self.lot_id, rnd=self.rnd_id or False, trn=self.trn_id or False, reason=self.reason
        )
        return {"type": "ir.actions.act_window_close"}

    def _new_test_action(self, kind):
        self.ensure_one()
        revision = self.env["mc.rov.acceptance.activity.automation"]._create_evidence(
            self.lot_id, kind, reason=self.reason
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Prueba de aceptación"),
            "res_model": "mc.rov.revision",
            "res_id": revision.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_new_performance(self):
        return self._new_test_action("rendimiento")

    def action_new_field(self):
        return self._new_test_action("terreno")
