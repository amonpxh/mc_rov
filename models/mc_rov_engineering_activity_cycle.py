from odoo import fields, models


class EngineeringActivityCycle(models.Model):
    """Conserva el aniversario total del ECO aunque cambie de etapa o se retire su tarea."""

    _name = "mc.rov.engineering.activity.cycle"
    _description = "Ciclo técnico de ingeniería"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    eco_id = fields.Many2one(
        "mrp.eco", required=True, index=True, ondelete="restrict", check_company=True
    )
    policy_id = fields.Many2one(
        "mc.rov.engineering.activity.policy", ondelete="restrict", check_company=True
    )
    eco_created_at = fields.Datetime(required=True)
    started_at = fields.Datetime(required=True)
    original_deadline = fields.Date(required=True)
    current_deadline = fields.Date(required=True)
    deadline_tz = fields.Char(required=True)
    lead_years = fields.Integer(required=True, default=1)
    observed_stage = fields.Selection(
        [("none", "Sin etapa seguida"), ("prepare", "Preparación"), ("apply", "Aplicación")],
        required=True,
        default="none",
    )
    event_sequence = fields.Integer(required=True, default=0)
    state = fields.Selection(
        [("open", "Pendiente"), ("done", "Aplicado"), ("cancel", "Archivado")],
        required=True,
        default="open",
    )

    _eco_unique = models.Constraint(
        "UNIQUE(eco_id)", "Este cambio ya tiene un ciclo de seguimiento."
    )
    _positive_years = models.Constraint(
        "CHECK(lead_years > 0)", "El plazo anual debe ser positivo."
    )
    _nonnegative_event = models.Constraint(
        "CHECK(event_sequence >= 0)", "El contador de eventos no puede ser negativo."
    )

    # Sin ACL pública: solo servicios autorizados sobre el ECO acceden al historial.
