"""Sella observaciones confirmadas sin equipararlas a incidentes únicos."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .production_kpi_event import append_event, lock_source, unit_design


class FindingDetection(models.Model):
    """Fecha declarada del hecho; vacío conserva una detección desconocida."""

    _inherit = "mc.rov.revision.hallazgo"

    mc_detected_at = fields.Datetime(
        string="Detectado el",
        help="Fecha real de detección. Déjela vacía si no está acreditada; no es la fecha de registro.",
        copy=False,
    )

    @api.constrains("mc_detected_at")
    def _check_detection_not_future(self):
        if any(
            line.mc_detected_at and line.mc_detected_at > fields.Datetime.now() for line in self
        ):
            raise ValidationError(_("La detección real no puede estar en el futuro."))


class RevisionFindingCapture(models.Model):
    """La confirmación técnica sella cada observación una sola vez."""

    _inherit = "mc.rov.revision"

    def action_confirmar(self):
        lock_source(self)
        result = super().action_confirmar()
        for revision in self.filtered(
            lambda row: row.estado == "confirmado" and row.lot_id.es_un_rov
        ):
            lot = revision.lot_id
            company = revision.repair_id.company_id or lot.company_id or self.env.company
            for finding in revision.hallazgo_ids:
                append_event(
                    revision,
                    lot,
                    "observation",
                    f"finding:{finding.id}",
                    {
                        "finding_id": finding.hallazgo_id.id,
                        "finding_label": finding.hallazgo_id.name,
                        "component_id": finding.componente_id.id,
                        "component_label": finding.componente_id.name,
                        "severity": finding.severidad,
                        "protocol": revision.tipo,
                        "visit_id": revision.repair_id.id,
                        "customer_id": revision.repair_id.partner_id.id,
                        "detection_point_id": finding.chequeo_origen_id.chequeo_id.id,
                        **unit_design(revision, lot, company),
                    },
                    at=finding.mc_detected_at,
                    revision_id=revision.id,
                    repair_id=revision.repair_id.id,
                )
        return result
