from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import SQL


class AcceptanceActivityLifecycle(models.AbstractModel):
    """Reconcilia evidencia explícita y conserva cada transición, incluso durante pausas."""

    _inherit = "mc.rov.acceptance.activity.automation"

    def _lock_acceptance_cycles(self, cycles, write=True):
        if not cycles:
            return
        lots = cycles.lot_id.with_user(self.env.uid)
        lots.check_access("read")
        if write:
            lots.check_access("write")
        if any(cycle.company_id.id not in self.env.companies.ids for cycle in cycles):
            raise AccessError(_("La aceptación pertenece a otra empresa activa."))
        self._capture(cycles.production_id)
        for table, ids in (("stock_lot", lots.ids), (cycles._table, cycles.ids)):
            if ids:
                self.env.cr.execute(
                    SQL(
                        "SELECT id FROM %s WHERE id IN %s ORDER BY id FOR UPDATE",
                        SQL.identifier(table),
                        tuple(sorted(ids)),
                    )
                )
        cycles.invalidate_recordset()

    def _open_cycles(self, lots):
        ids = [lot.id for lot in lots if isinstance(lot.id, int) and lot.id > 0]
        return (
            self.env["mc.rov.acceptance.activity.cycle"]
            .sudo()
            .search(
                [("lot_id", "in", ids), ("state", "=", "open")], order="production_id,lot_id,id"
            )
        )

    def _acceptance_runs(self, cycle, stage):
        return (
            self.env["mc.rov.acceptance.activity.run"]
            .sudo()
            .search(
                [("cycle_id", "=", cycle.id), ("stage", "=", stage), ("outcome", "=", "pending")]
            )
        )

    def _record_acceptance_outcome(self, runs, outcome, reason):
        if outcome not in ("business_done", "manual_done", "cancelled"):
            raise ValidationError(_("Resultado de seguimiento inválido."))
        for run in runs.filtered(lambda record: record.outcome == "pending"):
            run.write(
                {
                    "outcome": outcome,
                    "finished_at": fields.Datetime.now(),
                    "finished_by_id": self.env.uid,
                    "finish_reason": reason,
                    "current_deadline": run.activity_id.date_deadline or run.current_deadline,
                }
            )

    def _finish_acceptance_runs(self, runs, outcome, reason):
        for run in runs.filtered(lambda record: record.outcome == "pending"):
            activity = run.activity_id
            # El feedback nativo también pasa por los hooks de decisiones manuales.
            self._record_acceptance_outcome(run, outcome, reason)
            if activity and activity.active:
                if outcome == "business_done":
                    activity.action_feedback(feedback=reason)
                else:
                    activity.action_cancel()

    def _proof_status(self, revision):
        revision = self._readable_revision(revision)
        if not revision:
            return "none"
        if revision.estado != "confirmado":
            return "draft"
        if revision.resultado in ("aprobado", "aprobado_con_observaciones"):
            return "accepted"
        return "rejected" if revision.resultado == "rechazado" else "incomplete"

    def _reconcile_proof(self, cycle, stage, revision, instant):
        status = self._proof_status(revision)
        field = stage + "_status"
        previous = cycle[field]
        rejection = "rejection_" + stage
        if status in ("accepted", "rejected"):
            self._finish_acceptance_runs(
                self._acceptance_runs(cycle, stage),
                "business_done",
                _("Prueba seleccionada confirmada: %s", revision.display_name),
            )
        if status == "accepted":
            self._finish_acceptance_runs(
                self._acceptance_runs(cycle, rejection),
                "business_done",
                _("La prueba seleccionada confirma la resolución del rechazo."),
            )
        if status == "rejected" and previous != status:
            event_field = rejection + "_event"
            cycle[event_field] += 1
            if not self._acceptance_runs(cycle, rejection):
                self._start_stage(cycle, rejection, instant, occurrence=cycle[event_field])
        cycle[field] = status
        return status

    def _reconcile_fen_eligibility(self, cycle, statuses, instant):
        signature = (
            f"{cycle.rnd_id.id}:{cycle.trn_id.id}"
            if statuses == ("accepted", "accepted")
            else False
        )
        if signature == (cycle.fen_signature or False):
            return
        self._finish_acceptance_runs(
            self._acceptance_runs(cycle, "fen"),
            "cancelled",
            _("La selección ya no reúne las mismas pruebas aprobadas para emitir la ficha."),
        )
        cycle.fen_signature = signature
        if signature:
            cycle.fen_event += 1
            self._start_stage(cycle, "fen", instant, occurrence=cycle.fen_event)

    def _reconcile(self, lots):
        with self.env.cr.savepoint():
            cycles = self._open_cycles(lots)
            self._lock_acceptance_cycles(cycles)
            instant = fields.Datetime.now()
            for cycle in cycles.filtered(lambda record: record.state == "open"):
                statuses = (
                    self._reconcile_proof(cycle, "performance", cycle.rnd_id, instant),
                    self._reconcile_proof(cycle, "field", cycle.trn_id, instant),
                )
                self._reconcile_fen_eligibility(cycle, statuses, instant)

    def _after_evidence_selection(self, lot):
        result = super()._after_evidence_selection(lot)
        self._reconcile(lot)
        return result

    def _after_fen_emission(self, fichas):
        for ficha in fichas.with_user(self.env.uid):
            ficha.check_access("read")
            if ficha.estado != "emitida" or not ficha.pdf_attachment_id:
                continue
            cycles = self._open_cycles(ficha.lot_id)
            self._lock_acceptance_cycles(cycles)
            for cycle in cycles.filtered(lambda record: record.state == "open"):
                if cycle.rnd_id != ficha.rnd_id or cycle.trn_id != ficha.trn_id:
                    continue
                if (self._proof_status(cycle.rnd_id), self._proof_status(cycle.trn_id)) != (
                    "accepted",
                    "accepted",
                ):
                    continue
                self._finish_acceptance_runs(
                    self._acceptance_runs(cycle, "fen"),
                    "business_done",
                    _("Ficha de equipo nuevo emitida: %s", ficha.display_name),
                )
                cycle.write(
                    {"state": "done", "fen_id": ficha.id, "closed_at": fields.Datetime.now()}
                )


class AcceptanceRevisionLifecycle(models.Model):
    """Las confirmaciones y correcciones solo afectan ciclos que eligieron esta prueba."""

    _inherit = "mc.rov.revision"

    def _mc_acceptance_lots(self):
        ids = [record.id for record in self if isinstance(record.id, int) and record.id > 0]
        cycles = (
            self.env["mc.rov.acceptance.activity.cycle"]
            .sudo()
            .search([("state", "=", "open"), "|", ("rnd_id", "in", ids), ("trn_id", "in", ids)])
        )
        return self.env["stock.lot"].with_user(self.env.uid).browse(cycles.lot_id.ids)

    def write(self, values):
        with self.env.cr.savepoint():
            result = super().write(values)
            self.env["mc.rov.acceptance.activity.automation"]._reconcile(
                self._mc_acceptance_lots()
            )
            return result


class AcceptanceFichaLifecycle(models.Model):
    """La emisión efectiva con PDF, no guardar o previsualizar, termina la aceptación."""

    _inherit = "mc.rov.ficha.equipo.nuevo"

    def action_emitir(self):
        with self.env.cr.savepoint():
            result = super().action_emitir()
            self.env["mc.rov.acceptance.activity.automation"]._after_fen_emission(self)
            return result


class AcceptanceMailActivityLifecycle(models.Model):
    """Una decisión sobre el recordatorio deja intactos las pruebas y el PDF."""

    _inherit = "mail.activity"

    def _mc_acceptance_runs(self):
        ids = [record.id for record in self if isinstance(record.id, int) and record.id > 0]
        runs = (
            self.env["mc.rov.acceptance.activity.run"].sudo().search([("activity_id", "in", ids)])
        )
        if runs:
            self.with_user(self.env.uid).check_access("write")
            self.env["mc.rov.acceptance.activity.automation"]._lock_acceptance_cycles(
                runs.cycle_id, write=False
            )
            runs.invalidate_recordset(["outcome", "activity_id"])
            for run in runs:
                activity = run.activity_id
                if activity.res_model != "stock.lot" or activity.res_id != run.cycle_id.lot_id.id:
                    raise AccessError(_("La actividad ya no corresponde a su equipo de origen."))
        return runs

    def _mc_acceptance_manual_outcome(self, outcome, reason):
        runs = self._mc_acceptance_runs().filtered(lambda record: record.outcome == "pending")
        self.env["mc.rov.acceptance.activity.automation"]._record_acceptance_outcome(
            runs, outcome, reason
        )
        for lot in runs.cycle_id.lot_id.with_user(self.env.uid):
            lot.message_post(body=Markup("<p>%s</p>") % reason)
        return runs

    def _action_done(self, feedback=False, attachment_ids=None):
        with self.env.cr.savepoint():
            self._mc_acceptance_manual_outcome(
                "manual_done", feedback or _("Actividad marcada como hecha manualmente.")
            )
            return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def unlink(self):
        with self.env.cr.savepoint():
            runs = self._mc_acceptance_manual_outcome(
                "cancelled", _("Actividad cancelada manualmente.")
            )
            result = super().unlink()
            runs.invalidate_recordset(["activity_id"])
            return result

    def write(self, values):
        source_fields = {"res_model", "res_model_id", "res_id"}.intersection(values)
        if source_fields or values.get("active") is False:
            with self.env.cr.savepoint():
                for run in self._mc_acceptance_runs():
                    activity = run.activity_id
                    model = values.get("res_model", activity.res_model)
                    if "res_model_id" in values:
                        model = self.env["ir.model"].browse(values["res_model_id"]).model
                    if (
                        model != "stock.lot"
                        or values.get("res_id", activity.res_id) != run.cycle_id.lot_id.id
                    ):
                        raise ValidationError(
                            _("Una actividad de aceptación no puede cambiar de origen.")
                        )
                if values.get("active") is False:
                    self._mc_acceptance_manual_outcome(
                        "cancelled", _("Actividad archivada manualmente.")
                    )
                return super().write(values)
        return super().write(values)
