from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import SQL

from .inventory_activity_automation import _INVENTORY_INTERNAL, _OPEN_INVENTORY_STATES
from .mc_rov_activity_assignment_wizard import _WORK_ACTIVITY_DEADLINE_AUTH


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
        with self.env.cr.savepoint():
            self.env["mc.rov.inventory.activity.automation"]._check_source_changes(self, values)
            return self._inventory_event_call("write", values)

    def unlink(self):
        self.check_access("unlink")
        self.env["mc.rov.inventory.activity.automation"]._check_source_deletion(self)
        return super().unlink()

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


class InventoryMailActivityLifecycle(models.Model):
    """Registra decisiones sobre tareas propias sin validar ni cancelar el movimiento de stock."""

    _inherit = "mail.activity"

    def _mc_inventory_runs(self):
        ids = [
            row.id
            for row in self
            if isinstance(row.id, int) and not isinstance(row.id, bool) and row.id > 0
        ]
        empty = self.env["mc.rov.inventory.activity.run"].sudo().browse()
        if not ids:
            return empty
        own_types = set()
        for suffix in ("receipt", "delivery", "transfer"):
            kind = self.env.ref(
                "mc_rov.activity_type_inventory_" + suffix, raise_if_not_found=False
            )
            if kind:
                own_types.add(kind.id)
        activities = (
            self.browse(ids)
            .with_user(self.env.uid)
            .filtered(
                lambda activity: activity.res_model == "stock.picking"
                and activity.activity_type_id.id in own_types
            )
        )
        if not activities:
            return empty
        activities.check_access("write")
        pickings = self.env["stock.picking"].browse(activities.mapped("res_id"))
        # El servicio exige permisos y empresa antes de la consulta privada con sudo.
        runs = self.env["mc.rov.inventory.activity.automation"]._runs(pickings, access="read")
        runs = runs.filtered(lambda run: run.activity_id.id in activities.ids)
        runs.invalidate_recordset(["outcome", "activity_id"])
        activities.invalidate_recordset(
            ["res_model", "res_model_id", "res_id", "activity_type_id", "active", "date_deadline"]
        )
        for run in runs:
            activity = run.activity_id
            suffix = {"incoming": "receipt", "outgoing": "delivery", "internal": "transfer"}[
                run.cycle_id.operation_code
            ]
            if (
                activity.res_model != "stock.picking"
                or activity.res_id != run.picking_id.id
                or run.company_id != run.picking_id.company_id
                or activity.activity_type_id
                != self.env.ref("mc_rov.activity_type_inventory_" + suffix)
            ):
                raise AccessError(
                    _("La actividad ya no corresponde a su operación de inventario.")
                )
        return runs

    def _mc_inventory_check_recipient(self, runs, values):
        if not runs or "user_id" not in values:
            return
        user = self.env["res.users"].browse(values["user_id"])
        if not user or not user.active or user.share:
            raise ValidationError(_("Seleccione una cuenta interna activa."))
        for run in runs:
            company = run.company_id
            if company not in user.company_ids:
                raise ValidationError(_("La cuenta no tiene acceso a la empresa del documento."))
            target = (
                self.env["stock.picking"]
                .with_user(user)
                .with_context(allowed_company_ids=company.ids)
                .with_company(company)
                .browse(run.picking_id.id)
            )
            if (
                not target.has_access("read")
                or not target.has_access("write")
                or not target.picking_type_id.has_access("read")
            ):
                raise ValidationError(
                    _("La cuenta no puede consultar y gestionar esta operación.")
                )

    def _mc_inventory_manual_outcome(self, runs, outcome, reason):
        # Guardar primero impide que unlink/archivo anidados sobrescriban la decisión.
        for run in runs.filtered(lambda row: row.outcome == "pending"):
            deadline = (
                run.activity_id.date_deadline or run.current_deadline or run.original_deadline
            )
            run.write(
                {
                    "outcome": outcome,
                    "current_deadline": deadline,
                    "finished_at": fields.Datetime.now(),
                    "finished_by_id": self.env.uid,
                    "finish_reason": reason,
                }
            )
            run.cycle_id.write({"current_deadline": deadline})
            if outcome == "cancelled":
                run.picking_id.with_user(self.env.uid).message_post(
                    body=Markup("<p>%s</p>") % reason
                )

    def _action_done(self, feedback=False, attachment_ids=None):
        with self.env.cr.savepoint():
            self._mc_inventory_manual_outcome(
                self._mc_inventory_runs(),
                "manual_done",
                feedback or _("Actividad marcada como hecha manualmente."),
            )
            return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def unlink(self):
        with self.env.cr.savepoint():
            runs = self._mc_inventory_runs()
            self._mc_inventory_manual_outcome(
                runs, "cancelled", _("Actividad cancelada manualmente.")
            )
            result = super().unlink()
            runs.invalidate_recordset(["activity_id"])
            return result

    def _mc_inventory_check_deadline_authorization(self, runs, values):
        if not runs or "date_deadline" not in values:
            return
        try:
            deadline = fields.Date.to_date(values["date_deadline"])
        except (TypeError, ValueError) as error:
            raise ValidationError(_("Indique una fecha límite válida.")) from error
        changing = runs.filtered(lambda run: run.activity_id.date_deadline != deadline)
        if not changing:
            return
        if not self.env.user.has_group("mc_rov.group_work_assignment_coordinate"):
            raise AccessError(_("La reprogramación requiere permiso de coordinación."))
        authorization = self.env.context.get("_mc_activity_deadline_authorization")
        valid = (
            isinstance(authorization, tuple)
            and len(authorization) == 5
            and authorization[0] is _WORK_ACTIVITY_DEADLINE_AUTH
            and authorization[1] == self.env.uid
            and isinstance(authorization[2], tuple)
            and set(changing.activity_id.ids) <= set(authorization[2])
            and authorization[3] == deadline
            and isinstance(authorization[4], str)
            and bool(authorization[4].strip())
        )
        if not valid:
            raise UserError(_("Use Repartir actividades e indique el motivo para reprogramar."))

    def write(self, values):
        relevant = {
            "res_model",
            "res_model_id",
            "res_id",
            "activity_type_id",
            "date_deadline",
            "active",
            "user_id",
        }.intersection(values)
        if not relevant:
            return super().write(values)
        with self.env.cr.savepoint():
            runs = self._mc_inventory_runs()
            self._mc_inventory_check_deadline_authorization(runs, values)
            self._mc_inventory_check_recipient(runs, values)
            pending_before = runs.filtered(lambda row: row.outcome == "pending")
            for run in runs:
                activity = run.activity_id
                model = values.get("res_model", activity.res_model)
                if "res_model_id" in values:
                    model = self.env["ir.model"].browse(values["res_model_id"]).model
                if (
                    model != "stock.picking"
                    or values.get("res_id", activity.res_id) != run.picking_id.id
                    or values.get("activity_type_id", activity.activity_type_id.id)
                    != activity.activity_type_id.id
                ):
                    raise ValidationError(
                        _("Una actividad seguida no puede cambiar de origen ni tipo.")
                    )
            if values.get("active") is False:
                self._mc_inventory_manual_outcome(
                    runs, "cancelled", _("Actividad archivada manualmente.")
                )
            result = super().write(values)
            if "date_deadline" in values:
                # El mismo write puede haber archivado la tarea: conservar el conjunto
                # previo para registrar la fecha final también en ese resultado cerrado.
                for run in pending_before:
                    deadline = run.activity_id.date_deadline
                    if deadline:
                        run.write({"current_deadline": deadline})
                        run.cycle_id.write({"current_deadline": deadline})
            return result
