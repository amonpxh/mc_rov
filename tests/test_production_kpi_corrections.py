"""Las correcciones conservan causa, actor y observación original."""

from odoo.exceptions import UserError
from odoo.tests import tagged

from .acceptance_activity_common import AcceptanceActivityCommon
from .test_production_kpi_capture import TestProductionKPICapture
from .test_production_kpi_service import TestProductionKPIService


@tagged("post_install", "-at_install", "production_kpi_capture")
class TestProductionKPICorrections(AcceptanceActivityCommon):
    """Una enmienda no es otro incidente ni desaparece sin explicación."""

    _feature = TestProductionKPICapture._feature
    _finding = TestProductionKPICapture._finding
    _service = TestProductionKPIService._service

    def _recorded(self):
        self.assertTrue(
            "mc_findings_correction_reason" in self.env["mc.rov.revision"]._fields,
            "Faltan correcciones auditadas de hallazgos",
        )
        revision, finding = self._finding()
        revision.action_confirmar()
        revision.action_volver_a_borrador()
        return revision, finding

    def _summary(self):
        return self._service().get_summary(revision="all")

    def test_changed_recorded_finding_requires_reason(self):
        revision, finding = self._recorded()
        finding.severidad = "atencion"
        with self.assertRaises(UserError):
            revision.action_confirmar()

    def test_amendment_preserves_original_and_one_occurrence(self):
        revision, finding = self._recorded()
        finding.severidad = "atencion"
        revision.mc_findings_correction_reason = "Clasificación revisada por técnico QA"
        revision.action_confirmar()
        events = (
            self.env["mc.rov.production.event"].sudo().search([("revision_id", "=", revision.id)])
        )
        self.assertEqual(len(events.filtered(lambda row: row.kind == "observation")), 1)
        amendment = events.filtered(lambda row: row.kind == "observation_correction")
        self.assertEqual(len(amendment), 1)
        self.assertTrue(amendment.payload["reason"])
        self.assertEqual(self._summary()["findings"]["total"], 1)
        self.assertFalse(revision.mc_findings_correction_reason)

    def test_removed_observation_requires_audited_reason(self):
        revision, finding = self._recorded()
        finding.unlink()
        with self.assertRaises(UserError):
            revision.action_confirmar()
        revision.mc_findings_correction_reason = "Observación ingresada por error QA"
        revision.action_confirmar()
        self.assertEqual(self._summary()["findings"]["total"], 0)
        self.assertTrue(
            self.env["mc.rov.production.event"]
            .sudo()
            .search(
                [
                    ("revision_id", "=", revision.id),
                    ("kind", "=", "observation"),
                ]
            )
        )

    def test_new_detection_date_corrects_coverage_without_using_create_date(self):
        revision, finding = self._recorded()
        finding.mc_detected_at = "2026-11-09 13:00:00"
        revision.mc_findings_correction_reason = "Fecha comprobada en registro QA"
        revision.action_confirmar()
        self.assertEqual(
            self._service().get_summary(
                revision="all", date_from="2026-11-09", date_to="2026-11-09"
            )["findings"]["total"],
            1,
        )
        self.assertEqual(
            self._service().get_summary(
                revision="all", date_from="2026-11-10", date_to="2026-11-10"
            )["findings"]["total"],
            0,
        )
