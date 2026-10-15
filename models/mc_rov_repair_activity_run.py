from odoo import fields, models


class RepairActivityRun(models.Model):
    """Identidad privada que sobrevive al archivado o retirada del pendiente nativo."""

    _name = "mc.rov.repair.activity.run"
    _description = "Seguimiento técnico de etapa de reparación"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    repair_id = fields.Many2one(
        "repair.order", required=True, index=True, ondelete="restrict", check_company=True
    )
    cycle = fields.Integer(required=True)
    stage = fields.Selection(
        [("diagnosis", "Diagnóstico"), ("repair", "Reparación")], required=True
    )
    revision_id = fields.Many2one("mc.rov.revision", ondelete="restrict")
    activity_id = fields.Many2one("mail.activity", ondelete="set null", index=True)
    started_at = fields.Datetime(required=True)
    original_deadline = fields.Date(required=True)
    calendar_id = fields.Many2one("resource.calendar", required=True, ondelete="restrict")
    calendar_tz = fields.Char(required=True)
    outcome = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("business_done", "Etapa terminada"),
            ("manual_done", "Marcada como hecha"),
            ("cancelled", "Cancelada"),
        ],
        default="pending",
        required=True,
    )
    finished_at = fields.Datetime()
    finished_by_id = fields.Many2one("res.users", ondelete="set null")
    finish_reason = fields.Text()

    _stage_unique = models.Constraint(
        "UNIQUE(repair_id, cycle, stage)", "La etapa ya tiene seguimiento en este ciclo."
    )
    _positive_cycle = models.Constraint("CHECK(cycle > 0)", "El ciclo debe ser positivo.")

    # Sin ACL pública: los servicios privados operan tras validar el origen real.
