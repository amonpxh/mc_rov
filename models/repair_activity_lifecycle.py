from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL


class RepairActivityLifecycle(models.AbstractModel):
    """Registra el resultado del pendiente sin sustituir el evento de negocio."""

    _inherit = "mc.rov.repair.activity.automation"

    def _after_order_transition(self, order, old_state, started_at):
        result = super()._after_order_transition(order, old_state, started_at)
        if order.state in ("confirmed", "under_repair"):
            superseded = (
                self.env["mc.rov.repair.activity.run"]
                .sudo()
                .search(
                    [
                        ("repair_id", "=", order.id),
                        ("cycle", "<", order.mc_activity_cycle),
                        ("stage", "=", "diagnosis"),
                        ("outcome", "=", "pending"),
                    ]
                )
            )
            for run in superseded:
                self._finish_run(
                    run, "cancelled", _("Diagnóstico sustituido por la reapertura de la orden.")
                )
        if order.state not in ("done", "cancel"):
            return result
        order.check_access("write")
        runs = (
            self.env["mc.rov.repair.activity.run"]
            .sudo()
            .search(
                [
                    ("repair_id", "=", order.id),
                    ("outcome", "=", "pending"),
                ]
            )
        )
        for run in runs:
            if order.state == "cancel":
                self._finish_run(run, "cancelled", _("Orden cancelada."))
            elif run.stage == "repair":
                self._finish_run(run, "business_done", _("Orden de reparación terminada."))
        return result

    def _after_revision_confirmation(self, revision):
        revision.ensure_one()
        revision.check_access("write")
        if revision.estado != "confirmado" or not revision.repair_id:
            return
        revision.repair_id.check_access("read")
        runs = (
            self.env["mc.rov.repair.activity.run"]
            .sudo()
            .search(
                [
                    ("revision_id", "=", revision.id),
                    ("repair_id", "=", revision.repair_id.id),
                    ("stage", "=", "diagnosis"),
                    ("outcome", "=", "pending"),
                ]
            )
        )
        for run in runs:
            self._finish_run(run, "business_done", _("Revisión técnica confirmada."))

    def _record_outcome(self, runs, outcome, reason):
        if outcome not in ("business_done", "manual_done", "cancelled"):
            raise ValidationError(_("Resultado de seguimiento inválido."))
        pending = runs.filtered(lambda run: run.outcome == "pending")
        if pending:
            pending.write(
                {
                    "outcome": outcome,
                    "finished_at": fields.Datetime.now(),
                    "finished_by_id": self.env.uid,
                    "finish_reason": reason or False,
                }
            )

    def _validated_finish_order(self, run, outcome):
        run.ensure_one()
        order = run.repair_id.with_env(self.env)
        order.check_access("read")
        self.env.cr.execute(
            SQL(
                "SELECT id FROM %s WHERE id = %s FOR UPDATE",
                SQL.identifier(order._table),
                order.id,
            )
        )
        order.invalidate_recordset(["state"])
        if outcome == "cancelled":
            order.check_access("write")
            superseded = (
                run.stage == "diagnosis"
                and run.cycle < order.mc_activity_cycle
                and not order.mc_activity_cycle_closed
                and order.state in ("confirmed", "under_repair")
            )
            if order.state != "cancel" and not superseded:
                raise ValidationError(_("La orden no está cancelada."))
        elif outcome == "business_done" and run.stage == "diagnosis":
            revision = run.revision_id.with_env(self.env)
            revision.check_access("write")
            if not revision or revision.estado != "confirmado" or revision.repair_id != order:
                raise ValidationError(_("No está confirmada la revisión vinculada."))
        elif outcome == "business_done" and run.stage == "repair":
            order.check_access("write")
            if order.state != "done":
                raise ValidationError(_("La reparación no está terminada."))
        else:
            raise ValidationError(_("Evento de cierre inválido."))
        return order

    def _finish_run(self, run, outcome, feedback):
        order = self._validated_finish_order(run, outcome)
        with self.env.cr.savepoint():
            activity = run.activity_id
            if activity:
                # El evento ya autoriza el cierre; validar también su enlace actual.
                activity._mc_repair_runs()
            run.invalidate_recordset(["outcome"])
            if run.outcome != "pending":
                return
            self._record_outcome(run, outcome, feedback)
            if activity and activity.active:
                if outcome == "business_done":
                    activity.action_feedback(feedback=feedback)
                else:
                    activity.action_cancel()
            if outcome == "cancelled":
                order.message_post(body=Markup("<p>%s</p>") % feedback)


class RepairRevisionActivityLifecycle(models.Model):
    """Observa la confirmación exacta, conservando validación y emisión de la REV."""

    _inherit = "mc.rov.revision"

    def write(self, vals):
        to_confirm = (
            self.filtered(
                lambda revision: isinstance(revision.id, int) and revision.estado != "confirmado"
            )
            if (vals.get("estado") == "confirmado")
            else self.browse()
        )
        result = super().write(vals)
        for revision in to_confirm:
            self.env["mc.rov.repair.activity.automation"]._after_revision_confirmation(revision)
        return result


class MailActivityRepairLifecycle(models.Model):
    """Distingue las decisiones manuales del cierre automático de una etapa."""

    _inherit = "mail.activity"

    def _mc_repair_runs(self):
        real_ids = [key for key in self.ids if isinstance(key, int) and key > 0]
        runs = (
            self.env["mc.rov.repair.activity.run"]
            .sudo()
            .search(
                [
                    ("activity_id", "in", real_ids),
                ]
            )
            if real_ids
            else self.env["mc.rov.repair.activity.run"].sudo().browse()
        )
        if not runs:
            return runs
        self.check_access("write")
        orders = self.env["repair.order"].browse(runs.mapped("repair_id").ids)
        orders.check_access("read")
        # Mismo orden que la transición de orden: origen, seguimiento y actividad.
        self.env.cr.execute(
            SQL(
                "SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE",
                SQL.identifier(orders._table),
                tuple(sorted(orders.ids)),
            )
        )
        runs.invalidate_recordset(["outcome", "activity_id"])
        self.invalidate_recordset(["res_model", "res_model_id", "res_id", "active"])
        for run in runs:
            activity = run.activity_id
            if activity.res_model != "repair.order" or activity.res_id != run.repair_id.id:
                raise AccessError(_("La actividad ya no corresponde a su orden de origen."))
        return runs

    def _mc_record_manual_outcome(self, runs, outcome, reason):
        pending = runs.filtered(lambda run: run.outcome == "pending")
        self.env["mc.rov.repair.activity.automation"]._record_outcome(pending, outcome, reason)
        if outcome == "cancelled":
            for run in pending:
                # El permiso sobre actividad y lectura del origen ya se comprobaron.
                run.repair_id.message_post(body=Markup("<p>%s</p>") % reason)

    def _action_done(self, feedback=False, attachment_ids=None):
        with self.env.cr.savepoint():
            runs = self._mc_repair_runs()
            self._mc_record_manual_outcome(
                runs, "manual_done", feedback or _("Actividad marcada como hecha manualmente.")
            )
            return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def unlink(self):
        with self.env.cr.savepoint():
            runs = self._mc_repair_runs()
            self._mc_record_manual_outcome(
                runs, "cancelled", _("Actividad cancelada manualmente.")
            )
            result = super().unlink()
            runs.invalidate_recordset(["activity_id"])
            return result

    def write(self, values):
        source_fields = {"res_model", "res_model_id", "res_id"}
        if source_fields.intersection(values) or values.get("active") is False:
            with self.env.cr.savepoint():
                runs = self._mc_repair_runs()
                for run in runs:
                    activity = run.activity_id
                    model = values.get("res_model", activity.res_model)
                    if "res_model_id" in values:
                        model = self.env["ir.model"].browse(values["res_model_id"]).model
                    if (
                        model != "repair.order"
                        or values.get("res_id", activity.res_id) != run.repair_id.id
                    ):
                        raise ValidationError(
                            _("Una actividad seguida no puede cambiar de origen.")
                        )
                if values.get("active") is False:
                    self._mc_record_manual_outcome(
                        runs, "cancelled", _("Actividad archivada manualmente.")
                    )
                return super().write(values)
        return super().write(values)
