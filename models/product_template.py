from odoo import api, fields, models
from odoo.tools import is_html_empty


class ProductTemplate(models.Model):
    """La ficha del modelo muestra lo que se aprendió fabricándolo.

    Es consulta de referencia y no el lugar principal: quien arma un ROV no está en la
    ficha del producto, está en la orden de fabricación, y por eso la lista que importa es
    la de `mrp.production`. Ver `docs/designs/fabricacion.md` § 6.1.1.

    Aun así vale tenerla acá, porque es la única pantalla que responde «¿qué sabemos de
    este modelo?» sin partir de una orden.
    """

    _inherit = "product.template"

    mc_alerta_ids = fields.One2many(
        "quality.alert",
        "product_tmpl_id",
        string="Alertas de calidad",
    )
    mc_leccion_count = fields.Integer(
        string="Lecciones",
        compute="_compute_mc_leccion_count",
    )

    @api.depends("mc_alerta_ids.stage_id", "mc_alerta_ids.action_preventive")
    def _compute_mc_leccion_count(self):
        """Cuenta lecciones, no alertas, y la diferencia es la que ordena todo el diseño.

        Una alerta cerrada sin acción preventiva escrita arregló un equipo; una con acción
        preventiva cambió cómo se fabrican todos. Solo la segunda es una lección, así que
        es la única que se cuenta — el mismo criterio con que la orden de fabricación
        elige qué mostrar.
        """
        for plantilla in self:
            plantilla.mc_leccion_count = len(
                plantilla.mc_alerta_ids.filtered(
                    lambda alerta: alerta.stage_id.done
                    and not is_html_empty(alerta.action_preventive)
                )
            )

    def action_mc_ver_alertas(self):
        self.ensure_one()
        accion = self.env["ir.actions.actions"]._for_xml_id(
            "quality_control.quality_alert_action_check"
        )
        accion["domain"] = [("product_tmpl_id", "=", self.id)]
        accion["context"] = {"default_product_tmpl_id": self.id}
        return accion
