from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL

from .inventory_activity_automation import _INVENTORY_INTERNAL, _OPEN_INVENTORY_STATES


def _inside_inventory_event(env, ids):
    if env.context.get("_mc_inventory_creating") is _INVENTORY_INTERNAL:
        return True
    if env.context.get("_mc_inventory_capture") is _INVENTORY_INTERNAL:
        return True
    marker = env.context.get("_mc_inventory_event")
    return bool(
        isinstance(marker, tuple)
        and len(marker) == 2
        and marker[0] is _INVENTORY_INTERNAL
        and ids
        and set(ids) <= set(marker[1])
    )


class InventoryActivityLifecycle(models.AbstractModel):
    """Observa estados nativos y serializa la identidad del seguimiento por operación."""

    _name = "mc.rov.inventory.activity.lifecycle"
    _description = "Ciclo de actividades de inventario"

    def _capture(self, pickings, access="write"):
        service = self.env["mc.rov.inventory.activity.automation"]
        pickings = (
            pickings.with_env(self.env)
            .filtered(lambda picking: service._authorized(picking, access))
            .sorted("id")
            .with_context(_mc_inventory_capture=_INVENTORY_INTERNAL)
        )
        if not pickings:
            return {}
        names = [
            "state",
            "picking_type_id",
            "company_id",
            "backorder_id",
            "scheduled_date",
            "date_deadline",
        ]
        pickings.flush_recordset(names)
        cycles = (
            self.env["mc.rov.inventory.activity.cycle"]
            .sudo()
            .search([("picking_id", "in", pickings.ids)])
        )
        followed = set(cycles.picking_id.ids)
        serialized = [
            picking.id
            for picking in pickings
            if picking.id in followed or service._configured_policy(picking)
        ]
        if serialized:
            self.env.cr.execute(
                SQL(
                    "SELECT id FROM stock_picking WHERE id IN %s ORDER BY id FOR UPDATE",
                    tuple(serialized),
                )
            )
            # REPEATABLE READ necesita un conflicto de escritura para reintentar
            # dos confirmaciones que observaron simultáneamente el mismo borrador.
            self.env.cr.execute(
                SQL(
                    "UPDATE stock_picking SET write_date = write_date WHERE id IN %s",
                    tuple(serialized),
                )
            )
            pickings.invalidate_recordset(names)
            cycles.invalidate_recordset()
        return {
            picking.id: {
                "state": picking.state,
                "type_id": picking.picking_type_id.id,
                "company_id": picking.company_id.id,
            }
            for picking in pickings
        }

    def _finish(self, cycle, state, occurred_at):
        pending = (
            self.env["mc.rov.inventory.activity.run"]
            .sudo()
            .search([("cycle_id", "=", cycle.id), ("outcome", "=", "pending")])
        )
        outcome = "business_done" if state == "done" else "cancelled"
        reason = (
            _("Operación de inventario completada.")
            if state == "done"
            else _("Operación de inventario cancelada.")
        )
        for run in pending:
            activity = run.activity_id.exists()
            run.write(
                {
                    "outcome": outcome,
                    "current_deadline": cycle.current_deadline,
                    "finished_at": occurred_at,
                    "finished_by_id": self.env.uid,
                    "finish_reason": reason,
                }
            )
            if activity and activity.active:
                if state == "done":
                    activity.action_feedback(feedback=reason)
                else:
                    activity.action_cancel()
        cycle.write({"state": "done" if state == "done" else "cancel", "observed_state": state})

    def _sync(self, pickings, before, occurred_at):
        scoped = self.with_context(_mc_inventory_event=(_INVENTORY_INTERNAL, tuple(pickings.ids)))
        return scoped._sync_events(pickings, before, occurred_at)

    def _sync_events(self, pickings, before, occurred_at):
        current = self._capture(pickings)
        service = self.env["mc.rov.inventory.activity.automation"]
        for picking in pickings.with_env(self.env).sorted("id"):
            if picking.id not in before or picking.id not in current:
                continue
            snapshot, previous = current[picking.id], before[picking.id]
            cycle = (
                self.env["mc.rov.inventory.activity.cycle"]
                .sudo()
                .search([("picking_id", "=", picking.id)], limit=1)
            )
            if cycle and cycle.company_id != picking.company_id:
                raise ValidationError(_("La operación no pertenece a la empresa del seguimiento."))
            if snapshot["state"] in ("done", "cancel"):
                if cycle:
                    self._finish(cycle, snapshot["state"], occurred_at)
            elif cycle:
                if cycle.observed_state != snapshot["state"]:
                    cycle.observed_state = snapshot["state"]
            elif snapshot["state"] in _OPEN_INVENTORY_STATES and (
                previous is None or previous["state"] == "draft"
            ):
                service._start(picking, occurred_at)

    def _inherit_remaining(self, parent, remaining, occurred_at):
        service = self.env["mc.rov.inventory.activity.automation"]
        if not service._authorized(parent):
            return
        for picking in remaining:
            if picking.backorder_id == parent:
                service._start(picking, occurred_at, parent=parent)


class InventoryPickingEvents(models.Model):
    """Consolida las llamadas de stock; devuelve siempre el resultado nativo original."""

    _inherit = "stock.picking"

    @api.model_create_multi
    def create(self, vals_list):
        with self.env.cr.savepoint():
            scoped = self.with_context(_mc_inventory_creating=_INVENTORY_INTERNAL)
            pickings = super(InventoryPickingEvents, scoped).create(vals_list).with_env(self.env)
            self.env["mc.rov.inventory.activity.lifecycle"]._sync(
                pickings, {picking.id: None for picking in pickings}, fields.Datetime.now()
            )
            return pickings

    def _inventory_event_call(self, method, *args, **kwargs):
        if method not in (
            "write",
            "action_confirm",
            "action_assign",
            "action_cancel",
            "_action_done",
        ):
            raise ValidationError(_("El evento de inventario no es válido."))
        if _inside_inventory_event(self.env, self.ids):
            return getattr(super(), method)(*args, **kwargs)
        with self.env.cr.savepoint():
            lifecycle = self.env["mc.rov.inventory.activity.lifecycle"]
            before = lifecycle._capture(self)
            scoped = self.with_context(_mc_inventory_event=(_INVENTORY_INTERNAL, tuple(self.ids)))
            result = getattr(super(InventoryPickingEvents, scoped), method)(*args, **kwargs)
            lifecycle._sync(self, before, fields.Datetime.now())
            return result

    # El helper invoca super con el contexto consolidado del evento nativo.
    def write(self, values):  # pylint: disable=unknown-option-value,method-required-super
        return self._inventory_event_call("write", values)

    def action_confirm(self):
        return self._inventory_event_call("action_confirm")

    def action_assign(self):
        return self._inventory_event_call("action_assign")

    def action_cancel(self):
        return self._inventory_event_call("action_cancel")

    def _action_done(self):
        return self._inventory_event_call("_action_done")

    def _create_backorder(self, backorder_moves=None):
        with self.env.cr.savepoint():
            backorders = super()._create_backorder(backorder_moves=backorder_moves)
            lifecycle = self.env["mc.rov.inventory.activity.lifecycle"]
            for parent in self:
                lifecycle._inherit_remaining(
                    parent,
                    backorders.filtered_domain([("backorder_id", "=", parent.id)]),
                    fields.Datetime.now(),
                )
            return backorders


class InventoryMoveEvents(models.Model):
    """También observa transiciones calculadas por movimientos y sus documentos resultantes."""

    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        ids = {values["picking_id"] for values in vals_list if values.get("picking_id")}
        pickings = self.env["stock.picking"].browse(sorted(ids))
        if _inside_inventory_event(self.env, pickings.ids):
            return super().create(vals_list)
        with self.env.cr.savepoint():
            lifecycle = self.env["mc.rov.inventory.activity.lifecycle"]
            before = lifecycle._capture(pickings)
            scoped = self.with_context(
                _mc_inventory_event=(_INVENTORY_INTERNAL, tuple(pickings.ids))
            )
            moves = super(InventoryMoveEvents, scoped).create(vals_list).with_env(self.env)
            actual = pickings | moves.picking_id
            for picking in actual:
                before.setdefault(picking.id, None)
            lifecycle._sync(actual, before, fields.Datetime.now())
            return moves

    def _inventory_move_event_call(self, method, *args, **kwargs):
        if method not in (
            "write",
            "_action_confirm",
            "_action_assign",
            "_action_done",
            "_action_cancel",
        ):
            raise ValidationError(_("El evento de movimiento no es válido."))
        pickings = self.picking_id
        if method == "write" and args[0].get("picking_id"):
            pickings |= self.env["stock.picking"].browse(args[0]["picking_id"])
        if _inside_inventory_event(self.env, pickings.ids):
            return getattr(super(), method)(*args, **kwargs)
        with self.env.cr.savepoint():
            lifecycle = self.env["mc.rov.inventory.activity.lifecycle"]
            before = lifecycle._capture(pickings)
            scoped = self.with_context(
                _mc_inventory_event=(_INVENTORY_INTERNAL, tuple(pickings.ids))
            )
            result = getattr(super(InventoryMoveEvents, scoped), method)(*args, **kwargs)
            actual = pickings | self.exists().picking_id
            if method in ("_action_confirm", "_action_done") and isinstance(
                result, models.BaseModel
            ):
                actual |= result.picking_id
            for picking in actual:
                before.setdefault(picking.id, None)
            lifecycle._sync(actual, before, fields.Datetime.now())
            # El resultado no debe conservar el marcador que suprime eventos anidados.
            return result.with_env(self.env) if getattr(result, "_name", None) else result

    def write(self, values):  # pylint: disable=unknown-option-value,method-required-super
        return self._inventory_move_event_call("write", values)

    def _action_confirm(self, merge=True, merge_into=False, create_proc=True):
        return self._inventory_move_event_call(
            "_action_confirm", merge=merge, merge_into=merge_into, create_proc=create_proc
        )

    def _action_assign(self, force_qty=False):
        return self._inventory_move_event_call("_action_assign", force_qty=force_qty)

    def _action_done(self, cancel_backorder=False):
        return self._inventory_move_event_call("_action_done", cancel_backorder=cancel_backorder)

    def _action_cancel(self):
        return self._inventory_move_event_call("_action_cancel")
