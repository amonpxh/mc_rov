from datetime import date
from unittest.mock import patch

from odoo import Command, _
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .automatic_completion_assertions import assert_automatic_close_rejected
from .manufacturing_activity_common import ManufacturingActivityCommon


@tagged("post_install", "-at_install")
# Cada método es un contrato independiente; los cuatro nativos validan el escenario del RED.
# pylint: disable=too-many-public-methods
class TestManufacturingActivityLifecycle(ManufacturingActivityCommon):
    """El pendiente refleja el resultado real sin reemplazar la fabricación."""

    def _lifecycle(self):
        service = self.env["mc.rov.manufacturing.activity.automation"]
        self.assertTrue(hasattr(service, "_reconcile"), "Missing manufacturing activity lifecycle")
        return service

    def _confirmed(self, **values):
        production = self._production(**values)
        production.action_confirm()
        return production

    def _ready(self, production):
        production.write({"lot_producing_ids": [Command.set(self.lot.ids)], "qty_producing": 1})

    def _finish(self, production, **context):
        self._ready(production)
        return production.with_context(skip_redirection=True, **context).button_mark_done()

    def _visit(self, **values):
        self._lifecycle()
        policy = self._policy()
        production = self._confirmed(**values)
        return policy, production, self._runs(production)

    def test_native_finished_serial_production_fixture(self):
        production = self._confirmed()
        self._finish(production)
        self.assertEqual(production.state, "done")
        self.assertTrue(production.move_finished_ids)
        self.assertEqual(set(production.move_finished_ids.mapped("state")), {"done"})

    def test_native_partial_requires_backorder_decision_fixture(self):
        production = self._confirmed(product_qty=2)
        production.picking_type_id.create_backorder = "ask"
        result = self._finish(production)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("res_model"), "mrp.production.backorder")
        self.assertNotEqual(production.state, "done")

    def test_native_cancellation_fixture(self):
        production = self._confirmed()
        production.action_cancel()
        self.assertEqual(production.state, "cancel")

    def test_native_partial_completion_fixture(self):
        production = self._confirmed(product_qty=2)
        self._finish(production, skip_backorder=True, mo_ids_to_backorder=production.ids)
        self.assertEqual(production.state, "done")
        remaining = self.env["mrp.production"].search(
            [
                ("production_group_id", "=", production.production_group_id.id),
                ("id", "!=", production.id),
            ]
        )
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining.product_qty, 1)
        self.assertNotEqual(remaining.state, "done")

    def test_real_completion_closes_pending(self):
        _policy, production, run = self._visit()
        self._finish(production)
        self.assertEqual(production.state, "done")
        self.assertEqual(run.outcome, "business_done")
        self.assertFalse(run.activity_id and run.activity_id.active)
        self.assertTrue(run.finished_at)
        self.assertEqual(run.finished_by_id, self.env.user)
        self.assertTrue(run.finish_reason)

    def test_shop_floor_completion_closes_pending(self):
        _policy, production, run = self._visit()
        self._finish(production, from_workorder=True)
        self.assertEqual(production.state, "done")
        self.assertEqual(run.outcome, "business_done")

    def test_wizard_return_keeps_pending(self):
        _policy, production, run = self._visit(product_qty=2)
        production.picking_type_id.create_backorder = "ask"
        result = self._finish(production)
        self.assertEqual(result.get("res_model"), "mrp.production.backorder")
        self.assertNotEqual(production.state, "done")
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_ready_to_close_keeps_pending(self):
        _policy, production, run = self._visit()
        self._ready(production)
        self.assertEqual(production.state, "to_close")
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_cancelled_production_cancels_pending(self):
        _policy, production, run = self._visit()
        production.action_cancel()
        self.assertEqual(production.state, "cancel")
        self.assertEqual(run.outcome, "cancelled")
        self.assertFalse(run.activity_id and run.activity_id.active)
        self.assertTrue(run.finished_at)
        self.assertTrue(run.finish_reason)

    def test_actual_done_is_not_misreported_as_cancellation(self):
        _policy, production, run = self._visit()
        self._finish(production)
        production._action_cancel()
        self.assertEqual(production.state, "done")
        self.assertEqual(run.outcome, "business_done")

    def test_manual_done_is_blocked_without_finishing_or_recreating(self):
        _policy, production, run = self._visit()
        with assert_automatic_close_rejected(self, run):
            run.activity_id.action_feedback(feedback="QA cierre manual")
        production.write({"origin": "QA edición posterior"})
        self.assertEqual(production.state, "confirmed")
        self.assertEqual(run.outcome, "pending")
        self.assertFalse(run.finish_reason)
        self.assertEqual(self._runs(production), run)
        self.assertEqual(production.activity_ids, run.activity_id)

    def test_manual_cancel_is_blocked_without_cancelling_production(self):
        _policy, production, run = self._visit()
        with assert_automatic_close_rejected(self, run):
            run.activity_id.action_cancel()
        self.assertEqual(production.state, "confirmed")
        self.assertEqual(run.outcome, "pending")
        self.assertEqual(production.activity_ids, run.activity_id)
        self.assertEqual(self._runs(production), run)

    def test_manual_archive_is_blocked_and_keeps_pending(self):
        _policy, production, run = self._visit()
        with assert_automatic_close_rejected(self, run):
            run.activity_id.active = False
        self.assertEqual(run.outcome, "pending")
        self.assertEqual(production.state, "confirmed")

    def test_policy_pause_still_allows_completion(self):
        policy, production, run = self._visit()
        policy.enabled = False
        self._finish(production)
        self.assertEqual(run.outcome, "business_done")

    def test_general_pause_still_allows_completion(self):
        _policy, production, run = self._visit()
        controls = self.env["mc.rov.automation.control"]
        row = controls.search([("company_id", "=", self.env.company.id)], limit=1)
        if row:
            row.enabled = False
        else:
            controls.create({"company_id": self.env.company.id, "enabled": False})
        self._finish(production)
        self.assertEqual(run.outcome, "business_done")

    def test_same_title_manual_activity_is_untouched(self):
        policy, production, run = self._visit()
        manual = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("mrp.production"),
                "res_id": production.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "user_id": policy.user_id.id,
                "summary": run.activity_id.summary,
                "date_deadline": run.original_deadline,
            }
        )
        self._finish(production)
        self.assertEqual(run.outcome, "business_done")
        self.assertTrue(manual.active)

    def test_later_failure_rolls_back_completion_and_activity(self):
        _policy, production, run = self._visit()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._finish(production)
            self.assertEqual(run.outcome, "business_done")
            raise ValidationError(_("QA fallo posterior"))
        production.invalidate_recordset()
        run.invalidate_recordset()
        self.assertEqual(production.state, "confirmed")
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_activity_close_failure_rolls_back_business_event(self):
        _policy, production, run = self._visit()
        with self.assertRaises(RuntimeError), self.cr.savepoint(), patch.object(
            type(self.env["mail.activity"]),
            "action_feedback",
            side_effect=RuntimeError("QA cierre fallido"),
        ):
            self._finish(production)
        self.assertEqual(production.state, "confirmed")
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_partial_completion_closes_only_original(self):
        _policy, production, run = self._visit(product_qty=2)
        self._finish(production, skip_backorder=True, mo_ids_to_backorder=production.ids)
        self.assertEqual(production.state, "done")
        self.assertEqual(run.outcome, "business_done")
        remaining_run = self._run_model().search([("parent_run_id", "=", run.id)])
        self.assertEqual(len(remaining_run), 1)
        self.assertEqual(remaining_run.outcome, "pending")
        self.assertTrue(remaining_run.activity_id.active)
        self.assertNotEqual(remaining_run.production_id.state, "done")

    def test_split_after_blocked_deletion_keeps_reprogrammed_deadline(self):
        _policy, production, run = self._visit(product_qty=2)
        run.activity_id.date_deadline = date(2026, 10, 30)
        with assert_automatic_close_rejected(self, run):
            run.activity_id.unlink()
        remaining = production._split_productions(amounts={production: [1.0, 1.0]}) - production
        self.assertEqual(self._runs(remaining).activity_id.date_deadline, date(2026, 10, 30))

    def test_real_completion_after_blocked_manual_done_records_business_result(self):
        _policy, production, run = self._visit()
        with assert_automatic_close_rejected(self, run):
            run.activity_id.action_feedback(feedback="QA decisión manual")
        self._finish(production)
        self.assertEqual(production.state, "done")
        self.assertEqual(run.outcome, "business_done")
