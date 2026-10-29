from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL

from .engineering_activity_automation import _ENGINEERING_INTERNAL


def _inside_native_event(env, ids):
    if env.context.get("_mc_engineering_creating") is _ENGINEERING_INTERNAL:
        return True
    if env.context.get("_mc_engineering_capture") is _ENGINEERING_INTERNAL:
        return True
    marker = env.context.get("_mc_engineering_event")
    return bool(
        isinstance(marker, tuple)
        and len(marker) == 2
        and marker[0] is _ENGINEERING_INTERNAL
        and ids
        and set(ids) <= set(marker[1])
    )


class EngineeringActivityLifecycle(models.AbstractModel):
    """Observa el flujo real y conserva su identidad incluso cuando se pausa el seguimiento."""

    _name = "mc.rov.engineering.activity.lifecycle"
    _description = "Ciclo de actividades de ingeniería"

    def _phase(self, eco):
        if not eco.active or eco.state == "done":
            return None
        return (
            "apply"
            if self.env["mc.rov.engineering.activity.automation"]._applicable(eco)
            else "prepare"
        )

    def _capture(self, ecos, access="write"):
        """Serializar aprobaciones parciales también, antes de que el ECO quede aplicable."""
        ids = sorted(
            {
                record.id
                for record in ecos
                if isinstance(record.id, int) and not isinstance(record.id, bool) and record.id > 0
            }
        )
        if not ids:
            return {}
        ecos = (
            self.env["mrp.eco"]
            .with_user(self.env.uid)
            .browse(ids)
            .with_context(_mc_engineering_capture=_ENGINEERING_INTERNAL)
        )
        ecos.check_access(access)
        names = ["active", "state", "stage_id", "kanban_state"]
        ecos.flush_recordset(names)
        cycles = (
            self.env["mc.rov.engineering.activity.cycle"].sudo().search([("eco_id", "in", ids)])
        )
        followed = set(cycles.eco_id.ids)
        service = self.env["mc.rov.engineering.activity.automation"]
        serialized = []
        for eco in ecos:
            phase = self._phase(eco)
            if eco.id in followed or (phase and service._configured_policy(eco, phase)):
                serialized.append(eco.id)
        self.env.cr.execute(
            SQL("SELECT id FROM mrp_eco WHERE id IN %s ORDER BY id FOR UPDATE", tuple(ids))
        )
        if serialized:
            # Un bloqueo solo no refresca REPEATABLE READ: forzar retry evita write skew
            # entre dos aprobadores distintos que todavía no habían terminado todos.
            self.env.cr.execute(
                SQL("UPDATE mrp_eco SET write_date = write_date WHERE id IN %s", tuple(serialized))
            )
        ecos.invalidate_recordset(names + ["allow_apply_change", "allow_change_stage"])
        cycles.invalidate_recordset()
        return {
            eco.id: {"active": bool(eco.active), "state": eco.state, "phase": self._phase(eco)}
            for eco in ecos
        }

    def _finish(self, run, outcome, reason, occurred_at):
        if run.outcome != "pending":
            return
        activity = run.activity_id.exists()
        deadline = activity.date_deadline or run.current_deadline or run.original_deadline
        run.write(
            {
                "outcome": outcome,
                "current_deadline": deadline,
                "finished_at": occurred_at,
                "finished_by_id": self.env.uid,
                "finish_reason": reason,
            }
        )
        run.cycle_id.write({"current_deadline": deadline})
        if activity and activity.active:
            activity.with_user(self.env.uid).action_feedback(feedback=reason)
        # Odoo conserva actividades archivadas: mantener su vínculo histórico.
        # Si la elimina, ondelete='set null' limpia la relación automáticamente.

    def _close_pending(self, cycle, snapshot, occurred_at):
        pending = (
            self.env["mc.rov.engineering.activity.run"]
            .sudo()
            .search([("cycle_id", "=", cycle.id), ("outcome", "=", "pending")])
        )
        for run in pending:
            if snapshot["state"] == "done":
                outcome, reason = "business_done", _("Cambio de ingeniería aplicado.")
            elif not snapshot["active"]:
                outcome, reason = "cancelled", _("Cambio de ingeniería archivado.")
            elif run.stage == "prepare" and snapshot["phase"] == "apply":
                outcome, reason = "business_done", _("Cambio de ingeniería listo para aplicar.")
            elif run.stage != snapshot["phase"]:
                outcome, reason = "withdrawn", _("El cambio ya no permite esta etapa.")
            else:
                continue
            self._finish(run, outcome, reason, occurred_at)

    def _sync(self, ecos, before, occurred_at):
        # El feedback puede escribir chatter en el ECO: forma parte del mismo evento,
        # antes de sellar la fase, y no debe abrir un segundo pendiente por reentrada.
        scoped = self.with_context(_mc_engineering_event=(_ENGINEERING_INTERNAL, tuple(ecos.ids)))
        return scoped._sync_events(ecos, before, occurred_at)

    def _sync_events(self, ecos, before, occurred_at):
        current = self._capture(ecos)
        cycles = self.env["mc.rov.engineering.activity.cycle"].sudo()
        service = self.env["mc.rov.engineering.activity.automation"]
        for eco in ecos.filtered(lambda record: record.id in current).sorted("id"):
            if eco.id not in before or eco.id not in current:
                continue
            snapshot = current[eco.id]
            phase = snapshot["phase"]
            observed = phase or "none"
            previous = before[eco.id]
            cycle = cycles.search([("eco_id", "=", eco.id)], limit=1)
            if cycle and cycle.company_id != eco.company_id:
                raise ValidationError(
                    _("El ciclo pertenece a otra empresa; conserve el cambio original.")
                )
            changed = (
                (previous is None and not cycle)
                or (previous is not None and previous["phase"] != phase)
                or (cycle and cycle.observed_stage != observed)
            )
            if not changed:
                continue
            if cycle:
                self._close_pending(cycle, snapshot, occurred_at)
                state = (
                    "done"
                    if snapshot["state"] == "done"
                    else "open" if snapshot["active"] else "cancel"
                )
                cycle.write(
                    {
                        "observed_stage": observed,
                        "event_sequence": cycle.event_sequence + 1,
                        "state": state,
                    }
                )
            if phase:
                service._start(eco, phase, occurred_at)


class EngineeringEcoEvents(models.Model):
    """Consolida escrituras internas de PLM sin cambiar sus permisos o resultados."""

    _inherit = "mrp.eco"

    @api.model_create_multi
    def create(self, vals_list):
        with self.env.cr.savepoint():
            scoped = self.with_context(_mc_engineering_creating=_ENGINEERING_INTERNAL)
            ecos = super(EngineeringEcoEvents, scoped).create(vals_list).with_env(self.env)
            self.env["mc.rov.engineering.activity.lifecycle"]._sync(
                ecos, {eco.id: None for eco in ecos}, fields.Datetime.now()
            )
            return ecos

    def _engineering_event_call(self, method, *args, **kwargs):
        if method not in ("write", "action_new_revision", "approve", "reject", "action_apply"):
            raise ValidationError(_("El evento nativo de ingeniería no es válido."))
        if _inside_native_event(self.env, self.ids):
            return getattr(super(), method)(*args, **kwargs)
        with self.env.cr.savepoint():
            lifecycle = self.env["mc.rov.engineering.activity.lifecycle"]
            before = lifecycle._capture(self)
            scoped = self.with_context(
                _mc_engineering_event=(_ENGINEERING_INTERNAL, tuple(self.ids))
            )
            result = getattr(super(EngineeringEcoEvents, scoped), method)(*args, **kwargs)
            lifecycle._sync(self, before, fields.Datetime.now())
            return result

    # El helper invoca super con el contexto del evento para consolidar escrituras anidadas.
    def write(self, values):  # pylint: disable=unknown-option-value,method-required-super
        with self.env.cr.savepoint():
            self.env["mc.rov.engineering.activity.automation"]._check_source_changes(self, values)
            return self._engineering_event_call("write", values)

    def unlink(self):
        self.check_access("unlink")
        self.env["mc.rov.engineering.activity.automation"]._check_source_deletion(self)
        return super().unlink()

    def action_new_revision(self):
        return self._engineering_event_call("action_new_revision")

    def approve(self):
        return self._engineering_event_call("approve")

    def reject(self):
        return self._engineering_event_call("reject")

    def action_apply(self):
        return self._engineering_event_call("action_apply")


class EngineeringApprovalEvents(models.Model):
    """Los cambios de aprobación por ORM también actualizan el seguimiento del ECO."""

    _inherit = "mrp.eco.approval"

    @api.model_create_multi
    def create(self, vals_list):
        ids = [values["eco_id"] for values in vals_list if values.get("eco_id")]
        if _inside_native_event(self.env, ids):
            return super().create(vals_list)
        with self.env.cr.savepoint():
            ecos = self.env["mrp.eco"].browse(ids)
            lifecycle = self.env["mc.rov.engineering.activity.lifecycle"]
            before = lifecycle._capture(ecos)
            result = super().create(vals_list)
            lifecycle._sync(ecos, before, fields.Datetime.now())
            return result

    def write(self, values):
        ecos = self.eco_id
        if _inside_native_event(self.env, ecos.ids):
            return super().write(values)
        with self.env.cr.savepoint():
            lifecycle = self.env["mc.rov.engineering.activity.lifecycle"]
            before = lifecycle._capture(ecos)
            result = super().write(values)
            lifecycle._sync(ecos, before, fields.Datetime.now())
            return result

    def unlink(self):
        ecos = self.eco_id
        if _inside_native_event(self.env, ecos.ids):
            return super().unlink()
        with self.env.cr.savepoint():
            lifecycle = self.env["mc.rov.engineering.activity.lifecycle"]
            before = lifecycle._capture(ecos)
            result = super().unlink()
            lifecycle._sync(ecos, before, fields.Datetime.now())
            return result


class EngineeringMailActivityLifecycle(models.Model):
    """Registra decisiones sobre tareas propias sin aprobar ni aplicar el ECO."""

    _inherit = "mail.activity"

    def _mc_engineering_runs(self):
        ids = [
            row.id
            for row in self
            if isinstance(row.id, int) and not isinstance(row.id, bool) and row.id > 0
        ]
        runs = (
            self.env["mc.rov.engineering.activity.run"].sudo().search([("activity_id", "in", ids)])
        )
        if not runs:
            return runs
        self.check_access("write")
        self.env["mc.rov.engineering.activity.lifecycle"]._capture(
            self.env["mrp.eco"].browse(runs.eco_id.ids), access="read"
        )
        runs.invalidate_recordset(["outcome", "activity_id"])
        self.invalidate_recordset(
            ["res_model", "res_model_id", "res_id", "activity_type_id", "active", "date_deadline"]
        )
        for run in runs:
            activity = run.activity_id
            if (
                activity.res_model != "mrp.eco"
                or activity.res_id != run.eco_id.id
                or activity.activity_type_id
                != self.env.ref("mc_rov.activity_type_engineering_" + run.stage)
            ):
                raise AccessError(_("La actividad ya no corresponde a su cambio de ingeniería."))
        return runs

    def _mc_engineering_manual_outcome(self, runs, outcome, reason):
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
                run.eco_id.with_user(self.env.uid).message_post(body=Markup("<p>%s</p>") % reason)

    def _action_done(self, feedback=False, attachment_ids=None):
        with self.env.cr.savepoint():
            self._mc_engineering_manual_outcome(
                self._mc_engineering_runs(),
                "manual_done",
                feedback or _("Actividad marcada como hecha manualmente."),
            )
            return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def unlink(self):
        with self.env.cr.savepoint():
            runs = self._mc_engineering_runs()
            self._mc_engineering_manual_outcome(
                runs, "cancelled", _("Actividad cancelada manualmente.")
            )
            result = super().unlink()
            runs.invalidate_recordset(["activity_id"])
            return result

    def write(self, values):
        relevant = {
            "res_model",
            "res_model_id",
            "res_id",
            "activity_type_id",
            "date_deadline",
            "active",
        }.intersection(values)
        if not relevant:
            return super().write(values)
        with self.env.cr.savepoint():
            runs = self._mc_engineering_runs()
            for run in runs:
                activity = run.activity_id
                model = values.get("res_model", activity.res_model)
                if "res_model_id" in values:
                    model = self.env["ir.model"].browse(values["res_model_id"]).model
                if (
                    model != "mrp.eco"
                    or values.get("res_id", activity.res_id) != run.eco_id.id
                    or values.get("activity_type_id", activity.activity_type_id.id)
                    != activity.activity_type_id.id
                ):
                    raise ValidationError(
                        _("Una actividad seguida no puede cambiar de origen ni tipo.")
                    )
            if values.get("active") is False:
                self._mc_engineering_manual_outcome(
                    runs, "cancelled", _("Actividad archivada manualmente.")
                )
            result = super().write(values)
            if "date_deadline" in values:
                for run in runs.filtered(lambda row: row.outcome == "pending"):
                    deadline = run.activity_id.date_deadline
                    if deadline:
                        run.write({"current_deadline": deadline})
                        run.cycle_id.write({"current_deadline": deadline})
            return result
