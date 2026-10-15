from odoo import api, fields, models


class AutomationControl(models.Model):
    """Pausa por empresa de pendientes nuevos, independiente de su cierre real."""

    _name = "mc.rov.automation.control"
    _description = "Control de seguimiento automático"
    _inherit = ["mail.thread"]
    _rec_name = "company_id"
    _check_company_auto = True

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    enabled = fields.Boolean(
        string="Crear actividades automáticas",
        default=True,
        tracking=True,
        help="Permite nuevos pendientes de nuestros procesos. No pausa Odoo ni sus reglas nativas.",
    )

    _company_unique = models.Constraint(
        "UNIQUE(company_id)", "Solo puede existir un control general por empresa."
    )

    @api.model
    def _creation_enabled(self, company):
        """Los eventos autorizados consultan el control sin dar acceso a su configuración."""
        company.ensure_one()
        control = self.sudo().search([("company_id", "=", company.id)], limit=1)
        # Sin fila no hay pausa explícita: instalar no desactiva un proceso configurado.
        return not control or control.enabled
