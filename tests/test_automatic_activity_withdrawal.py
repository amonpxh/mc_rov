"""Retirar un aviso exige Supervisor, motivo y trazabilidad de trabajo abierto."""

from datetime import timedelta
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from . import test_automatic_activity_completion as completion
from .acceptance_activity_common import AcceptanceActivityCommon
from .engineering_activity_common import EngineeringActivityCommon
from .inventory_activity_common import InventoryActivityCommon
from .manufacturing_activity_common import ManufacturingActivityCommon
from .quality_activity_common import QualityActivityCommon
from .test_mc_rov_revision import RevisionCommon


class AutomaticWithdrawalChecks(
    completion.AutomaticCompletionChecks
):  # pylint: disable=abstract-method
    """Fixtures autorizados y contratos comunes; ninguna prueba heredada."""

    def _withdrawal_model(self):
        self.assertTrue(
            "mc.rov.activity.withdrawal.wizard" in self.env.registry.models,
            "Missing audited automatic withdrawal wizard",
        )
        return self.env["mc.rov.activity.withdrawal.wizard"]

    def _withdrawal_coordinator(self, source, activity):
        recipient = activity.with_env(self.env).user_id
        groups = recipient.group_ids | self.env.ref("mc_rov.group_work_assignment_coordinate")
        coordinator = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "QA Retirada Supervisor",
                    "login": "qa_automatic_withdraw_coordinator",
                    "company_id": self.env.company.id,
                    "company_ids": [Command.set(self.env.company.ids)],
                    "group_ids": [Command.set(groups.ids)],
                }
            )
        )
        self.assertFalse(coordinator.has_group("base.group_system"))
        self.assertTrue(coordinator.has_group("mc_rov.group_work_assignment_coordinate"))
        self.assertTrue(source.with_user(coordinator).has_access("read"))
        self.assertTrue(source.with_user(coordinator).has_access("write"))
        self.assertTrue(activity.with_user(coordinator).has_access("write"))
        return coordinator

    def _withdrawal_fixture(self):
        self._withdrawal_model()
        source, run, activity = self._assert_open_fixture()
        coordinator = self._withdrawal_coordinator(source, activity)
        return source, run, activity, coordinator

    def _withdrawal_wizard(self, activities, user, **values):
        return (
            self._withdrawal_model()
            .with_user(user)
            .create(
                {
                    "activity_ids": [Command.set(activities.ids)],
                    "reason": "QA retiro excepcional; el trabajo sigue abierto",
                    "acknowledge_open_work": True,
                    **values,
                }
            )
        )

    def _withdrawal_source_status(self, source):
        names = [
            name for name in ("state", "estado", "stage_id", "resultado") if name in source._fields
        ]
        return source.read(names or ["id"])

    # Cada rama ejercita un contrato público distinto con el mismo escenario.
    # pylint: disable=too-many-locals,too-many-statements
    def _assert_withdrawal_contract(self, case):
        source, run, activity, coordinator = self._withdrawal_fixture()
        before = self._withdrawal_source_status(source)
        original = run.original_deadline
        deadline = activity.date_deadline
        if case == "authorized":
            result = self._withdrawal_wizard(activity, coordinator).action_apply()
            self.assertEqual(result, {"type": "ir.actions.act_window_close"})
        elif case == "reason":
            with self.assertRaises(UserError), self.env.cr.savepoint():
                self._withdrawal_wizard(activity, coordinator, reason="   ").action_apply()
            self.assertEqual(run.outcome, "pending")
            self.assertTrue(activity.exists() and activity.active)
            return
        elif case == "acknowledgement":
            with self.assertRaises(UserError), self.env.cr.savepoint():
                self._withdrawal_wizard(
                    activity, coordinator, acknowledge_open_work=False
                ).action_apply()
            self.assertEqual(run.outcome, "pending")
            self.assertTrue(activity.with_env(self.env).active)
            return
        elif case == "role":
            recipient = activity.user_id
            self.assertFalse(recipient.has_group("mc_rov.group_work_assignment_coordinate"))
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                self._withdrawal_wizard(activity, recipient).action_apply()
            self.assertEqual(run.outcome, "pending")
            self.assertTrue(activity.with_env(self.env).active)
            return
        elif case == "mixed":
            manual = self._untracked_activity(source, activity)
            with self.assertRaises(UserError), self.env.cr.savepoint():
                self._withdrawal_wizard(manual | activity, coordinator).action_apply()
            self.assertEqual(run.outcome, "pending")
            self.assertTrue(activity.active and manual.active)
            return
        elif case == "source_access":
            wizard = self._withdrawal_wizard(activity, coordinator)
            self.env["ir.rule"].create(
                {
                    "name": "QA origen retirado tras abrir asistente",
                    "model_id": self.env["ir.model"]._get_id(source._name),
                    "domain_force": repr([("id", "!=", source.id)]),
                }
            )
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                wizard.action_apply()
            self.assertEqual(run.outcome, "pending")
            self.assertTrue(activity.with_env(self.env).active)
            return
        elif case == "company":
            wizard = self._withdrawal_wizard(activity, coordinator)
            with patch.object(
                type(self.env["res.company"]), "_create_internal_project_task", create=True
            ):
                other = self.env["res.company"].create({"name": "QA Retirada empresa ajena"})
            self.assertNotIn(other, coordinator.company_ids)
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                wizard.with_context(allowed_company_ids=other.ids).action_apply()
            self.assertEqual(run.outcome, "pending")
            self.assertTrue(activity.with_env(self.env).active)
            return
        elif case == "repeat":
            wizard = self._withdrawal_wizard(activity, coordinator)
            wizard.action_apply()
            audit = run.read(["outcome", "finished_at", "finished_by_id", "finish_reason"])
            with self.assertRaises(UserError), self.env.cr.savepoint():
                wizard.action_apply()
            self.assertEqual(
                run.read(["outcome", "finished_at", "finished_by_id", "finish_reason"]), audit
            )
        elif case == "escaped_reason":
            reason = "QA retiro <script>alert(1)</script> & motivo"
            self._withdrawal_wizard(activity, coordinator, reason=reason).action_apply()
            self.assertEqual(run.finish_reason, reason)
            note = self.env["mail.message"].search(
                [
                    ("model", "=", source._name),
                    ("res_id", "=", source.id),
                    ("body", "ilike", "QA retiro"),
                ],
                order="id desc",
                limit=1,
            )
            self.assertTrue(note)
            self.assertNotIn("<script>", note.body)
            self.assertIn("&lt;script&gt;", note.body)
            self.assertEqual(note.author_id, coordinator.partner_id)
        elif case == "deadline":
            deadline += timedelta(days=2)
            self.env["mc.rov.activity.assignment.wizard"].with_user(coordinator).create(
                {
                    "activity_ids": [Command.set(activity.ids)],
                    "apply_deadline": True,
                    "date_deadline": deadline,
                    "reason": "QA compromiso reprogramado autorizado",
                }
            ).action_apply()
            self._withdrawal_wizard(activity, coordinator).action_apply()
        else:
            self.fail("Contrato desconocido")
        run.invalidate_recordset()
        activity.invalidate_recordset()
        source.invalidate_recordset()
        self.assertEqual(run.outcome, "exception_withdrawn")
        self.assertEqual(run.original_deadline, original)
        self.assertIn("current_deadline", run._fields)
        self.assertEqual(run.current_deadline, deadline)
        self.assertTrue(run.finished_at and run.finish_reason)
        self.assertEqual(run.finished_by_id, coordinator)
        self.assertFalse(activity.exists() and activity.active)
        self.assertEqual(self._withdrawal_source_status(source), before)

    def _assert_withdrawal_context_rejected(self):
        _source, run, activity = self._assert_open_fixture()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            activity.with_context(
                mc_automatic_withdrawal_authorized=True,
                _mc_activity_withdrawal_authorization=[
                    activity.user_id.id,
                    activity.id,
                    "QA motivo RPC",
                ],
            ).action_cancel()
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(activity.exists() and activity.active)

    def _assert_coordinator_fixture(self):
        source, _run, activity = self._assert_open_fixture()
        self._withdrawal_coordinator(source, activity)


@tagged("post_install", "-at_install")
class TestRepairAutomaticWithdrawal(AutomaticWithdrawalChecks, RevisionCommon):
    """Retirada excepcional auditada del flujo Repair."""

    _policy = completion.TestRepairAutomaticCompletion._policy
    _order = completion.TestRepairAutomaticCompletion._order
    _runs = completion.TestRepairAutomaticCompletion._runs
    _completion_fixture = completion.TestRepairAutomaticCompletion._completion_fixture

    def test_supervisor_withdraws_without_completing_work(self):
        self._assert_withdrawal_contract("authorized")

    def test_withdrawal_requires_nonempty_reason(self):
        self._assert_withdrawal_contract("reason")

    def test_withdrawal_requires_open_work_acknowledgement(self):
        self._assert_withdrawal_contract("acknowledgement")

    def test_assignee_without_coordination_cannot_withdraw(self):
        self._assert_withdrawal_contract("role")

    def test_withdrawal_rejects_mixed_manual_selection_atomically(self):
        self._assert_withdrawal_contract("mixed")

    def test_withdrawal_rechecks_source_access_after_opening(self):
        self._assert_withdrawal_contract("source_access")

    def test_withdrawal_rechecks_allowed_company_context(self):
        self._assert_withdrawal_contract("company")

    def test_repeated_withdrawal_cannot_rewrite_audit(self):
        self._assert_withdrawal_contract("repeat")

    def test_withdrawal_reason_is_escaped_and_attributed(self):
        self._assert_withdrawal_contract("escaped_reason")

    def test_withdrawal_captures_reprogrammed_deadline(self):
        self._assert_withdrawal_contract("deadline")

    def test_rpc_context_cannot_authorize_withdrawal(self):
        self._assert_withdrawal_context_rejected()

    def test_native_coordinator_has_source_write_without_admin(self):
        self._assert_coordinator_fixture()


@tagged("post_install", "-at_install")
class TestManufacturingAutomaticWithdrawal(AutomaticWithdrawalChecks, ManufacturingActivityCommon):
    """Retirada excepcional auditada del flujo Manufacturing."""

    _completion_fixture = completion.TestManufacturingAutomaticCompletion._completion_fixture

    def test_supervisor_withdraws_without_completing_work(self):
        self._assert_withdrawal_contract("authorized")

    def test_withdrawal_requires_nonempty_reason(self):
        self._assert_withdrawal_contract("reason")

    def test_withdrawal_requires_open_work_acknowledgement(self):
        self._assert_withdrawal_contract("acknowledgement")

    def test_assignee_without_coordination_cannot_withdraw(self):
        self._assert_withdrawal_contract("role")

    def test_withdrawal_rejects_mixed_manual_selection_atomically(self):
        self._assert_withdrawal_contract("mixed")

    def test_withdrawal_rechecks_source_access_after_opening(self):
        self._assert_withdrawal_contract("source_access")

    def test_withdrawal_rechecks_allowed_company_context(self):
        self._assert_withdrawal_contract("company")

    def test_repeated_withdrawal_cannot_rewrite_audit(self):
        self._assert_withdrawal_contract("repeat")

    def test_withdrawal_reason_is_escaped_and_attributed(self):
        self._assert_withdrawal_contract("escaped_reason")

    def test_withdrawal_captures_reprogrammed_deadline(self):
        self._assert_withdrawal_contract("deadline")

    def test_rpc_context_cannot_authorize_withdrawal(self):
        self._assert_withdrawal_context_rejected()

    def test_native_coordinator_has_source_write_without_admin(self):
        self._assert_coordinator_fixture()


@tagged("post_install", "-at_install")
class TestAcceptanceAutomaticWithdrawal(AutomaticWithdrawalChecks, AcceptanceActivityCommon):
    """Retirada excepcional auditada del flujo Acceptance."""

    _completion_fixture = completion.TestAcceptanceAutomaticCompletion._completion_fixture

    def test_supervisor_withdraws_without_completing_work(self):
        self._assert_withdrawal_contract("authorized")

    def test_withdrawal_requires_nonempty_reason(self):
        self._assert_withdrawal_contract("reason")

    def test_withdrawal_requires_open_work_acknowledgement(self):
        self._assert_withdrawal_contract("acknowledgement")

    def test_assignee_without_coordination_cannot_withdraw(self):
        self._assert_withdrawal_contract("role")

    def test_withdrawal_rejects_mixed_manual_selection_atomically(self):
        self._assert_withdrawal_contract("mixed")

    def test_withdrawal_rechecks_source_access_after_opening(self):
        self._assert_withdrawal_contract("source_access")

    def test_withdrawal_rechecks_allowed_company_context(self):
        self._assert_withdrawal_contract("company")

    def test_repeated_withdrawal_cannot_rewrite_audit(self):
        self._assert_withdrawal_contract("repeat")

    def test_withdrawal_reason_is_escaped_and_attributed(self):
        self._assert_withdrawal_contract("escaped_reason")

    def test_withdrawal_captures_reprogrammed_deadline(self):
        self._assert_withdrawal_contract("deadline")

    def test_rpc_context_cannot_authorize_withdrawal(self):
        self._assert_withdrawal_context_rejected()

    def test_native_coordinator_has_source_write_without_admin(self):
        self._assert_coordinator_fixture()


@tagged("post_install", "-at_install")
class TestQualityAutomaticWithdrawal(AutomaticWithdrawalChecks, QualityActivityCommon):
    """Retirada excepcional auditada del flujo Quality."""

    _completion_fixture = completion.TestQualityAutomaticCompletion._completion_fixture

    def test_supervisor_withdraws_without_completing_work(self):
        self._assert_withdrawal_contract("authorized")

    def test_withdrawal_requires_nonempty_reason(self):
        self._assert_withdrawal_contract("reason")

    def test_withdrawal_requires_open_work_acknowledgement(self):
        self._assert_withdrawal_contract("acknowledgement")

    def test_assignee_without_coordination_cannot_withdraw(self):
        self._assert_withdrawal_contract("role")

    def test_withdrawal_rejects_mixed_manual_selection_atomically(self):
        self._assert_withdrawal_contract("mixed")

    def test_withdrawal_rechecks_source_access_after_opening(self):
        self._assert_withdrawal_contract("source_access")

    def test_withdrawal_rechecks_allowed_company_context(self):
        self._assert_withdrawal_contract("company")

    def test_repeated_withdrawal_cannot_rewrite_audit(self):
        self._assert_withdrawal_contract("repeat")

    def test_withdrawal_reason_is_escaped_and_attributed(self):
        self._assert_withdrawal_contract("escaped_reason")

    def test_withdrawal_captures_reprogrammed_deadline(self):
        self._assert_withdrawal_contract("deadline")

    def test_rpc_context_cannot_authorize_withdrawal(self):
        self._assert_withdrawal_context_rejected()

    def test_native_coordinator_has_source_write_without_admin(self):
        self._assert_coordinator_fixture()


@tagged("post_install", "-at_install")
class TestEngineeringAutomaticWithdrawal(AutomaticWithdrawalChecks, EngineeringActivityCommon):
    """Retirada excepcional auditada del flujo Engineering."""

    _completion_fixture = completion.TestEngineeringAutomaticCompletion._completion_fixture

    def test_supervisor_withdraws_without_completing_work(self):
        self._assert_withdrawal_contract("authorized")

    def test_withdrawal_requires_nonempty_reason(self):
        self._assert_withdrawal_contract("reason")

    def test_withdrawal_requires_open_work_acknowledgement(self):
        self._assert_withdrawal_contract("acknowledgement")

    def test_assignee_without_coordination_cannot_withdraw(self):
        self._assert_withdrawal_contract("role")

    def test_withdrawal_rejects_mixed_manual_selection_atomically(self):
        self._assert_withdrawal_contract("mixed")

    def test_withdrawal_rechecks_source_access_after_opening(self):
        self._assert_withdrawal_contract("source_access")

    def test_withdrawal_rechecks_allowed_company_context(self):
        self._assert_withdrawal_contract("company")

    def test_repeated_withdrawal_cannot_rewrite_audit(self):
        self._assert_withdrawal_contract("repeat")

    def test_withdrawal_reason_is_escaped_and_attributed(self):
        self._assert_withdrawal_contract("escaped_reason")

    def test_withdrawal_captures_reprogrammed_deadline(self):
        self._assert_withdrawal_contract("deadline")

    def test_rpc_context_cannot_authorize_withdrawal(self):
        self._assert_withdrawal_context_rejected()

    def test_native_coordinator_has_source_write_without_admin(self):
        self._assert_coordinator_fixture()


@tagged("post_install", "-at_install")
class TestInventoryAutomaticWithdrawal(AutomaticWithdrawalChecks, InventoryActivityCommon):
    """Retirada excepcional auditada del flujo Inventory."""

    _completion_fixture = completion.TestInventoryAutomaticCompletion._completion_fixture

    def test_supervisor_withdraws_without_completing_work(self):
        self._assert_withdrawal_contract("authorized")

    def test_withdrawal_requires_nonempty_reason(self):
        self._assert_withdrawal_contract("reason")

    def test_withdrawal_requires_open_work_acknowledgement(self):
        self._assert_withdrawal_contract("acknowledgement")

    def test_assignee_without_coordination_cannot_withdraw(self):
        self._assert_withdrawal_contract("role")

    def test_withdrawal_rejects_mixed_manual_selection_atomically(self):
        self._assert_withdrawal_contract("mixed")

    def test_withdrawal_rechecks_source_access_after_opening(self):
        self._assert_withdrawal_contract("source_access")

    def test_withdrawal_rechecks_allowed_company_context(self):
        self._assert_withdrawal_contract("company")

    def test_repeated_withdrawal_cannot_rewrite_audit(self):
        self._assert_withdrawal_contract("repeat")

    def test_withdrawal_reason_is_escaped_and_attributed(self):
        self._assert_withdrawal_contract("escaped_reason")

    def test_withdrawal_captures_reprogrammed_deadline(self):
        self._assert_withdrawal_contract("deadline")

    def test_rpc_context_cannot_authorize_withdrawal(self):
        self._assert_withdrawal_context_rejected()

    def test_native_coordinator_has_source_write_without_admin(self):
        self._assert_coordinator_fixture()
