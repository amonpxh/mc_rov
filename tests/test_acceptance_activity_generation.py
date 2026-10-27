from datetime import date, datetime
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install")
# Cada escenario prueba una frontera independiente; tres validan primero MRP nativo.
# pylint: disable=too-many-public-methods
class TestAcceptanceActivityGeneration(AcceptanceActivityCommon):
    """Aceptar lo efectivamente fabricado, no lo previsto ni la fabricación restante."""

    def _service(self):
        self.assertIn(
            "mc.rov.acceptance.activity.automation",
            self.env.registry.models,
            "Missing acceptance activity generation service",
        )
        return self.env["mc.rov.acceptance.activity.automation"]

    def _cycles(self, production):
        return self.env["mc.rov.acceptance.activity.cycle"].search(
            [("production_id", "=", production.id)]
        )

    def _remaining(self, production):
        return self.env["mrp.production"].search(
            [
                ("production_group_id", "=", production.production_group_id.id),
                ("id", "!=", production.id),
            ]
        )

    def test_native_finished_serial_has_real_done_move_lines(self):
        production = self._finished_production()
        self.assertEqual(production.state, "done")
        lines = production.move_finished_ids.filtered(
            lambda move: move.product_id == production.product_id and move.state == "done"
        ).move_line_ids
        self.assertEqual(len(lines.lot_id), 1)
        self.assertGreater(sum(lines.mapped("quantity")), 0)

    def test_native_two_serials_are_really_produced(self):
        production = self._finished_production(quantity=2)
        self.assertEqual(production.state, "done")
        lines = production.move_finished_ids.filtered(
            lambda move: move.product_id == production.product_id and move.state == "done"
        ).move_line_ids
        self.assertEqual(len(lines.lot_id), 2)
        self.assertEqual(sum(lines.mapped("quantity")), 2)

    def test_native_partial_keeps_remaining_unfinished(self):
        production = self._production(product_qty=2)
        production.action_confirm()
        self._finish_acceptance_production(
            production, skip_backorder=True, mo_ids_to_backorder=production.ids
        )
        self.assertEqual(production.state, "done")
        remaining = self._remaining(production)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining.product_qty, 1)
        self.assertNotEqual(remaining.state, "done")

    def test_draft_has_no_acceptance(self):
        self._service()
        self._acceptance_policy()
        production = self._production()
        self.assertFalse(self._cycles(production))

    def test_confirmation_is_not_acceptance_start(self):
        self._service()
        self._acceptance_policy()
        production = self._production()
        production.action_confirm()
        self.assertFalse(self._cycles(production))

    def test_prepared_serial_without_done_moves_is_not_produced(self):
        service = self._service()
        self._acceptance_policy()
        production = self._production()
        production.action_confirm()
        production.write(
            {"lot_producing_ids": [Command.set(self._serials().ids)], "qty_producing": 1}
        )
        self.assertFalse(service._produced_lots(production))
        self.assertFalse(self._cycles(production))

    def test_backorder_wizard_before_done_creates_nothing(self):
        self._service()
        self._acceptance_policy()
        production = self._production(product_qty=2)
        production.action_confirm()
        production.picking_type_id.create_backorder = "ask"
        result = self._finish_acceptance_production(production)
        self.assertEqual(result.get("res_model"), "mrp.production.backorder")
        self.assertNotEqual(production.state, "done")
        self.assertFalse(self._cycles(production))

    def test_done_creates_two_activities_with_policy_account_and_deadline(self):
        service = self._service()
        policy = self._acceptance_policy(employee_id=self.empleado.id)
        with patch("odoo.fields.Datetime.now", return_value=datetime(2026, 10, 16, 15)):
            production = self._finished_production()
        cycles = self._cycles(production)
        self.assertEqual(len(cycles), 1)
        activities = self._acceptance_activities(service._produced_lots(production))
        self.assertEqual(len(activities), 2)
        self.assertEqual(activities.user_id, policy.user_id)
        self.assertEqual(activities.mc_employee_id, self.empleado)
        self.assertEqual(set(activities.mapped("date_deadline")), {date(2026, 10, 19)})

    def test_two_completed_serials_get_independent_cycles(self):
        service = self._service()
        self._acceptance_policy()
        production = self._finished_production(quantity=2)
        self.assertEqual(len(self._cycles(production)), 2)
        self.assertEqual(len(self._acceptance_activities(service._produced_lots(production))), 4)

    def test_partial_only_starts_for_completed_unit(self):
        service = self._service()
        self._acceptance_policy()
        production = self._production(product_qty=2)
        production.action_confirm()
        self._finish_acceptance_production(
            production, skip_backorder=True, mo_ids_to_backorder=production.ids
        )
        self.assertEqual(len(self._cycles(production)), 1)
        self.assertFalse(self._cycles(self._remaining(production)))
        self.assertEqual(len(self._acceptance_activities(service._produced_lots(production))), 2)

    def test_repeated_start_does_not_duplicate(self):
        service = self._service()
        self._acceptance_policy()
        production = self._finished_production()
        lot = service._produced_lots(production)
        service._start(production, lot, datetime(2026, 10, 16, 15))
        self.assertEqual(len(self._cycles(production)), 1)
        self.assertEqual(len(self._acceptance_activities(lot)), 2)

    def test_disabled_policy_keeps_native_completion_without_acceptance(self):
        self._service()
        self._acceptance_policy(enabled=False)
        production = self._finished_production()
        self.assertEqual(production.state, "done")
        self.assertFalse(self._cycles(production))

    def test_general_pause_does_not_prevent_completion(self):
        self._service()
        self._acceptance_policy()
        control = self.env["mc.rov.automation.control"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        if control:
            control.enabled = False
        else:
            self.env["mc.rov.automation.control"].create(
                {"company_id": self.env.company.id, "enabled": False}
            )
        production = self._finished_production()
        self.assertEqual(production.state, "done")
        self.assertFalse(self._cycles(production))

    def test_missing_account_leaves_notice_without_blocking_completion(self):
        self._service()
        self._acceptance_policy(user_id=False)
        production = self._finished_production()
        self.assertEqual(production.state, "done")
        self.assertFalse(self._cycles(production))
        self.assertTrue(
            production.message_ids.filtered(
                lambda message: "aceptación" in (message.body or "").lower()
            )
        )

    def test_product_outside_rov_root_does_not_start_acceptance(self):
        self._service()
        self._acceptance_policy()
        category = self.env["product.category"].create({"name": "QA producto ajeno a ROV"})
        self.product.categ_id = category
        production = self._finished_production()
        self.assertEqual(production.state, "done")
        self.assertFalse(self._cycles(production))

    def test_product_without_serial_does_not_invent_equipment(self):
        self._service()
        self._acceptance_policy()
        product = self.env["product.product"].create(
            {"name": "QA sin serie", "categ_id": self.product.categ_id.id, "tracking": "none"}
        )
        production = self._production(product_id=product.id, product_uom_id=product.uom_id.id)
        production.action_confirm()
        self._finish_acceptance_production(production, lots=self.env["stock.lot"])
        self.assertEqual(production.state, "done")
        self.assertFalse(self._cycles(production))

    def test_edit_after_reactivation_does_not_backfill(self):
        self._service()
        policy = self._acceptance_policy(enabled=False)
        production = self._finished_production()
        policy.enabled = True
        production.write({"origin": "QA edición posterior sin reconstruir aceptación"})
        self.assertFalse(self._cycles(production))

    def test_activity_failure_rolls_back_completion_and_both_pending_stages(self):
        self._service()
        self._acceptance_policy()
        production = self._production()
        production.action_confirm()
        lots = self._serials()
        with self.assertRaises(RuntimeError), self.cr.savepoint(), patch.object(
            type(self.env["mail.activity"]),
            "create",
            side_effect=RuntimeError("QA aceptación atómica"),
        ):
            self._finish_acceptance_production(production, lots)
        self.assertEqual(production.state, "confirmed")
        self.assertFalse(self._cycles(production))
        self.assertFalse(self._acceptance_activities(lots))

    def test_activity_types_do_not_chain_or_invent_technical_documents(self):
        self._service()
        self._acceptance_policy()
        before = self.env["mc.rov.revision"].search_count([])
        fen_before = self.env["mc.rov.ficha.equipo.nuevo"].search_count([])
        self._finished_production()
        for suffix in ("performance", "field"):
            kind = self.env.ref("mc_rov.activity_type_acceptance_" + suffix)
            self.assertEqual(kind.res_model, "stock.lot")
            self.assertFalse(kind.triggered_next_type_id)
        self.assertEqual(self.env["mc.rov.revision"].search_count([]), before)
        self.assertEqual(self.env["mc.rov.ficha.equipo.nuevo"].search_count([]), fen_before)
