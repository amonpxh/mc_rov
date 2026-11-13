"""Observaciones y enmiendas auditadas, sin inventar incidentes únicos."""

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .production_kpi_event import append_event, event_values, lock_source, unit_design
from .production_kpi_metrics import project_observations


def finding_values(finding):
    """Datos observados; etiquetas congeladas junto con sus referencias."""
    return {
        "finding_id": finding.hallazgo_id.id,
        "finding_label": finding.hallazgo_id.name,
        "component_id": finding.componente_id.id,
        "component_label": finding.componente_id.name,
        "severity": finding.severidad,
        "detection_point_id": finding.chequeo_origen_id.chequeo_id.id,
        "detail": finding.detalle or False,
    }


class FindingDetection(models.Model):
    """Fecha declarada del hecho; vacío conserva una detección desconocida."""

    _inherit = "mc.rov.revision.hallazgo"

    mc_detected_at = fields.Datetime(
        string="Detectado el",
        copy=False,
        help="Fecha real de detección. Vacío significa desconocida; no es la fecha de registro.",
    )

    @api.constrains("mc_detected_at")
    def _check_detection_not_future(self):
        if any(
            line.mc_detected_at and line.mc_detected_at > fields.Datetime.now() for line in self
        ):
            raise ValidationError(_("La detección real no puede estar en el futuro."))


class RevisionFindingCapture(models.Model):
    """Cada observación tiene un original inmutable y enmiendas con motivo/actor."""

    _inherit = "mc.rov.revision"

    mc_findings_correction_reason = fields.Text(
        string="Motivo de corrección de hallazgos",
        copy=False,
        help="Obligatorio al confirmar si cambió o retiró una observación ya registrada.",
    )
    mc_findings_history_html = fields.Html(
        string="Evidencia de hallazgos",
        compute="_compute_findings_history",
        sanitize=True,
        groups="mc_rov.group_work_assignment_team",
    )

    def _finding_history(self):
        self.ensure_one()
        self.check_access("read")
        self.lot_id.check_access("read")
        self.product_id.check_access("read")
        company = self.repair_id.company_id or self.lot_id.company_id or self.env.company
        if self.env.user.share or company not in self.env.companies:
            raise AccessError(_("La revisión no pertenece a una empresa autorizada."))
        return (
            self.env["mc.rov.production.event"]
            .sudo()
            .search(
                [
                    ("revision_id", "=", self.id),
                    ("company_id", "=", company.id),
                    ("kind", "in", ["observation", "observation_correction"]),
                ],
                order="id",
            )
        )

    def _finding_changes(self):
        self.ensure_one()
        history = self._finding_history()
        if history and any(event.lot_id.id != self.lot_id.id for event in history):
            raise UserError(
                _("La evidencia conserva la serie original; cree otra revisión para otro equipo.")
            )
        current = {f"finding:{line.id}": line for line in self.hallazgo_ids}
        changes = []
        compared = ("finding_id", "component_id", "severity", "detection_point_id", "detail")
        for original in project_observations([event_values(event) for event in history]):
            line = current.get(original["identity"])
            replacement = finding_values(line) if line else False
            detected_at = (
                fields.Datetime.to_string(line.mc_detected_at)
                if line and line.mc_detected_at
                else False
            )
            if (
                not line
                or original.get("at") != detected_at
                or any(
                    (original.get(key) or False) != (replacement.get(key) or False)
                    for key in compared
                )
            ):
                changes.append((original["identity"], replacement, detected_at))
        if changes and not (self.mc_findings_correction_reason or "").strip():
            raise UserError(
                _("Explique el motivo de la corrección o retiro de los hallazgos registrados.")
            )
        return history, changes

    def _append_finding_changes(self, history, changes):
        self.ensure_one()
        for identity, replacement, detected_at in changes:
            ordinal = 1 + len(
                history.filtered(
                    lambda event, root_identity=identity: event.kind == "observation_correction"
                    and event.payload.get("observation_identity") == root_identity
                )
            )
            append_event(
                self,
                self.lot_id,
                "observation_correction",
                f"{identity}:correction:{ordinal}",
                {
                    "observation_identity": identity,
                    "replacement": replacement,
                    "detected_at": detected_at,
                    "reason": self.mc_findings_correction_reason.strip(),
                },
                at=fields.Datetime.now(),
                revision_id=self.id,
                repair_id=self.repair_id.id,
            )

    def action_confirmar(self):
        lock_source(self)
        prepared = {
            revision.id: revision._finding_changes()
            for revision in self
            if revision.lot_id.es_un_rov
        }
        result = super().action_confirmar()
        for revision in self.filtered(
            lambda row: row.estado == "confirmado" and row.id in prepared
        ):
            lot = revision.lot_id
            company = revision.repair_id.company_id or lot.company_id or self.env.company
            history, changes = prepared[revision.id]
            revision._append_finding_changes(history, changes)
            for finding in revision.hallazgo_ids:
                append_event(
                    revision,
                    lot,
                    "observation",
                    f"finding:{finding.id}",
                    {
                        **finding_values(finding),
                        "protocol": revision.tipo,
                        "visit_id": revision.repair_id.id,
                        "customer_id": revision.repair_id.partner_id.id,
                        **unit_design(revision, lot, company),
                    },
                    at=finding.mc_detected_at,
                    revision_id=revision.id,
                    repair_id=revision.repair_id.id,
                )
            if revision.mc_findings_correction_reason:
                revision.mc_findings_correction_reason = False
        return result

    @api.depends("estado", "hallazgo_ids", "mc_findings_correction_reason")
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_findings_history(self):
        for revision in self:
            if not isinstance(revision.id, int) or not self.env.user.has_group(
                "mc_rov.group_work_assignment_team"
            ):
                revision.mc_findings_history_html = False
                continue
            rows = []
            for event in revision._finding_history():
                label = event.payload.get("finding_label") or "Corrección de observación"
                reason = event.payload.get("reason") or "Registro original"
                rows.append(
                    Markup("<li><strong>%s</strong> · %s · %s · %s</li>")
                    % (
                        escape(label),
                        escape(reason),
                        escape(event.actor_id.display_name),
                        escape(fields.Datetime.to_string(event.create_date)),
                    )
                )
            revision.mc_findings_history_html = (
                Markup("<ul>%s</ul>") % Markup("").join(rows) if rows else False
            )
