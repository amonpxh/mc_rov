"""Contrato del tablero: selecciones completas y lectura por origen autorizado."""

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .test_mc_rov_revision import RevisionCommon
from . import test_repair_acceptance_history as acceptance


class MissingKPIDashboard(AssertionError):
    """Distingue contrato ausente de un error de preparación del caso nativo."""


@tagged("post_install", "-at_install", "kpi_dashboard")
class TestKPIDashboard(RevisionCommon):
    """La vista no debe mejorar tasas ocultando órdenes o convirtiendo vacíos en cero."""

    # Matriz de contratos de una misma selección; separar clases duplicaría el fixture.
    # pylint: disable=too-many-public-methods

    _feature = acceptance.TestRepairAcceptanceHistory._feature
    _native_revision = acceptance.TestRepairAcceptanceHistory._native_revision
    _final = acceptance.TestRepairAcceptanceHistory._final
    _history = acceptance.TestRepairAcceptanceHistory._history

    def setUp(self):
        super().setUp()
        self.viewer = new_test_user(
            self.env,
            login="qa_kpi_dashboard_viewer",
            groups="base.group_user,stock.group_stock_user,mrp.group_mrp_user,mc_rov.group_work_assignment_team",
        )

    def _dashboard(self, user=None):
        if "mc.rov.kpi.dashboard" not in self.env.registry.models:
            raise MissingKPIDashboard("Missing authorized KPI dashboard service")
        return self.env["mc.rov.kpi.dashboard"].with_user(user or self.viewer)

    def _orders(self, count=1, **values):
        return self.env["repair.order"].create(
            [
                {
                    "product_id": self.product.id,
                    "product_qty": 1,
                    "product_uom": self.product.uom_id.id,
                    "lot_id": self.lot.id,
                    "company_id": self.env.company.id,
                    **values,
                }
                for _ in range(count)
            ]
        )

    def _quality(self, report):
        row = report["quality"]["repair"]
        self.assertTrue(row["available"])
        return row["metrics"]

    def test_native_source_population_exceeds_page(self):
        orders = self._orders(25)
        self.assertEqual(len(orders), 25)
        self.assertEqual(len(set(orders.ids)), 25)

    def test_native_final_acceptance_seals_success(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        self.assertEqual(self._history(revision).state, "confirmed")

    def test_native_failure_is_preserved(self):
        revision = self._final(False)
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        revision.action_abort_final_acceptance("Fallo de control nativo QA")
        self.assertEqual(self._history(revision).verdict_snapshot, "rechazado")

    def test_native_center_filters_rov_category(self):
        self._orders()
        definition, domain = self.env["mc.rov.work.center"]._get_domain("repair", "orders", "all")
        self.assertIn(self.lot, self.env[definition[0]].search(domain).lot_id)

    def test_dashboard_contract_has_four_sections(self):
        report = self._dashboard().get_dashboard()
        self.assertTrue({"portfolio", "quality", "tracking", "coverage", "cohort"} <= set(report))
        self.assertEqual(report["cohort"]["basis"], "current_authorized_rov_orders")

    def test_empty_quality_is_without_denominator(self):
        metrics = self._quality(self._dashboard().get_dashboard())
        self.assertEqual(metrics["population"], 0)
        self.assertIsNone(metrics["value"])

    def test_unrecorded_final_attempt_is_unknown(self):
        service = self._dashboard()
        self._orders()
        metrics = self._quality(service.get_dashboard())
        self.assertEqual(metrics["unknown"], 1)
        self.assertEqual(metrics["evaluated"], 0)
        self.assertIsNone(metrics["value"])

    def test_quality_does_not_use_twenty_row_page(self):
        service = self._dashboard()
        self._orders(25)
        self.assertEqual(self._quality(service.get_dashboard())["population"], 25)

    def test_quality_keeps_cancelled_orders_without_inventing_verdict(self):
        service = self._dashboard()
        orders = self._orders(2)
        orders[0].action_repair_cancel()
        metrics = self._quality(service.get_dashboard())
        self.assertEqual(metrics["population"], 2)
        self.assertEqual(metrics["unknown"], 2)

    def test_non_rov_order_is_outside_selection(self):
        service = self._dashboard()
        category = self.env["product.category"].create({"name": "QA fuera de ROV"})
        product = self.env["product.product"].create(
            {"name": "QA otro producto", "categ_id": category.id}
        )
        self._orders(product_id=product.id, lot_id=False, product_uom=product.uom_id.id)
        self.assertEqual(self._quality(service.get_dashboard())["population"], 0)

    def test_history_failure_is_not_replaced_by_later_pass(self):
        service = self._dashboard()
        revision = self._final()
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        revision.action_abort_final_acceptance("Primer fallo formal QA")
        self._responder_todo(revision)
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        metrics = self._quality(service.get_dashboard())
        self.assertEqual(metrics["failed"], 1)
        self.assertEqual(metrics["passed"], 0)

    def test_quality_result_does_not_return_episode_details(self):
        report = self._dashboard().get_dashboard()
        for row in report["quality"].values():
            if row["available"]:
                self.assertNotIn("episodes", row["metrics"])

    def test_period_only_filters_tracking_not_quality(self):
        service = self._dashboard()
        self._orders()
        current = self._quality(service.get_dashboard())
        bounded = self._quality(
            service.get_dashboard(date_from="2000-01-01", date_to="2000-01-02")
        )
        self.assertEqual(current, bounded)

    def test_invalid_period_rejected(self):
        service = self._dashboard()
        with self.assertRaises(ValidationError):
            service.get_dashboard(date_from="2026-12-01", date_to="2026-01-01")

    def test_team_role_is_required(self):
        service = self._dashboard()
        user = new_test_user(
            self.env,
            login="qa_kpi_dashboard_no_team",
            groups="base.group_user,stock.group_stock_user",
        )
        with self.assertRaises(AccessError):
            service.with_user(user).get_dashboard()

    def test_portal_is_rejected(self):
        service = self._dashboard()
        with self.assertRaises(AccessError):
            service.with_user(self.env.ref("base.public_user")).get_dashboard()

    def test_company_context_cannot_be_forged(self):
        service = self._dashboard()
        foreign = self.env["res.company"].create({"name": "QA empresa ajena tablero"})
        with self.assertRaises(AccessError):
            service.with_context(allowed_company_ids=[foreign.id]).get_dashboard()

    def test_foreign_company_orders_are_not_included(self):
        service = self._dashboard()
        foreign = self.env["res.company"].create({"name": "QA otro origen tablero"})
        self._orders(company_id=foreign.id, lot_id=False)
        self.assertEqual(self._quality(service.get_dashboard())["population"], 0)

    def test_read_keeps_native_source_unchanged(self):
        service = self._dashboard()
        orders = self._orders()
        self.env.flush_all()
        self.env.cr.precommit.run()
        before = orders.read(["state", "product_id", "lot_id", "write_date"])
        service.get_dashboard()
        self.env.flush_all()
        self.assertEqual(orders.read(["state", "product_id", "lot_id", "write_date"]), before)

    def test_coverage_contains_eleven_initial_families(self):
        report = self._dashboard().get_dashboard()
        for row in report["coverage"]:
            self.assertTrue({"decision", "source", "population", "formula"} <= set(row))
        self.assertEqual(
            {row["key"] for row in report["coverage"]},
            {"F1", "F2", "F3", "F4", "F5", "F6", "Q1", "Q2", "Q3", "Q4", "A1"},
        )

    def test_detail_keeps_complete_quality_selection(self):
        service = self._dashboard()
        orders = self._orders(25)
        action = service.action_detail("quality_repair")
        self.assertEqual(action["res_model"], "repair.order")
        actual = (
            self.env["repair.order"]
            .with_user(self.viewer)
            .with_context(**action.get("context", {}))
            .search(action["domain"])
        )
        self.assertEqual(set(actual.ids), set(orders.ids))

    def test_detail_cannot_select_arbitrary_model(self):
        service = self._dashboard()
        with self.assertRaises(ValidationError):
            service.action_detail("res.users")
