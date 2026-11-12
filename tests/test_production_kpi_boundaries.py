"""Fronteras de contexto histórico, saldos y datos sin evidencia."""

import inspect

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .acceptance_activity_common import AcceptanceActivityCommon
from .test_production_kpi_service import TestProductionKPIService
from .test_production_kpi_dimensions import TestProductionKPIDimensions


@tagged("post_install", "-at_install", "production_kpi_capture")
class TestProductionKPIBoundaries(AcceptanceActivityCommon):
    """Filtros históricos y cobertura explícita evitan poblaciones engañosas."""

    _service = TestProductionKPIService._service
    _made = TestProductionKPIDimensions._made
    _design_feature = TestProductionKPIDimensions._design_feature
    _events = TestProductionKPIDimensions._events
    _move = TestProductionKPIDimensions._move

    def _filters_feature(self):
        service = self._service()
        self.assertIn(
            "customer_id",
            inspect.signature(service.get_summary).parameters,
            "Faltan cortes históricos",
        )
        return service

    def _repair(self, **values):
        return self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "product_qty": 1,
                "tipo_intervencion_ids": [
                    Command.set(self.env.ref("mc_rov.tipo_reparacion_correctiva").ids)
                ],
                **values,
            }
        )

    def test_customer_filter_uses_customer_at_closure(self):
        service = self._filters_feature()
        customer = self.env["res.partner"].create({"name": "QA cliente del cierre"})
        other = self.env["res.partner"].create({"name": "QA cliente posterior"})
        order = self._repair(partner_id=customer.id)
        order.action_repair_done()
        order.partner_id = other
        report = service.get_summary(revision="all", customer_id=customer.id)
        self.assertEqual(report["repair"]["visits"], 1)
        self.assertEqual(
            service.get_summary(revision="all", customer_id=other.id)["repair"]["visits"], 0
        )

    def test_severity_filters_observations_without_weighting(self):
        service = self._filters_feature()
        self.assertIn("severity", inspect.signature(service.get_summary).parameters)
        report = service.get_summary(revision="all", severity="informativo")
        self.assertEqual(report["findings"]["total"], 0)

    def test_balance_contract_is_separate_from_period_counts(self):
        service = self._service()
        self._made()
        report = service.get_summary(revision="all", date_from="2099-01-01")
        self.assertIn("balances", report, "Faltan saldos al corte")
        self.assertEqual(report["manufacturing"]["manufactured"], 0)
        self.assertEqual(report["balances"]["manufactured_not_accepted"], 1)

    def test_old_observation_without_capture_is_not_dated_today(self):
        service = self._service()
        revision = self._revision(tipo="reparacion", motivo="otro")
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
            }
        )
        report = service.get_summary(revision="all")
        self.assertEqual(report["coverage"]["unknown_observation_capture"], 1)
        self.assertEqual(report["findings"]["total"], 0)

    def test_historical_product_dimension_survives_source_product_edit(self):
        service = self._service()
        order = self._repair()
        order.action_repair_done()
        other = self.product.copy({"name": "QA producto posterior"})
        # Cambia solo la etiqueta administrativa actual del origen; el hecho
        # conserva equipo, producto y modelo registrados cuando se cerró.
        order.product_id = other
        report = service.get_summary(model_id=self.product.product_tmpl_id.id, revision="all")
        self.assertEqual(report["repair"]["visits"], 1)

    def test_forged_company_context_is_rejected(self):
        service = self._service()
        other = self.env["res.company"].create({"name": "QA empresa ajena KPI"})
        with self.assertRaises(AccessError):
            service.with_context(allowed_company_ids=[other.id]).get_summary()

    def test_unbuild_keeps_manufacture_and_records_reversal(self):
        self.product.is_storable = True
        production, lot, bom = self._made()
        unbuild = self.env["mrp.unbuild"].create(
            {
                "product_id": self.product.id,
                "product_qty": 1,
                "product_uom_id": self.product.uom_id.id,
                "bom_id": bom.id,
                "mo_id": production.id,
                "lot_id": lot.id,
                "location_id": production.location_dest_id.id,
                "location_dest_id": production.location_src_id.id,
            }
        )
        unbuild.action_unbuild()
        self.assertEqual(len(self._events("manufactured", lot)), 1)
        self.assertEqual(len(self._events("reversed", lot)), 1)
