"""Aceptación por protocolo y liberación explícita son evidencias independientes."""

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError

from .production_kpi_event import append_event, lock_source, unit_design


class AcceptedUnitCapture(models.AbstractModel):
    """Una aprobación formal conjunta acredita aceptación, no despacho ni liberación."""

    _inherit = "mc.rov.new.acceptance"

    def _capture_native_result(self, attempt, revision, reason=None):
        result = super()._capture_native_result(attempt, revision, reason=reason)
        if attempt.state == "confirmed" and attempt.first_pass_snapshot == "passed":
            episode = attempt.episode_id
            append_event(
                revision,
                episode.lot_id,
                "accepted",
                f"group:{episode.production_group_id.id}:lot:{episode.lot_id.id}",
                {
                    "attempt_id": attempt.id,
                    **unit_design(revision, episode.lot_id, episode.company_id),
                },
                at=attempt.closed_at,
                production_id=episode.production_id.id,
                revision_id=revision.id,
            )
        return result


class UnitReleaseProduction(models.Model):
    """Supervisor valida evidencia real sin completar movimientos en nombre del usuario."""

    _inherit = "mrp.production"

    def _check_release_supervisor(self):
        self.ensure_one()
        if (
            self.env.user.share
            or self.env.user._is_public()
            or not self.env.user.has_group("mrp.group_mrp_manager")
        ):
            raise AccessError(_("La liberación requiere un Supervisor de Fabricación."))
        self.check_access("write")
        if self.company_id not in self.env.companies:
            raise AccessError(_("La fabricación no pertenece a una empresa autorizada."))

    def action_open_unit_release(self):
        self._check_release_supervisor()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mc.rov.unit.release.wizard",
            "name": _("Validar liberación de unidad"),
            "view_mode": "form",
            "target": "new",
            "context": {"default_production_id": self.id},
        }

    def _release_rov_unit(self, lot, fen, no_blocking_nc):
        self._check_release_supervisor()
        lock_source(self)
        lot.check_access("read")
        fen.check_access("read")
        if lot not in self.env["mc.rov.acceptance.activity.automation"]._produced_lots(self):
            raise UserError(_("Seleccione una serie realmente fabricada por esta orden."))
        if not no_blocking_nc:
            raise UserError(
                _("Supervisor debe revisar las no conformidades bloqueantes pendientes.")
            )
        if fen.lot_id != lot or fen.estado != "emitida" or not fen.pdf_attachment_id:
            raise UserError(_("Se requiere la Ficha de Equipo Nuevo emitida de esta unidad."))
        fen.pdf_attachment_id.check_access("read")
        for revision in (fen.rnd_id, fen.trn_id):
            revision.check_access("read")
            if revision.estado != "confirmado" or revision.resultado not in (
                "aprobado",
                "aprobado_con_observaciones",
            ):
                raise UserError(_("Las pruebas de la ficha deben seguir confirmadas y aprobadas."))
        accepted = (
            self.env["mc.rov.production.event"]
            .sudo()
            .search(
                [
                    ("kind", "=", "accepted"),
                    ("lot_id", "=", lot.id),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
        )
        if not accepted:
            raise UserError(_("Falta aceptación conjunta formal acreditada para esta unidad."))
        attempt = (
            self.env["mc.rov.new.acceptance.attempt"].sudo().browse(accepted.payload["attempt_id"])
        )
        if attempt.rnd_id.id != fen.rnd_id.id or attempt.trn_id.id != fen.trn_id.id:
            raise UserError(_("La ficha debe corresponder al protocolo conjunto acreditado."))
        append_event(
            self,
            lot,
            "released",
            accepted.identity,
            {
                "fen_id": fen.id,
                "pdf_attachment_id": fen.pdf_attachment_id.id,
                "attempt_id": attempt.id,
                "no_blocking_nc_reviewed": True,
                **unit_design(self, lot, self.company_id),
            },
            at=fields.Datetime.now(),
            production_id=self.id,
        )
        return True
