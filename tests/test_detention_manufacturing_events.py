"""Caracteriza cierres MRP reales: botón, asistentes, parciales y movimientos."""

from odoo import Command, _
from odoo.exceptions import UserError
from odoo.tests import tagged

from . import test_detention_capture as capture_contracts
from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install", "detention_manufacturing_events")
class TestDetentionManufacturingEvents(AcceptanceActivityCommon):
    """Los intervalos solo terminan cuando termina de verdad la orden de origen."""

    _service = capture_contracts.TestDetentionCapture._service
    _workshop = capture_contracts.TestDetentionCapture._workshop
    _start = capture_contracts.TestDetentionCapture._start
    _history = capture_contracts.TestDetentionCapture._history

    def _confirmed(self, quantity=1):
        production = self._production(product_qty=quantity)
        production.action_confirm()
        return production

    def _ready(self, production):
        production.write({"lot_producing_ids": [Command.set(self.lot.ids)], "qty_producing": 1})

    def _finish(self, production, **context):
        self._ready(production)
        return production.with_context(skip_redirection=True, **context).button_mark_done()

    def _stopped(self, quantity=1):
        service = self._service()
        production = self._confirmed(quantity)
        self._start(service, production)
        return service, production, self._history(service, production)[0]

    def _assert_closed(self, service, production, original):
        current = self._history(service, production)[0]
        self.assertTrue(
            current["ended_at"],
            "F2 debe cerrar al terminar Fabricación por evento nativo",
        )
        self.assertEqual(current["end_kind"], "source_closed")
        self.assertEqual(current["closed_by_id"], self.env.uid)
        for key in ("id", "started_at", "actor_id", "responsible_employee_id", "cause"):
            self.assertEqual(current[key], original[key])

    def test_native_serial_completion_fixture(self):
        production = self._confirmed()
        self._finish(production)
        self.assertEqual(production.state, "done")
        self.assertEqual(set(production.move_finished_ids.mapped("state")), {"done"})

    def test_native_backorder_prompt_fixture(self):
        production = self._confirmed(2)
        production.picking_type_id.create_backorder = "ask"
        result = self._finish(production)
        self.assertEqual(result.get("res_model"), "mrp.production.backorder")
        self.assertNotEqual(production.state, "done")

    def test_button_completion_closes_detention(self):
        service, production, original = self._stopped()
        self._finish(production)
        self.assertEqual(production.state, "done")
        self._assert_closed(service, production, original)

    def test_shop_floor_completion_closes_detention(self):
        service, production, original = self._stopped()
        self._finish(production, from_workorder=True)
        self.assertEqual(production.state, "done")
        self._assert_closed(service, production, original)

    def test_pending_backorder_prompt_keeps_detention(self):
        service, production, original = self._stopped(2)
        production.picking_type_id.create_backorder = "ask"
        result = self._finish(production)
        self.assertEqual(result.get("res_model"), "mrp.production.backorder")
        self.assertNotEqual(production.state, "done")
        self.assertEqual(self._history(service, production)[0], original)

    def test_ready_to_close_keeps_detention(self):
        service, production, original = self._stopped()
        self._ready(production)
        self.assertEqual(production.state, "to_close")
        self.assertEqual(self._history(service, production)[0], original)

    def test_native_partial_closes_only_completed_origin(self):
        service, production, original = self._stopped(2)
        self._finish(production, skip_backorder=True, mo_ids_to_backorder=production.ids)
        self.assertEqual(production.state, "done")
        remaining = self.env["mrp.production"].search(
            [
                ("production_group_id", "=", production.production_group_id.id),
                ("id", "!=", production.id),
            ]
        )
        self.assertEqual(len(remaining), 1)
        self.assertNotIn(remaining.state, ("done", "cancel"))
        self._assert_closed(service, production, original)

    def test_direct_finished_move_cancellation_closes_detention(self):
        service, production, original = self._stopped()
        self.assertTrue(production.move_finished_ids)
        production.move_finished_ids.with_context(skip_mo_check=True)._action_cancel()
        self.assertEqual(production.state, "cancel")
        self._assert_closed(service, production, original)

    def test_direct_stock_completion_closes_detention(self):
        service = self._service()
        production = self._production()
        component = self.env["product.product"].create({"name": "QA F2 componente consumido"})
        raw = self.env["stock.move"].create(
            production._get_move_raw_values(component, 1, component.uom_id)
        )
        production.action_confirm()
        self._start(service, production)
        original = self._history(service, production)[0]
        self._ready(production)
        raw.write({"quantity": 1, "picked": True})
        raw._action_done()
        self.assertNotIn(production.state, ("done", "cancel"))
        self.assertEqual(self._history(service, production)[0], original)
        finished = production.move_finished_ids.filtered(
            lambda row: row.product_id == self.product
        )
        finished.write({"lot_ids": [Command.set(self.lot.ids)], "quantity": 1, "picked": True})
        finished._action_done()
        self.assertEqual(production.state, "done")
        self._assert_closed(service, production, original)

    def test_completion_rollback_preserves_open_source_and_evidence(self):
        service, production, original = self._stopped()
        previous_state = production.state
        with self.assertRaisesRegex(UserError, "Rollback F2"), self.env.cr.savepoint():
            self._finish(production)
            self.assertEqual(production.state, "done")
            raise UserError(_("Rollback F2"))
        self.assertEqual(production.state, previous_state)
        self.assertEqual(self._history(service, production)[0], original)
