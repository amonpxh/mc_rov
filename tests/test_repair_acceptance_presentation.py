"""Native form contracts for explicit final acceptance, before visual installation."""

from lxml import etree

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_mc_rov_revision import RevisionCommon
from . import test_repair_acceptance_history as history


class MissingRepairAcceptancePresentation(AssertionError):
    """Distinguish absent presentation from broken native fixtures."""


@tagged("post_install", "-at_install", "repair_acceptance_presentation")
class TestRepairAcceptancePresentation(RevisionCommon):
    """Expose formal intent and durable attempts without generic activity completion."""

    _feature = history.TestRepairAcceptanceHistory._feature
    _native_revision = history.TestRepairAcceptanceHistory._native_revision
    _final = history.TestRepairAcceptanceHistory._final
    _history = history.TestRepairAcceptanceHistory._history

    def _presentation(self):
        revision = self.env["mc.rov.revision"]
        if not {
            "mc_final_attempt_pending",
            "mc_final_failure_reason",
            "mc_acceptance_history_html",
        } <= set(revision._fields) or not callable(
            getattr(revision, "action_record_final_failure", None)
        ):
            raise MissingRepairAcceptancePresentation("Missing repair acceptance presentation")
        # The presentation is restricted to this role, including for technical admins.
        self.env.user.with_env(self.env).write(
            {"group_ids": [Command.link(self.env.ref("mc_rov.group_work_assignment_team").id)]}
        )

    def _arch(self):
        view = self.env.ref("mc_rov.view_mc_rov_revision_form")
        result = self.env["mc.rov.revision"].get_view(view_id=view.id, view_type="form")
        return etree.fromstring(result["arch"].encode())

    def test_native_revision_form_is_available(self):
        self.assertEqual(self._arch().tag, "form")

    def test_native_private_history_still_has_no_public_acl(self):
        self.assertFalse(
            self.env["ir.model.access"].search_count(
                [
                    ("model_id.model", "=", "mc.rov.repair.acceptance.attempt"),
                    ("active", "=", True),
                ]
            )
        )

    def test_form_exposes_explicit_purpose_and_classification(self):
        self._presentation()
        arch = self._arch()
        for name in ("mc_acceptance_purpose", "mc_correction_required", "mc_retest_required"):
            self.assertTrue(arch.xpath(f"//field[@name='{name}']"), name)

    def test_form_has_start_and_real_failure_actions(self):
        self._presentation()
        arch = self._arch()
        for name in ("action_start_final_acceptance", "action_record_final_failure"):
            self.assertTrue(arch.xpath(f"//button[@name='{name}'][@type='object']"), name)

    def test_history_is_readonly_and_team_restricted(self):
        self._presentation()
        field = self.env["mc.rov.revision"]._fields["mc_acceptance_history_html"]
        self.assertTrue(field.readonly)
        self.assertFalse(field.store)
        self.assertIn("mc_rov.group_work_assignment_team", field.groups)
        self.assertTrue(self._arch().xpath("//field[@name='mc_acceptance_history_html']"))

    def test_pending_indicator_tracks_start_and_confirmation(self):
        self._presentation()
        revision = self._final()
        self.assertFalse(revision.mc_final_attempt_pending)
        revision.action_start_final_acceptance()
        self.assertTrue(revision.mc_final_attempt_pending)
        revision.action_confirmar()
        self.assertFalse(revision.mc_final_attempt_pending)

    def test_history_displays_first_failure_after_later_approval(self):
        self._presentation()
        revision = self._final()
        self._responder_todo(revision, "no_ok")
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        revision.action_volver_a_borrador()
        self._responder_todo(revision)
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        html = str(revision.mc_acceptance_history_html)
        self.assertIn("Rechazado", html)
        self.assertIn("Aprobado", html)
        self.assertEqual(len(self._history(revision)), 2)

    def test_failure_action_requires_reason_without_false_confirmation(self):
        self._presentation()
        revision = self._final(False)
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        with self.assertRaises(UserError):
            revision.action_record_final_failure()
        revision.mc_final_failure_reason = "Fallo real durante comprobación QA"
        revision.action_record_final_failure()
        self.assertEqual(revision.estado, "borrador")
        self.assertEqual(self._history(revision).state, "aborted")
        self.assertEqual(self._history(revision).reason, revision.mc_final_failure_reason)

    def test_history_escapes_free_text(self):
        self._presentation()
        revision = self._final(False)
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        revision.mc_final_failure_reason = "<img src=x onerror=alert(1)> QA evidence"
        revision.action_record_final_failure()
        html = str(revision.mc_acceptance_history_html)
        self.assertIn("QA evidence", html)
        self.assertNotIn("<img", html)

    def test_confirm_button_requires_pending_final_attempt(self):
        self._presentation()
        buttons = self._arch().xpath("//button[@name='action_confirmar']")
        self.assertTrue(buttons)
        self.assertTrue(
            all("mc_final_attempt_pending" in row.get("invisible", "") for row in buttons)
        )
