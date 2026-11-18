"""Contratos del adaptador F2 y su entrega autorizada al tablero."""

from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from . import test_detention_capture as capture_contracts
from . import test_detention_boundaries as boundaries
from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install", "detention_kpi_service")
class TestDetentionKPIService(AcceptanceActivityCommon):
    """La consulta no inventa ausencia histórica ni suma dos veces causas simultáneas."""

    _service = capture_contracts.TestDetentionCapture._service
    _workshop = capture_contracts.TestDetentionCapture._workshop
    _order = capture_contracts.TestDetentionCapture._order
    _start = capture_contracts.TestDetentionCapture._start
    _history = capture_contracts.TestDetentionCapture._history
    _rule = boundaries.TestDetentionBoundaries._rule

    def _kpi(self):
        self.assertTrue(
            "mc.rov.detention.kpi" in self.env.registry.models,
            "Falta consulta KPI F2 autorizada",
        )
        user = new_test_user(
            self.env,
            login="qa_detention_kpi_team",
            groups="base.group_user,stock.group_stock_user,mrp.group_mrp_user,mc_rov.group_work_assignment_team",
        )
        return self.env["mc.rov.detention.kpi"].with_user(user)

    def _summary(self, kpi, **kwargs):
        with patch.object(fields.Datetime, "now", return_value=datetime(2026, 11, 18, 16)):
            return kpi.get_summary(date_from="2026-11-18", date_to="2026-11-18", **kwargs)

    def _timed_start(self, service, order, cause="materials"):
        with patch.object(fields.Datetime, "now", return_value=datetime(2026, 11, 18, 14)):
            return self._start(service, order, cause=cause)

    def test_team_permission_is_required(self):
        kpi = self._kpi()
        service = self._service()
        with self.assertRaises(AccessError):
            self._summary(kpi.with_user(service.env.user))

    def test_portal_is_rejected(self):
        kpi = self._kpi()
        portal = new_test_user(
            self.env, login="qa_detention_kpi_portal", groups="base.group_portal"
        )
        with self.assertRaises(AccessError):
            self._summary(kpi.with_user(portal))

    def test_forged_company_is_rejected(self):
        kpi = self._kpi()
        company = self.env["res.company"].create({"name": "QA F2 empresa KPI ajena"})
        with self.assertRaises(AccessError):
            self._summary(kpi.with_context(allowed_company_ids=company.ids))

    def test_empty_population_is_not_zero_percent(self):
        summary = self._summary(self._kpi())
        self.assertEqual(summary["open_orders"], 0)
        self.assertIsNone(summary["registered_stopped_percent"])

    def test_open_registered_detention_is_counted(self):
        kpi = self._kpi()
        service = self._service()
        self._timed_start(service, self._order())
        summary = self._summary(kpi)
        self.assertEqual(summary["open_orders"], 1)
        self.assertEqual(summary["registered_stopped_orders"], 1)
        self.assertEqual(summary["registered_stopped_percent"], 100)

    def test_known_closed_duration_is_one_hour(self):
        kpi = self._kpi()
        service = self._service()
        identity = self._timed_start(service, self._order())
        with patch.object(fields.Datetime, "now", return_value=datetime(2026, 11, 18, 15)):
            service.finish_detention(identity)
        summary = self._summary(kpi)
        self.assertEqual(summary["recorded_seconds"], 3600)
        self.assertEqual(summary["registered_stopped_orders"], 0)

    def test_overlapping_causes_are_not_added(self):
        kpi = self._kpi()
        service = self._service()
        order = self._order()
        first = self._timed_start(service, order)
        second = self._timed_start(service, order, "client")
        with patch.object(fields.Datetime, "now", return_value=datetime(2026, 11, 18, 15)):
            service.finish_detention(first)
            service.finish_detention(second)
        summary = self._summary(kpi)
        self.assertEqual(summary["recorded_seconds"], 3600)
        self.assertEqual(summary["by_cause"]["materials"]["recorded_seconds"], 3600)
        self.assertEqual(summary["by_cause"]["client"]["recorded_seconds"], 3600)
        self.assertFalse(summary["causes_additive"])

    def test_open_duration_stops_at_server_cutoff(self):
        kpi = self._kpi()
        service = self._service()
        self._timed_start(service, self._order())
        self.assertEqual(self._summary(kpi)["recorded_seconds"], 7200)

    def test_no_history_remains_explicit_in_coverage(self):
        kpi = self._kpi()
        self._order()
        summary = self._summary(kpi)
        self.assertEqual(summary["orders_without_recorded_intervals"], 1)
        self.assertEqual(summary["coverage_basis"], "recorded_intervals_only")
        self.assertEqual(summary["coverage_scope"], "population_history")
        self.assertEqual(summary["duration_unit"], "order_seconds")

    def test_process_filter_and_invalid_process(self):
        kpi = self._kpi()
        self._order()
        production = self._production()
        production.action_confirm()
        self.assertEqual(self._summary(kpi, process="repair")["open_orders"], 1)
        with self.assertRaises(ValidationError):
            self._summary(kpi, process="inventory")

    def test_hidden_source_is_not_silently_zero(self):
        kpi = self._kpi()
        service = self._service()
        self._timed_start(service, self._order())
        self._rule(perm_read=True)
        with self.assertRaises(AccessError):
            self._summary(kpi)

    def test_dashboard_exposes_authorized_detention_metrics(self):
        kpi = self._kpi()
        service = self._service()
        order = self._order()
        self._timed_start(service, order)
        original = self._history(service, order)
        with patch.object(fields.Datetime, "now", return_value=datetime(2026, 11, 18, 16)):
            report = (
                self.env["mc.rov.kpi.dashboard"]
                .with_user(kpi.env.user)
                .get_dashboard(
                    date_from="2026-11-18",
                    date_to="2026-11-18",
                    detention_filters={"process": "all"},
                )
            )
        self.assertTrue(report["detentions"]["available"])
        self.assertEqual(report["detentions"]["metrics"]["registered_stopped_orders"], 1)
        self.assertEqual(self._history(service, order), original)
