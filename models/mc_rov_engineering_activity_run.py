from odoo import fields, models


class EngineeringActivityRun(models.Model):
    """Identifica una tarea propia sin atribuirse las aprobaciones nativas de PLM."""

    _name = "mc.rov.engineering.activity.run"
    _description = "Ejecución técnica de ingeniería"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    cycle_id = fields.Many2one(
        "mc.rov.engineering.activity.cycle", required=True, ondelete="restrict", check_company=True
    )
    eco_id = fields.Many2one(related="cycle_id.eco_id", store=True, index=True)
    event = fields.Integer(required=True)
    stage = fields.Selection([("prepare", "Preparación"), ("apply", "Aplicación")], required=True)
    activity_id = fields.Many2one("mail.activity", ondelete="set null", index=True)
    started_at = fields.Datetime(required=True)
    original_deadline = fields.Date(required=True)
    current_deadline = fields.Date()
    outcome = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("business_done", "Etapa completada"),
            ("manual_done", "Marcada como hecha"),
            ("cancelled", "Cancelada"),
            ("withdrawn", "Retirada al cambiar de etapa"),
        ],
        required=True,
        default="pending",
    )
    finished_at = fields.Datetime()
    finished_by_id = fields.Many2one("res.users", ondelete="set null")
    finish_reason = fields.Text()

    _event_unique = models.Constraint(
        "UNIQUE(cycle_id, event, stage)", "Esta etapa ya tiene seguimiento para este evento."
    )
    _positive_event = models.Constraint("CHECK(event > 0)", "El evento debe ser positivo.")

    # Sin ACL pública; la actividad y el origen son las interfaces del trabajo del equipo.
