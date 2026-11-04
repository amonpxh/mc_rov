"""Explicit final repair acceptance, independent of diagnostic confirmation."""

import hashlib
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .repair_acceptance_history import _CAPTURE, _CAPTURE_KEY


# Only revision-defined scalar evidence; inherited mail/account fields are excluded.
_CAPTURE_SOURCE_FIELDS = (
    "name",
    "tipo",
    "fecha",
    "estado",
    "documento_emitido",
    "horas_operacion",
    "es_un_rov",
    "luces_internas",
    "luces_externas",
    "luces_total",
    "luces_ficha",
    "luces_difieren",
    "version_software_ficha",
    "version_ardusub_ficha",
    "version_controlador_ficha",
    "software_difiere",
    "software_diferencias",
    "version_software_instalada",
    "version_ardusub_instalada",
    "version_controlador_instalada",
    "umbilical",
    "largo",
    "umbilical_serie",
    "umbilical_difiere",
    "umbilical_ficha",
    "largo_ficha",
    "diametro_ficha",
    "alimentacion",
    "tension_salida",
    "funcionamiento_continuo_duracion",
    "funcionamiento_continuo_resultado",
    "subida",
    "bajada",
    "modelo_fuente",
    "duracion",
    "condiciones_notas",
    "presion_bar",
    "presion_tiempo",
    "fuga_corriente",
    "consumo_reposo",
    "consumo_carga",
    "limitacion_pilot_gain",
    "ganancia_luz",
    "temperatura_interior",
    "temperatura_exterior",
    "motivo",
    "lugar",
    "profundidad",
    "velocidad_corriente",
    "numero_en_visita",
    "resultado",
)


class RepairAcceptanceRevision(models.Model):
    """Keep final attempts durable while leaving the native diagnostic path unchanged."""

    _inherit = "mc.rov.revision"

    mc_acceptance_purpose = fields.Selection(
        [("unset", "Sin clasificar"), ("diagnostic", "Diagnóstico"), ("final", "Revisión final")],
        default="unset",
        required=True,
        copy=False,
    )
    mc_correction_required = fields.Selection(
        [("unknown", "Por revisar"), ("no", "No"), ("yes", "Sí")],
        default="unknown",
        copy=False,
    )
    mc_retest_required = fields.Selection(
        [("unknown", "Por revisar"), ("no", "No"), ("yes", "Sí")],
        default="unknown",
        copy=False,
    )

    def _acceptance_source_access(self, access="write"):
        self.ensure_one()
        if not isinstance(self.id, int) or isinstance(self.id, bool) or self.id <= 0:
            raise UserError(_("Guarde la revisión antes de registrar aceptación final."))
        if self.env.user._is_public() or self.env.user.share:
            raise AccessError(_("La aceptación final requiere una cuenta interna."))
        self.check_access(access)
        repair = self.repair_id
        if not repair or not self.lot_id or self.tipo != "reparacion":
            raise UserError(_("La revisión final requiere orden de reparación y serie."))
        repair.check_access(access)
        self.lot_id.check_access("read")
        if repair.company_id.id not in self.env.companies.ids:
            raise AccessError(_("La reparación no pertenece a una empresa autorizada."))
        if repair.lot_id != self.lot_id or repair.product_id != self.lot_id.product_id:
            raise UserError(_("La serie de la revisión debe coincidir con la reparación."))
        return repair

    def _acceptance_attempts(self):
        return (
            self.env["mc.rov.repair.acceptance.attempt"]
            .sudo()
            .search(
                [
                    ("repair_id", "=", self.repair_id.id),
                    ("lot_id", "=", self.lot_id.id),
                    ("company_id", "=", self.repair_id.company_id.id),
                ],
                order="ordinal",
            )
        )

    def _get_repair_acceptance_attempts(self, repair):
        self.ensure_one()
        if not self.env.user.has_group("mc_rov.group_work_assignment_team"):
            raise AccessError(_("Se requiere consulta del trabajo del equipo."))
        if self._acceptance_source_access("read") != repair:
            raise AccessError(_("La reparación no corresponde a esta revisión."))
        attempts = self._acceptance_attempts()
        self.env["mc.rov.revision"].browse(attempts.revision_id.ids).check_access("read")
        return attempts

    def _lock_acceptance_episode(self):
        repair = self._acceptance_source_access()
        self.env.cr.execute(
            "UPDATE repair_order SET write_date=write_date WHERE id=%s RETURNING id", [repair.id]
        )
        self.invalidate_recordset()
        return repair

    def _acceptance_configuration(self):
        self.ensure_one()
        checks = []
        for line in self.chequeo_ids.sorted("id"):
            check = line.chequeo_id
            checks.append(
                {
                    "line_id": line.id,
                    "check_id": check.id,
                    "name": check.name,
                    "sequence": check.sequence,
                    "section": check.seccion,
                    "per_component": check.por_componente,
                    "repair": check.aplica_reparacion,
                }
            )
        configuration = {
            "schema": 1,
            "type": self.tipo,
            "checks": checks,
            "inspection_ids": sorted(self.inspeccion_ids.ids),
        }
        digest = hashlib.sha256(
            json.dumps(configuration, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        return configuration, digest

    def _acceptance_evidence(self):
        self.ensure_one()
        scalar_types = {
            "boolean",
            "integer",
            "float",
            "char",
            "text",
            "date",
            "datetime",
            "selection",
        }
        scalar_names = [
            name
            for name in _CAPTURE_SOURCE_FIELDS
            if name in self._fields
            and self._fields[name].store
            and self._fields[name].type in scalar_types
            and not self._fields[name].groups
        ]
        values = self.read(scalar_names, load=None)[0]
        # Freeze Date/Datetime as their original representations, without inventing a time.
        values = json.loads(json.dumps(values, default=str))
        return {
            "source_values": values,
            "source_types": {name: self._fields[name].type for name in scalar_names},
            "customer_id": self.repair_id.partner_id.id or None,
            "product_id": self.repair_id.product_id.id or None,
            "checks": self.chequeo_ids.read(["chequeo_id", "resultado"], load=None),
            "inspections": self.inspeccion_ids.read(["estado_sello"], load=None),
            "continuous": self.funcionamiento_continuo_resultado,
            "continuous_duration": self.funcionamiento_continuo_duracion,
            "findings": self.hallazgo_ids.read(["severidad"], load=None),
        }

    def _pending_acceptance_attempt(self):
        pending = self._acceptance_attempts().filtered(lambda row: row.state == "pending")
        if len(pending) != 1 or pending.revision_id != self:
            raise UserError(_("Inicie el intento final de esta revisión antes de registrarlo."))
        return pending

    def action_start_final_acceptance(self):
        self.ensure_one()
        repair = self._lock_acceptance_episode()
        if self.mc_acceptance_purpose != "final" or self.estado != "borrador":
            raise UserError(_("Solo una revisión final en borrador puede iniciar un intento."))
        attempts = self._acceptance_attempts()
        pending = attempts.filtered(lambda row: row.state == "pending")
        if pending:
            if pending.revision_id != self:
                raise UserError(
                    _("Otra revisión tiene un intento pendiente para esta reparación.")
                )
            return True
        configuration, digest = self._acceptance_configuration()
        self.env["mc.rov.repair.acceptance.attempt"].sudo().with_context(
            **{_CAPTURE_KEY: _CAPTURE}
        ).create(
            {
                "company_id": repair.company_id.id,
                "repair_id": repair.id,
                "lot_id": self.lot_id.id,
                "revision_id": self.id,
                "ordinal": max(attempts.mapped("ordinal"), default=0) + 1,
                "started_at": fields.Datetime.now(),
                "actor_id": self.env.uid,
                "responsable_id": self.responsable_id.id,
                "requirements_snapshot": {"configuration": configuration},
                "configuration_digest": digest,
            }
        )
        return True

    def _seal_acceptance_attempt(self, attempt, state, verdict, reason=False):
        configuration, digest = self._acceptance_configuration()
        if digest != attempt.configuration_digest:
            raise UserError(_("Los requisitos cambiaron durante el intento; revise el protocolo."))
        now = fields.Datetime.now()
        attempt.with_context(**{_CAPTURE_KEY: _CAPTURE}).write(
            {
                "state": state,
                "closed_at": now,
                "confirmed_at": now if state == "confirmed" else False,
                "actor_id": self.env.uid,
                "responsable_id": self.responsable_id.id,
                "verdict_snapshot": verdict,
                "reason": reason,
                "correction_snapshot": self.mc_correction_required,
                "retest_snapshot": self.mc_retest_required,
                "requirements_snapshot": {
                    "configuration": configuration,
                    "evidence": self._acceptance_evidence(),
                },
            }
        )

    def action_abort_final_acceptance(self, reason):
        self.ensure_one()
        self._lock_acceptance_episode()
        if (
            self.mc_acceptance_purpose != "final"
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise UserError(_("La interrupción de una revisión final requiere motivo."))
        attempts = self._acceptance_attempts()
        if not attempts.filtered(lambda row: row.state == "pending"):
            if attempts and attempts[-1].state == "aborted" and attempts[-1].revision_id == self:
                return True
        attempt = self._pending_acceptance_attempt()
        real_failure = (
            any(line.resultado == "no_ok" for line in self.chequeo_ids)
            or self.funcionamiento_continuo_resultado == "con_problemas"
            or any(row.severidad == "impide_operar" for row in self.hallazgo_ids)
        )
        if not real_failure:
            raise UserError(_("Se requiere evidencia de fallo real para interrumpir el intento."))
        self._seal_acceptance_attempt(attempt, "aborted", "rechazado", reason.strip())
        return True

    def action_confirmar(self):
        result = None
        finals = self.filtered(lambda row: row.mc_acceptance_purpose == "final")
        for revision in finals.sorted(lambda row: (row.repair_id.id, row.id)):
            revision._lock_acceptance_episode()
        # Lock final episodes deterministically, but preserve the native confirmation order.
        for revision in self:
            if revision.mc_acceptance_purpose != "final":
                result = super(RepairAcceptanceRevision, revision).action_confirmar()
                continue
            if revision.estado == "confirmado":
                continue
            attempt = revision._pending_acceptance_attempt()
            trusted = revision.with_context(**{_CAPTURE_KEY: _CAPTURE})
            result = super(RepairAcceptanceRevision, trusted).action_confirmar()
            revision._seal_acceptance_attempt(attempt, "confirmed", revision.resultado)
        return result

    def _lock_final_write_sources(self, values):
        if not {
            "lot_id",
            "repair_id",
            "tipo",
            "mc_acceptance_purpose",
            "mc_correction_required",
            "mc_retest_required",
            "estado",
        }.intersection(values):
            return
        finals = self.filtered(
            lambda row: row.mc_acceptance_purpose == "final"
            or values.get("mc_acceptance_purpose") == "final"
        )
        if not finals:
            return
        if self.env.user._is_public() or self.env.user.share:
            raise AccessError(_("La aceptación final requiere una cuenta interna."))
        repairs = finals.mapped("repair_id")
        if values.get("repair_id"):
            repairs |= self.env["repair.order"].browse(values["repair_id"])
        for repair in repairs.sorted("id"):
            repair.check_access("write")
            if repair.company_id.id not in self.env.companies.ids:
                raise AccessError(_("La reparación no pertenece a una empresa autorizada."))
            self.env.cr.execute(
                "UPDATE repair_order SET write_date=write_date WHERE id=%s", [repair.id]
            )
        finals.invalidate_recordset()

    def write(self, values):
        self.check_access("write")
        self._lock_final_write_sources(values)
        identity = {"lot_id", "repair_id", "tipo", "mc_acceptance_purpose"}
        classification = {"mc_correction_required", "mc_retest_required"}
        for revision in self:
            if values.get("estado") == "confirmado" and (
                values.get("mc_acceptance_purpose", revision.mc_acceptance_purpose) == "final"
                and self.env.context.get(_CAPTURE_KEY) is not _CAPTURE
            ):
                raise UserError(_("Confirme la revisión final mediante su acción validada."))
            relevant = identity.intersection(values)
            final_source = (
                revision.mc_acceptance_purpose == "final"
                or values.get("mc_acceptance_purpose") == "final"
            )
            if relevant and revision.repair_id and final_source:
                revision.repair_id.check_access("write")
                if revision.repair_id.company_id.id not in self.env.companies.ids:
                    raise AccessError(_("La reparación no pertenece a una empresa autorizada."))
            followed = (
                relevant
                and final_source
                and revision.repair_id
                and revision._acceptance_attempts().filtered(
                    lambda row, source=revision: row.revision_id == source
                )
            )
            if followed:
                for name in relevant:
                    current = revision[name]
                    current = current.id if revision._fields[name].type == "many2one" else current
                    if current != values[name]:
                        raise UserError(
                            _("La identidad de la aceptación final conserva su historial.")
                        )
            if (classification | {"mc_acceptance_purpose"}).intersection(
                values
            ) and revision.estado != "borrador":
                raise UserError(_("Clasifique la revisión únicamente mientras está en borrador."))
        result = super().write(values)
        if identity.intersection(values):
            for revision in self.filtered(lambda row: row.mc_acceptance_purpose == "final"):
                revision._acceptance_source_access()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if (
                values.get("mc_acceptance_purpose") == "final"
                and values.get("estado", "borrador") != "borrador"
            ):
                raise UserError(
                    _("La revisión final se inicia en borrador, sin aceptación retrospectiva.")
                )
        revisions = super().create(vals_list)
        for revision in revisions.filtered(lambda row: row.mc_acceptance_purpose == "final"):
            revision._acceptance_source_access()
        return revisions


class RepairAcceptanceOrder(models.Model):
    """The parent visit cannot move sealed evidence to another identity or company."""

    _inherit = "repair.order"

    def write(self, values):
        relevant = {"company_id", "lot_id", "product_id"}.intersection(values)
        if relevant:
            self.check_access("write")
            history = self.env["mc.rov.repair.acceptance.attempt"].sudo()
            for repair in self.sorted("id"):
                self.env.cr.execute(
                    "UPDATE repair_order SET write_date=write_date WHERE id=%s", [repair.id]
                )
                repair.invalidate_recordset(list(relevant))
                if history.search_count([("repair_id", "=", repair.id)]):
                    if repair.company_id.id not in self.env.companies.ids:
                        raise AccessError(
                            _("La reparación no pertenece a una empresa autorizada.")
                        )
                    if any(repair[name].id != (values[name] or False) for name in relevant):
                        raise UserError(
                            _(
                                "La reparación conserva empresa, producto y serie de sus intentos finales."
                            )
                        )
        return super().write(values)
