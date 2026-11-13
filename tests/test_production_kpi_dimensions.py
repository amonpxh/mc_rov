"""Configuración de diseño histórica, movimientos y cobertura del tablero."""

import inspect

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install", "production_kpi_capture")
class TestProductionKPIDimensions(AcceptanceActivityCommon):
    """Un ECO posterior no cambia qué se fabricó ni una salida interna es entrega."""

    def _design_feature(self):
        self.assertTrue(
            "mc_design_snapshot" in self.env["mrp.production"]._fields, "Falta diseño acreditado"
        )

    def _made(self):
        self._design_feature()
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "product_qty": 1,
                "version": 2,
            }
        )
        production = self._production(bom_id=bom.id)
        production.action_confirm()
        lots = self._serials()
        self._finish_acceptance_production(production, lots)
        return production, lots, bom

    def _events(self, kind, lot):
        return (
            self.env["mc.rov.production.event"]
            .sudo()
            .search(
                [
                    ("kind", "=", kind),
                    ("lot_id", "=", lot.id),
                ]
            )
        )

    def _move(self, lot, source, destination):
        move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 1,
                "product_uom": self.product.uom_id.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "company_id": self.env.company.id,
                "picked": True,
                "move_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_id": self.product.uom_id.id,
                            "quantity": 1,
                            "lot_id": lot.id,
                            "location_id": source.id,
                            "location_dest_id": destination.id,
                        }
                    )
                ],
            }
        )
        move._action_done()
        return move

    def test_product_eco_during_work_does_not_relabel_design(self):
        self._design_feature()
        bom = self.env["mrp.bom"].create({"product_tmpl_id": self.product.product_tmpl_id.id})
        production = self._production(bom_id=bom.id)
        production.action_confirm()
        version = self.product.version
        self.product.product_tmpl_id.version = version + 1
        lot = self._serials()
        self._finish_acceptance_production(production, lot)
        self.assertEqual(self._events("manufactured", lot).payload["model_version"], version)

    def test_bom_change_after_completion_does_not_relabel_history(self):
        _production, lot, bom = self._made()
        before = self._events("manufactured", lot).payload.copy()
        bom.version += 1
        self.assertEqual(self._events("manufactured", lot).payload, before)

    def test_rpc_cannot_write_design_snapshot(self):
        self._design_feature()
        production = self._production()
        with self.assertRaises(UserError):
            production.write({"mc_design_snapshot": {"revision_key": "forged"}})

    def test_real_customer_transfer_records_outbound(self):
        production, lot, _bom = self._made()
        self._move(
            lot, production.location_dest_id, self.env.ref("stock.stock_location_customers")
        )
        self.assertEqual(len(self._events("outbound", lot)), 1)

    def test_internal_transfer_is_not_customer_delivery(self):
        production, lot, _bom = self._made()
        other = self.env["stock.location"].create(
            {"name": "QA otra ubicación", "usage": "internal"}
        )
        self._move(lot, production.location_dest_id, other)
        self.assertFalse(self._events("outbound", lot))

    def test_customer_return_is_reversal_without_erasing_manufacture(self):
        production, lot, _bom = self._made()
        customer = self.env.ref("stock.stock_location_customers")
        self._move(lot, production.location_dest_id, customer)
        self._move(lot, customer, production.location_dest_id)
        self.assertEqual(len(self._events("manufactured", lot)), 1)
        self.assertEqual(len(self._events("reversed", lot)), 1)

    def test_dashboard_exposes_production_only_when_requested(self):
        viewer = new_test_user(
            self.env,
            login="qa_volume_bridge",
            groups="base.group_user,stock.group_stock_user,mrp.group_mrp_user,mc_rov.group_work_assignment_team",
        )
        service = self.env["mc.rov.kpi.dashboard"].with_user(viewer)
        self.assertTrue(
            "production_filters" in inspect.signature(service.get_dashboard).parameters,
            "Falta integración del tablero",
        )
        report = service.get_dashboard(production_filters={"revision": "all"})
        self.assertTrue(report["production"]["available"])
        self.assertIn("findings", report["production"]["metrics"])
