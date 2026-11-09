"""Additional source authorization and evidence controls for joint native outcomes."""

import copy
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .acceptance_activity_common import AcceptanceActivityCommon
from . import test_new_acceptance_events as events


@tagged("post_install", "-at_install", "new_acceptance_boundaries")
class TestNewAcceptanceBoundaries(AcceptanceActivityCommon):
    """Every linked business source must remain authorized at result capture."""

    # The matrix uses independent transactions/fixtures for each denied source.
    # pylint: disable=too-many-public-methods
    _service = events.TestNewAcceptanceEvents._service
    _pause = events.TestNewAcceptanceEvents._pause
    _unit = events.TestNewAcceptanceEvents._unit
    _start = events.TestNewAcceptanceEvents._start
    _attempts = events.TestNewAcceptanceEvents._attempts
    _operator = events.TestNewAcceptanceEvents._operator
    _deny = events.TestNewAcceptanceEvents._deny
    _events = events.TestNewAcceptanceEvents._events
    _complete = events.TestNewAcceptanceEvents._complete
    _started = events.TestNewAcceptanceEvents._started
    _result = events.TestNewAcceptanceEvents._result

    def _source_denial(self, kind, abort=False):
        unit = self._started(self._events())
        if abort:
            unit[2].chequeo_ids[0].resultado = "no_ok"
        source = {"production": unit[0], "lot": unit[1], "product": unit[1].product_id}[kind]
        self._deny(source)
        revision = unit[2].with_user(self._operator())
        before = copy.deepcopy(self._result(unit).requirements_snapshot)
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            if abort:
                revision.action_abort_new_acceptance("QA fallo sin acceso al origen")
            else:
                revision.action_confirmar()
        self.assertEqual(self._result(unit).requirements_snapshot, before)
        self.assertEqual(unit[2].estado, "borrador")

    def test_denied_manufacturing_blocks_confirmation(self):
        self._source_denial("production")

    def test_denied_serial_blocks_confirmation(self):
        self._source_denial("lot")

    def test_denied_product_blocks_confirmation(self):
        self._source_denial("product")

    def test_denied_manufacturing_blocks_abort(self):
        self._source_denial("production", abort=True)

    def test_denied_serial_blocks_abort(self):
        self._source_denial("lot", abort=True)

    def test_denied_product_blocks_abort(self):
        self._source_denial("product", abort=True)

    def test_internal_user_cannot_read_private_attempt(self):
        unit = self._started(self._events())
        with self.assertRaises(AccessError):
            self._result(unit).with_user(self._operator()).read(["requirements_snapshot"])

    def test_serializable_context_cannot_write_attempt(self):
        unit = self._started(self._events())
        with self.assertRaises(UserError):
            self._result(unit).sudo().with_context(mc_new_acceptance_capability=True).write(
                {"first_pass_snapshot": "passed"}
            )

    def test_serializable_context_cannot_create_attempt(self):
        self._events()
        with self.assertRaises(UserError):
            self.env["mc.rov.new.acceptance.attempt"].sudo().with_context(
                mc_new_acceptance_capability="authorized"
            ).create({})

    def test_sudo_cannot_replace_captured_configuration(self):
        unit = self._started(self._events())
        with self.assertRaises(UserError):
            self._result(unit).sudo().write({"requirements_snapshot": {"configuration": {}}})

    def test_captured_phase_classification_stays_frozen_while_peer_pending(self):
        unit = self._started(self._events())
        unit[2].action_confirmar()
        before = copy.deepcopy(self._result(unit).requirements_snapshot)
        with self.assertRaises(UserError):
            unit[2].write({"mc_retest_required": "yes"})
        self.assertEqual(self._result(unit).requirements_snapshot, before)

    def test_abort_capture_error_rolls_back_history(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        before = copy.deepcopy(self._result(unit).requirements_snapshot)
        with patch.object(
            type(self._service()),
            "_capture_native_result",
            side_effect=UserError("QA abort rollback"),
        ):
            with self.assertRaises(UserError), self.env.cr.savepoint():
                unit[2].action_abort_new_acceptance("QA fallo real")
        self.assertEqual(self._result(unit).requirements_snapshot, before)
        self.assertEqual(self._result(unit).state, "pending")

    def test_aborted_source_later_pass_keeps_first_failure(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_abort_new_acceptance("QA fallo inicial")
        original = copy.deepcopy(self._result(unit).requirements_snapshot)
        unit[2].chequeo_ids.write({"resultado": "ok"})
        (unit[2] | unit[3]).action_confirmar()
        self.assertEqual(self._result(unit).requirements_snapshot, original)
        self.assertEqual(self._result(unit).first_pass_snapshot, "failed")

    def test_unknown_retest_does_not_invent_first_pass(self):
        unit = self._started(self._events())
        unit[3].mc_retest_required = "unknown"
        (unit[2] | unit[3]).action_confirmar()
        self.assertEqual(self._result(unit).state, "confirmed")
        self.assertEqual(self._result(unit).first_pass_snapshot, "unknown")

    def test_blocking_finding_aborts_incomplete_protocol(self):
        unit = self._started(self._events(), complete=False)
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": unit[2].id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "impide_operar",
            }
        )
        unit[2].action_abort_new_acceptance("QA hallazgo bloqueante")
        self.assertEqual(self._result(unit).state, "failed")
        self.assertEqual(unit[2].estado, "borrador")

    def test_continuous_failure_aborts_incomplete_protocol(self):
        unit = self._started(self._events(), complete=False)
        unit[2].funcionamiento_continuo_resultado = "con_problemas"
        unit[2].action_abort_new_acceptance("QA fallo continuo")
        self.assertEqual(self._result(unit).state, "failed")
        self.assertEqual(unit[2].estado, "borrador")
