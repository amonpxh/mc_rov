"""Private evidence for formal repair acceptance; no public history write gateway."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_CAPTURE = object()
_CAPTURE_KEY = "mc_repair_acceptance_capability"


class RepairAcceptanceAttempt(models.Model):
    """Freeze each adjudicated attempt independently of the current revision."""

    _name = "mc.rov.repair.acceptance.attempt"
    _description = "Intento de aceptación final de reparación"
    _order = "repair_id, ordinal, id"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    repair_id = fields.Many2one(
        "repair.order", required=True, ondelete="restrict", check_company=True
    )
    lot_id = fields.Many2one("stock.lot", required=True, ondelete="restrict", check_company=True)
    revision_id = fields.Many2one("mc.rov.revision", required=True, ondelete="restrict")
    ordinal = fields.Integer(required=True)
    state = fields.Selection(
        [("pending", "En comprobación"), ("confirmed", "Confirmado"), ("aborted", "Interrumpido")],
        required=True,
        default="pending",
    )
    started_at = fields.Datetime(required=True)
    closed_at = fields.Datetime()
    confirmed_at = fields.Datetime()
    actor_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    responsable_id = fields.Many2one("hr.employee", ondelete="restrict")
    verdict_snapshot = fields.Selection(
        [
            ("aprobado", "Aprobado"),
            ("aprobado_con_observaciones", "Aprobado con observaciones"),
            ("rechazado", "Rechazado"),
        ]
    )
    correction_snapshot = fields.Selection(
        [("unknown", "Por revisar"), ("no", "No"), ("yes", "Sí")]
    )
    retest_snapshot = fields.Selection([("unknown", "Por revisar"), ("no", "No"), ("yes", "Sí")])
    requirements_snapshot = fields.Json(required=True)
    configuration_digest = fields.Char(required=True)
    reason = fields.Text()

    _ordinal_unique = models.Constraint(
        "UNIQUE(repair_id, lot_id, ordinal)", "El intento ya existe para esta reparación y serie."
    )
    _positive_ordinal = models.Constraint("CHECK(ordinal > 0)", "El ordinal debe ser positivo.")

    def _check_capture_capability(self):
        if not self.env.su or self.env.context.get(_CAPTURE_KEY) is not _CAPTURE:
            raise UserError(_("El historial se registra desde la comprobación final validada."))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_capture_capability()
        return super().create(vals_list)

    def write(self, values):
        self._check_capture_capability()
        if any(row.state != "pending" for row in self):
            raise UserError(_("Un intento cerrado conserva su evidencia original."))
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_acceptance_evidence(self):
        raise UserError(_("El historial de aceptación final no se puede borrar."))

    # No public ACL: callers must authorize company and every source before sudo reads.
