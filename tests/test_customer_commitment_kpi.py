"""Contratos del adaptador F3 con datos ficticios y permisos nativos."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .test_mc_rov_revision import RevisionCommon
from .test_inventory_activity_events import InventoryEventCommon
from ..models.production_kpi_metrics import local_day
from ..models.stock_lot import ROV_CATEG_PARAM


@tagged("post_install", "-at_install", "customer_commitment")
class TestCustomerCommitmentKPI(RevisionCommon):
    """La ausencia de captura y de acceso se distingue de un resultado numérico."""

    def test_team_dashboard_exposes_f3_on_request(self):
        viewer = new_test_user(
            self.env,
            login="qa_commitment_summary",
            groups="base.group_user,mc_rov.group_work_assignment_team,"
            "sales_team.group_sale_manager,stock.group_stock_user",
        )
        dashboard = self.env["mc.rov.kpi.dashboard"].with_user(viewer)
        report = dashboard.get_dashboard(customer_commitments=True)
        self.assertTrue(report["commitments"]["available"])
        for name in ("due", "completed"):
            self.assertEqual(report["commitments"]["metrics"][name]["denominator"], 0)
            self.assertIsNone(report["commitments"]["metrics"][name]["percentage"])

    def test_commitment_service_rejects_user_without_team_access(self):
        viewer = new_test_user(self.env, login="qa_commitment_no_team", groups="base.group_user")
        with self.assertRaises(AccessError):
            self.env["mc.rov.customer.commitment.kpi"].with_user(viewer).get_summary()

    def test_commitment_service_rejects_period_reversed(self):
        viewer = new_test_user(
            self.env,
            login="qa_commitment_period",
            groups="base.group_user,mc_rov.group_work_assignment_team",
        )
        with self.assertRaises(ValidationError):
            self.env["mc.rov.customer.commitment.kpi"].with_user(viewer).get_summary(
                date_from="2026-11-21", date_to="2026-11-20"
            )


@tagged("post_install", "-at_install", "customer_commitment")
class TestCustomerCommitmentRepairDispatch(InventoryEventCommon):
    """Una reparación sin venta se acredita por la visita y la serie entregada."""

    @staticmethod
    def _promise_for(repair, supervisor):
        now = fields.Datetime.now()
        due = local_day(now)
        origin = repair.with_user(supervisor)
        operation = origin.action_mc_customer_commitment()
        wizard = (
            origin.env[operation["res_model"]]
            .with_context(**operation["context"])
            .create(
                {
                    "precision": "day",
                    "promised_date": due,
                    "agreed_at": now - timedelta(days=2),
                    "evidence": "Aceptación ficticia",
                }
            )
        )
        wizard.action_apply()
        return due

    def test_native_outgoing_needs_a_linked_physical_evidence(self):
        self.env["ir.config_parameter"].set_param(ROV_CATEG_PARAM, self.product.categ_id.id)
        self.product.tracking = "serial"
        lot = self.env["stock.lot"].create(
            {
                "name": "QA-SALIDA-REPARACION",
                "product_id": self.product.id,
                "company_id": self.env.company.id,
            }
        )
        partner = self.env["res.partner"].create({"name": "QA Cliente reparación"})
        repair = self.env["repair.order"].create(
            {
                "partner_id": partner.id,
                "product_id": self.product.id,
                "lot_id": lot.id,
                "product_uom": self.product.uom_id.id,
            }
        )
        supervisor = new_test_user(
            self.env,
            login="qa_commitment_repair_outbound",
            groups="stock.group_stock_manager,mc_rov.group_customer_commitment_supervisor,"
            "mc_rov.group_work_assignment_team",
        )
        due = self._promise_for(repair, supervisor)
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.locations["stock"], 1, lot_id=lot
        )
        picking = self._picking("outgoing", partner_id=partner.id)
        picking.move_ids.product_uom_qty = 1
        self._confirm(picking)
        picking.with_user(self.operator).action_assign()
        self.assertEqual(picking.move_line_ids.lot_id, lot)
        self._finish(picking)
        service = self.env["mc.rov.customer.commitment.kpi"].with_user(supervisor)
        span = {"date_from": due.isoformat(), "date_to": due.isoformat()}
        # Consultar después de los sellos del ORM, que pueden incluir fracciones de segundo.
        with patch.object(
            fields.Datetime, "now", return_value=datetime.now(timezone.utc).replace(tzinfo=None)
        ):
            self.assertEqual(service.get_summary(**span)["due"]["unknown"], 1)
        attachment = self.env["ir.attachment"].create(
            {
                "name": "Constancia QA",
                "type": "url",
                "url": "https://example.com/f3-qa",
                "res_model": "stock.picking",
                "res_id": picking.id,
            }
        )
        action = picking.with_user(supervisor).action_open_customer_dispatch()
        evidence = self.env[action["res_model"]].with_user(supervisor).browse(action["res_id"])
        evidence.write(
            {
                "repair_ids": [Command.set(repair.ids)],
                "mode": "pickup",
                "precision": "date",
                "effective_date": due,
                "attachment_id": attachment.id,
            }
        )
        evidence.action_apply()
        with patch.object(
            fields.Datetime, "now", return_value=datetime.now(timezone.utc).replace(tzinfo=None)
        ):
            result = service.get_summary(**span)
        self.assertEqual(result["due"]["on_time"], 1)
        self.assertEqual(result["completed"]["on_time"], 1)
        self.assertEqual(result["rows"][0]["origin"], repair.display_name)
