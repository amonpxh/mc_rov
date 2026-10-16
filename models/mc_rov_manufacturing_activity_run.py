from odoo import fields, models


class ManufacturingActivityRun(models.Model):
    """Identidad privada de una fabricación, conservada al retirar su pendiente."""

    _name = "mc.rov.manufacturing.activity.run"
    _description = "Seguimiento técnico de fabricación"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    production_id = fields.Many2one(
        "mrp.production", required=True, index=True, ondelete="restrict", check_company=True
    )
    cycle = fields.Integer(required=True)
    parent_run_id = fields.Many2one(
        "mc.rov.manufacturing.activity.run", ondelete="restrict", check_company=True
    )
    activity_id = fields.Many2one("mail.activity", ondelete="set null", index=True)
    started_at = fields.Datetime(required=True)
    original_deadline = fields.Date(required=True)
    # Sobrevive al unlink nativo de la actividad para no reiniciar el plazo del retropedido.
    current_deadline = fields.Date()
    calendar_id = fields.Many2one("resource.calendar", required=True, ondelete="restrict")
    calendar_tz = fields.Char(required=True)
    outcome = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("business_done", "Fabricación terminada"),
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
        "UNIQUE(production_id, cycle)", "La fabricación ya tiene seguimiento en este ciclo."
    )
    _positive_cycle = models.Constraint("CHECK(cycle > 0)", "El ciclo debe ser positivo.")

    # Sin ACL pública: solo servicios privados con autorización sobre la MO gestionan historia.
