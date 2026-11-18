"""Evidencia privada de detenciones; ninguna ACL permite editarla directamente."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from .detention_kpi_metrics import CAUSES


_CAPABILITY = object()
_KEY = "mc_detention_capability"
CAUSE_LABELS = dict(
    zip(
        CAUSES,
        (
            "Repuestos/materiales",
            "Autorización/información del cliente",
            "Ingeniería",
            "Documentación",
            "Personal/equipo de prueba",
            "Servicio externo",
            "Otro",
        ),
    )
)


class DetentionInterval(models.Model):
    """Conserva motivo, origen, inicio y autores; el cierre no reemplaza el comienzo."""

    _name = "mc.rov.detention.interval"
    _description = "Detención efectiva de trabajo ROV"
    _check_company_auto = True
    _order = "started_at, id"

    company_id = fields.Many2one("res.company", required=True, ondelete="restrict")
    repair_id = fields.Many2one(
        "repair.order", ondelete="restrict", check_company=True, index=True
    )
    production_id = fields.Many2one(
        "mrp.production", ondelete="restrict", check_company=True, index=True
    )
    cause = fields.Selection(list(CAUSE_LABELS.items()), required=True, index=True)
    started_at = fields.Datetime(required=True, index=True)
    ended_at = fields.Datetime(index=True)
    actor_id = fields.Many2one("res.users", required=True, ondelete="restrict")
    # Un empleado puede no tener login: no se confunde con el actor del registro.
    responsible_employee_id = fields.Many2one(
        "hr.employee", required=True, ondelete="restrict", check_company=True
    )
    explanation = fields.Text()
    closed_by_id = fields.Many2one("res.users", ondelete="restrict")
    closing_explanation = fields.Text()
    end_kind = fields.Selection(
        [("resumed", "Trabajo reanudado"), ("source_closed", "Fin por cierre de orden")]
    )
    _one_source = models.Constraint(
        "CHECK ((repair_id IS NOT NULL) <> (production_id IS NOT NULL))",
        "La detención pertenece a una única orden.",
    )
    _chronology = models.Constraint(
        "CHECK (ended_at IS NULL OR ended_at >= started_at)",
        "La detención no puede terminar antes de comenzar.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su or self.env.context.get(_KEY) is not _CAPABILITY:
            raise AccessError(_("Registre la detención desde su orden autorizada."))
        return super().create(vals_list)

    def write(self, values):
        allowed = {"ended_at", "closed_by_id", "closing_explanation", "end_kind"}
        if (
            not self.env.su
            or self.env.context.get(_KEY) is not _CAPABILITY
            or not values
            or not set(values) <= allowed
            or any(self.mapped("ended_at"))
        ):
            raise AccessError(_("La evidencia no se edita; registre su fin desde la orden."))
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_history(self):
        raise AccessError(_("No se elimina el historial de detenciones."))
