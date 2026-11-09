"""Seal joint acceptance at real native outcomes, preserving the first failed presentation."""

# Keep outcome capture separate from the previously validated identity/start boundary.
# pylint: disable=unknown-option-value,consider-merging-classes-inherited

import copy
import hashlib
import json

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError

from .new_acceptance_start import _CAPTURE, _CAPTURE_KEY


_NATIVE = object()
_NATIVE_KEY = "mc_new_acceptance_native"


class NewAcceptanceResult(models.Model):
    """Closed outcomes remain private and independent of later source corrections."""

    _inherit = "mc.rov.new.acceptance.attempt"

    closed_at = fields.Datetime()
    finished_by_id = fields.Many2one("res.users", ondelete="restrict")
    first_pass_snapshot = fields.Selection(
        [("unknown", "Sin determinar"), ("passed", "Aprobado"), ("failed", "Fallido")],
        default="unknown",
        required=True,
    )


class NewAcceptanceResultService(models.AbstractModel):
    """Append a single source result atomically with its native confirmation."""

    _inherit = "mc.rov.new.acceptance"

    def _capture_native_result(self, attempt, revision, reason=None):
        # A single atomic evidence assembly keeps the captured inputs visible together.
        # pylint: disable=too-many-locals
        revision.ensure_one()
        attempt.ensure_one()
        # Callers hold manufacturing/serial/revision locks before inspecting history.
        if attempt.state != "pending":
            return
        phase = "performance" if revision.id == attempt.rnd_id.id else "field"
        if revision.id not in (attempt.rnd_id.id, attempt.trn_id.id):
            raise UserError(_("La prueba no pertenece al intento formal."))
        snapshot = copy.deepcopy(attempt.requirements_snapshot)
        results = snapshot.setdefault("results", {})
        if phase in results:
            return
        configuration = snapshot["configuration"]
        digest = hashlib.sha256(
            json.dumps(configuration, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        if digest != attempt.configuration_digest:
            raise UserError(_("El alcance histórico no supera su verificación de integridad."))
        revision._validate_captured_acceptance_scope(configuration[phase])
        if not reason and revision.estado != "confirmado":
            raise UserError(_("Confirme la prueba mediante su acción nativa."))
        evidence = revision._acceptance_evidence()
        evidence["product_id"] = attempt.episode_id.product_id.id
        now = fields.Datetime.now()
        verdict = "rechazado" if reason else revision.resultado
        correction = revision.mc_correction_required or "unknown"
        retest = revision.mc_retest_required or "unknown"
        results[phase] = {
            "revision_id": revision.id,
            "actor_id": self.env.uid,
            "captured_at": fields.Datetime.to_string(now),
            "verdict": verdict,
            "correction": correction,
            "retest": retest,
            "reason": reason or None,
            "evidence": evidence,
        }
        failed = any(
            row["verdict"] == "rechazado" or row["correction"] == "yes" or row["retest"] == "yes"
            for row in results.values()
        )
        passed = set(results) == {"performance", "field"} and all(
            row["verdict"] in ("aprobado", "aprobado_con_observaciones")
            for row in results.values()
        )
        values = {"requirements_snapshot": snapshot}
        if failed or passed:
            known_pass = passed and all(
                row["correction"] == row["retest"] == "no" for row in results.values()
            )
            values.update(
                state="failed" if failed else "confirmed",
                closed_at=now,
                finished_by_id=self.env.uid,
                first_pass_snapshot="failed" if failed else "passed" if known_pass else "unknown",
            )
        attempt.with_context(**{_CAPTURE_KEY: _CAPTURE}).write(values)


class NewAcceptanceResultRevision(models.Model):
    """Native source actions control results; generic writes cannot impersonate confirmation."""

    _inherit = "mc.rov.revision"

    def _new_result_access(self, attempts):
        if self.env.user.share or self.env.user._is_public():
            raise AccessError(_("La aceptación requiere una cuenta interna."))
        self.check_access("read")
        self.check_access("write")
        for episode in attempts.episode_id:
            for record in (episode.production_id, episode.lot_id, episode.product_id):
                self.env[record._name].browse(record.ids).check_access("read")
            if episode.company_id.id not in self.env.companies.ids:
                raise AccessError(_("La unidad no pertenece a una empresa activa autorizada."))

    def action_confirmar(self):
        # The savepoint includes native side effects, so failed capture cannot leave
        # a confirmed source without its formal evidence, even if an RPC catches errors.
        with self.env.cr.savepoint():
            attempts = self._new_acceptance_followed()
            if attempts:
                self._new_result_access(attempts)
            trusted = self.with_context(**{_NATIVE_KEY: _NATIVE})
            result = super(NewAcceptanceResultRevision, trusted).action_confirmar()
            service = self.env["mc.rov.new.acceptance"]
            for revision in self:
                for attempt in attempts.filtered(
                    lambda row, source=revision: source.id in (row.rnd_id.id, row.trn_id.id)
                ):
                    service._capture_native_result(attempt, revision)
            return result

    def action_abort_new_acceptance(self, reason):
        """Record an evidenced failed presentation without confirming an incomplete test."""
        self.ensure_one()
        with self.env.cr.savepoint():
            attempts = self._new_acceptance_followed()
            self._new_result_access(attempts)
            pending = attempts.filtered(lambda row: row.state == "pending")
            if len(pending) != 1 or not isinstance(reason, str) or not reason.strip():
                raise UserError(_("Se requiere un intento pendiente y un motivo de fallo real."))
            phase = "performance" if self.id == pending.rnd_id.id else "field"
            if phase in pending.requirements_snapshot.get("results", {}):
                raise UserError(_("La prueba ya tiene su resultado formal registrado."))
            failure = (
                any(row.resultado == "no_ok" for row in self.chequeo_ids)
                or self.funcionamiento_continuo_resultado == "con_problemas"
                or any(row.severidad == "impide_operar" for row in self.hallazgo_ids)
            )
            if not failure:
                raise UserError(_("Se requiere evidencia de fallo real para interrumpir."))
            self.env["mc.rov.new.acceptance"]._capture_native_result(pending, self, reason.strip())
        return True

    def write(self, values):
        if "estado" in values:
            attempts = self._new_acceptance_followed()
            for revision in self:
                for attempt in attempts.filtered(
                    lambda row, source=revision: row.state == "pending"
                    and source.id in (row.rnd_id.id, row.trn_id.id)
                ):
                    phase = "performance" if revision.id == attempt.rnd_id.id else "field"
                    captured = phase in attempt.requirements_snapshot.get("results", {})
                    if (
                        values["estado"] == "confirmado"
                        and self.env.context.get(_NATIVE_KEY) is not _NATIVE
                    ):
                        raise UserError(
                            _("Confirme la prueba mediante su acción nativa validada.")
                        )
                    if captured and values["estado"] != "confirmado":
                        raise UserError(
                            _(
                                "La otra prueba sigue pendiente; el resultado capturado se conserva."
                            )
                        )
        return super().write(values)
