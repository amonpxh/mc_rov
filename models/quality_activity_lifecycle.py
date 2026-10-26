from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL


class QualityActivityLifecycle(models.AbstractModel):
    """Eventos de alerta y decisiones de seguimiento conservan historias distintas."""

    _name = "mc.rov.quality.activity.lifecycle"
    _description = "Ciclo de actividades de Calidad"

    def _lock_stages(self, ids):
        ids = sorted(set(ids))
        if ids:
            self.env["quality.alert.stage"].flush_model(["done"])
            self.env.cr.execute(
                SQL(
                    "SELECT id FROM quality_alert_stage WHERE id IN %s ORDER BY id FOR UPDATE",
                    tuple(ids),
                )
            )
            self.env["quality.alert.stage"].browse(ids).invalidate_recordset(["done"])

    def _capture(self, alerts, stage_ids=(), access="write"):
        """Etapas antes de alertas: mismo orden en eventos, cierres y acciones manuales."""
        ids = sorted(
            {record.id for record in alerts if isinstance(record.id, int) and record.id > 0}
        )
        if not ids:
            return {}
        alerts = self.env["quality.alert"].with_user(self.env.uid).browse(ids)
        alerts.check_access(access)
        self._lock_stages(alerts.stage_id.ids + list(stage_ids))
        alerts.flush_recordset(["stage_id"])
        self.env.cr.execute(
            SQL("SELECT id FROM quality_alert WHERE id IN %s ORDER BY id FOR UPDATE", tuple(ids))
        )
        alerts.invalidate_recordset(["stage_id"])
        alerts.stage_id.invalidate_recordset(["done"])
        return {record.id: bool(record.stage_id.done) for record in alerts}

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

    def _reconcile(self, alerts, previously_closed, occurred_at):
        """Solo crear al nacer abierta o reabrir; las pausas no impiden cerrar."""
        alerts = alerts.with_user(self.env.uid)
        self._capture(alerts)
        for alert in alerts.filtered(lambda record: record.id in previously_closed):
            if alert.stage_id.done:
                runs = (
                    self.env["mc.rov.quality.activity.run"]
                    .sudo()
                    .search([("alert_id", "=", alert.id), ("outcome", "=", "pending")])
                )
                for run in runs:
                    reason = _("Alerta de Calidad resuelta.")
                    activity = run.activity_id
                    self._record_outcome(run, "business_done", reason)
                    if activity and activity.active:
                        activity.with_user(self.env.uid).action_feedback(feedback=reason)
            elif previously_closed[alert.id] is not False:
                self.env["mc.rov.quality.activity.automation"]._start(
                    alert, occurred_at, reopening=previously_closed[alert.id] is True
                )


class QualityAlertActivityLifecycle(models.Model):
    """Observa eventos reales sin exigir nuevos campos para resolver la alerta."""

    _inherit = "quality.alert"

    @api.model_create_multi
    def create(self, vals_list):
        with self.env.cr.savepoint():
            alerts = super().create(vals_list)
            self.env["mc.rov.quality.activity.lifecycle"]._reconcile(
                alerts, {alert.id: None for alert in alerts}, fields.Datetime.now()
            )
            return alerts

    def write(self, values):
        if "stage_id" not in values:
            return super().write(values)
        lifecycle = self.env["mc.rov.quality.activity.lifecycle"]
        with self.env.cr.savepoint():
            before = lifecycle._capture(self, [values["stage_id"]] if values["stage_id"] else [])
            result = super().write(values)
            lifecycle._reconcile(self, before, fields.Datetime.now())
            return result


class QualityAlertStageActivityLifecycle(models.Model):
    """Cambiar done en una etapa compartida afecta a todas sus alertas actuales."""

    _inherit = "quality.alert.stage"

    def write(self, values):
        if "done" not in values:
            return super().write(values)
        lifecycle = self.env["mc.rov.quality.activity.lifecycle"]
        with self.env.cr.savepoint():
            ids = [record.id for record in self if isinstance(record.id, int) and record.id > 0]
            lifecycle._lock_stages(ids)
            # Descubrir todas no concede acceso: _capture exige escritura del actor original.
            alerts = self.env["quality.alert"].sudo().search([("stage_id", "in", ids)])
            alerts = alerts.with_user(self.env.uid)
            before = lifecycle._capture(alerts)
            result = super().write(values)
            lifecycle._reconcile(alerts, before, fields.Datetime.now())
            return result


class QualityMailActivityLifecycle(models.Model):
    """Hecho, cancelación y archivo manuales no resuelven la alerta de origen."""

    _inherit = "mail.activity"

    def _mc_quality_runs(self):
        ids = [record.id for record in self if isinstance(record.id, int) and record.id > 0]
        runs = self.env["mc.rov.quality.activity.run"].sudo().search([("activity_id", "in", ids)])
        if not runs:
            return runs
        self.check_access("write")
        alerts = self.env["quality.alert"].browse(runs.alert_id.ids)
        self.env["mc.rov.quality.activity.lifecycle"]._capture(alerts, access="read")
        runs.invalidate_recordset(["outcome", "activity_id"])
        self.invalidate_recordset(["res_model", "res_model_id", "res_id", "active"])
        for run in runs:
            if (
                run.activity_id.res_model != "quality.alert"
                or run.activity_id.res_id != run.alert_id.id
            ):
                raise AccessError(_("La actividad ya no corresponde a su alerta de origen."))
        return runs

    def _mc_quality_manual_outcome(self, runs, outcome, reason):
        pending = runs.filtered(lambda record: record.outcome == "pending")
        self.env["mc.rov.quality.activity.lifecycle"]._record_outcome(pending, outcome, reason)
        if outcome == "cancelled":
            for run in pending:
                run.alert_id.with_user(self.env.uid).message_post(
                    body=Markup("<p>%s</p>") % reason
                )

    def _action_done(self, feedback=False, attachment_ids=None):
        with self.env.cr.savepoint():
            self._mc_quality_manual_outcome(
                self._mc_quality_runs(),
                "manual_done",
                feedback or _("Actividad marcada como hecha manualmente."),
            )
            return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def unlink(self):
        with self.env.cr.savepoint():
            runs = self._mc_quality_runs()
            self._mc_quality_manual_outcome(
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
                runs = self._mc_quality_runs()
                for run in runs:
                    activity = run.activity_id
                    model = values.get("res_model", activity.res_model)
                    if "res_model_id" in values:
                        model = self.env["ir.model"].browse(values["res_model_id"]).model
                    if (
                        model != "quality.alert"
                        or values.get("res_id", activity.res_id) != run.alert_id.id
                    ):
                        raise ValidationError(
                            _("Una actividad seguida no puede cambiar de origen.")
                        )
                if values.get("active") is False:
                    self._mc_quality_manual_outcome(
                        runs, "cancelled", _("Actividad archivada manualmente.")
                    )
                return super().write(values)
        return super().write(values)
