from psycopg2 import Error as DatabaseError

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from . import test_repair_activity_lifecycle as lifecycle_tests
from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestRepairActivityBoundaries(RevisionCommon):
    """La coordinación respeta empresa y permisos incluso después de la creación."""

    _policy = lifecycle_tests.TestRepairActivityLifecycle._policy
    _order = lifecycle_tests.TestRepairActivityLifecycle._order
    _runs = lifecycle_tests.TestRepairActivityLifecycle._runs
    _visit = lifecycle_tests.TestRepairActivityLifecycle._visit

    def _coordinator(self):
        return new_test_user(
            self.env,
            login="qa_repair_policy_coordinate",
            groups="mc_rov.group_work_assignment_coordinate",
            company_id=self.env.company.id,
        )

    def test_coordinator_reads_own_company_policy(self):
        policy = self._policy()
        values = policy.with_user(self._coordinator()).read(["company_id", "enabled"])
        self.assertEqual(values[0]["company_id"][0], self.env.company.id)
        self.assertTrue(values[0]["enabled"])

    def test_coordinator_cannot_read_other_company_policy(self):
        company = self.env["res.company"].create({"name": "QA empresa ajena seguimiento"})
        policy = self.env["mc.rov.repair.activity.policy"].create({"company_id": company.id})
        user = self._coordinator()
        restricted = policy.with_user(user).with_context(allowed_company_ids=user.company_ids.ids)
        with self.assertRaises(AccessError):
            restricted.read(["enabled"])
        with self.assertRaises(AccessError), self.cr.savepoint():
            restricted.write({"enabled": False})

    def test_assignee_cannot_read_policy_without_coordination(self):
        policy = self._policy()
        with self.assertRaises(AccessError):
            policy.with_user(policy.user_id).read(["user_id"])

    def test_pending_order_cannot_change_company(self):
        _policy, order, _diagnosis, _repair = self._visit()
        company = self.env["res.company"].create({"name": "QA cambio de empresa"})
        with self.assertRaisesRegex(ValidationError, "seguimiento"), self.cr.savepoint():
            order.write({"company_id": company.id})

    def test_pending_revision_cannot_change_type(self):
        _policy, _order, diagnosis, _repair = self._visit()
        with self.assertRaisesRegex(ValidationError, "seguimiento"), self.cr.savepoint():
            diagnosis.revision_id.write({"tipo": "rendimiento"})

    def test_lost_source_access_prevents_manual_closure(self):
        policy, order, diagnosis, _repair = self._visit()
        self.env["ir.rule"].create(
            {
                "name": "QA permiso retirado después de generar",
                "model_id": self.env["ir.model"]._get_id("repair.order"),
                "domain_force": f"[('id', '!=', {order.id})]",
            }
        )
        with self.assertRaises(AccessError), self.cr.savepoint():
            diagnosis.activity_id.with_user(policy.user_id).action_feedback(feedback="QA")
        self.assertEqual(diagnosis.outcome, "pending")
        self.assertTrue(diagnosis.activity_id.active)

    def test_followed_order_deletion_has_explanation(self):
        _policy, order, _diagnosis, _repair = self._visit()
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            order.unlink()

    def test_multicompany_actor_does_not_expand_recipient_context(self):
        self._policy(employee_id=self.empleado.id)
        company = self.env["res.company"].create({"name": "QA empresa del coordinador"})
        actor = new_test_user(
            self.env,
            login="qa_repair_multicompany_actor",
            groups="stock.group_stock_user",
            company_id=self.env.company.id,
        )
        actor.company_ids = [Command.set((self.env.company | company).ids)]
        order = self._order()
        order.with_user(actor).with_context(allowed_company_ids=actor.company_ids.ids).write(
            {"state": "confirmed"}
        )
        self.assertEqual(len(self._runs(order)), 1, "Recipient context inherited actor companies")
        order.with_user(actor).with_context(allowed_company_ids=actor.company_ids.ids).write(
            {"state": "under_repair"}
        )
        self.assertEqual(len(self._runs(order)), 2)

    def test_temporary_activity_archive_does_not_cancel_real_run(self):
        _policy, _order, diagnosis, _repair = self._visit()
        activity = diagnosis.activity_id
        temporary = self.env["mail.activity"].new(origin=activity)
        temporary.write({"active": False})
        diagnosis.invalidate_recordset()
        self.assertEqual(diagnosis.outcome, "pending", "Temporary activity changed real outcome")
        self.assertTrue(activity.active)

    def test_temporary_order_cancel_does_not_cancel_real_runs(self):
        _policy, order, diagnosis, repair = self._visit()
        temporary = self.env["repair.order"].new(origin=order)
        self._cancel_temporary_order(temporary)
        diagnosis.invalidate_recordset()
        repair.invalidate_recordset()
        self.assertEqual(diagnosis.outcome, "pending", "Temporary order changed real outcome")
        self.assertEqual(repair.outcome, "pending")
        self.assertEqual(order.state, "under_repair")

    def _cancel_temporary_order(self, temporary):
        try:
            with self.cr.savepoint():
                temporary.write({"state": "cancel"})
        except DatabaseError:
            self.fail("Temporary order attempted persistent SQL")

    def test_temporary_order_without_origin_has_no_persistent_effects(self):
        _policy, order, diagnosis, repair = self._visit()
        temporary = self.env["repair.order"].new(
            {"product_id": self.product.id, "lot_id": self.lot.id, "state": "draft"}
        )
        self._cancel_temporary_order(temporary)
        self.assertFalse(temporary.mc_activity_cycle)
        self.assertEqual(diagnosis.outcome, "pending")
        self.assertEqual(repair.outcome, "pending")
        self.assertEqual(order.state, "under_repair")
