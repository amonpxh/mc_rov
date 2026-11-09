"""Capture a joint formal result at native confirmation, never from activity closure."""

import copy
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .acceptance_activity_common import AcceptanceActivityCommon
from . import test_new_acceptance_start as start


class MissingNewAcceptanceEvents(AssertionError):
    """Expected missing native-event assertions, separated from fixture errors."""


@tagged("post_install", "-at_install", "new_acceptance_events")
class TestNewAcceptanceEvents(AcceptanceActivityCommon):
    """Preserve the first joint outcome and both independent native source records."""

    # One fixture covers outcomes, provenance, atomicity and source permissions.
    # pylint: disable=too-many-public-methods

    _service = start.TestNewAcceptanceStart._service
    _pause = start.TestNewAcceptanceStart._pause
    _unit = start.TestNewAcceptanceStart._unit
    _start = start.TestNewAcceptanceStart._start
    _attempts = start.TestNewAcceptanceStart._attempts
    _operator = start.TestNewAcceptanceStart._operator
    _deny = start.TestNewAcceptanceStart._deny

    def _events(self):
        model = self.env["mc.rov.new.acceptance.attempt"]
        if not {"closed_at", "finished_by_id", "first_pass_snapshot"} <= set(
            model._fields
        ) or not callable(
            getattr(self.env["mc.rov.revision"], "action_abort_new_acceptance", None)
        ):
            raise MissingNewAcceptanceEvents("Missing joint native acceptance results")
        return self._service()

    def _complete(self, revisions):
        for revision in revisions:
            self._corrida_completa(revision)
            self._responder_todo(revision)
            self._responder_sellos(revision)
            revision.write({"mc_correction_required": "no", "mc_retest_required": "no"})

    def _started(self, service, complete=True):
        unit = self._unit()
        if complete:
            self._complete(unit[2] | unit[3])
        self._start(service, unit)
        return unit

    def _result(self, unit):
        return self._attempts(unit[1])

    def test_native_unselected_performance_confirms_normally(self):
        unit = self._unit()
        self._complete(unit[2])
        unit[2].action_confirmar()
        self.assertEqual(unit[2].resultado, "aprobado")
        self.assertFalse(self._attempts(unit[1]))

    def test_native_unselected_field_confirms_normally(self):
        unit = self._unit()
        self._complete(unit[3])
        unit[3].action_confirmar()
        self.assertEqual(unit[3].resultado, "aprobado")
        self.assertFalse(self._attempts(unit[1]))

    def test_native_rejected_source_keeps_native_verdict(self):
        unit = self._unit()
        self._complete(unit[2])
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_confirmar()
        self.assertEqual(unit[2].resultado, "rechazado")

    def test_native_incomplete_source_cannot_confirm(self):
        unit = self._unit()
        with self.assertRaises(UserError):
            unit[2].action_confirmar()
        self.assertEqual(unit[2].estado, "borrador")

    def test_performance_pass_alone_keeps_joint_pending(self):
        unit = self._started(self._events())
        unit[2].action_confirmar()
        attempt = self._result(unit)
        self.assertEqual(attempt.state, "pending")
        self.assertEqual(
            attempt.requirements_snapshot["results"]["performance"]["verdict"], "aprobado"
        )

    def test_field_pass_alone_keeps_joint_pending(self):
        unit = self._started(self._events())
        unit[3].action_confirmar()
        self.assertEqual(self._result(unit).state, "pending")
        self.assertIn("field", self._result(unit).requirements_snapshot["results"])

    def test_both_passes_close_joint_and_first_pass(self):
        unit = self._started(self._events())
        unit[2].action_confirmar()
        unit[3].action_confirmar()
        attempt = self._result(unit)
        self.assertEqual((attempt.state, attempt.first_pass_snapshot), ("confirmed", "passed"))
        self.assertTrue(attempt.closed_at)

    def test_performance_rejection_closes_before_field(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_confirmar()
        self.assertEqual(
            (self._result(unit).state, self._result(unit).first_pass_snapshot),
            ("failed", "failed"),
        )
        self.assertEqual(unit[3].estado, "borrador")

    def test_field_rejection_closes_before_performance(self):
        unit = self._started(self._events())
        unit[3].chequeo_ids[0].resultado = "no_ok"
        unit[3].action_confirmar()
        self.assertEqual(self._result(unit).state, "failed")
        self.assertEqual(unit[2].estado, "borrador")

    def test_incomplete_performance_can_abort_for_real_failure(self):
        unit = self._started(self._events(), complete=False)
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_abort_new_acceptance("Fallo real QA antes de completar rendimiento")
        self.assertEqual(self._result(unit).first_pass_snapshot, "failed")
        self.assertEqual(unit[2].estado, "borrador")

    def test_incomplete_field_can_abort_for_real_failure(self):
        unit = self._started(self._events(), complete=False)
        unit[3].chequeo_ids[0].resultado = "no_ok"
        unit[3].action_abort_new_acceptance("Fallo real QA antes de completar terreno")
        self.assertEqual(self._result(unit).state, "failed")

    def test_abort_requires_nonempty_reason(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        with self.assertRaises(UserError):
            unit[2].action_abort_new_acceptance(" ")
        self.assertEqual(self._result(unit).state, "pending")

    def test_abort_requires_real_failure_evidence(self):
        unit = self._started(self._events())
        with self.assertRaises(UserError):
            unit[2].action_abort_new_acceptance("Una nota no prueba un fallo")
        self.assertEqual(self._result(unit).state, "pending")

    def test_unselected_source_cannot_abort_an_attempt(self):
        self._events()
        unit = self._unit()
        unit[2].chequeo_ids[0].resultado = "no_ok"
        with self.assertRaises(UserError):
            unit[2].action_abort_new_acceptance("Fallo QA sin intento formal")
        self.assertFalse(self._attempts(unit[1]))

    def test_raw_confirmation_cannot_bypass_event_capture(self):
        unit = self._started(self._events())
        with self.assertRaises(UserError):
            unit[2].write({"estado": "confirmado"})

    def test_rpc_context_cannot_forge_native_confirmation(self):
        unit = self._started(self._events())
        with self.assertRaises(UserError):
            unit[2].with_context(mc_new_acceptance_native=True).write({"estado": "confirmado"})

    def test_reopen_closed_sources_preserves_joint_result(self):
        unit = self._started(self._events())
        (unit[2] | unit[3]).action_confirmar()
        original = copy.deepcopy(self._result(unit).requirements_snapshot)
        unit[2].action_volver_a_borrador()
        self.assertEqual(self._result(unit).requirements_snapshot, original)
        self.assertEqual(self._result(unit).first_pass_snapshot, "passed")

    def test_reopen_captured_phase_while_joint_pending_is_blocked(self):
        unit = self._started(self._events())
        unit[2].action_confirmar()
        with self.assertRaises(UserError):
            unit[2].action_volver_a_borrador()

    def test_second_attempt_success_preserves_first_failure(self):
        service = self._events()
        unit = self._started(service)
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_confirmar()
        rnd = self._revision(lot_id=unit[1].id, tipo="rendimiento")
        trn = self._revision(lot_id=unit[1].id, tipo="terreno")
        self._complete(rnd | trn)
        self._start(service, (*unit[:2], rnd, trn))
        (rnd | trn).action_confirmar()
        self.assertEqual(
            self._attempts(unit[1]).mapped("first_pass_snapshot"), ["failed", "passed"]
        )

    def test_batch_confirmation_captures_both_once(self):
        unit = self._started(self._events())
        (unit[2] | unit[3]).action_confirmar()
        self.assertEqual(
            set(self._result(unit).requirements_snapshot["results"]), {"performance", "field"}
        )
        self.assertEqual(self._result(unit).state, "confirmed")

    def test_repeated_native_confirmation_does_not_replace_snapshot(self):
        unit = self._started(self._events())
        (unit[2] | unit[3]).action_confirmar()
        original = copy.deepcopy(self._result(unit).requirements_snapshot)
        unit[2].action_confirmar()
        self.assertEqual(self._result(unit).requirements_snapshot, original)

    def test_catalog_rename_does_not_strand_native_completion(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].chequeo_id.name = "QA catálogo posterior"
        (unit[2] | unit[3]).action_confirmar()
        self.assertEqual(self._result(unit).first_pass_snapshot, "passed")

    def test_later_answers_do_not_change_captured_evidence(self):
        unit = self._started(self._events())
        (unit[2] | unit[3]).action_confirmar()
        original = copy.deepcopy(self._result(unit).requirements_snapshot)
        unit[2].action_volver_a_borrador()
        unit[2].chequeo_ids[0].resultado = "no_ok"
        self.assertEqual(self._result(unit).requirements_snapshot, original)

    def test_unknown_flags_do_not_invent_first_pass(self):
        unit = self._started(self._events())
        unit[2].mc_correction_required = "unknown"
        (unit[2] | unit[3]).action_confirmar()
        self.assertEqual(self._result(unit).state, "confirmed")
        self.assertEqual(self._result(unit).first_pass_snapshot, "unknown")

    def test_explicit_correction_requirement_fails_first_pass(self):
        unit = self._started(self._events())
        unit[2].mc_correction_required = "yes"
        unit[2].action_confirmar()
        self.assertEqual(self._result(unit).first_pass_snapshot, "failed")

    def test_explicit_retest_requirement_fails_first_pass(self):
        unit = self._started(self._events())
        unit[3].mc_retest_required = "yes"
        unit[3].action_confirmar()
        self.assertEqual(self._result(unit).state, "failed")

    def test_informative_observations_can_pass_joint_acceptance(self):
        unit = self._started(self._events())
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": unit[2].id,
                "componente_id": self.env.ref("mc_rov.comp_motor").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
            }
        )
        (unit[2] | unit[3]).action_confirmar()
        self.assertEqual(unit[2].resultado, "aprobado_con_observaciones")
        self.assertEqual(self._result(unit).first_pass_snapshot, "passed")

    def test_closed_result_is_immutable_even_for_sudo(self):
        unit = self._started(self._events())
        (unit[2] | unit[3]).action_confirmar()
        with self.assertRaises(UserError):
            self._result(unit).sudo().write({"first_pass_snapshot": "failed"})

    def test_history_failure_rolls_back_native_confirmation(self):
        self._events()
        unit = self._started(self._service())
        before = copy.deepcopy(self._result(unit).requirements_snapshot)
        service_type = type(self.env["mc.rov.new.acceptance"])
        with patch.object(
            service_type, "_capture_native_result", side_effect=UserError("QA capture rollback")
        ):
            with self.assertRaises(UserError), self.env.cr.savepoint():
                unit[2].action_confirmar()
        self.assertEqual(unit[2].estado, "borrador")
        self.assertEqual(self._result(unit).requirements_snapshot, before)

    def test_restricted_source_cannot_abort_formal_attempt(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        self._deny(unit[2])
        with self.assertRaises(AccessError):
            unit[2].with_user(self._operator()).action_abort_new_acceptance("Fallo QA restringido")

    def test_other_company_context_cannot_abort(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        user = self._operator()
        company = self.env["res.company"].create({"name": "QA resultado otra empresa"})
        user.write({"company_ids": [Command.link(company.id)]})
        with self.assertRaises(AccessError):
            unit[2].with_user(user).with_context(
                allowed_company_ids=[company.id]
            ).action_abort_new_acceptance("Fallo QA otra empresa")

    def test_portal_cannot_abort(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        with self.assertRaises(AccessError):
            unit[2].with_user(self._operator(portal=True)).action_abort_new_acceptance(
                "Fallo QA portal"
            )

    def test_peer_success_after_failure_does_not_rewrite_joint(self):
        unit = self._started(self._events())
        unit[2].chequeo_ids[0].resultado = "no_ok"
        unit[2].action_confirmar()
        original = copy.deepcopy(self._result(unit).requirements_snapshot)
        unit[3].action_confirmar()
        self.assertEqual(self._result(unit).requirements_snapshot, original)
        self.assertEqual(self._result(unit).state, "failed")

    def test_actor_is_preserved_on_both_results(self):
        unit = self._started(self._events())
        user = self._operator()
        (unit[2] | unit[3]).with_user(user).action_confirmar()
        attempt = self._result(unit)
        self.assertEqual(attempt.finished_by_id, user)
        self.assertEqual(
            {row["actor_id"] for row in attempt.requirements_snapshot["results"].values()},
            {user.id},
        )
