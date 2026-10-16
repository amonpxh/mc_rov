from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL


class ManufacturingActivityLifecycle(models.AbstractModel):
    """Distingue el resultado de fabricación de las decisiones sobre su pendiente."""

    _inherit = "mc.rov.manufacturing.activity.automation"

    def _followed_productions(self, productions):
        ids = [record.id for record in productions if isinstance(record.id, int) and record.id > 0]
        if not ids:
            return self.env["mrp.production"].with_user(self.env.uid).browse()
        runs = (
            self.env["mc.rov.manufacturing.activity.run"]
            .sudo()
            .search([("production_id", "in", ids), ("outcome", "=", "pending")])
        )
        # Una llamada nativa con sudo no debe convertir al operario en administrador.
        return (
            self.env["mrp.production"]
            .with_user(self.env.uid)
            .browse(sorted(set(runs.production_id.ids)))
        )

    def _lock_followed(self, productions):
        followed = self._followed_productions(productions)
        if followed:
            followed._mc_lock_manufacturing()
        return followed

    def _reconcile(self, productions):
        followed = self._lock_followed(productions)
        for production in followed:
            if production.state not in ("done", "cancel"):
                continue
            runs = (
                self.env["mc.rov.manufacturing.activity.run"]
                .sudo()
                .search([("production_id", "=", production.id), ("outcome", "=", "pending")])
            )
            for run in runs:
                self._finish_run(run)

    def _record_outcome(self, runs, outcome, reason):
        if outcome not in ("business_done", "manual_done", "cancelled"):
            raise ValidationError(_("Resultado de seguimiento inválido."))
        for run in runs.filtered(lambda record: record.outcome == "pending"):
            run.write(
                {
                    "outcome": outcome,
                    "finished_at": fields.Datetime.now(),
                    "finished_by_id": self.env.uid,
                    "finish_reason": reason,
                    "current_deadline": run.activity_id.date_deadline
                    or run.current_deadline
                    or run.original_deadline,
                }
            )

    def _finish_run(self, run):
        production = run.production_id.with_user(self.env.uid)
        production._mc_lock_manufacturing()
        if production.state not in ("done", "cancel"):
            raise ValidationError(_("La fabricación todavía no está terminada ni cancelada."))
        with self.env.cr.savepoint():
            activity = run.activity_id
            if activity:
                activity._mc_manufacturing_runs()
            run.invalidate_recordset(["outcome"])
            if run.outcome != "pending":
                return
            done = production.state == "done"
            reason = _("Fabricación terminada.") if done else _("Fabricación cancelada.")
            self._record_outcome(run, "business_done" if done else "cancelled", reason)
            if activity and activity.active:
                if done:
                    activity.action_feedback(feedback=reason)
                else:
                    activity.action_cancel()
            if not done:
                production.message_post(body=Markup("<p>%s</p>") % reason)


class ManufacturingProductionLifecycle(models.Model):
    """Observa las acciones efectivas conservando asistentes y retornos nativos."""

    _inherit = "mrp.production"

    def write(self, values):
        result = super().write(values)
        if "state" in values:
            self.env["mc.rov.manufacturing.activity.automation"]._reconcile(self)
        return result

    def button_mark_done(self):
        service = self.env["mc.rov.manufacturing.activity.automation"]
        service._lock_followed(self)
        result = super().button_mark_done()
        service._reconcile(self)
        return result

    def _action_cancel(self):
        service = self.env["mc.rov.manufacturing.activity.automation"]
        service._lock_followed(self)
        result = super()._action_cancel()
        service._reconcile(self)
        return result

    def _post_inventory(self, *args, **kwargs):
        service = self.env["mc.rov.manufacturing.activity.automation"]
        service._lock_followed(self)
        result = super()._post_inventory(*args, **kwargs)
        service._reconcile(self)
        return result


class ManufacturingStockMoveLifecycle(models.Model):
    """Los movimientos pueden terminar una MO sin escribir directamente su estado."""

    _inherit = "stock.move"

    def _mc_manufacturing_origins(self):
        return self.production_id | self.raw_material_production_id

    def _action_done(self, *args, **kwargs):
        service = self.env["mc.rov.manufacturing.activity.automation"]
        productions = self._mc_manufacturing_origins()
        service._lock_followed(productions)
        result = super()._action_done(*args, **kwargs)
        service._reconcile(productions | result._mc_manufacturing_origins())
        return result

    def _action_cancel(self, *args, **kwargs):
        service = self.env["mc.rov.manufacturing.activity.automation"]
        productions = self._mc_manufacturing_origins()
        service._lock_followed(productions)
        result = super()._action_cancel(*args, **kwargs)
        service._reconcile(productions | self._mc_manufacturing_origins())
        return result


class ManufacturingMailActivityLifecycle(models.Model):
    """Una decisión manual se audita sin terminar o cancelar la orden de fabricación."""

    _inherit = "mail.activity"

    def _mc_manufacturing_runs(self):
        ids = [record.id for record in self if isinstance(record.id, int) and record.id > 0]
        runs = (
            self.env["mc.rov.manufacturing.activity.run"]
            .sudo()
            .search([("activity_id", "in", ids)])
        )
        if not runs:
            return runs
        self.check_access("write")
        productions = self.env["mrp.production"].browse(runs.production_id.ids)
        productions.check_access("read")
        # Mismo orden de bloqueo que las acciones de negocio, incluso en un lote mixto.
        self.env.cr.execute(
            SQL(
                "SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE",
                SQL.identifier(productions._table),
                tuple(sorted(productions.ids)),
            )
        )
        runs.invalidate_recordset(["outcome", "activity_id"])
        self.invalidate_recordset(["res_model", "res_model_id", "res_id", "active"])
        for run in runs:
            if (
                run.activity_id.res_model != "mrp.production"
                or run.activity_id.res_id != run.production_id.id
            ):
                raise AccessError(_("La actividad ya no corresponde a su fabricación de origen."))
        return runs

    def _mc_manufacturing_manual_outcome(self, runs, outcome, reason):
        pending = runs.filtered(lambda record: record.outcome == "pending")
        self.env["mc.rov.manufacturing.activity.automation"]._record_outcome(
            pending, outcome, reason
        )
        if outcome == "cancelled":
            for run in pending:
                run.production_id.message_post(body=Markup("<p>%s</p>") % reason)

    def _action_done(self, feedback=False, attachment_ids=None):
        with self.env.cr.savepoint():
            self._mc_manufacturing_manual_outcome(
                self._mc_manufacturing_runs(),
                "manual_done",
                feedback or _("Actividad marcada como hecha manualmente."),
            )
            return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def unlink(self):
        with self.env.cr.savepoint():
            runs = self._mc_manufacturing_runs()
            self._mc_manufacturing_manual_outcome(
                runs, "cancelled", _("Actividad cancelada manualmente.")
            )
            result = super().unlink()
            runs.invalidate_recordset(["activity_id"])
            return result

    def write(self, values):
        if {"res_model", "res_model_id", "res_id"}.intersection(values) or values.get(
            "active"
        ) is False:
            with self.env.cr.savepoint():
                runs = self._mc_manufacturing_runs()
                for run in runs:
                    activity = run.activity_id
                    model = values.get("res_model", activity.res_model)
                    if "res_model_id" in values:
                        model = self.env["ir.model"].browse(values["res_model_id"]).model
                    if (
                        model != "mrp.production"
                        or values.get("res_id", activity.res_id) != run.production_id.id
                    ):
                        raise ValidationError(
                            _("Una actividad seguida no puede cambiar de origen.")
                        )
                if values.get("active") is False:
                    self._mc_manufacturing_manual_outcome(
                        runs, "cancelled", _("Actividad archivada manualmente.")
                    )
                return super().write(values)
        return super().write(values)
