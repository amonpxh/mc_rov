from odoo import api, fields, models


class MrpEco(models.Model):
    """El otro extremo del puente entre la lección y el cambio de ingeniería.

    El diseño lo dice así: *el historial de maduración de un diseño es la cadena de
    alertas y ECOs de ese modelo, en orden — qué encontramos → qué cambiamos → qué
    encontramos después*. Ya estaba casi todo modelado y faltaba el campo que los une.
    Ver `docs/designs/fabricacion.md` § 6.4.
    """

    _inherit = "mrp.eco"

    mc_alerta_ids = fields.One2many(
        "quality.alert",
        "mc_eco_id",
        string="Lecciones que lo originaron",
        help="Las alertas de calidad que llevaron a hacer este cambio.",
    )
    mc_alerta_count = fields.Integer(compute="_compute_mc_alerta_count")

    @api.depends("mc_alerta_ids")
    def _compute_mc_alerta_count(self):
        for eco in self:
            eco.mc_alerta_count = len(eco.mc_alerta_ids)

    def action_mc_ver_alertas(self):
        self.ensure_one()
        # La acción de Calidad y no una propia: así la alerta se abre con las vistas y los
        # filtros que su módulo ya define, en vez de con una copia que se queda atrás.
        accion = self.env["ir.actions.actions"]._for_xml_id(
            "quality_control.quality_alert_action_check"
        )
        accion["domain"] = [("mc_eco_id", "=", self.id)]
        accion["context"] = {"default_mc_eco_id": self.id}
        return accion
