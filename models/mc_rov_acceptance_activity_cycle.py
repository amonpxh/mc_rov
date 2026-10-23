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
    rnd_id = fields.Many2one("mc.rov.revision", ondelete="restrict")
    trn_id = fields.Many2one("mc.rov.revision", ondelete="restrict")
    # Registrar también eventos pausados impide reconstruirlos al reactivar la política.
    performance_status = fields.Char(default="none", required=True)
    field_status = fields.Char(default="none", required=True)
    rejection_performance_event = fields.Integer(default=0)
    rejection_field_event = fields.Integer(default=0)
    fen_signature = fields.Char()
    fen_event = fields.Integer(default=0)
    fen_id = fields.Many2one("mc.rov.ficha.equipo.nuevo", ondelete="restrict")
    closed_at = fields.Datetime()
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
