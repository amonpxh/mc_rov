from odoo import fields, models


class AcceptanceActivityCycle(models.Model):
    """Identidad privada del equipo fabricado que espera su evidencia de aceptación."""

    _name = "mc.rov.acceptance.activity.cycle"
    _description = "Ciclo de aceptación de equipo"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    production_id = fields.Many2one(
        "mrp.production", required=True, index=True, ondelete="restrict", check_company=True
    )
    lot_id = fields.Many2one(
        "stock.lot", required=True, index=True, ondelete="restrict", check_company=True
    )
    started_at = fields.Datetime(required=True)
    state = fields.Selection(
        [("open", "Pendiente"), ("done", "Aceptado"), ("cancel", "Cancelado")],
        required=True,
        default="open",
    )

    _unit_unique = models.Constraint(
        "UNIQUE(production_id, lot_id)",
        "Este equipo ya tiene un ciclo de aceptación para esta fabricación.",
    )
    # No ACL pública: el equipo autoriza los servicios que consultan este historial.
