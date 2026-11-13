"""La aceptación conjunta, la liberación y la salida son hitos distintos."""

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .acceptance_activity_common import AcceptanceActivityCommon
from .test_new_acceptance_start import TestNewAcceptanceStart
from .test_new_acceptance_events import TestNewAcceptanceEvents
from .test_production_kpi_service import TestProductionKPIService


@tagged("post_install", "-at_install", "production_kpi_capture")
class TestProductionKPIRelease(AcceptanceActivityCommon):
    """Supervisor deja evidencia explícita; emitir FEN no libera automáticamente."""

    _pause = TestNewAcceptanceStart._pause
    _unit = TestNewAcceptanceStart._unit
    _complete = TestNewAcceptanceEvents._complete

    def _feature(self):
        self.assertTrue(
            "mc.rov.unit.release.wizard" in self.env.registry.models, "Falta liberación explícita"
        )

    _kpi_service = TestProductionKPIService._service

    def _accepted(self, customer=False):
        self._feature()
        if not customer:
            production, lot, rnd, trn = self._unit()
        else:
            self._pause()
            sale = self.env["sale.order"].create({"partner_id": customer.id})
            line = self.env["sale.order.line"].create(
                {
                    "order_id": sale.id,
                    "product_id": self.product.id,
                    "product_uom_qty": 1,
                }
            )
            production = self._production(sale_line_id=line.id)
            production.action_confirm()
            lot = self._serials()
            self._finish_acceptance_production(production, lot)
            rnd = self._revision(lot_id=lot.id, tipo="rendimiento")
            trn = self._revision(lot_id=lot.id, tipo="terreno")
        self._complete(rnd | trn)
        self.env["mc.rov.new.acceptance"].start_attempt(production.id, lot.id, rnd.id, trn.id)
        rnd.action_confirmar()
        trn.action_confirmar()
        return production, lot, rnd, trn

    def _fen(self, unit, emit=True):
        _production, lot, rnd, trn = unit
        fen = self.env["mc.rov.ficha.equipo.nuevo"].create(
            {
                "lot_id": lot.id,
                "rnd_id": rnd.id,
                "trn_id": trn.id,
            }
        )
        if emit:
            fen.action_emitir()
        return fen

    def _wizard(self, unit, fen, reviewed=True, user=None):
        model = self.env["mc.rov.unit.release.wizard"]
        if user:
            model = model.with_user(user)
        return model.create(
            {
                "production_id": unit[0].id,
                "lot_id": unit[1].id,
                "fen_id": fen.id,
                "no_blocking_nc": reviewed,
            }
        )

    def _events(self, kind, unit):
        return (
            self.env["mc.rov.production.event"]
            .sudo()
            .search(
                [
                    ("kind", "=", kind),
                    ("lot_id", "=", unit[1].id),
                ]
            )
        )

    def test_joint_acceptance_records_accepted_hito(self):
        unit = self._accepted()
        self.assertEqual(len(self._events("accepted", unit)), 1)
        self.assertFalse(self._events("released", unit))

    def test_emitting_fen_does_not_release_unit(self):
        unit = self._accepted()
        self._fen(unit)
        self.assertFalse(self._events("released", unit))

    def test_supervisor_explicitly_releases_with_fen_and_nc_review(self):
        unit = self._accepted()
        fen = self._fen(unit)
        self._wizard(unit, fen).action_release()
        event = self._events("released", unit)
        self.assertEqual(len(event), 1)
        self.assertEqual(event.payload["fen_id"], fen.id)
        self.assertEqual(event.actor_id, self.env.user)
        self.assertFalse(self._events("outbound", unit))

    def test_draft_fen_cannot_release(self):
        unit = self._accepted()
        with self.assertRaises(UserError):
            self._wizard(unit, self._fen(unit, False)).action_release()

    def test_unreviewed_nc_cannot_release(self):
        unit = self._accepted()
        with self.assertRaises(UserError):
            self._wizard(unit, self._fen(unit), reviewed=False).action_release()

    def test_repeated_release_keeps_first_event(self):
        unit = self._accepted()
        wizard = self._wizard(unit, self._fen(unit))
        wizard.action_release()
        before = self._events("released", unit).read(["at", "payload", "actor_id"])
        wizard.action_release()
        self.assertEqual(
            self._events("released", unit).read(["at", "payload", "actor_id"]), before
        )

    def test_operator_cannot_impersonate_supervisor(self):
        unit = self._accepted()
        fen = self._fen(unit)
        user = new_test_user(
            self.env,
            login="qa_no_release_supervisor",
            groups="base.group_user,stock.group_stock_user,mrp.group_mrp_user",
        )
        with self.assertRaises(AccessError):
            self._wizard(unit, fen, user=user).action_release()

    def test_other_unit_fen_is_rejected(self):
        unit = self._accepted()
        other = self._accepted()
        with self.assertRaises(UserError):
            self._wizard(unit, self._fen(other)).action_release()

    def test_reopening_current_protocol_invalidates_current_readiness(self):
        unit = self._accepted()
        self._wizard(unit, self._fen(unit)).action_release()
        unit[2].action_volver_a_borrador()
        events = (
            self.env["mc.rov.production.event"]
            .sudo()
            .search(
                [
                    ("lot_id", "=", unit[1].id),
                    ("kind", "=", "unit_movement"),
                ]
            )
        )
        self.assertTrue(
            events.filtered(lambda row: row.payload.get("effect") == "invalidate_acceptance"),
            "Falta invalidar la preparación al reabrir el protocolo vigente",
        )
        self.assertEqual(len(self._events("released", unit)), 1)

    def test_new_approved_attempt_can_release_with_its_own_fen(self):
        unit = self._accepted()
        self._wizard(unit, self._fen(unit)).action_release()
        rnd = self._revision(lot_id=unit[1].id, tipo="rendimiento")
        trn = self._revision(lot_id=unit[1].id, tipo="terreno")
        self._complete(rnd | trn)
        self.env["mc.rov.new.acceptance"].start_attempt(unit[0].id, unit[1].id, rnd.id, trn.id)
        self.assertTrue(
            self._events("unit_movement", unit).filtered(
                lambda row: row.payload.get("effect") == "invalidate_acceptance"
            )
        )
        (rnd | trn).action_confirmar()
        renewed = unit[0], unit[1], rnd, trn
        try:
            self._wizard(renewed, self._fen(renewed)).action_release()
        except UserError as error:
            self.fail(f"La liberación debe usar el protocolo vigente: {error}")
        self.assertEqual(len(self._events("released", unit)), 1)

    def test_customer_balance_replays_reopening_without_customer_metadata(self):
        service = self._kpi_service()
        customer = self.env["res.partner"].create({"name": "QA cohorte cliente"})
        unit = self._accepted(customer)
        self._wizard(unit, self._fen(unit)).action_release()
        unit[2].action_volver_a_borrador()
        balances = service.get_summary(revision="all", customer_id=customer.id)["balances"]
        self.assertEqual(balances["released_in_workshop"], 0)
        self.assertEqual(balances["manufactured_not_accepted"], 1)

    def test_restricted_acceptance_source_is_not_counted_through_mo(self):
        service = self._kpi_service()
        unit = self._accepted()
        self.env["ir.rule"].create(
            {
                "name": "QA protocolo restringido KPI",
                "model_id": self.env["ir.model"]._get_id("mc.rov.revision"),
                "domain_force": f"[('id', '!=', {unit[2].id})]",
            }
        )
        with self.assertRaises(AccessError):
            service.get_summary(revision="all")

    def test_restricted_fen_source_is_not_counted_through_mo(self):
        service = self._kpi_service()
        unit = self._accepted()
        fen = self._fen(unit)
        self._wizard(unit, fen).action_release()
        self.env["ir.rule"].create(
            {
                "name": "QA FEN restringida KPI",
                "model_id": self.env["ir.model"]._get_id("mc.rov.ficha.equipo.nuevo"),
                "domain_force": f"[('id', '!=', {fen.id})]",
            }
        )
        with self.assertRaises(AccessError):
            service.get_summary(revision="all")

    def test_reconfirming_reopened_protocol_cannot_reuse_issued_fen(self):
        unit = self._accepted()
        fen = self._fen(unit)
        self._wizard(unit, fen).action_release()
        unit[2].action_volver_a_borrador()
        unit[2].action_confirmar()
        with self.assertRaises(UserError):
            self._wizard(unit, fen).action_release()
