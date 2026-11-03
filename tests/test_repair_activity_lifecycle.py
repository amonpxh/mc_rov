from odoo import Command, _
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .automatic_completion_assertions import assert_automatic_close_rejected
from . import test_repair_activity_generation as generation_tests
from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestRepairActivityLifecycle(RevisionCommon):
    """Cerrar pendientes no sustituye diagnóstico ni reparación del equipo."""

    _policy = generation_tests.TestRepairActivityGeneration._policy
    _order = generation_tests.TestRepairActivityGeneration._order
    _runs = generation_tests.TestRepairActivityGeneration._runs

    def _visit(self):
        self.assertTrue(
            hasattr(self.env["mc.rov.repair.activity.automation"], "_after_revision_confirmation"),
            "Missing repair activity lifecycle service",
        )
        policy = self._policy()
        order = self._order()
        order.action_repair_start()
        runs = self._runs(order)
        return (
            policy,
            order,
            runs.filtered(lambda run: run.stage == "diagnosis"),
            runs.filtered(lambda run: run.stage == "repair"),
        )

    def _confirm(self, revision):
        revision.responsable_id = self.empleado
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self._responder_sellos(revision)
        revision.action_confirmar()

    def _finish_order(self, order):
        order.tipo_intervencion_ids = [
            Command.set(self.env.ref("mc_rov.tipo_reparacion_correctiva").ids)
        ]
        order.write({"state": "done"})

    def test_confirm_exact_revision_closes_only_diagnosis(self):
        _policy, order, diagnosis, repair = self._visit()
        self._confirm(diagnosis.revision_id)
        self.assertEqual(diagnosis.outcome, "business_done")
        self.assertFalse(diagnosis.activity_id.active)
        self.assertTrue(repair.activity_id.active)
        self.assertEqual(order.state, "under_repair")

    def test_other_revision_does_not_close_diagnosis(self):
        _policy, order, diagnosis, repair = self._visit()
        other = self._revision(tipo="reparacion", repair_id=order.id, motivo="retest")
        self._confirm(other)
        self.assertEqual(diagnosis.outcome, "pending")
        self.assertTrue(diagnosis.activity_id.active)
        self.assertTrue(repair.activity_id.active)

    def test_done_order_closes_repair_after_diagnosis(self):
        _policy, order, diagnosis, repair = self._visit()
        self._confirm(diagnosis.revision_id)
        self._finish_order(order)
        self.assertEqual(repair.outcome, "business_done")
        self.assertFalse(repair.activity_id.active)
        self.assertTrue(repair.finished_at)

    def test_failed_order_validation_does_not_close_activities(self):
        _policy, order, diagnosis, repair = self._visit()
        with self.assertRaises(UserError):
            order.write({"state": "done"})
        self.assertEqual(order.state, "under_repair")
        self.assertTrue(diagnosis.activity_id.active)
        self.assertTrue(repair.activity_id.active)

    def test_cancelled_order_cancels_without_marking_done(self):
        _policy, order, diagnosis, repair = self._visit()
        order.action_repair_cancel()
        self.assertEqual(set((diagnosis | repair).mapped("outcome")), {"cancelled"})
        self.assertFalse(diagnosis.activity_id and diagnosis.activity_id.active)
        self.assertFalse(repair.activity_id and repair.activity_id.active)

    def test_manual_done_is_blocked_without_confirming_or_recreating(self):
        _policy, order, diagnosis, repair = self._visit()
        activity = diagnosis.activity_id
        with assert_automatic_close_rejected(self, diagnosis):
            activity.action_feedback(feedback="QA cierre manual")
        order.write({"state": "under_repair"})
        self.assertEqual(diagnosis.outcome, "pending")
        self.assertTrue(activity.active)
        self.assertEqual(diagnosis.revision_id.estado, "borrador")
        self.assertEqual(order.state, "under_repair")
        self.assertTrue(repair.activity_id.active)
        self.assertEqual(len(self._runs(order)), 2)

    def test_manual_cancel_is_blocked_without_changing_or_recreating(self):
        _policy, order, diagnosis, repair = self._visit()
        with assert_automatic_close_rejected(self, repair):
            repair.activity_id.action_cancel()
        order.write({"state": "under_repair"})
        self.assertEqual(repair.outcome, "pending")
        self.assertEqual(order.state, "under_repair")
        self.assertTrue(diagnosis.activity_id.active)
        self.assertEqual(len(self._runs(order)), 2)

    def test_reopened_order_has_new_cycle_and_keeps_previous(self):
        _policy, order, diagnosis, repair = self._visit()
        old_cycle = repair.cycle
        order.action_repair_cancel()
        order.action_repair_cancel_draft()
        order.action_repair_start()
        runs = self._runs(order)
        current = runs.filtered(lambda run: run.cycle != old_cycle)
        self.assertEqual(len(runs), 4)
        self.assertEqual(len(current), 2)
        self.assertEqual(set(current.mapped("cycle")), {old_cycle + 1})
        self.assertEqual(set((diagnosis | repair).mapped("outcome")), {"cancelled"})

    def test_revision_back_to_draft_does_not_recreate_pending(self):
        _policy, order, diagnosis, repair = self._visit()
        self._confirm(diagnosis.revision_id)
        diagnosis.revision_id.action_volver_a_borrador()
        self.assertEqual(diagnosis.outcome, "business_done")
        self.assertEqual(len(self._runs(order)), 2)
        self.assertTrue(repair.activity_id.active)

    def test_disabling_policy_still_closes_existing_activities(self):
        policy, order, diagnosis, repair = self._visit()
        policy.enabled = False
        self._confirm(diagnosis.revision_id)
        self._finish_order(order)
        self.assertEqual(set((diagnosis | repair).mapped("outcome")), {"business_done"})

    def test_manual_activity_with_same_title_is_untouched(self):
        policy, order, diagnosis, _repair = self._visit()
        manual = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("repair.order"),
                "res_id": order.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "user_id": policy.user_id.id,
                "summary": diagnosis.activity_id.summary,
                "date_deadline": diagnosis.original_deadline,
            }
        )
        self._confirm(diagnosis.revision_id)
        self._finish_order(order)
        self.assertTrue(manual.active)

    def test_failed_confirmation_transaction_rolls_back_activity_close(self):
        _policy, _order, diagnosis, repair = self._visit()
        revision = diagnosis.revision_id
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._confirm(revision)
            self.assertEqual(diagnosis.outcome, "business_done")
            raise ValidationError(_("QA fallo posterior a confirmación"))
        revision.invalidate_recordset()
        diagnosis.invalidate_recordset()
        self.assertEqual(revision.estado, "borrador")
        self.assertEqual(diagnosis.outcome, "pending")
        self.assertTrue(diagnosis.activity_id.active)
        self.assertTrue(repair.activity_id.active)
