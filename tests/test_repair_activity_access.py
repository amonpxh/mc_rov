from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from . import test_repair_activity_lifecycle as lifecycle_tests
from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestRepairActivityAccess(RevisionCommon):
    """La automatización conserva permisos e identidad del trabajo seguido."""

    _policy = lifecycle_tests.TestRepairActivityLifecycle._policy
    _order = lifecycle_tests.TestRepairActivityLifecycle._order
    _runs = lifecycle_tests.TestRepairActivityLifecycle._runs
    _visit = lifecycle_tests.TestRepairActivityLifecycle._visit
    _confirm = lifecycle_tests.TestRepairActivityLifecycle._confirm
    _finish_order = lifecycle_tests.TestRepairActivityLifecycle._finish_order

    def test_pending_order_cannot_change_equipment(self):
        _policy, order, diagnosis, _repair = self._visit()
        with self.assertRaisesRegex(ValidationError, "seguimiento"), self.cr.savepoint():
            order.write({"lot_id": False})
        self.assertEqual(diagnosis.repair_id.lot_id, self.lot)

    def test_pending_revision_cannot_change_order(self):
        _policy, _order, diagnosis, _repair = self._visit()
        other = self._order()
        with self.assertRaisesRegex(ValidationError, "seguimiento"), self.cr.savepoint():
            diagnosis.revision_id.write({"repair_id": other.id})

    def test_pending_revision_cannot_change_equipment(self):
        _policy, _order, diagnosis, _repair = self._visit()
        other_lot = self.env["stock.lot"].create(
            {
                "name": "QA otro equipo seguido",
                "product_id": self.product.id,
                "company_id": self.env.company.id,
            }
        )
        with self.assertRaisesRegex(ValidationError, "seguimiento"), self.cr.savepoint():
            diagnosis.revision_id.write({"lot_id": other_lot.id})

    def test_internal_cycle_cannot_be_written(self):
        _policy, order, _diagnosis, _repair = self._visit()
        with self.assertRaises(AccessError), self.cr.savepoint():
            order.with_context(mc_internal=True).write({"mc_activity_cycle": 100})
        self.assertEqual(order.mc_activity_cycle, 1)

    def test_internal_cycle_cannot_be_created(self):
        with self.assertRaises(AccessError), self.cr.savepoint():
            self._order(mc_activity_cycle=100)

    def test_context_defaults_do_not_forge_cycle(self):
        order = (
            self.env["repair.order"]
            .with_context(default_mc_activity_cycle=100)
            .create({"product_id": self.product.id, "lot_id": self.lot.id})
        )
        self.assertEqual(order.mc_activity_cycle, 0)

    def test_ledger_is_private_to_technical_service(self):
        policy, _order, diagnosis, _repair = self._visit()
        with self.assertRaises(AccessError):
            diagnosis.with_user(policy.user_id).read(["finish_reason"])
        # Aislar la ACL del ledger del permiso general de exportación de Odoo.
        policy.user_id.write(
            {"group_ids": [Command.link(self.env.ref("base.group_allow_export").id)]}
        )
        with self.assertRaises(AccessError):
            diagnosis.with_user(policy.user_id).export_data(["stage"])

    def test_assignee_without_source_permission_is_rejected(self):
        policy = self._policy()
        order = self._order()
        self.env["ir.rule"].create(
            {
                "name": "QA origen restringido",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": f"[('id', '!=', {order.id})]",
            }
        )
        self.assertTrue(policy._configuration_error(order))
        order.write({"state": "confirmed"})
        self.assertFalse(self._runs(order))

    def test_archived_recipient_does_not_generate(self):
        policy = self._policy()
        policy.user_id.active = False
        order = self._order()
        order.write({"state": "confirmed"})
        self.assertFalse(self._runs(order))

    def test_activity_cannot_move_to_other_order(self):
        _policy, _order, diagnosis, _repair = self._visit()
        other = self._order()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            diagnosis.activity_id.write({"res_id": other.id})

    def test_activity_copy_has_no_followup_identity(self):
        _policy, order, diagnosis, _repair = self._visit()
        copied = diagnosis.activity_id.copy()
        copied.action_feedback(feedback="QA copia independiente")
        self.assertEqual(diagnosis.outcome, "pending")
        self.assertTrue(diagnosis.activity_id.active)
        self.assertEqual(len(self._runs(order)), 2)

    def test_followed_revision_deletion_is_explained(self):
        _policy, _order, diagnosis, _repair = self._visit()
        with self.assertRaises(UserError):
            try:
                with self.cr.savepoint():
                    diagnosis.revision_id.unlink()
            except IntegrityError:
                self.fail("Missing user-facing deletion guard")

    def test_diagnosis_confirmation_after_order_done(self):
        _policy, order, diagnosis, repair = self._visit()
        self._finish_order(order)
        self.assertEqual(diagnosis.outcome, "pending")
        self._confirm(diagnosis.revision_id)
        self.assertEqual(diagnosis.outcome, "business_done")
        self.assertEqual(repair.outcome, "business_done")
        self.assertEqual(order.state, "done")

    def test_audit_records_actor_without_changing_employee(self):
        _policy, _order, diagnosis, _repair = self._visit()
        employee = diagnosis.activity_id.mc_employee_id
        self._confirm(diagnosis.revision_id)
        self.assertEqual(diagnosis.finished_by_id, self.env.user)
        self.assertTrue(diagnosis.finished_at)
        self.assertTrue(diagnosis.finish_reason)
        self.assertEqual(diagnosis.activity_id.mc_employee_id, employee)

    def test_reopening_done_does_not_leave_duplicate_diagnoses(self):
        _policy, order, diagnosis, _repair = self._visit()
        self._finish_order(order)
        order.write({"state": "under_repair"})
        pending = self._runs(order).filtered(
            lambda run: run.stage == "diagnosis" and run.outcome == "pending"
        )
        self.assertEqual(len(pending), 1, "Duplicate pending diagnosis after reopening")
        self.assertEqual(pending.cycle, 2)
        self.assertEqual(diagnosis.outcome, "cancelled")
