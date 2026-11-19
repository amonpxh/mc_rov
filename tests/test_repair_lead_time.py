"""F6 conserva fechas reales con movimientos y permisos nativos."""

from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

from .test_customer_commitment_browser import dispatch_wizard, prepare_f3_case


@tagged("post_install", "-at_install", "repair_lead_time")
class TestRepairLeadTime(TransactionCase):
    """Las constancias pertenecen a la misma recepción y serie."""

    def _case(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        repair, outgoing, attachment = prepare_f3_case(self.env, warehouse, "F6")
        receipt = self._receive(warehouse, repair)
        operator = new_test_user(
            self.env,
            login="qa_f6_operator",
            groups="stock.group_stock_manager,mc_rov.group_work_assignment_team,"
            "mc_rov.group_customer_commitment_supervisor",
        )
        return repair.with_user(operator), receipt, outgoing.with_user(operator), attachment

    def _receive(self, warehouse, repair):
        source, target = repair.partner_id.property_stock_customer, warehouse.lot_stock_id
        receipt = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.in_type_id.id,
                "partner_id": repair.partner_id.id,
                "location_id": source.id,
                "location_dest_id": target.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": repair.product_id.id,
                            "product_uom": repair.product_uom.id,
                            "product_uom_qty": 1,
                            "location_id": source.id,
                            "location_dest_id": target.id,
                        }
                    )
                ],
            }
        )
        receipt.action_confirm()
        receipt.move_ids.quantity = 1
        receipt.move_line_ids.lot_id = repair.lot_id
        receipt.move_ids.picked = True
        receipt.button_validate()
        self.assertEqual(receipt.state, "done")
        return receipt

    def _wizard(self, repair, picking, **values):
        action = repair.action_mc_record_arrival()
        return (
            repair.env[action["res_model"]]
            .with_context(**action["context"])
            .create({"picking_id": picking.id, **values})
        )

    def test_capture_and_measure_without_sale_promise(self):
        repair, receipt, outgoing, attachment = self._case()
        now = fields.Datetime.now()
        dispatch_wizard(outgoing, repair, attachment, now).action_apply()
        service = repair.env["mc.rov.repair.lead.time.kpi"]
        self.assertEqual(service.get_summary()["missing_arrival"], 1)
        self.assertFalse(repair.mc_arrived_at)
        wizard = self._wizard(repair, receipt)
        wizard.action_apply()
        wizard.action_apply()
        self.assertEqual(repair.mc_arrived_at, receipt.date_done)
        result = service.get_summary()
        self.assertEqual((result["samples"], result["median_days"]), (1, 0))

    def test_delayed_validation_uses_earlier_arrival_and_preserves_actor(self):
        repair, receipt, _outgoing, _attachment = self._case()
        actual = receipt.date_done - timedelta(days=3)
        self._wizard(
            repair, receipt, delayed=True, arrived_at=actual, reason="Validación posterior QA"
        ).action_apply()
        event = self.env["mc.rov.repair.arrival"].sudo().search([("repair_id", "=", repair.id)])
        self.assertEqual((event.arrived_at, event.validated_at), (actual, receipt.date_done))
        self.assertEqual(event.actor_id, repair.env.user)
        with self.assertRaises(AccessError):
            event.write({"arrived_at": receipt.date_done})

    def test_rejects_later_time_and_wrong_transfer(self):
        repair, receipt, outgoing, _attachment = self._case()
        with self.assertRaises(UserError):
            self._wizard(repair, outgoing).action_apply()
        with self.assertRaises(UserError):
            self._wizard(
                repair, receipt, delayed=True, arrived_at=receipt.date_done, reason="QA"
            ).action_apply()

    def test_without_team_access_cannot_request_metrics(self):
        viewer = new_test_user(
            self.env, login="qa_f6_without_team", groups="stock.group_stock_user"
        )
        with self.assertRaises(AccessError):
            self.env["mc.rov.repair.lead.time.kpi"].with_user(viewer).get_summary()
