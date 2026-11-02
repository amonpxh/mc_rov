"""El trabajo automático abierto no se retira por cerrar su recordatorio."""

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .acceptance_activity_common import AcceptanceActivityCommon
from .engineering_activity_common import EngineeringActivityCommon
from .inventory_activity_common import InventoryActivityCommon
from .manufacturing_activity_common import ManufacturingActivityCommon
from .quality_activity_common import QualityActivityCommon
from .test_mc_rov_revision import RevisionCommon
from . import test_repair_activity_generation as repair_generation


class AutomaticCompletionChecks(TransactionCase):
    """Aserciones compartidas sin métodos test heredados ni sustitución de eventos."""

    def _completion_fixture(self):
        raise NotImplementedError("Cada flujo aporta su evento nativo")

    def _completion_control(self):
        controls = self.env["mc.rov.automation.control"]
        control = controls.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = True
        else:
            controls.create({"company_id": self.env.company.id, "enabled": True})

    def _assert_open_fixture(self):
        self._completion_control()
        source, run = self._completion_fixture()
        run.ensure_one()
        self.assertEqual(run.outcome, "pending")
        activity = run.activity_id
        self.assertTrue(activity.exists() and activity.active)
        self.assertEqual((activity.res_model, activity.res_id), (source._name, source.id))
        acting = activity.with_user(activity.user_id)
        self.assertTrue(acting.has_access("read") and acting.has_access("write"))
        self.assertTrue(source.with_user(activity.user_id).has_access("read"))
        return source, run, acting

    def _untracked_activity(self, source, followed, own_type=False):
        kind = (
            followed.activity_type_id if own_type else self.env.ref("mail.mail_activity_data_todo")
        )
        return (
            self.env["mail.activity"]
            .create(
                {
                    "res_model_id": self.env["ir.model"]._get_id(source._name),
                    "res_id": source.id,
                    "activity_type_id": kind.id,
                    "user_id": followed.user_id.id,
                    "summary": followed.summary,
                }
            )
            .with_user(followed.user_id)
        )

    def _assert_completion_rejected(self, operation):
        source, run, activity = self._assert_open_fixture()
        names = [
            name for name in ("state", "estado", "stage_id", "resultado") if name in source._fields
        ]
        before = source.read(names or ["id"])
        manual = self._untracked_activity(source, activity) if operation == "mixed" else None
        with self.assertRaises(UserError), self.env.cr.savepoint():
            if operation == "feedback":
                activity.action_feedback(feedback="No debe completar el trabajo")
            elif operation == "private_done":
                activity._action_done(feedback="No debe completar el trabajo")
            elif operation == "cancel":
                activity.action_cancel()
            elif operation == "archive":
                activity.write({"active": False})
            elif operation == "unlink":
                activity.unlink()
            elif operation == "context":
                activity.with_context(
                    mc_automatic_completion_allowed=True,
                    _mc_activity_completion_authorization=True,
                    _mc_inventory_event=True,
                ).action_feedback(feedback="Contexto RPC no autoriza cerrar")
            elif operation == "mixed":
                (manual | activity).action_feedback(feedback="Lote mixto debe revertirse entero")
            else:
                self.fail("Operación de prueba desconocida")
        run.invalidate_recordset()
        activity.invalidate_recordset()
        source.invalidate_recordset()
        self.assertEqual(run.outcome, "pending")
        self.assertFalse(run.finished_at)
        self.assertTrue(activity.exists() and activity.active)
        self.assertEqual(source.read(names or ["id"]), before)
        if manual:
            manual.invalidate_recordset()
            self.assertTrue(manual.exists() and manual.active)

    def _assert_manual_still_native(self, own_type=False):
        source, run, activity = self._assert_open_fixture()
        manual = self._untracked_activity(source, activity, own_type=own_type)
        manual.action_feedback(feedback="Actividad sin seguimiento conserva cierre nativo")
        self.assertFalse(manual.exists() and manual.active)
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(activity.active)


@tagged("post_install", "-at_install")
class TestRepairAutomaticCompletion(AutomaticCompletionChecks, RevisionCommon):
    """Bloqueo común sobre un pendiente generado por eventos reales de Repair."""

    _policy = repair_generation.TestRepairActivityGeneration._policy
    _order = repair_generation.TestRepairActivityGeneration._order
    _runs = repair_generation.TestRepairActivityGeneration._runs

    def _completion_fixture(self):
        self._policy()
        order = self._order()
        order.write({"state": "confirmed"})
        return order, self._runs(order)

    def test_feedback_cannot_hide_open_work(self):
        self._assert_completion_rejected("feedback")

    def test_private_done_cannot_hide_open_work(self):
        self._assert_completion_rejected("private_done")

    def test_cancel_cannot_hide_open_work(self):
        self._assert_completion_rejected("cancel")

    def test_archive_cannot_hide_open_work(self):
        self._assert_completion_rejected("archive")

    def test_unlink_cannot_hide_open_work(self):
        self._assert_completion_rejected("unlink")

    def test_context_cannot_hide_open_work(self):
        self._assert_completion_rejected("context")

    def test_mixed_cannot_hide_open_work(self):
        self._assert_completion_rejected("mixed")

    def test_native_fixture_has_authorized_pending(self):
        self._assert_open_fixture()

    def test_manual_todo_still_closes_natively(self):
        self._assert_manual_still_native()

    def test_same_type_without_run_still_closes_natively(self):
        self._assert_manual_still_native(own_type=True)


@tagged("post_install", "-at_install")
class TestManufacturingAutomaticCompletion(AutomaticCompletionChecks, ManufacturingActivityCommon):
    """Bloqueo común sobre un pendiente generado por eventos reales de Manufacturing."""

    def _completion_fixture(self):
        self._policy()
        production = self._production()
        production.action_confirm()
        return production, self._runs(production)

    def test_feedback_cannot_hide_open_work(self):
        self._assert_completion_rejected("feedback")

    def test_private_done_cannot_hide_open_work(self):
        self._assert_completion_rejected("private_done")

    def test_cancel_cannot_hide_open_work(self):
        self._assert_completion_rejected("cancel")

    def test_archive_cannot_hide_open_work(self):
        self._assert_completion_rejected("archive")

    def test_unlink_cannot_hide_open_work(self):
        self._assert_completion_rejected("unlink")

    def test_context_cannot_hide_open_work(self):
        self._assert_completion_rejected("context")

    def test_mixed_cannot_hide_open_work(self):
        self._assert_completion_rejected("mixed")

    def test_native_fixture_has_authorized_pending(self):
        self._assert_open_fixture()

    def test_manual_todo_still_closes_natively(self):
        self._assert_manual_still_native()

    def test_same_type_without_run_still_closes_natively(self):
        self._assert_manual_still_native(own_type=True)


@tagged("post_install", "-at_install")
class TestAcceptanceAutomaticCompletion(AutomaticCompletionChecks, AcceptanceActivityCommon):
    """Bloqueo común sobre un pendiente generado por eventos reales de Acceptance."""

    def _completion_fixture(self):
        self._acceptance_policy()
        production = self._finished_production()
        lot = self.env["mc.rov.acceptance.activity.automation"]._produced_lots(production)
        cycle = self.env["mc.rov.acceptance.activity.cycle"].search(
            [
                ("production_id", "=", production.id),
                ("lot_id", "=", lot.id),
            ]
        )
        run = self.env["mc.rov.acceptance.activity.run"].search(
            [
                ("cycle_id", "=", cycle.id),
                ("stage", "=", "performance"),
            ]
        )
        return lot, run

    def test_feedback_cannot_hide_open_work(self):
        self._assert_completion_rejected("feedback")

    def test_private_done_cannot_hide_open_work(self):
        self._assert_completion_rejected("private_done")

    def test_cancel_cannot_hide_open_work(self):
        self._assert_completion_rejected("cancel")

    def test_archive_cannot_hide_open_work(self):
        self._assert_completion_rejected("archive")

    def test_unlink_cannot_hide_open_work(self):
        self._assert_completion_rejected("unlink")

    def test_context_cannot_hide_open_work(self):
        self._assert_completion_rejected("context")

    def test_mixed_cannot_hide_open_work(self):
        self._assert_completion_rejected("mixed")

    def test_native_fixture_has_authorized_pending(self):
        self._assert_open_fixture()

    def test_manual_todo_still_closes_natively(self):
        self._assert_manual_still_native()

    def test_same_type_without_run_still_closes_natively(self):
        self._assert_manual_still_native(own_type=True)


@tagged("post_install", "-at_install")
class TestQualityAutomaticCompletion(AutomaticCompletionChecks, QualityActivityCommon):
    """Bloqueo común sobre un pendiente generado por eventos reales de Quality."""

    def _completion_fixture(self):
        self._quality_policy()
        alert = self._quality_alert()
        run = self.env["mc.rov.quality.activity.run"].search([("alert_id", "=", alert.id)])
        return alert, run

    def test_feedback_cannot_hide_open_work(self):
        self._assert_completion_rejected("feedback")

    def test_private_done_cannot_hide_open_work(self):
        self._assert_completion_rejected("private_done")

    def test_cancel_cannot_hide_open_work(self):
        self._assert_completion_rejected("cancel")

    def test_archive_cannot_hide_open_work(self):
        self._assert_completion_rejected("archive")

    def test_unlink_cannot_hide_open_work(self):
        self._assert_completion_rejected("unlink")

    def test_context_cannot_hide_open_work(self):
        self._assert_completion_rejected("context")

    def test_mixed_cannot_hide_open_work(self):
        self._assert_completion_rejected("mixed")

    def test_native_fixture_has_authorized_pending(self):
        self._assert_open_fixture()

    def test_manual_todo_still_closes_natively(self):
        self._assert_manual_still_native()

    def test_same_type_without_run_still_closes_natively(self):
        self._assert_manual_still_native(own_type=True)


@tagged("post_install", "-at_install")
class TestEngineeringAutomaticCompletion(AutomaticCompletionChecks, EngineeringActivityCommon):
    """Bloqueo común sobre un pendiente generado por eventos reales de Engineering."""

    def _completion_fixture(self):
        self._policy()
        eco = self._eco()
        run = self.env["mc.rov.engineering.activity.run"].search([("eco_id", "=", eco.id)])
        return eco, run

    def test_feedback_cannot_hide_open_work(self):
        self._assert_completion_rejected("feedback")

    def test_private_done_cannot_hide_open_work(self):
        self._assert_completion_rejected("private_done")

    def test_cancel_cannot_hide_open_work(self):
        self._assert_completion_rejected("cancel")

    def test_archive_cannot_hide_open_work(self):
        self._assert_completion_rejected("archive")

    def test_unlink_cannot_hide_open_work(self):
        self._assert_completion_rejected("unlink")

    def test_context_cannot_hide_open_work(self):
        self._assert_completion_rejected("context")

    def test_mixed_cannot_hide_open_work(self):
        self._assert_completion_rejected("mixed")

    def test_native_fixture_has_authorized_pending(self):
        self._assert_open_fixture()

    def test_manual_todo_still_closes_natively(self):
        self._assert_manual_still_native()

    def test_same_type_without_run_still_closes_natively(self):
        self._assert_manual_still_native(own_type=True)


@tagged("post_install", "-at_install")
class TestInventoryAutomaticCompletion(AutomaticCompletionChecks, InventoryActivityCommon):
    """Bloqueo común sobre un pendiente generado por eventos reales de Inventory."""

    def _completion_fixture(self):
        _policy, picking = self._configured()
        picking.with_user(self.operator).action_confirm()
        run = self.env["mc.rov.inventory.activity.run"].search([("picking_id", "=", picking.id)])
        return picking, run

    def test_feedback_cannot_hide_open_work(self):
        self._assert_completion_rejected("feedback")

    def test_private_done_cannot_hide_open_work(self):
        self._assert_completion_rejected("private_done")

    def test_cancel_cannot_hide_open_work(self):
        self._assert_completion_rejected("cancel")

    def test_archive_cannot_hide_open_work(self):
        self._assert_completion_rejected("archive")

    def test_unlink_cannot_hide_open_work(self):
        self._assert_completion_rejected("unlink")

    def test_context_cannot_hide_open_work(self):
        self._assert_completion_rejected("context")

    def test_mixed_cannot_hide_open_work(self):
        self._assert_completion_rejected("mixed")

    def test_native_fixture_has_authorized_pending(self):
        self._assert_open_fixture()

    def test_manual_todo_still_closes_natively(self):
        self._assert_manual_still_native()

    def test_same_type_without_run_still_closes_natively(self):
        self._assert_manual_still_native(own_type=True)
