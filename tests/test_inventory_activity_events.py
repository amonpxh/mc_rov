"""Eventos reales de stock y asistentes de parciales, sin sustituir sus resultados."""

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import tagged

from .inventory_activity_common import InventoryActivityCommon


class InventoryEventCommon(InventoryActivityCommon):
    """Operaciones transaccionales propias; cantidades y asistentes siguen siendo nativos."""

    instant = datetime(2026, 10, 30, 15)

    def _stock(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.locations["stock"], 20
        )

    def _confirm(self, picking):
        with patch.object(fields.Datetime, "now", return_value=self.instant):
            picking.with_user(self.operator).action_confirm()
        for operation in picking:
            self.assertIn(operation.state, ("confirmed", "waiting", "assigned"))
        return picking

    def _finish(self, picking, quantity=None):
        if picking.state == "draft":
            self._confirm(picking)
        for move in picking.move_ids.filtered(
            lambda record: record.state not in ("done", "cancel")
        ):
            move.with_user(self.operator).write(
                {
                    "quantity": quantity if quantity is not None else move.product_uom_qty,
                    "picked": True,
                }
            )
        acting = picking.with_user(self.operator)
        result = acting.button_validate()
        if isinstance(result, dict) and result.get("res_model") == "stock.backorder.confirmation":
            self.env["stock.backorder.confirmation"].with_user(self.operator).with_context(
                **result.get("context", {})
            ).create(
                {
                    "pick_ids": [Command.set(picking.ids)],
                    "backorder_confirmation_line_ids": [
                        Command.create({"picking_id": picking.id, "to_backorder": True})
                    ],
                }
            ).process()
        else:
            self.assertIs(result, True, "Unexpected native validation assistant")
        self.assertEqual(picking.state, "done")
        return self.env["stock.picking"].search([("backorder_id", "=", picking.id)])

    def _return(self, picking):
        self.types["incoming"].return_picking_type_id = self.types["outgoing"]
        wizard = (
            self.env["stock.return.picking"]
            .with_user(self.operator)
            .create({"picking_id": picking.id})
        )
        self.assertEqual(len(wizard.product_return_moves), 1)
        wizard.product_return_moves.quantity = 1
        result = wizard.action_create_returns()
        returned = self.env["stock.picking"].browse(result["res_id"])
        self.assertEqual(returned.return_id, picking)
        self.assertIn(returned.state, ("confirmed", "waiting", "assigned"))
        return returned

    def _prepared(self, code="incoming", quantity=2):
        self.types[code].create_backorder = "ask"
        picking = self._picking(code, scheduled_date=self.instant)
        picking.move_ids.product_uom_qty = quantity
        if code != "incoming":
            self._stock()
        return picking


@tagged("post_install", "-at_install")
class TestInventoryNativeEventFixtures(InventoryEventCommon):
    """Llegar al evento nativo debe funcionar antes de instalar el seguimiento."""

    def test_native_reservation_and_completion(self):
        for code in ("incoming", "outgoing", "internal"):
            picking = self._confirm(self._prepared(code))
            picking.with_user(self.operator).action_assign()
            self.assertFalse(self._finish(picking))

    def test_native_partial_wizard_creates_remaining(self):
        picking = self._confirm(self._prepared())
        remaining = self._finish(picking, 1)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining.move_ids.product_uom_qty, 1)
        self.assertIn(remaining.state, ("confirmed", "waiting", "assigned"))

    def test_native_nested_partial_retains_quantities(self):
        first = self._confirm(self._prepared(quantity=3))
        second = self._finish(first, 1)
        third = self._finish(second, 1)
        self.assertEqual(third.move_ids.product_uom_qty, 1)
        self.assertFalse(self._finish(third))

    def test_native_return_has_new_document(self):
        picking = self._prepared()
        self._finish(picking)
        returned = self._return(picking)
        self.assertNotEqual(returned, picking)
        self.assertEqual(returned.picking_type_id, self.types["outgoing"])

    def test_native_move_confirmation_updates_picking(self):
        picking = self._prepared()
        moves = picking.move_ids.with_user(self.operator)._action_confirm()
        self.assertEqual(moves.picking_id, picking)
        self.assertIn(picking.state, ("confirmed", "waiting", "assigned"))

    def test_native_create_with_confirmed_move(self):
        picking = self._picking(
            move_ids=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 2,
                        "product_uom": self.product.uom_id.id,
                        "state": "confirmed",
                        "location_id": self.locations["supplier"].id,
                        "location_dest_id": self.locations["stock"].id,
                    }
                )
            ]
        )
        self.assertIn(picking.state, ("confirmed", "waiting", "assigned"))


@tagged("post_install", "-at_install")
# Cada evento comprueba una transición de negocio distinta.
# pylint: disable=too-many-public-methods
class TestInventoryActivityEvents(InventoryEventCommon):
    """Un pendiente por operación y un compromiso heredado por los restantes."""

    def _events(self):
        self.assertIn(
            "mc.rov.inventory.activity.automation",
            self.env.registry.models,
            "Missing inventory event automation",
        )
        self.assertIn(
            "mc.rov.inventory.activity.lifecycle",
            self.env.registry.models,
            "Missing inventory event automation lifecycle",
        )

    def _case(self, code="incoming", quantity=2):
        self._events()
        policy = self._policy()
        self._rule(self.types[code], policy=policy)
        return policy, self._prepared(code, quantity)

    def _cycle(self, picking):
        return self.env["mc.rov.inventory.activity.cycle"].search(
            [("picking_id", "=", picking.id)]
        )

    def _runs(self, picking):
        return self.env["mc.rov.inventory.activity.run"].search([("picking_id", "=", picking.id)])

    def _pending(self, picking, count=1):
        runs = self._runs(picking)
        pending = runs.filtered(lambda run: run.outcome == "pending")
        self.assertEqual(len(pending), count)
        for run in pending:
            self.assertTrue(run.activity_id.exists())
            self.assertEqual(run.activity_id.res_id, picking.id)
            self.assertEqual(run.activity_id.res_model, "stock.picking")
            self.assertEqual(run.activity_id.user_id, self.operator)
        return pending

    def test_draft_has_no_cycle_or_activity(self):
        _policy, picking = self._case()
        self.assertFalse(self._cycle(picking))
        self._pending(picking, 0)

    def _confirmation_kind(self, code, suffix):
        _policy, picking = self._case(code)
        self._confirm(picking)
        run = self._pending(picking)
        self.assertEqual(
            run.activity_id.activity_type_id,
            self.env.ref("mc_rov.activity_type_inventory_" + suffix),
        )
        self.assertEqual(len(self._cycle(picking)), 1)

    def test_incoming_confirmation_creates_receipt(self):
        self._confirmation_kind("incoming", "receipt")

    def test_outgoing_confirmation_creates_delivery(self):
        self._confirmation_kind("outgoing", "delivery")

    def test_internal_confirmation_creates_transfer(self):
        self._confirmation_kind("internal", "transfer")

    def test_repeated_confirmation_does_not_duplicate(self):
        _policy, picking = self._case()
        self._confirm(picking)
        original = self._pending(picking)
        self._confirm(picking)
        self.assertEqual(self._pending(picking), original)
        self.assertEqual(len(self._runs(picking)), 1)

    def test_reservation_does_not_close_pending(self):
        _policy, picking = self._case("outgoing")
        self._confirm(picking)
        run = self._pending(picking)
        picking.with_user(self.operator).action_assign()
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(self._pending(picking), run)

    def test_native_move_autoconfirmation_generates(self):
        _policy, picking = self._case()
        picking.move_ids.with_user(self.operator)._action_confirm()
        self._pending(picking)

    def test_create_with_confirmed_move_generates(self):
        self._events()
        self._rule(policy=self._policy())
        picking = self._picking(
            move_ids=[
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_uom_qty": 2,
                        "product_uom": self.product.uom_id.id,
                        "state": "confirmed",
                        "location_id": self.locations["supplier"].id,
                        "location_dest_id": self.locations["stock"].id,
                    }
                )
            ]
        )
        self._pending(picking)

    def test_batch_confirmation_keeps_distinct_identities(self):
        _policy, first = self._case()
        second = self._prepared()
        self._confirm(first | second)
        self._pending(first)
        self._pending(second)
        self.assertNotEqual(self._cycle(first), self._cycle(second))

    def test_batch_move_confirmation_keeps_each_document(self):
        _policy, first = self._case()
        second = self._prepared()
        (first | second).move_ids.with_user(self.operator)._action_confirm()
        self._pending(first)
        self._pending(second)

    def test_button_validate_from_draft_captures_and_closes(self):
        _policy, picking = self._case()
        picking.move_ids.write({"quantity": 2, "picked": True})
        self.assertIs(picking.with_user(self.operator).button_validate(), True)
        self.assertEqual(picking.state, "done")
        self._pending(picking, 0)
        self.assertEqual(self._runs(picking).outcome, "business_done")

    def _done_kind(self, code):
        _policy, picking = self._case(code)
        self._confirm(picking)
        self._pending(picking)
        self._finish(picking)
        self._pending(picking, 0)
        self.assertEqual(self._runs(picking).outcome, "business_done")

    def test_receipt_done_closes_only_own_pending(self):
        self._done_kind("incoming")

    def test_delivery_done_closes_pending(self):
        self._done_kind("outgoing")

    def test_transfer_done_closes_pending(self):
        self._done_kind("internal")

    def test_native_cancel_records_cancellation(self):
        _policy, picking = self._case()
        self._confirm(picking)
        picking.with_user(self.operator).action_cancel()
        self.assertEqual(picking.state, "cancel")
        self._pending(picking, 0)
        self.assertEqual(self._runs(picking).outcome, "cancelled")

    def test_batch_cancel_closes_each_pending(self):
        _policy, first = self._case()
        second = self._prepared()
        self._confirm(first | second)
        (first | second).with_user(self.operator).action_cancel()
        self._pending(first, 0)
        self._pending(second, 0)
        self.assertEqual(
            (self._runs(first) | self._runs(second)).mapped("outcome"), ["cancelled", "cancelled"]
        )

    def test_direct_move_done_closes_picking_pending(self):
        _policy, picking = self._case()
        self._confirm(picking)
        picking.move_ids.write({"quantity": 2, "picked": True})
        picking.move_ids.with_user(self.operator)._action_done()
        self.assertEqual(picking.state, "done")
        self._pending(picking, 0)

    def test_direct_move_cancel_closes_picking_pending(self):
        _policy, picking = self._case()
        self._confirm(picking)
        picking.move_ids.with_user(self.operator)._action_cancel()
        self.assertEqual(picking.state, "cancel")
        self._pending(picking, 0)

    def test_partial_inherits_deadline_and_closes_original(self):
        _policy, picking = self._case()
        self._confirm(picking)
        parent = self._cycle(picking)
        remaining = self._finish(picking, 1)
        self._pending(picking, 0)
        run = self._pending(remaining)
        self.assertEqual(self._cycle(remaining).parent_id, parent)
        self.assertEqual(run.current_deadline, parent.current_deadline)
        self.assertEqual(self._cycle(remaining).original_deadline, parent.original_deadline)

    def test_nested_remaining_keeps_same_deadline(self):
        _policy, picking = self._case(quantity=3)
        self._confirm(picking)
        deadline = self._cycle(picking).current_deadline
        second = self._finish(picking, 1)
        third = self._finish(second, 1)
        self.assertEqual(self._pending(third).current_deadline, deadline)
        self.assertEqual(self._cycle(third).parent_id, self._cycle(second))
        self._pending(picking, 0)
        self._pending(second, 0)

    def test_partial_keeps_earlier_native_commitment(self):
        _policy, picking = self._case()
        picking.date_deadline = datetime(2026, 11, 2, 15)
        self._confirm(picking)
        parent = self._cycle(picking)
        self.assertEqual(parent.current_deadline, fields.Date.to_date("2026-11-02"))
        remaining = self._finish(picking, 1)
        self.assertEqual(self._pending(remaining).current_deadline, parent.current_deadline)

    def test_partial_inherits_current_captured_deadline(self):
        _policy, picking = self._case()
        self._confirm(picking)
        cycle = self._cycle(picking)
        original = cycle.original_deadline
        # Simula un compromiso ya autorizado; la autorización manual se cubre en Task3.
        cycle.current_deadline = original + timedelta(days=2)
        remaining = self._finish(picking, 1)
        self.assertEqual(self._pending(remaining).current_deadline, cycle.current_deadline)
        self.assertEqual(cycle.original_deadline, original)

    def test_return_uses_new_cycle_in_selected_type(self):
        policy, picking = self._case()
        self._rule(self.types["outgoing"], policy=policy)
        self._finish(picking)
        returned = self._return(picking)
        self._pending(returned)
        self.assertNotEqual(self._cycle(returned), self._cycle(picking))
        self.assertFalse(self._cycle(returned).parent_id)

    def test_absent_policy_creates_nothing(self):
        self._events()
        picking = self._confirm(self._prepared())
        self.assertFalse(self._cycle(picking))

    def test_disabled_policy_creates_nothing(self):
        policy, picking = self._case()
        policy.enabled = False
        self._confirm(picking)
        self.assertFalse(self._cycle(picking))

    def test_removed_type_rule_creates_nothing(self):
        policy, picking = self._case()
        policy.rule_ids.unlink()
        self._confirm(picking)
        self.assertFalse(self._cycle(picking))

    def _pause(self):
        model = self.env["mc.rov.automation.control"]
        control = model.search([("company_id", "=", self.env.company.id)])
        if not control:
            control = model.create({"company_id": self.env.company.id})
        control.enabled = False

    def test_general_pause_prevents_new_pending(self):
        _policy, picking = self._case()
        self._pause()
        self._confirm(picking)
        self.assertFalse(self._cycle(picking))

    def test_pause_does_not_prevent_real_closure(self):
        policy, picking = self._case()
        self._confirm(picking)
        self._pending(picking)
        policy.enabled = False
        self._pause()
        self._finish(picking)
        self._pending(picking, 0)
        self.assertEqual(self._runs(picking).outcome, "business_done")

    def test_future_schedule_captured_as_anchor(self):
        policy, picking = self._case()
        picking.scheduled_date = datetime(2026, 11, 5, 15)
        self._confirm(picking)
        self.assertEqual(self._cycle(picking).anchor_at, picking.scheduled_date)
        self.assertEqual(
            self._pending(picking).current_deadline,
            policy._deadline(self.instant, picking.scheduled_date),
        )

    def test_schedule_edit_does_not_duplicate_or_extend(self):
        _policy, picking = self._case()
        self._confirm(picking)
        run = self._pending(picking)
        deadline = run.current_deadline
        picking.scheduled_date = datetime(2026, 12, 1, 15)
        self.assertEqual(self._pending(picking), run)
        self.assertEqual(run.current_deadline, deadline)

    def test_confirmation_does_not_validate_stock(self):
        _policy, picking = self._case()
        before = (
            self.env["stock.quant"]
            .search([("product_id", "=", self.product.id)])
            .read(["quantity"])
        )
        self._confirm(picking)
        self._pending(picking)
        after = (
            self.env["stock.quant"]
            .search([("product_id", "=", self.product.id)])
            .read(["quantity"])
        )
        self.assertEqual(after, before)
        self.assertNotEqual(picking.state, "done")

    def test_native_activity_is_not_closed_with_own_pending(self):
        _policy, picking = self._case()
        self._confirm(picking)
        native = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("stock.picking"),
                "res_id": picking.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "user_id": self.operator.id,
                "summary": "QA aviso independiente",
            }
        )
        self._finish(picking)
        self._pending(picking, 0)
        self.assertTrue(native.exists())
