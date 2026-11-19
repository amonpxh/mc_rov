"""Constancias sobre operaciones de Inventario validadas por el flujo nativo."""

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .test_inventory_activity_events import InventoryEventCommon


@tagged("post_install", "-at_install", "customer_commitment")
class TestCustomerDispatch(InventoryEventCommon):
    """La constancia acredita la fecha física y conserva sus ediciones."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].set_param("mc_rov.rov_category_id", cls.product.categ_id.id)
        cls.supervisor = new_test_user(
            cls.env,
            login="qa_dispatch_supervisor",
            groups="stock.group_stock_user,mc_rov.group_customer_commitment_supervisor",
        )

    def _evidence(self, picking):
        return self.env["ir.attachment"].create(
            {
                "name": "Constancia ficticia",
                "type": "url",
                "url": "https://example.com/constancia-ficticia",
                "res_model": "stock.picking",
                "res_id": picking.id,
            }
        )

    def _dispatch_rows(self, picking):
        return (
            self.env["mc.rov.customer.dispatch"]
            .sudo()
            .search([("picking_id", "=", picking.id)], order="id")
        )

    def _open_dispatch(self, picking, *, invalidation=False):
        acting = picking.with_user(self.supervisor)
        action = (
            acting.action_open_customer_dispatch_invalidation()
            if invalidation
            else acting.action_open_customer_dispatch()
        )
        return acting.env[action["res_model"]].browse(action["res_id"])

    def _document_pickup(self, wizard, attachment, **values):
        wizard.write(
            {
                "mode": "pickup",
                "precision": "date",
                "effective_date": "2026-01-10",
                "attachment_id": attachment.id,
                **values,
            }
        )
        wizard.action_apply()

    def test_qualified_partial_keeps_own_date_and_leaves_backorder_unattested(self):
        picking = self._prepared("outgoing")
        backorder = self._finish(picking, quantity=1)
        evidence = self._evidence(picking)
        wizard = self._open_dispatch(picking)
        self._document_pickup(wizard, evidence)

        event = self._dispatch_rows(picking).ensure_one()
        self.assertEqual(event.kind, "confirmed")
        self.assertEqual(event.mode, "pickup")
        self.assertEqual(event.effective_date.isoformat(), "2026-01-10")
        self.assertFalse(event.effective_at)
        self.assertEqual(event.actor_id, self.supervisor)
        self.assertEqual(event.attachment_id, evidence)
        self.assertFalse(self._dispatch_rows(backorder))
        self.assertIn("Constancia ficticia", picking.with_user(self.operator).mc_dispatch_history)
        with self.assertRaises(AccessError):
            event.with_user(self.operator).read(["effective_date"])

    def test_correction_and_invalidation_preserve_distinct_events(self):
        picking = self._prepared("outgoing")
        self._finish(picking)
        evidence = self._evidence(picking)
        self._document_pickup(self._open_dispatch(picking), evidence)
        wizard = self._open_dispatch(picking)
        self._document_pickup(
            wizard,
            evidence,
            precision="datetime",
            effective_at="2026-01-11 14:30:00",
            reason="La constancia incluye hora.",
        )
        invalidation = self._open_dispatch(picking, invalidation=True)
        invalidation.reason = "La firma corresponde a otra salida."
        invalidation.action_apply()

        original, correction, last = self._dispatch_rows(picking)
        self.assertEqual(original.effective_date.isoformat(), "2026-01-10")
        self.assertEqual(correction.kind, "corrected")
        self.assertEqual(str(correction.effective_at), "2026-01-11 14:30:00")
        self.assertFalse(correction.effective_date)
        self.assertEqual(last.kind, "invalidated")
        self.assertEqual(last.previous_id, correction)
        with self.assertRaises(AccessError):
            original.write({"reason": "Reescribir historial"})

    def test_same_snapshot_cannot_post_twice(self):
        picking = self._prepared("outgoing")
        self._finish(picking)
        evidence = self._evidence(picking)
        first = self._open_dispatch(picking)
        second = self._open_dispatch(picking)
        self._document_pickup(first, evidence)
        with self.assertRaises(UserError):
            self._document_pickup(second, evidence)
        self.assertEqual(len(self._dispatch_rows(picking)), 1)

    def test_rejects_transfer_without_permission_or_conforming_movement(self):
        picking = self._prepared("outgoing")
        self._finish(picking)
        with self.assertRaises(AccessError):
            picking.with_user(self.operator).action_open_customer_dispatch()
        internal = self._prepared("internal")
        self._finish(internal)
        with self.assertRaises(UserError):
            self._open_dispatch(internal)

    def test_supervisor_without_native_write_cannot_register(self):
        picking = self._prepared("outgoing")
        self._finish(picking)
        self.env["ir.rule"].create(
            {
                "name": "QA transferencia de solo lectura",
                "model_id": self.env["ir.model"]._get_id("stock.picking"),
                "domain_force": f"[('id', '!=', {picking.id})]",
                "perm_read": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        self.assertEqual(picking.with_user(self.supervisor).state, "done")
        with self.assertRaises(AccessError):
            self._open_dispatch(picking)
        with self.assertRaises(AccessError):
            self.env["mc.rov.customer.dispatch.wizard"].with_user(self.supervisor).create(
                {"picking_id": picking.id, "kind": "confirmed"}
            )

    def test_effective_time_cannot_be_future_at_either_precision(self):
        picking = self._prepared("outgoing")
        self._finish(picking)
        evidence = self._evidence(picking)
        wizard = self._open_dispatch(picking)
        for dates in (
            {"effective_date": "2099-01-10"},
            {"precision": "datetime", "effective_at": "2099-01-10 09:30:00"},
        ):
            with self.subTest(dates=dates), self.assertRaises(ValidationError):
                self._document_pickup(wizard, evidence, **dates)
        self.assertFalse(self._dispatch_rows(picking))

    def test_rejects_attachment_linked_to_another_transfer(self):
        picking = self._prepared("outgoing")
        self._finish(picking)
        unrelated = self._evidence(self._picking("outgoing"))
        with self.assertRaises(ValidationError):
            self._document_pickup(self._open_dispatch(picking), unrelated)
        self.assertFalse(self._dispatch_rows(picking))

    def _delivered_repair_visits(self):
        self.product.tracking = "serial"
        customer = self.env["res.partner"].create({"name": "QA Cliente de reparación"})
        first, second, other = self.env["stock.lot"].create(
            [
                {"name": name, "product_id": self.product.id, "company_id": self.env.company.id}
                for name in ("QA-SALIDA-A", "QA-SALIDA-B", "QA-SALIDA-C")
            ]
        )
        picking = self._picking("outgoing", partner_id=customer.id)
        for lot in first | second:
            self.env["stock.quant"]._update_available_quantity(
                self.product, self.locations["stock"], 1, lot_id=lot
            )
        self._confirm(picking)
        picking.action_assign()
        self.assertEqual(picking.move_line_ids.lot_id, first | second)
        self._finish(picking)
        visits = self.env["repair.order"].create(
            [
                {
                    "product_id": self.product.id,
                    "product_qty": 1,
                    "product_uom": self.product.uom_id.id,
                    "company_id": self.env.company.id,
                    "lot_id": lot.id,
                    "partner_id": customer.id,
                }
                for lot in (first, second, first, other)
            ]
        )
        return picking, visits

    def test_repair_links_allow_distinct_delivered_serials_and_reject_other_visits(self):
        picking, visits = self._delivered_repair_visits()
        first_visit, second_visit, duplicate_serial, wrong_serial = visits
        evidence = self._evidence(picking)
        wizard = self._open_dispatch(picking)
        with self.assertRaises(ValidationError):
            self._document_pickup(wizard, evidence, repair_ids=[Command.set(wrong_serial.ids)])
        with self.assertRaises(ValidationError):
            self._document_pickup(
                wizard, evidence, repair_ids=[Command.set((first_visit | duplicate_serial).ids)]
            )
        selected = first_visit | second_visit
        self._document_pickup(wizard, evidence, repair_ids=[Command.set(selected.ids)])
        original = self._dispatch_rows(picking).ensure_one()
        self.assertEqual(original.repair_ids, selected)
        correction = self._open_dispatch(picking)
        self.assertEqual(correction.repair_ids, selected)
        correction.reason = "La constancia confirma el retiro conjunto."
        correction.action_apply()
        invalidation = self._open_dispatch(picking, invalidation=True)
        invalidation.reason = "El cliente desconoce la firma."
        invalidation.action_apply()
        history = self._dispatch_rows(picking)
        self.assertEqual(history.filtered(lambda event: event.repair_ids == selected), history)
        with self.assertRaises(UserError):
            first_visit.unlink()
        self.env["ir.rule"].create(
            {
                "name": "QA visita de acceso restringido",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": f"[('id', '!=', {second_visit.id})]",
            }
        )
        with self.assertRaises(AccessError):
            self._open_dispatch(picking)

    def test_attachment_changes_leave_original_event_without_current_evidence(self):
        picking = self._prepared("outgoing")
        self._finish(picking)
        attachment = self._evidence(picking)
        acting = picking.with_user(self.supervisor)
        self._document_pickup(self._open_dispatch(picking), attachment)
        original = self._dispatch_rows(picking).ensure_one()
        self.assertTrue(original._evidence_matches(acting))
        attachment.url = "https://example.com/constancia-reemplazada"
        self.assertFalse(original._evidence_matches(acting))

        correction = self._open_dispatch(picking)
        correction.reason = "El enlace actualizado corresponde a la constancia firmada."
        correction.action_apply()
        first_event, corrected = self._dispatch_rows(picking)
        self.assertEqual(first_event, original)
        self.assertFalse(first_event._evidence_matches(acting))
        self.assertTrue(corrected._evidence_matches(acting))
        wizard = self._open_dispatch(picking, invalidation=True)
        wizard.reason = "Se retiró la constancia."
        wizard.action_apply()
        invalidated = self._dispatch_rows(picking)[-1]
        self.assertEqual(invalidated.attachment_fingerprint, corrected.attachment_fingerprint)

    def test_attachment_binary_replacement_detected_by_native_checksum(self):
        picking = self._prepared("outgoing")
        self._finish(picking)
        attachment = self.env["ir.attachment"].create(
            {
                "name": "Constancia ficticia.txt",
                "raw": b"Respaldo inicial de QA",
                "res_model": "stock.picking",
                "res_id": picking.id,
            }
        )
        self._document_pickup(self._open_dispatch(picking), attachment)
        event = self._dispatch_rows(picking).ensure_one()
        acting = picking.with_user(self.supervisor)
        self.assertTrue(event._evidence_matches(acting))
        attachment.raw = b"Respaldo sustituido de QA"
        self.assertFalse(event._evidence_matches(acting))
