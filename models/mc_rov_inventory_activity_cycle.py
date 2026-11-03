from odoo import fields, models


class InventoryActivityCycle(models.Model):
    """Captura el ancla y el compromiso original; un parcial heredará su límite vigente."""

    _name = "mc.rov.inventory.activity.cycle"
    _description = "Ciclo técnico de inventario"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    picking_id = fields.Many2one(
        "stock.picking", required=True, ondelete="restrict", check_company=True, index=True
    )
    policy_id = fields.Many2one(
        "mc.rov.inventory.activity.policy", ondelete="restrict", check_company=True
    )
    rule_id = fields.Many2one(
        "mc.rov.inventory.activity.rule", ondelete="set null", check_company=True
    )
    parent_id = fields.Many2one(
        "mc.rov.inventory.activity.cycle", ondelete="restrict", check_company=True
    )
    picking_type_id = fields.Many2one(
        "stock.picking.type", required=True, ondelete="restrict", check_company=True
    )
    operation_code = fields.Selection(
        [("incoming", "Recepción"), ("outgoing", "Entrega"), ("internal", "Transferencia")],
        required=True,
    )
    confirmed_at = fields.Datetime(required=True)
    anchor_at = fields.Datetime(required=True)
    scheduled_at_initial = fields.Datetime()
    native_deadline_initial = fields.Datetime()
    original_deadline = fields.Date(required=True)
    current_deadline = fields.Date(required=True)
    calendar_id = fields.Many2one("resource.calendar", ondelete="restrict", check_company=True)
    deadline_tz = fields.Char(required=True)
    lead_days = fields.Integer(required=True, default=3)
    observed_state = fields.Char()
    event_sequence = fields.Integer(required=True, default=0)
    state = fields.Selection(
        [("open", "Pendiente"), ("done", "Completado"), ("cancel", "Cancelado")],
        required=True,
        default="open",
    )

    _picking_unique = models.Constraint(
        "UNIQUE(picking_id)", "Esta operación ya tiene seguimiento."
    )
    _positive_days = models.Constraint(
        "CHECK(lead_days BETWEEN 1 AND 365)", "El plazo debe estar entre 1 y 365 días laborables."
    )
    _nonnegative_event = models.Constraint(
        "CHECK(event_sequence >= 0)", "El contador de eventos no puede ser negativo."
    )

    # Sin ACL pública; solo servicios autorizados sobre el picking acceden al historial.
