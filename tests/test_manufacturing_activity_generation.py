from datetime import date, datetime
from unittest.mock import patch

from odoo.tests import tagged

from .manufacturing_activity_common import ManufacturingActivityCommon


@tagged("post_install", "-at_install")
class TestManufacturingActivityGeneration(ManufacturingActivityCommon):
    """El pendiente nace de una confirmación real y conserva el alcance de su MO."""

    def _service(self):
        self.assertIn(
            "mc.rov.manufacturing.activity.automation",
            self.env.registry.models,
            "Missing manufacturing activity generation service",
        )
        return self.env["mc.rov.manufacturing.activity.automation"]

    def _confirm_production(self, production):
        with patch("odoo.fields.Datetime.now", return_value=datetime(2026, 10, 16, 15)):
            production.action_confirm()
        return self._runs(production)

    def _other_company_production(self):
        company = self.env["res.company"].create({"name": "QA fabricación sin política"})
        warehouse = self.env["stock.warehouse"].create(
            {"name": "QA taller de fabricación", "code": "QAMF", "company_id": company.id}
        )
        return self._production(company_id=company.id, picking_type_id=warehouse.manu_type_id.id)

    def _remaining(self, production):
        result = production._split_productions(amounts={production: [1.0, 1.0]})
        remaining = result - production
        self.assertEqual(len(remaining), 1)
        return remaining

    def test_native_fresh_company_confirmation_fixture(self):
        production = self._other_company_production()
        production.action_confirm()
        self.assertEqual(production.state, "confirmed")
        self.assertNotEqual(production.company_id, self.env.company)

    def test_native_partial_production_fixture(self):
        production = self._production(product_qty=2)
        production.action_confirm()
        remaining = self._remaining(production)
        self.assertEqual(remaining.state, "confirmed")
        self.assertEqual(remaining.product_qty, 1)
        self.assertEqual(production.product_qty, 1)

    def test_draft_does_not_create_activity(self):
        self._service()
        self._policy()
        production = self._production()
        self.assertEqual(production.state, "draft")
        self.assertFalse(self._runs(production))

    def test_confirmation_creates_one_assigned_native_activity(self):
        self._service()
        policy = self._policy()
        production = self._production()
        run = self._confirm_production(production)
        self.assertEqual(len(run), 1)
        self.assertEqual(run.cycle, 1)
        self.assertEqual(run.outcome, "pending")
        self.assertEqual(run.original_deadline, date(2026, 11, 13))
        activity = run.activity_id
        self.assertTrue(activity.active)
        self.assertEqual(activity.res_model, "mrp.production")
        self.assertEqual(activity.res_id, production.id)
        self.assertEqual(activity.summary, "Completar fabricación")
        self.assertEqual(activity.user_id, policy.user_id)
        self.assertFalse(activity.mc_employee_id)
        self.assertEqual(activity.date_deadline, date(2026, 11, 13))

    def test_repeated_confirmation_does_not_duplicate(self):
        self._service()
        self._policy()
        production = self._production()
        original = self._confirm_production(production)
        self._confirm_production(production)
        self.assertEqual(self._runs(production), original)
        self.assertEqual(len(production.activity_ids), 1)

    def test_general_pause_does_not_block_native_confirmation(self):
        self._service()
        self._policy()
        control = self.env["mc.rov.automation.control"]
        row = control.search([("company_id", "=", self.env.company.id)])
        if row:
            row.enabled = False
        else:
            control.create({"company_id": self.env.company.id, "enabled": False})
        production = self._production()
        self._confirm_production(production)
        self.assertEqual(production.state, "confirmed")
        self.assertFalse(self._runs(production))

    def test_disabled_policy_does_not_create(self):
        self._service()
        self._policy(enabled=False)
        production = self._production()
        self._confirm_production(production)
        self.assertFalse(self._runs(production))

    def test_missing_recipient_leaves_notice_without_activity(self):
        self._service()
        self._policy(user_id=False)
        production = self._production()
        self._confirm_production(production)
        self.assertFalse(self._runs(production))
        self.assertTrue(
            production.message_ids.filtered(
                lambda message: "Seguimiento automático no generado" in str(message.body)
            )
        )

    def test_company_without_policy_does_not_infer_recipient(self):
        self._service()
        production = self._other_company_production()
        self._confirm_production(production)
        self.assertFalse(self._runs(production))
        self.assertTrue(
            production.message_ids.filtered(
                lambda message: "Seguimiento automático no generado" in str(message.body)
            )
        )

    def test_component_outside_rov_root_is_excluded(self):
        self._service()
        self._policy()
        # La exclusión debe ser independiente de categorías de ejemplo de la instalación.
        category = self.env["product.category"].create(
            {"name": "QA categoría ajena a ROV", "parent_id": False}
        )
        component = self.env["product.product"].create(
            {"name": "QA componente", "categ_id": category.id}
        )
        production = self._production(product_id=component.id)
        self._confirm_production(production)
        self.assertEqual(production.state, "confirmed")
        self.assertFalse(self._runs(production))
        self.assertFalse(production.activity_ids)

    def test_explicit_earlier_deadline_is_used_by_activity(self):
        self._service()
        self._policy()
        production = self._production(date_deadline=datetime(2026, 10, 30, 15))
        run = self._confirm_production(production)
        self.assertEqual(run.activity_id.date_deadline, date(2026, 10, 30))
        self.assertEqual(production.date_deadline, datetime(2026, 10, 30, 15))

    def test_regular_copy_waits_for_confirmation_and_has_no_parent(self):
        self._service()
        self._policy()
        production = self._production()
        original = self._confirm_production(production)
        copied = production.copy()
        self.assertEqual(copied.state, "draft")
        self.assertFalse(self._runs(copied))
        new_run = self._confirm_production(copied)
        self.assertEqual(len(new_run), 1)
        self.assertFalse(new_run.parent_run_id)
        self.assertNotEqual(new_run.activity_id, original.activity_id)

    def test_remaining_production_keeps_parent_and_original_deadline(self):
        self._service()
        self._policy()
        production = self._production(product_qty=2)
        original = self._confirm_production(production)
        remaining = self._remaining(production)
        run = self._runs(remaining)
        self.assertEqual(len(run), 1)
        self.assertEqual(run.parent_run_id, original)
        self.assertEqual(run.activity_id.date_deadline, original.activity_id.date_deadline)

    def test_remaining_production_keeps_manually_reprogrammed_deadline(self):
        self._service()
        self._policy()
        production = self._production(product_qty=2)
        original = self._confirm_production(production)
        original.activity_id.date_deadline = date(2026, 11, 6)
        remaining = self._remaining(production)
        self.assertEqual(self._runs(remaining).activity_id.date_deadline, date(2026, 11, 6))

    def test_edit_after_reactivation_does_not_backfill(self):
        self._service()
        policy = self._policy(enabled=False)
        production = self._production()
        self._confirm_production(production)
        policy.enabled = True
        production.write({"origin": "QA edición posterior"})
        self.assertFalse(self._runs(production))

    def test_unexpected_activity_failure_rolls_back_confirmation_and_history(self):
        self._service()
        self._policy()
        production = self._production()
        with self.assertRaises(RuntimeError), self.cr.savepoint(), patch.object(
            type(self.env["mail.activity"]),
            "create",
            side_effect=RuntimeError("QA activity failure"),
        ):
            production.action_confirm()
        self.assertEqual(production.state, "draft")
        self.assertFalse(self._runs(production))
        self.assertFalse(production.activity_ids)

    def test_activity_type_has_no_automatic_successor(self):
        self._service()
        kind = self.env.ref(
            "mc_rov.activity_type_manufacturing_complete", raise_if_not_found=False
        )
        self.assertTrue(kind, "Missing native manufacturing activity type")
        self.assertEqual(kind.res_model, "mrp.production")
        self.assertEqual(kind.chaining_type, "suggest")
        self.assertFalse(kind.triggered_next_type_id)

    def test_ready_to_close_is_not_a_finished_production(self):
        self._service()
        self._policy()
        production = self._production()
        run = self._confirm_production(production)
        production.qty_producing = 1
        self.assertEqual(production.state, "to_close")
        self.assertEqual(self._runs(production), run)
        self.assertEqual(run.outcome, "pending")
