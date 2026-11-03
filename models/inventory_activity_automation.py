from markupsafe import Markup

from odoo import _, models
from odoo.exceptions import ValidationError


# Una identidad en memoria evita que un contexto RPC suplante un evento interno.
_INVENTORY_INTERNAL = object()
_OPEN_INVENTORY_STATES = ("waiting", "confirmed", "assigned")


class InventoryActivityAutomation(models.AbstractModel):
    """Genera seguimiento sobre operaciones autorizadas sin reservar ni validar stock."""

    _name = "mc.rov.inventory.activity.automation"
    _description = "Automatización de actividades de inventario"

    def _authorized(self, picking, access="write"):
        picking = picking.with_env(self.env)
        return bool(
            isinstance(picking.id, int)
            and not isinstance(picking.id, bool)
            and picking.id > 0
            and picking.has_access("read")
            and picking.has_access(access)
            and picking.company_id in self.env.companies
        )

    def _configured_policy(self, picking, explain=False):
        picking = picking.with_env(self.env)
        if not self._authorized(picking):
            return False
        policy = (
            self.env["mc.rov.inventory.activity.policy"]
            .sudo()
            .search([("company_id", "=", picking.company_id.id)], limit=1)
        )
        if (
            not policy
            or not policy.enabled
            or not self.env["mc.rov.automation.control"]._creation_enabled(picking.company_id)
        ):
            return False
        # Un tipo no seleccionado es una exclusión deliberada, no un error operativo.
        if not policy._rule_for(picking):
            return False
        reason = policy._configuration_error(picking)
        if reason:
            if explain:
                picking.message_post(body=_("Seguimiento automático no generado: %s", reason))
            return False
        return policy

    def _new_cycle(self, picking, policy, occurred_at, parent):
        cycles = self.env["mc.rov.inventory.activity.cycle"].sudo()
        parent = (parent or picking.backorder_id).with_env(self.env)
        inherited = cycles.browse()
        if parent and picking.backorder_id == parent and self._authorized(parent):
            inherited = cycles.search([("picking_id", "=", parent.id)], limit=1)
        if inherited and inherited.company_id != picking.company_id:
            raise ValidationError(_("El restante no pertenece a la empresa del compromiso."))
        instant = policy._utc_instant(occurred_at)
        anchor = max(instant, policy._utc_instant(picking.scheduled_date))
        try:
            deadline = (
                inherited.current_deadline
                if inherited
                else policy._deadline(instant, picking.scheduled_date, picking.date_deadline)
            )
        except ValidationError as error:
            picking.message_post(body=_("Seguimiento automático no generado: %s", str(error)))
            return False
        return cycles.create(
            {
                "company_id": picking.company_id.id,
                "picking_id": picking.id,
                "policy_id": policy.id,
                "rule_id": policy._rule_for(picking).id,
                "parent_id": inherited.id or False,
                "picking_type_id": picking.picking_type_id.id,
                "operation_code": picking.picking_type_id.code,
                "confirmed_at": instant,
                "anchor_at": inherited.anchor_at if inherited else anchor,
                "scheduled_at_initial": picking.scheduled_date,
                "native_deadline_initial": picking.date_deadline,
                "original_deadline": inherited.original_deadline if inherited else deadline,
                "current_deadline": deadline,
                "calendar_id": (inherited.calendar_id.id if inherited else policy.calendar_id.id),
                "deadline_tz": inherited.deadline_tz if inherited else policy.calendar_id.tz,
                "lead_days": inherited.lead_days if inherited else policy.lead_days,
                "observed_state": picking.state,
                "event_sequence": 1,
            }
        )

    def _start(self, picking, occurred_at, parent=False):
        """El documento y su evento son únicos; un restante conserva el compromiso padre."""
        picking = picking.with_env(self.env)
        if not self._authorized(picking) or picking.state not in _OPEN_INVENTORY_STATES:
            return False
        policy = self._configured_policy(picking, explain=True)
        if not policy:
            return False
        self.env["mc.rov.inventory.activity.lifecycle"]._capture(picking)
        cycles = self.env["mc.rov.inventory.activity.cycle"].sudo()
        cycle = cycles.search([("picking_id", "=", picking.id)], limit=1)
        if not cycle:
            cycle = self._new_cycle(picking, policy, occurred_at, parent)
            if not cycle:
                return False
        runs = self.env["mc.rov.inventory.activity.run"].sudo()
        existing = runs.search([("cycle_id", "=", cycle.id), ("event", "=", 1)], limit=1)
        if existing:
            return existing
        rule = policy._rule_for(picking)
        suffix, summary = {
            "incoming": ("receipt", _("Gestionar recepción")),
            "outgoing": ("delivery", _("Gestionar entrega")),
            "internal": ("transfer", _("Gestionar transferencia interna")),
        }[picking.picking_type_id.code]
        activity = (
            self.env["mail.activity"]
            .sudo()
            .with_company(picking.company_id)
            .create(
                {
                    "res_model_id": self.env["ir.model"]._get_id("stock.picking"),
                    "res_id": picking.id,
                    "activity_type_id": self.env.ref(
                        "mc_rov.activity_type_inventory_" + suffix
                    ).id,
                    "summary": summary,
                    "note": Markup('<p><a href="/odoo/stock.picking/%s">%s</a></p>')
                    % (picking.id, picking.display_name),
                    "user_id": rule.user_id.id,
                    "mc_employee_id": rule.employee_id.id or False,
                    "date_deadline": cycle.current_deadline,
                }
            )
        )
        return runs.create(
            {
                "company_id": picking.company_id.id,
                "cycle_id": cycle.id,
                "event": 1,
                "activity_id": activity.id,
                "started_at": occurred_at,
                "original_deadline": cycle.original_deadline,
                "current_deadline": cycle.current_deadline,
            }
        )
