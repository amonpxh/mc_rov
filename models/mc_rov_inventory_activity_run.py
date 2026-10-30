from odoo import fields, models


class InventoryActivityRun(models.Model):
    """Identifica la actividad propia sin sustituir reservas ni avisos nativos de stock."""

    _name = "mc.rov.inventory.activity.run"
    _description = "Ejecución técnica de inventario"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    cycle_id = fields.Many2one(
        "mc.rov.inventory.activity.cycle", required=True, ondelete="restrict", check_company=True
    )
    picking_id = fields.Many2one(related="cycle_id.picking_id", store=True, index=True)
    event = fields.Integer(required=True)
    activity_id = fields.Many2one("mail.activity", ondelete="set null", index=True)
    started_at = fields.Datetime(required=True)
    original_deadline = fields.Date(required=True)
    current_deadline = fields.Date()
    outcome = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("business_done", "Operación completada"),
            ("manual_done", "Marcada como hecha"),
            ("cancelled", "Cancelada"),
            ("withdrawn", "Retirada"),
        ],
        required=True,
        default="pending",
    )
    finished_at = fields.Datetime()
    finished_by_id = fields.Many2one("res.users", ondelete="set null")
    finish_reason = fields.Text()

    _event_unique = models.Constraint(
        "UNIQUE(cycle_id, event)", "Este evento ya tiene seguimiento en la operación."
    )
    _positive_event = models.Constraint("CHECK(event > 0)", "El evento debe ser positivo.")

    # Sin ACL pública; el origen y su actividad son las interfaces del trabajo del equipo.
