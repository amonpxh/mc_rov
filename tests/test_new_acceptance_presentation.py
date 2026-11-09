"""Native joint acceptance presentation, separated from private capture and KPI."""

from lxml import etree

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .acceptance_activity_common import AcceptanceActivityCommon
from . import test_new_acceptance_events as events


class MissingNewAcceptancePresentation(AssertionError):
    """Identify missing presentation without accepting broken native fixtures."""


@tagged("post_install", "-at_install", "new_acceptance_presentation")
class TestNewAcceptancePresentation(AcceptanceActivityCommon):
    """Keep source actions native and the joint history protected at the end of the form."""

    _service = events.TestNewAcceptanceEvents._service
    _pause = events.TestNewAcceptanceEvents._pause
    _unit = events.TestNewAcceptanceEvents._unit
    _start = events.TestNewAcceptanceEvents._start
    _attempts = events.TestNewAcceptanceEvents._attempts
    _events = events.TestNewAcceptanceEvents._events
    _complete = events.TestNewAcceptanceEvents._complete
    _started = events.TestNewAcceptanceEvents._started
    _result = events.TestNewAcceptanceEvents._result

    def _presentation(self):
        revision = self.env["mc.rov.revision"]
        if not {
            "mc_new_attempt_pending",
            "mc_new_acceptance_state",
            "mc_new_phase_recorded",
            "mc_new_failure_reason",
            "mc_new_acceptance_history_html",
        } <= set(revision._fields) or not callable(
            getattr(revision, "action_record_new_acceptance_failure", None)
        ):
            raise MissingNewAcceptancePresentation("Missing joint acceptance presentation")
        self.env.user.with_env(self.env).write(
            {"group_ids": [Command.link(self.env.ref("mc_rov.group_work_assignment_team").id)]}
        )

    def _arch(self):
        view = self.env.ref("mc_rov.view_mc_rov_revision_form")
        return etree.fromstring(
            self.env["mc.rov.revision"]
            .get_view(view_id=view.id, view_type="form")["arch"]
            .encode()
        )

    def test_native_revision_form_is_available(self):
        self.assertEqual(self._arch().tag, "form")

    def test_native_joint_history_has_no_public_acl(self):
        self.assertFalse(
            self.env["ir.model.access"].search_count(
                [
                    (
                        "model_id.model",
                        "in",
                        ["mc.rov.new.acceptance.episode", "mc.rov.new.acceptance.attempt"],
                    ),
                    ("active", "=", True),
                ]
            )
        )

    def test_state_tracks_both_native_confirmations(self):
        self._presentation()
        unit = self._started(self._events())
        self.assertTrue(unit[3].mc_new_attempt_pending)
        unit[2].action_confirmar()
        self.assertEqual(unit[2].mc_new_acceptance_state, "pending")
        self.assertTrue(unit[2].mc_new_phase_recorded)
        unit[3].action_confirmar()
        self.assertFalse(unit[2].mc_new_attempt_pending)
        self.assertEqual(unit[2].mc_new_acceptance_state, "confirmed")

    def test_unselected_source_has_no_formal_status(self):
        self._presentation()
        unit = self._unit()
        self.assertFalse(unit[2].mc_new_acceptance_state)
        self.assertFalse(unit[2].mc_new_attempt_pending)
        self.assertFalse(unit[2].mc_new_phase_recorded)

    def test_history_is_readonly_team_restricted(self):
        self._presentation()
        field = self.env["mc.rov.revision"]._fields["mc_new_acceptance_history_html"]
        self.assertTrue(field.readonly)
        self.assertFalse(field.store)
        self.assertIn("mc_rov.group_work_assignment_team", field.groups)
        self.assertTrue(self._arch().xpath("//field[@name='mc_new_acceptance_history_html']"))

    def test_joint_acceptance_page_is_last(self):
        self._presentation()
        pages = self._arch().xpath("//notebook/page")
        self.assertEqual(pages[-1].get("name"), "new_acceptance")

    def test_page_exposes_classification_and_real_failure(self):
        self._presentation()
        page = self._arch().xpath("//page[@name='new_acceptance']")[0]
        for name in ("mc_correction_required", "mc_retest_required", "mc_new_failure_reason"):
            self.assertTrue(page.xpath(f".//field[@name='{name}']"))
        self.assertTrue(
            page.xpath(".//button[@name='action_record_new_acceptance_failure'][@type='object']")
        )

    def test_failure_action_requires_reason(self):
        self._presentation()
        unit = self._started(self._events(), complete=False)
        unit[2].chequeo_ids[0].resultado = "no_ok"
        with self.assertRaises(UserError):
            unit[2].action_record_new_acceptance_failure()
        unit[2].mc_new_failure_reason = "QA fallo real"
        unit[2].action_record_new_acceptance_failure()
        self.assertEqual(self._result(unit).state, "failed")
        self.assertEqual(unit[2].estado, "borrador")

    def test_failure_action_keeps_native_evidence_requirement(self):
        self._presentation()
        unit = self._started(self._events())
        unit[2].mc_new_failure_reason = "Una nota no demuestra fallo"
        with self.assertRaises(UserError):
            unit[2].action_record_new_acceptance_failure()
        self.assertEqual(self._result(unit).state, "pending")

    def test_history_escapes_free_text(self):
        self._presentation()
        unit = self._started(self._events(), complete=False)
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].mc_new_failure_reason = "<img src=x onerror=alert(1)> QA joint evidence"
        unit[2].action_record_new_acceptance_failure()
        html = str(unit[2].mc_new_acceptance_history_html)
        self.assertIn("QA joint evidence", html)
        self.assertNotIn("<img", html)

    def test_new_source_history_retains_first_failure_after_later_pass(self):
        self._presentation()
        service = self._events()
        unit = self._started(service)
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_confirmar()
        rnd = self._revision(lot_id=unit[1].id, tipo="rendimiento")
        trn = self._revision(lot_id=unit[1].id, tipo="terreno")
        self._complete(rnd | trn)
        self._start(service, (*unit[:2], rnd, trn))
        (rnd | trn).action_confirmar()
        html = str(rnd.mc_new_acceptance_history_html)
        self.assertIn("Fallido", html)
        self.assertIn("Aprobado", html)
        self.assertEqual(len(self._attempts(unit[1])), 2)

    def test_captured_phase_cannot_record_another_failure(self):
        self._presentation()
        unit = self._started(self._events())
        unit[2].action_confirmar()
        unit[2].mc_new_failure_reason = "QA fase ya sellada"
        with self.assertRaises(UserError):
            unit[2].action_record_new_acceptance_failure()
        self.assertEqual(self._result(unit).state, "pending")
