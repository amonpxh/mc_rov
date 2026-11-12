"""Hechos reales e inmutables para volumen y observaciones, con políticas apagadas."""

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install", "production_kpi_capture")
class TestProductionKPICapture(AcceptanceActivityCommon):
    """La evidencia sigue al negocio; ni importar estados ni reconfirmar crea hechos."""

    # Una misma matriz comprueba el contrato completo de captura y sus fronteras.
    # pylint: disable=too-many-public-methods

    def _feature(self):
        self.assertIn("mc.rov.production.event", self.env.registry.models, "Falta captura KPI")
        self.assertIn("mc_detected_at", self.env["mc.rov.revision.hallazgo"]._fields)

    def _events(self, kind, **domain):
        return (
            self.env["mc.rov.production.event"]
            .sudo()
            .search([("kind", "=", kind), *[(key, "=", value) for key, value in domain.items()]])
        )

    def _repair(self, **values):
        self._feature()
        return self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "product_qty": 1,
                "product_uom": self.product.uom_id.id,
                "lot_id": self.lot.id,
                "company_id": self.env.company.id,
                "tipo_intervencion_ids": [
                    Command.set(self.env.ref("mc_rov.tipo_reparacion_correctiva").ids)
                ],
                **values,
            }
        )

    def _finding(self, dated=True):
        self._feature()
        revision = self._revision(tipo="reparacion", motivo="otro")
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self._responder_sellos(revision)
        finding = self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": revision.id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
                "mc_detected_at": "2026-11-10 13:00:00" if dated else False,
            }
        )
        return revision, finding

    def test_native_repair_closure_records_first_event(self):
        order = self._repair()
        order.action_repair_done()
        event = self._events("repair_done", repair_id=order.id)
        self.assertEqual(len(event), 1)
        self.assertEqual(event.lot_id, self.lot)
        self.assertTrue(event.at)
        self.assertEqual(event.payload["customer_id"], order.partner_id.id)

    def test_reclose_keeps_first_event(self):
        order = self._repair()
        order.action_repair_done()
        before = self._events("repair_done", repair_id=order.id).read(["at", "payload"])
        order.write({"state": "under_repair"})
        order.action_repair_done()
        self.assertEqual(
            self._events("repair_done", repair_id=order.id).read(["at", "payload"]), before
        )

    def test_import_done_does_not_invent_closure(self):
        order = self._repair(state="done")
        self.assertFalse(self._events("repair_done", repair_id=order.id))

    def test_direct_state_write_does_not_invent_native_closure(self):
        order = self._repair()
        order.state = "done"
        self.assertFalse(self._events("repair_done", repair_id=order.id))

    def test_edit_delivery_date_does_not_move_closure(self):
        order = self._repair()
        order.action_repair_done()
        event = self._events("repair_done", repair_id=order.id)
        original = event.at
        order.fecha_entrega_real = "2020-01-01"
        self.assertEqual(event.at, original)

    def test_failed_transaction_rolls_back_event_and_stock(self):
        order = self._repair()
        with self.assertRaisesRegex(UserError, "Rollback QA"), self.env.cr.savepoint():
            order.action_repair_done()
            self.assertTrue(self._events("repair_done", repair_id=order.id))
            raise UserError("Rollback QA")
        self.assertNotEqual(order.state, "done")
        self.assertFalse(self._events("repair_done", repair_id=order.id))

    def test_real_manufacture_records_serial_unit(self):
        self._feature()
        production = self._finished_production()
        event = self._events("manufactured", production_id=production.id)
        self.assertEqual(len(event), 1)
        self.assertEqual(event.lot_id, production.lot_producing_ids)
        self.assertEqual(event.payload["production_group_id"], production.production_group_id.id)

    def test_two_serials_are_two_manufactured_units(self):
        self._feature()
        production = self._finished_production(2)
        events = self._events("manufactured", production_id=production.id)
        self.assertEqual(len(events), 2)
        self.assertEqual(events.lot_id, production.lot_producing_ids)

    def test_draft_manufacturing_creates_no_event(self):
        self._feature()
        production = self._production()
        self.assertFalse(self._events("manufactured", production_id=production.id))

    def test_confirmed_finding_records_detection_not_registration(self):
        revision, finding = self._finding()
        revision.action_confirmar()
        event = self._events("observation", revision_id=revision.id)
        self.assertEqual(len(event), 1)
        self.assertEqual(event.at, finding.mc_detected_at)
        self.assertEqual(event.payload["finding_id"], finding.hallazgo_id.id)

    def test_unknown_detection_stays_unknown(self):
        revision, _finding = self._finding(False)
        revision.action_confirmar()
        event = self._events("observation", revision_id=revision.id)
        self.assertEqual(len(event), 1)
        self.assertFalse(event.at)

    def test_reconfirmation_does_not_duplicate_observation(self):
        revision, _finding = self._finding()
        revision.action_confirmar()
        revision.action_volver_a_borrador()
        revision.action_confirmar()
        self.assertEqual(len(self._events("observation", revision_id=revision.id)), 1)

    def test_history_rejects_direct_changes(self):
        order = self._repair()
        order.action_repair_done()
        event = self._events("repair_done", repair_id=order.id)
        with self.assertRaises(UserError):
            event.write({"at": "2020-01-01 00:00:00"})
        with self.assertRaises(UserError):
            event.unlink()

    def test_rpc_context_cannot_forge_event(self):
        self._feature()
        with self.assertRaises(UserError):
            self.env["mc.rov.production.event"].sudo().with_context(
                mc_production_event_capability=True
            ).create({"kind": "repair_done", "identity": "forged", "payload": {}})

    def test_internal_user_cannot_query_private_ledger(self):
        self._feature()
        user = new_test_user(self.env, login="qa_private_production", groups="base.group_user")
        with self.assertRaises(AccessError):
            self.env["mc.rov.production.event"].with_user(user).search([])
