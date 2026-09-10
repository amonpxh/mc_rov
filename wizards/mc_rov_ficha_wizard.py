from odoo import fields, models


class McRovFichaWizard(models.TransientModel):
    """Opciones de la copia entregable sin modificar los resultados de la revisión."""

    _name = "mc.rov.ficha.wizard"
    _description = "Imprimir ficha ROV"

    revision_id = fields.Many2one("mc.rov.revision", required=True, ondelete="cascade")
    tipo = fields.Selection(related="revision_id.tipo")
    mostrar_firmas = fields.Boolean(string="Espacios para firmas", default=True)
    mostrar_sellos = fields.Boolean(string="Sellos al recibir", default=True)
    mostrar_hallazgos = fields.Boolean(string="Hallazgos", default=True)
    mostrar_diferencias = fields.Boolean(string="Diferencias con la ficha", default=True)

    def action_imprimir(self):
        """Solo cambia la presentación; no confirma ni modifica la prueba."""
        self.ensure_one()
        self.revision_id.check_access("read")
        # Mantener docids en la URL del reporte: las opciones viajan en el contexto,
        # no como `data`, que activa otra ruta del cliente de reportes de Odoo.
        reporte = self.env.ref("mc_rov.action_report_ficha").with_context(
            rov_options={
                "firmas": self.mostrar_firmas,
                "sellos": self.mostrar_sellos,
                "hallazgos": self.mostrar_hallazgos,
                "diferencias": self.mostrar_diferencias,
            }
        )
        return reporte.report_action(self.revision_id)
