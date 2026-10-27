from odoo import fields, models


class AcceptanceEvidenceHistory(models.Model):
    """Conserva evidencia reemplazada sin publicar el historial técnico del ciclo."""

    _name = "mc.rov.acceptance.evidence.history"
    _description = "Selección de evidencia de aceptación"
    _order = "id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    cycle_id = fields.Many2one(
        "mc.rov.acceptance.activity.cycle",
        required=True,
        index=True,
        check_company=True,
        ondelete="restrict",
    )
    stage = fields.Selection([("performance", "Rendimiento"), ("field", "Terreno")], required=True)
    revision_id = fields.Many2one("mc.rov.revision", ondelete="restrict")
    previous_revision_id = fields.Many2one("mc.rov.revision", ondelete="restrict")
    actor_id = fields.Many2one("res.users", ondelete="set null")
    selected_at = fields.Datetime(required=True, default=fields.Datetime.now)
    reason = fields.Text()

    _has_evidence = models.Constraint(
        "CHECK(revision_id IS NOT NULL OR previous_revision_id IS NOT NULL)",
        "La auditoría debe conservar al menos una prueba de la selección.",
    )
    # Sin ACL pública: solo los servicios autorizados por el equipo escriben estos eventos.
