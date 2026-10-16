import logging

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)
_CYCLE_FIELDS = {"mc_activity_cycle", "mc_activity_cycle_closed"}
_OPEN_STATES = {"confirmed", "under_repair"}
_TERMINAL_STATES = {"done", "cancel"}


class RepairActivityAutomation(models.AbstractModel):
    """Traduce transiciones de una visita en pendientes; no dirige la reparación."""

    _name = "mc.rov.repair.activity.automation"
    _description = "Automatización de actividades de reparación"

    def _after_order_transition(self, order, old_state, started_at):
        order.ensure_one()
        order.check_access("write")
        if not order.lot_id or not order.lot_id.es_un_rov:
            return
        if order.state in _TERMINAL_STATES:
            if order.mc_activity_cycle:
                order._mc_set_activity_cycle(order.mc_activity_cycle, closed=True)
            return
        if order.state not in _OPEN_STATES:
            return
        reopening = old_state in _TERMINAL_STATES or (
            old_state == "draft" and order.mc_activity_cycle_closed
        )
        if not order.mc_activity_cycle or reopening:
            order._mc_set_activity_cycle(order.mc_activity_cycle + 1, closed=False)
        if old_state == "draft" or reopening:
            revision = self.env["mc.rov.revision"].search(
                [
                    ("repair_id", "=", order.id),
                    ("tipo", "=", "reparacion"),
                ],
                order="id",
                limit=1,
            )
            if revision and revision.estado != "confirmado":
                self._start_stage(order, "diagnosis", started_at, revision=revision)
        if order.state == "under_repair" and old_state != "under_repair":
            self._start_stage(order, "repair", started_at)

    def _configuration_notice(self, order, reason):
        # El mensaje es accionable sin revelar nombres privados o ampliar permisos.
        order.message_post(body=_("Seguimiento automático no generado: %s", reason))
        _logger.warning("Seguimiento de reparación %s incompleto: %s", order.id, reason)

    def _start_stage(self, order, stage, started_at, revision=False):
        order.ensure_one()
        order.check_access("write")
        if stage not in {"diagnosis", "repair"} or not order.mc_activity_cycle:
            raise ValidationError(_("Etapa o ciclo de seguimiento inválido."))
        # Solo este servicio privado consulta configuración protegida y el ledger.
        policy = (
            self.env["mc.rov.repair.activity.policy"]
            .sudo()
            .search(
                [
                    ("company_id", "=", order.company_id.id),
                ],
                limit=1,
            )
        )
        if not self.env["mc.rov.automation.control"]._creation_enabled(order.company_id) or (
            policy and not policy.enabled
        ):
            return False
        if not policy:
            self._configuration_notice(
                order, _("Configure cuenta y calendario en Seguimiento de reparaciones.")
            )
            return False
        reason = policy._configuration_error(order)
        if reason:
            self._configuration_notice(order, reason)
            return False
        runs = self.env["mc.rov.repair.activity.run"].sudo().with_company(order.company_id)
        existing = runs.search(
            [
                ("repair_id", "=", order.id),
                ("cycle", "=", order.mc_activity_cycle),
                ("stage", "=", stage),
            ],
            limit=1,
        )
        if existing:
            return existing
        try:
            deadline = policy._deadline(
                started_at, policy.diagnosis_days if stage == "diagnosis" else policy.repair_days
            )
        except ValidationError as error:
            self._configuration_notice(order, str(error))
            return False
        run = runs.create(
            {
                "company_id": order.company_id.id,
                "repair_id": order.id,
                "cycle": order.mc_activity_cycle,
                "stage": stage,
                "revision_id": revision.id if revision else False,
                "started_at": started_at,
                "original_deadline": deadline,
                "calendar_id": policy.calendar_id.id,
                "calendar_tz": policy.calendar_id.tz,
            }
        )
        title = (
            _("Completar diagnóstico técnico")
            if stage == "diagnosis"
            else _("Realizar reparación")
        )
        note = Markup('<p><a href="/odoo/repair.order/%s">%s</a></p>') % (
            order.id,
            order.display_name,
        )
        if revision:
            note += Markup('<p><a href="/odoo/mc.rov.revision/%s">%s</a></p>') % (
                revision.id,
                revision.display_name,
            )
        activity = (
            self.env["mail.activity"]
            .sudo()
            .with_company(order.company_id)
            .create(
                {
                    "res_model_id": self.env["ir.model"]._get_id("repair.order"),
                    "res_id": order.id,
                    "activity_type_id": self.env.ref("mc_rov.activity_type_repair_" + stage).id,
                    "summary": title,
                    "note": note,
                    "user_id": policy.user_id.id,
                    "mc_employee_id": policy.employee_id.id or False,
                    "date_deadline": deadline,
                }
            )
        )
        run.activity_id = activity
        return run


class RepairOrderAutomation(models.Model):
    """Observa estados efectivos después de las validaciones y creación nativa de REV."""

    _inherit = "repair.order"

    mc_activity_cycle = fields.Integer(readonly=True, copy=False, default=0)
    mc_activity_cycle_closed = fields.Boolean(readonly=True, copy=False, default=False)

    @api.model_create_multi
    def create(self, vals_list):
        if any(_CYCLE_FIELDS.intersection(values) for values in vals_list):
            raise AccessError(_("El ciclo de seguimiento se administra internamente."))
        # Impedir que default_* del contexto RPC eluda la protección de campos internos.
        values = [
            dict(item, mc_activity_cycle=0, mc_activity_cycle_closed=False) for item in vals_list
        ]
        return super().create(values)

    def _mc_set_activity_cycle(self, cycle, closed):
        self.ensure_one()
        self.check_access("write")
        return super().write({"mc_activity_cycle": cycle, "mc_activity_cycle_closed": closed})

    def write(self, vals):
        if _CYCLE_FIELDS.intersection(vals):
            raise AccessError(_("El ciclo de seguimiento se administra internamente."))
        # ids resuelve NewId(origin=...) al origen; id conserva su naturaleza temporal.
        if (
            "state" not in vals
            or not self
            or any(not isinstance(order.id, int) or order.id <= 0 for order in self)
        ):
            return super().write(vals)
        self.check_access("write")
        self.flush_recordset(["state", "mc_activity_cycle", "mc_activity_cycle_closed"])
        # Mismo orden de bloqueo para lotes de órdenes; leer estado tras tomar el lock.
        self.env.cr.execute(
            SQL(
                "SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE",
                SQL.identifier(self._table),
                tuple(sorted(self.ids)),
            )
        )
        self.invalidate_recordset(["state", "mc_activity_cycle", "mc_activity_cycle_closed"])
        previous = {order.id: order.state for order in self}
        result = super().write(vals)
        service = self.env["mc.rov.repair.activity.automation"]
        started_at = fields.Datetime.now()
        for order in self:
            if previous[order.id] != order.state:
                service._after_order_transition(order, previous[order.id], started_at)
        return result
