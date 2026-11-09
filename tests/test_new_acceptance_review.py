"""Reproduce independent review: historically confirmed protocols cannot become first attempts."""

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools.safe_eval import safe_eval

from .acceptance_activity_common import AcceptanceActivityCommon
from . import test_new_acceptance_events as events


@tagged("post_install", "-at_install", "new_acceptance_review")
class TestNewAcceptanceReview(AcceptanceActivityCommon):
    """Protect prospective first acceptance while preserving native reopen and copy."""

    _service = events.TestNewAcceptanceEvents._service
    _pause = events.TestNewAcceptanceEvents._pause
    _unit = events.TestNewAcceptanceEvents._unit
    _start = events.TestNewAcceptanceEvents._start
    _attempts = events.TestNewAcceptanceEvents._attempts
    _operator = events.TestNewAcceptanceEvents._operator
    _complete = events.TestNewAcceptanceEvents._complete

    def _reopened_rejection(self, unit, index):
        source = unit[index]
        self._complete(source)
        source.chequeo_ids[0].resultado = "no_ok"
        source.action_confirmar()
        self.assertEqual(source.resultado, "rechazado")
        source.action_volver_a_borrador()
        source.chequeo_ids[0].resultado = "ok"
        return source

    def test_native_reopen_preserves_ever_confirmed_indicator(self):
        unit = self._unit()
        source = self._reopened_rejection(unit, 2)
        self.assertEqual(source.estado, "borrador")
        self.assertTrue(source.documento_emitido)

    def test_native_copy_is_a_new_unissued_draft(self):
        unit = self._unit()
        source = self._reopened_rejection(unit, 2)
        duplicate = source.copy()
        self.assertNotEqual(duplicate, source)
        self.assertEqual(duplicate.estado, "borrador")
        self.assertFalse(duplicate.documento_emitido)
        self.assertTrue(source.documento_emitido)

    def test_native_fresh_drafts_can_start_formal_attempt(self):
        unit = self._unit()
        self._start(self._service(), unit)
        self.assertEqual(self._attempts(unit[1]).state, "pending")

    def test_reopened_historical_performance_cannot_start_first_attempt(self):
        unit = self._unit()
        self._reopened_rejection(unit, 2)
        with self.assertRaises(UserError):
            self._start(self._service(), unit)
        self.assertFalse(self._attempts(unit[1]))

    def test_reopened_historical_field_cannot_start_first_attempt(self):
        unit = self._unit()
        self._reopened_rejection(unit, 3)
        with self.assertRaises(UserError):
            self._start(self._service(), unit)
        self.assertFalse(self._attempts(unit[1]))

    def test_rpc_cannot_clear_ever_confirmed_indicator(self):
        unit = self._unit()
        source = self._reopened_rejection(unit, 2)
        user = self._operator()
        for value in (False, 0, None):
            with self.assertRaises(UserError):
                source.with_user(user).write({"documento_emitido": value})
            self.assertTrue(source.documento_emitido)

    def test_dialog_excludes_historically_confirmed_protocols(self):
        view = self.env.ref("mc_rov.view_mc_rov_new_acceptance_wizard_form")
        arch = etree.fromstring(
            self.env["mc.rov.new.acceptance.wizard"]
            .get_view(view_id=view.id, view_type="form")["arch"]
            .encode()
        )
        for name in ("rnd_id", "trn_id"):
            field = arch.xpath(f"//field[@name='{name}']")[0]
            domain = safe_eval(field.get("domain"), {"lot_id": False})
            self.assertIn(("documento_emitido", "=", False), domain)
