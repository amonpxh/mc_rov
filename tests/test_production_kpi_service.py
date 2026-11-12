"""Agregados solo sobre documentos y empresas autorizados, sin inventar cobertura."""

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install", "production_kpi_capture")
class TestProductionKPIService(AcceptanceActivityCommon):
    """Contratos del adaptador independiente de las tarjetas y la paginación."""

    def _service(self, user=None):
        self.assertTrue(
            "mc.rov.production.kpi" in self.env.registry.models, "Falta servicio de volumen"
        )
        if user is None:
            user = new_test_user(
                self.env,
                login="qa_production_kpi_viewer",
                groups="base.group_user,stock.group_stock_user,mrp.group_mrp_user,mc_rov.group_work_assignment_team",
            )
        return self.env["mc.rov.production.kpi"].with_user(user)

    def _summary(self, service, **values):
        return service.get_summary(model_id=self.product.product_tmpl_id.id, **values)

    def test_empty_model_has_explicit_coverage(self):
        report = self._summary(self._service())
        self.assertTrue(
            {"repair", "manufacturing", "findings", "coverage", "filters"} <= set(report)
        )
        self.assertEqual(report["repair"]["visits"], 0)
        self.assertEqual(report["coverage"]["unknown_repair_closure"], 0)

    def test_all_revisions_include_real_manufacture(self):
        service = self._service()
        self._finished_production()
        self.assertEqual(
            self._summary(service, revision="all")["manufacturing"]["manufactured"], 1
        )

    def test_latest_does_not_assign_revision_to_unknown_unit(self):
        service = self._service()
        self._finished_production()
        report = self._summary(service)
        self.assertEqual(report["manufacturing"]["manufactured"], 0)
        self.assertEqual(report["manufacturing"]["unknown_revision"], 1)

    def test_imported_repair_is_coverage_not_closure_today(self):
        service = self._service()
        self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "state": "done",
                "tipo_intervencion_ids": [
                    Command.set(self.env.ref("mc_rov.tipo_reparacion_correctiva").ids)
                ],
            }
        )
        report = self._summary(service, revision="all")
        self.assertEqual(report["repair"]["visits"], 0)
        self.assertEqual(report["coverage"]["unknown_repair_closure"], 1)

    def test_missing_team_role_is_denied(self):
        user = new_test_user(self.env, login="qa_no_volume_team", groups="base.group_user")
        service = self._service(user)
        with self.assertRaises(AccessError):
            self._summary(service)

    def test_invalid_period_is_not_silently_ignored(self):
        service = self._service()
        with self.assertRaises(ValidationError):
            self._summary(service, date_from="2026-12-01", date_to="2026-11-01")

    def test_invalid_revision_selector_is_rejected(self):
        service = self._service()
        with self.assertRaises(ValidationError):
            self._summary(service, revision={"sudo": True})

    def test_unknown_revision_key_is_rejected(self):
        service = self._service()
        with self.assertRaises(ValidationError):
            self._summary(service, revision="bom:999999999:v1")

    def test_private_events_are_not_returned(self):
        service = self._service()
        self._finished_production()
        report = self._summary(service, revision="all")
        self.assertNotIn("events", report)
        self.assertNotIn("episodes", report)

    def test_unreadable_product_is_not_counted_through_history(self):
        service = self._service()
        self._finished_production()
        self.env["ir.rule"].create(
            {
                "name": "QA producto restringido de volumen",
                "model_id": self.env["ir.model"]._get_id("product.product"),
                "domain_force": f"[('id', '!=', {self.product.id})]",
            }
        )
        with self.assertRaises(AccessError):
            self._summary(service, revision="all")
