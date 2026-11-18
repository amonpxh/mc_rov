"""Contratos RED del registro F2; no implementar captura antes de reproducirlos."""

from odoo import _, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .acceptance_activity_common import AcceptanceActivityCommon

# Contratos separados para que el descubrimiento compruebe cada frontera nativa.
# pylint: disable=too-many-public-methods


@tagged("post_install", "-at_install", "detention_capture")
class TestDetentionCapture(AcceptanceActivityCommon):
    """Taller registra hechos con su acceso nativo; el historial no concede acceso."""

    def _service(self, user=None):
        self.assertTrue(
            "mc.rov.detention.service" in self.env.registry.models, "Falta captura F2 autorizada"
        )
        if user is None:
            user = self._workshop()
        return self.env["mc.rov.detention.service"].with_user(user)

    def _workshop(self):
        return new_test_user(
            self.env,
            login="qa_detention_workshop",
            groups="base.group_user,stock.group_stock_user,mrp.group_mrp_user",
        )

    def _order(self, confirmed=True):
        order = self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "company_id": self.env.company.id,
                "tipo_intervencion_ids": [
                    Command.set(self.env.ref("mc_rov.tipo_reparacion_correctiva").ids)
                ],
            }
        )
        if confirmed:
            # Odoo19 expone action_validate; el helper de confirmación es privado.
            order.action_validate()
        return order

    def _start(self, service, source, **values):
        return service.start_detention(
            source._name,
            source.id,
            values.get("cause", "materials"),
            self.empleado.id,
            values.get("explanation", "Repuesto QA impide continuar"),
        )

    def _history(self, service, order):
        return service.get_intervals(order._name, order.id)

    def test_workshop_can_record_on_accessible_repair(self):
        service = self._service()
        order = self._order()
        identity = self._start(service, order)
        rows = self._history(service, order)
        self.assertEqual([row["id"] for row in rows], [identity])
        self.assertEqual(rows[0]["actor_id"], service.env.uid)
        self.assertEqual(rows[0]["responsible_employee_id"], self.empleado.id)

    def test_workshop_can_record_on_accessible_production(self):
        service = self._service()
        order = self._production()
        order.action_confirm()
        identity = self._start(service, order)
        self.assertEqual(self._history(service, order)[0]["id"], identity)

    def test_registration_does_not_pause_native_order(self):
        service = self._service()
        order = self._order()
        state = order.state
        self._start(service, order)
        self.assertEqual(order.state, state)

    def test_finish_preserves_original_start_and_actor(self):
        service = self._service()
        order = self._order()
        identity = self._start(service, order)
        before = self._history(service, order)[0]
        service.finish_detention(identity, "Repuesto QA recibido")
        after = self._history(service, order)[0]
        self.assertEqual(after["started_at"], before["started_at"])
        self.assertEqual(after["actor_id"], before["actor_id"])
        self.assertTrue(after["ended_at"])
        self.assertEqual(after["closed_by_id"], service.env.uid)

    def test_duplicate_finish_is_idempotent(self):
        service = self._service()
        order = self._order()
        identity = self._start(service, order)
        service.finish_detention(identity, "Solucionado")
        before = self._history(service, order)
        service.finish_detention(identity, "Segundo clic")
        self.assertEqual(self._history(service, order), before)

    def test_same_cause_can_restart_after_ending(self):
        service = self._service()
        order = self._order()
        first = self._start(service, order)
        service.finish_detention(first, "Solucionado")
        second = self._start(service, order)
        self.assertNotEqual(first, second)
        self.assertEqual(len(self._history(service, order)), 2)

    def test_duplicate_start_does_not_create_second_active_cause(self):
        service = self._service()
        order = self._order()
        self._start(service, order)
        with self.assertRaises(UserError):
            self._start(service, order)
        self.assertEqual(len(self._history(service, order)), 1)

    def test_distinct_causes_can_overlap(self):
        service = self._service()
        order = self._order()
        self._start(service, order)
        self._start(service, order, cause="client")
        self.assertEqual(len(self._history(service, order)), 2)

    def test_other_requires_explanation(self):
        service = self._service()
        with self.assertRaises(UserError):
            self._start(service, self._order(), cause="other", explanation="  ")

    def test_draft_order_cannot_claim_actual_detention(self):
        service = self._service()
        with self.assertRaises(UserError):
            self._start(service, self._order(confirmed=False))

    def test_invalid_cause_rejected(self):
        service = self._service()
        with self.assertRaises(ValidationError):
            self._start(service, self._order(), cause="invented")

    def test_source_read_access_cannot_be_bypassed(self):
        service = self._service()
        order = self._order()
        self.env["ir.rule"].create(
            {
                "name": "QA F2 fuente restringida",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": '[("id", "=", 0)]',
            }
        )
        with self.assertRaises(AccessError):
            self._start(service, order)

    def test_internal_account_without_native_rights_cannot_record(self):
        self._service()
        outsider = new_test_user(self.env, login="qa_detention_outsider", groups="base.group_user")
        with self.assertRaises(AccessError):
            self._start(self._service(outsider), self._order())

    def test_forged_context_does_not_authorize_history_creation(self):
        user = self._service().env.user
        with self.assertRaises(AccessError):
            self.env["mc.rov.detention.interval"].with_user(user).with_context(
                mc_detention_capability=True, sudo=True
            ).create({})

    def test_direct_history_write_and_delete_are_denied(self):
        service = self._service()
        identity = self._start(service, self._order())
        history = (
            self.env["mc.rov.detention.interval"].with_user(service.env.user).browse(identity)
        )
        with self.assertRaises(AccessError):
            history.write({"cause": "client"})
        with self.assertRaises(AccessError):
            history.unlink()

    def test_native_cancel_ends_interval_without_claiming_resumption(self):
        service = self._service()
        order = self._order()
        self._start(service, order)
        order.action_repair_cancel()
        row = self._history(service, order)[0]
        self.assertTrue(row["ended_at"])
        self.assertEqual(row["end_kind"], "source_closed")

    def test_rollback_does_not_preserve_partial_capture(self):
        service = self._service()
        order = self._order()
        with self.assertRaisesRegex(UserError, "Rollback QA"), self.env.cr.savepoint():
            self._start(service, order)
            raise UserError(_("Rollback QA"))
        self.assertFalse(self._history(service, order))

    def test_registration_does_not_generate_activities_or_move_stock(self):
        service = self._service()
        order = self._order()
        before = self.env["stock.quant"].search([]).read(["quantity", "reserved_quantity"])
        activities = self.env["mail.activity"].search_count([])
        self._start(service, order)
        self.assertEqual(
            self.env["stock.quant"].search([]).read(["quantity", "reserved_quantity"]), before
        )
        self.assertEqual(self.env["mail.activity"].search_count([]), activities)

    def test_supervisor_can_finish_workshop_record(self):
        service = self._service()
        order = self._order()
        identity = self._start(service, order)
        supervisor = new_test_user(
            self.env,
            login="qa_detention_supervisor",
            groups="base.group_user,stock.group_stock_manager,mrp.group_mrp_manager",
        )
        self._service(supervisor).finish_detention(identity, "Resuelto por Supervisor QA")
        self.assertEqual(self._history(service, order)[0]["closed_by_id"], supervisor.id)

    def test_actor_company_context_cannot_cross_companies(self):
        service = self._service()
        order = self._order()
        foreign = self.env["res.company"].create({"name": "QA F2 otra empresa"})
        with self.assertRaises(AccessError):
            self._start(service.with_context(allowed_company_ids=[foreign.id]), order)

    def test_native_control_repair_confirmation(self):
        self.assertEqual(self._order().state, "confirmed")

    def test_native_control_manufacturing_confirmation(self):
        order = self._production()
        order.action_confirm()
        self.assertEqual(order.state, "confirmed")

    def test_native_control_public_employee_identity(self):
        employee = self.env["hr.employee.public"].browse(self.empleado.id)
        self.assertEqual(employee.id, self.empleado.id)
        self.assertTrue(employee.exists())

    def test_native_control_default_does_not_create_detention_source(self):
        self.assertEqual(self._order(confirmed=False).state, "draft")
