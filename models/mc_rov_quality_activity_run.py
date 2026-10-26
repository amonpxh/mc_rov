from odoo import fields, models


class QualityActivityRun(models.Model):
    """Ciclo privado de una alerta, conservado al retirar su pendiente."""

    _name = "mc.rov.quality.activity.run"
    _description = "Seguimiento técnico de Calidad"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    alert_id = fields.Many2one(
        "quality.alert", required=True, index=True, ondelete="restrict", check_company=True
    )
    cycle = fields.Integer(required=True)
    activity_id = fields.Many2one("mail.activity", ondelete="set null", index=True)
    started_at = fields.Datetime(required=True)
    original_deadline = fields.Date(required=True)
    current_deadline = fields.Date(required=True)
    calendar_id = fields.Many2one("resource.calendar", required=True, ondelete="restrict")
    calendar_tz = fields.Char(required=True)
    outcome = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("business_done", "Alerta resuelta"),
            ("manual_done", "Marcada como hecha"),
            ("cancelled", "Cancelada"),
        ],
        default="pending",
        required=True,
    )
    finished_at = fields.Datetime()
    finished_by_id = fields.Many2one("res.users", ondelete="set null")
    finish_reason = fields.Text()

    _cycle_unique = models.Constraint(
        "UNIQUE(alert_id, cycle)", "La alerta ya tiene seguimiento en este ciclo."
    )
    _positive_cycle = models.Constraint("CHECK(cycle > 0)", "El ciclo debe ser positivo.")

    # Sin ACL pública: solo servicios privados con autorización sobre la alerta gestionan historia.
