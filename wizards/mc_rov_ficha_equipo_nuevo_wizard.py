"""Selección explícita de las pruebas que respaldan la ficha de equipo nuevo."""

from odoo import fields, models


class McRovFichaEquipoNuevoWizard(models.TransientModel):
    """Permite revisar RND y TRN sugeridas antes de crear el documento del equipo."""

    _name = "mc.rov.ficha.equipo.nuevo.wizard"
    _description = "Preparar ficha de equipo nuevo"

    lot_id = fields.Many2one("stock.lot", string="Equipo", required=True)
    rnd_id = fields.Many2one("mc.rov.revision", string="Validación de rendimiento")
    trn_id = fields.Many2one("mc.rov.revision", string="Validación en terreno")
    fecha_emision = fields.Date(default=fields.Date.context_today, required=True)
    responsable_id = fields.Many2one(
        "hr.employee", string="Responsable", default=lambda self: self.env.user.employee_id
    )
    observacion = fields.Text(string="Observaciones y aceptación")

    def _crear_ficha(self):
        self.ensure_one()
        return self.env["mc.rov.ficha.equipo.nuevo"].create(
            {
                "lot_id": self.lot_id.id,
                "rnd_id": self.rnd_id.id,
                "trn_id": self.trn_id.id,
                "fecha_emision": self.fecha_emision,
                "responsable_id": self.responsable_id.id,
                "observacion": self.observacion,
            }
        )

    def action_guardar_borrador(self):
        """Un equipo pendiente de TRN conserva una vista previa, sin declarar aceptación."""
        ficha = self._crear_ficha()
        return {
            "type": "ir.actions.act_window",
            "name": "Ficha de equipo nuevo",
            "res_model": ficha._name,
            "res_id": ficha.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_emitir(self):
        """Emite la selección visible en el asistente y entrega el binario guardado."""
        return self._crear_ficha().action_emitir()

