"""La presentación distingue seguimiento real sin ofrecer cierres ni retiradas."""

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from . import test_automatic_activity_completion as completion
from .acceptance_activity_common import AcceptanceActivityCommon
from .engineering_activity_common import EngineeringActivityCommon
from .inventory_activity_common import InventoryActivityCommon
from .manufacturing_activity_common import ManufacturingActivityCommon
from .quality_activity_common import QualityActivityCommon
from .test_mc_rov_revision import RevisionCommon


class AutomaticPresentationChecks(
    completion.AutomaticCompletionChecks
):  # pylint: disable=abstract-method
    """Contratos de transporte/identidad; no hereda métodos de prueba."""

    def _presentation_field(self):
        self.assertTrue(
            "mc_automatic_pending" in self.env["mail.activity"]._fields,
            "Missing authorized automatic presentation field",
        )
        return self.env["mail.activity"]._fields["mc_automatic_pending"]

    def _assert_presentation(self, case):
        field = self._presentation_field()
        source, run, activity = self._assert_open_fixture()
        if case == "pending":
            self.assertTrue(activity.mc_automatic_pending)
        elif case in ("manual", "untracked"):
            manual = self._untracked_activity(source, activity, own_type=case == "untracked")
            self.assertFalse(manual.mc_automatic_pending)
            self.assertTrue(activity.mc_automatic_pending)
        elif case == "temporary":
            temporary = activity.env["mail.activity"].new(
                {
                    "res_model_id": self.env["ir.model"]._get_id(source._name),
                    "res_id": source.id,
                    "activity_type_id": activity.activity_type_id.id,
                    "user_id": activity.user_id.id,
                },
                origin=activity,
            )
            self.assertFalse(temporary.id)
            self.assertFalse(temporary.mc_automatic_pending)
        elif case == "store":
            data = activity.activity_format()
            rows = data.get("mail.activity", [])
            selected = [row for row in rows if row.get("id") == activity.id]
            self.assertEqual(len(selected), 1)
            self.assertIs(selected[0].get("mc_automatic_pending"), True)
            manual = self._untracked_activity(source, activity)
            rows = manual.activity_format().get("mail.activity", [])
            selected = [row for row in rows if row.get("id") == manual.id]
            self.assertEqual(len(selected), 1)
            self.assertIs(selected[0].get("mc_automatic_pending"), False)
        elif case == "metadata":
            self.assertTrue(field.readonly)
            self.assertFalse(field.store)
            self.assertFalse(field.compute_sudo)
            self.assertTrue(activity.mc_automatic_pending)
        elif case == "revoked":
            self.env["ir.rule"].create(
                {
                    "name": "QA lectura de origen revocada",
                    "model_id": self.env["ir.model"]._get_id(source._name),
                    "domain_force": repr([("id", "!=", source.id)]),
                }
            )
            activity.invalidate_recordset(["mc_automatic_pending"])
            with self.assertRaises(AccessError), self.env.cr.savepoint():
                activity.read(["mc_automatic_pending"])
        else:
            self.fail("Contrato desconocido")
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(activity.with_env(self.env).active)

    def _assert_native_open_does_not_close(self):
        source, run, activity = self._assert_open_fixture()
        names = [name for name in ("state", "estado", "stage_id") if name in source._fields]
        before = source.read(names or ["id"])
        deadline = activity.date_deadline
        action = activity.action_open_document()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual((action["res_model"], action["res_id"]), (source._name, source.id))
        self.assertEqual(source.read(names or ["id"]), before)
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(activity.active)
        self.assertEqual(activity.date_deadline, deadline)

    def _assert_no_exception_route(self):
        _source, run, activity = self._assert_open_fixture()
        self.assertNotIn("mc.rov.activity.withdrawal.wizard", self.env.registry.models)
        self.assertFalse(hasattr(activity, "_mc_withdraw_automatic"))
        # Incluso el administrador debe resolver la operación real.
        with self.assertRaises(UserError), self.env.cr.savepoint():
            activity.with_env(self.env).action_cancel()
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(activity.active)


@tagged("post_install", "-at_install")
class TestRepairAutomaticPresentation(AutomaticPresentationChecks, RevisionCommon):
    """Presentación de Repair sobre su evento nativo ya comprobado."""

    _policy = completion.TestRepairAutomaticCompletion._policy
    _order = completion.TestRepairAutomaticCompletion._order
    _runs = completion.TestRepairAutomaticCompletion._runs

    _completion_fixture = completion.TestRepairAutomaticCompletion._completion_fixture

    def test_automatic_pending_flag_uses_private_identity(self):
        self._assert_presentation("pending")

    def test_manual_reminder_keeps_native_actions(self):
        self._assert_presentation("manual")

    def test_same_type_without_tracking_stays_manual(self):
        self._assert_presentation("untracked")

    def test_temporary_record_never_borrows_persistent_origin(self):
        self._assert_presentation("temporary")

    def test_mail_store_carries_pending_flag_and_manual_false(self):
        self._assert_presentation("store")

    def test_presentation_field_is_readonly_without_sudo(self):
        self._assert_presentation("metadata")

    def test_revoked_source_cannot_read_private_presentation(self):
        self._assert_presentation("revoked")

    def test_native_card_action_opens_source_without_closing(self):
        self._assert_native_open_does_not_close()

    def test_even_admin_has_no_exceptional_withdrawal(self):
        self._assert_no_exception_route()


@tagged("post_install", "-at_install")
class TestManufacturingAutomaticPresentation(
    AutomaticPresentationChecks, ManufacturingActivityCommon
):
    """Presentación de Manufacturing sobre su evento nativo ya comprobado."""

    _completion_fixture = completion.TestManufacturingAutomaticCompletion._completion_fixture

    def test_automatic_pending_flag_uses_private_identity(self):
        self._assert_presentation("pending")

    def test_manual_reminder_keeps_native_actions(self):
        self._assert_presentation("manual")

    def test_same_type_without_tracking_stays_manual(self):
        self._assert_presentation("untracked")

    def test_temporary_record_never_borrows_persistent_origin(self):
        self._assert_presentation("temporary")

    def test_mail_store_carries_pending_flag_and_manual_false(self):
        self._assert_presentation("store")

    def test_presentation_field_is_readonly_without_sudo(self):
        self._assert_presentation("metadata")

    def test_revoked_source_cannot_read_private_presentation(self):
        self._assert_presentation("revoked")

    def test_native_card_action_opens_source_without_closing(self):
        self._assert_native_open_does_not_close()

    def test_even_admin_has_no_exceptional_withdrawal(self):
        self._assert_no_exception_route()


@tagged("post_install", "-at_install")
class TestAcceptanceAutomaticPresentation(AutomaticPresentationChecks, AcceptanceActivityCommon):
    """Presentación de Acceptance sobre su evento nativo ya comprobado."""

    _completion_fixture = completion.TestAcceptanceAutomaticCompletion._completion_fixture

    def test_automatic_pending_flag_uses_private_identity(self):
        self._assert_presentation("pending")

    def test_manual_reminder_keeps_native_actions(self):
        self._assert_presentation("manual")

    def test_same_type_without_tracking_stays_manual(self):
        self._assert_presentation("untracked")

    def test_temporary_record_never_borrows_persistent_origin(self):
        self._assert_presentation("temporary")

    def test_mail_store_carries_pending_flag_and_manual_false(self):
        self._assert_presentation("store")

    def test_presentation_field_is_readonly_without_sudo(self):
        self._assert_presentation("metadata")

    def test_revoked_source_cannot_read_private_presentation(self):
        self._assert_presentation("revoked")

    def test_native_card_action_opens_source_without_closing(self):
        self._assert_native_open_does_not_close()

    def test_even_admin_has_no_exceptional_withdrawal(self):
        self._assert_no_exception_route()


@tagged("post_install", "-at_install")
class TestQualityAutomaticPresentation(AutomaticPresentationChecks, QualityActivityCommon):
    """Presentación de Quality sobre su evento nativo ya comprobado."""

    _completion_fixture = completion.TestQualityAutomaticCompletion._completion_fixture

    def test_automatic_pending_flag_uses_private_identity(self):
        self._assert_presentation("pending")

    def test_manual_reminder_keeps_native_actions(self):
        self._assert_presentation("manual")

    def test_same_type_without_tracking_stays_manual(self):
        self._assert_presentation("untracked")

    def test_temporary_record_never_borrows_persistent_origin(self):
        self._assert_presentation("temporary")

    def test_mail_store_carries_pending_flag_and_manual_false(self):
        self._assert_presentation("store")

    def test_presentation_field_is_readonly_without_sudo(self):
        self._assert_presentation("metadata")

    def test_revoked_source_cannot_read_private_presentation(self):
        self._assert_presentation("revoked")

    def test_native_card_action_opens_source_without_closing(self):
        self._assert_native_open_does_not_close()

    def test_even_admin_has_no_exceptional_withdrawal(self):
        self._assert_no_exception_route()


@tagged("post_install", "-at_install")
class TestEngineeringAutomaticPresentation(AutomaticPresentationChecks, EngineeringActivityCommon):
    """Presentación de Engineering sobre su evento nativo ya comprobado."""

    _completion_fixture = completion.TestEngineeringAutomaticCompletion._completion_fixture

    def test_automatic_pending_flag_uses_private_identity(self):
        self._assert_presentation("pending")

    def test_manual_reminder_keeps_native_actions(self):
        self._assert_presentation("manual")

    def test_same_type_without_tracking_stays_manual(self):
        self._assert_presentation("untracked")

    def test_temporary_record_never_borrows_persistent_origin(self):
        self._assert_presentation("temporary")

    def test_mail_store_carries_pending_flag_and_manual_false(self):
        self._assert_presentation("store")

    def test_presentation_field_is_readonly_without_sudo(self):
        self._assert_presentation("metadata")

    def test_revoked_source_cannot_read_private_presentation(self):
        self._assert_presentation("revoked")

    def test_native_card_action_opens_source_without_closing(self):
        self._assert_native_open_does_not_close()

    def test_even_admin_has_no_exceptional_withdrawal(self):
        self._assert_no_exception_route()


@tagged("post_install", "-at_install")
class TestInventoryAutomaticPresentation(AutomaticPresentationChecks, InventoryActivityCommon):
    """Presentación de Inventory sobre su evento nativo ya comprobado."""

    _completion_fixture = completion.TestInventoryAutomaticCompletion._completion_fixture

    def test_automatic_pending_flag_uses_private_identity(self):
        self._assert_presentation("pending")

    def test_manual_reminder_keeps_native_actions(self):
        self._assert_presentation("manual")

    def test_same_type_without_tracking_stays_manual(self):
        self._assert_presentation("untracked")

    def test_temporary_record_never_borrows_persistent_origin(self):
        self._assert_presentation("temporary")

    def test_mail_store_carries_pending_flag_and_manual_false(self):
        self._assert_presentation("store")

    def test_presentation_field_is_readonly_without_sudo(self):
        self._assert_presentation("metadata")

    def test_revoked_source_cannot_read_private_presentation(self):
        self._assert_presentation("revoked")

    def test_native_card_action_opens_source_without_closing(self):
        self._assert_native_open_does_not_close()

    def test_even_admin_has_no_exceptional_withdrawal(self):
        self._assert_no_exception_route()
