from odoo import fields, models


class AcceptanceActivityRun(models.Model):
    """Una etapa y sus decisiones sobreviven a retirar la actividad nativa."""

    _name = "mc.rov.acceptance.activity.run"
    _description = "Seguimiento de etapa de aceptación"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    cycle_id = fields.Many2one(
        "mc.rov.acceptance.activity.cycle",
        required=True,
        index=True,
        ondelete="restrict",
        check_company=True,
    )
    stage = fields.Selection(
        [
            ("performance", "Rendimiento"),
            ("field", "Terreno"),
            ("rejection_performance", "Resolver rechazo de rendimiento"),
            ("rejection_field", "Resolver rechazo de terreno"),
            ("fen", "Emisión de ficha"),
        ],
        required=True,
    )
    occurrence = fields.Integer(required=True, default=1)
    activity_id = fields.Many2one("mail.activity", ondelete="set null", index=True)
    started_at = fields.Datetime(required=True)
    original_deadline = fields.Date(required=True)
    current_deadline = fields.Date(required=True)
    calendar_id = fields.Many2one("resource.calendar", required=True, ondelete="restrict")
    calendar_tz = fields.Char(required=True)
    outcome = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("business_done", "Etapa completada"),
            ("manual_done", "Marcada como hecha"),
            ("cancelled", "Cancelada"),
        ],
        required=True,
        default="pending",
    )
    finished_at = fields.Datetime()
    finished_by_id = fields.Many2one("res.users", ondelete="set null")
    finish_reason = fields.Text()

    _stage_unique = models.Constraint(
        "UNIQUE(cycle_id, stage, occurrence)", "La etapa ya tiene seguimiento para este evento."
    )
    _positive_occurrence = models.Constraint(
        "CHECK(occurrence > 0)", "La generación de la etapa debe ser positiva."
    )
