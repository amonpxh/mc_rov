from datetime import datetime
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install")
# Cada caso representa un evento de negocio o una frontera de decisión manual.
# pylint: disable=too-many-public-methods
class TestAcceptanceActivityLifecycle(AcceptanceActivityCommon):
    """Cerrar un pendiente nunca sustituye confirmar pruebas o emitir la ficha."""

    def _lifecycle(self):
        service = self.env["mc.rov.acceptance.activity.automation"]
        self.assertTrue(
            callable(getattr(service, "_reconcile", None)),
            "Missing acceptance evidence lifecycle",
        )
        return service

    def _visit(self):
        service = self._lifecycle()
        policy = self._acceptance_policy()
        production = self._finished_production()
        lot = service._produced_lots(production)
        cycle = self.env["mc.rov.acceptance.activity.cycle"].search(
            [("production_id", "=", production.id), ("lot_id", "=", lot.id)]
        )
        return service, policy, lot, cycle

    def _stage_runs(self, cycle, stage):
        return self.env["mc.rov.acceptance.activity.run"].search(
            [("cycle_id", "=", cycle.id), ("stage", "=", stage)], order="occurrence,id"
        )

    def _pending(self, cycle, stage):
        return self._stage_runs(cycle, stage).filtered(lambda run: run.outcome == "pending")

    def _proof(self, lot, kind="rendimiento", rejected=False):
        revision = self._revision(lot_id=lot.id, tipo=kind)
        self._corrida_completa(revision)
        self._responder_todo(revision)
        self._responder_sellos(revision)
        if rejected:
            self.assertTrue(revision.chequeo_ids)
            revision.chequeo_ids[:1].resultado = "no_ok"
        return revision

    def _selected(self, service, lot, kind="rendimiento", rejected=False):
        proof = self._proof(lot, kind, rejected)
        service._select_evidence(lot, **{"rnd" if kind == "rendimiento" else "trn": proof})
        return proof

    def _accepted_pair(self, service, lot):
        rnd = self._selected(service, lot)
        trn = self._selected(service, lot, "terreno")
        rnd.action_confirmar()
        trn.action_confirmar()
        return rnd, trn

    def _fen(self, lot, rnd, trn):
        return self.env["mc.rov.ficha.equipo.nuevo"].create(
            {"lot_id": lot.id, "rnd_id": rnd.id, "trn_id": trn.id}
        )

    def test_native_confirmed_approved_and_rejected_proofs(self):
        approved = self._proof(self.lot)
        rejected = self._proof(self.lot, "terreno", rejected=True)
        approved.action_confirmar()
        rejected.action_confirmar()
        self.assertEqual(approved.resultado, "aprobado")
        self.assertEqual(rejected.resultado, "rechazado")

    def test_native_correction_restores_draft_without_verdict(self):
        revision = self._proof(self.lot, rejected=True)
        revision.action_confirmar()
        revision.action_volver_a_borrador()
        self.assertEqual(revision.estado, "borrador")
        self.assertFalse(revision.resultado)

    def test_native_emission_creates_frozen_pdf(self):
        rnd = self._proof(self.lot)
        trn = self._proof(self.lot, "terreno")
        (rnd | trn).action_confirmar()
        fen = self._fen(self.lot, rnd, trn)
        self.assertFalse(fen.pdf_attachment_id)
        fen.action_emitir()
        self.assertEqual(fen.estado, "emitida")
        self.assertTrue(fen.pdf_attachment_id.raw)

    def test_confirmed_approved_proof_closes_realization(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot)
        rnd.action_confirmar()
        run = self._stage_runs(cycle, "performance")
        self.assertEqual(run.outcome, "business_done")
        self.assertFalse(self._pending(cycle, "performance"))
        self.assertTrue(run.finished_at)
        self.assertEqual(run.finished_by_id, self.env.user)
        self.assertTrue(self._pending(cycle, "field"))

    def test_rejected_proof_finishes_realization_and_opens_resolution(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        rnd.action_confirmar()
        self.assertEqual(self._stage_runs(cycle, "performance").outcome, "business_done")
        self.assertEqual(len(self._pending(cycle, "rejection_performance")), 1)
        self.assertFalse(self._stage_runs(cycle, "fen"))

    def test_repeated_confirmation_does_not_duplicate_resolution(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        rnd.action_confirmar()
        rnd.action_confirmar()
        service._reconcile(lot)
        self.assertEqual(len(self._stage_runs(cycle, "rejection_performance")), 1)

    def test_draft_correction_keeps_rejection_pending(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        rnd.action_confirmar()
        resolution = self._pending(cycle, "rejection_performance")
        rnd.action_volver_a_borrador()
        self._responder_todo(rnd)
        self.assertEqual(resolution.outcome, "pending")
        self.assertFalse(self._stage_runs(cycle, "fen"))

    def test_accepted_correction_closes_resolution(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        rnd.action_confirmar()
        rnd.action_volver_a_borrador()
        self._responder_todo(rnd)
        rnd.action_confirmar()
        self.assertEqual(self._stage_runs(cycle, "rejection_performance").outcome, "business_done")

    def test_explicit_accepted_repetition_closes_old_rejection(self):
        service, _policy, lot, cycle = self._visit()
        rejected = self._selected(service, lot, rejected=True)
        rejected.action_confirmar()
        repeated = self._proof(lot)
        repeated.action_confirmar()
        self.assertTrue(self._pending(cycle, "rejection_performance"))
        service._select_evidence(lot, rnd=repeated, reason="Repetición tras corregir equipo")
        self.assertFalse(self._pending(cycle, "rejection_performance"))
        self.assertEqual(rejected.resultado, "rechazado")

    def test_two_rejections_have_independent_resolutions(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        trn = self._selected(service, lot, "terreno", rejected=True)
        (rnd | trn).action_confirmar()
        self.assertEqual(len(self._pending(cycle, "rejection_performance")), 1)
        self.assertEqual(len(self._pending(cycle, "rejection_field")), 1)

    def test_unselected_confirmed_proof_does_not_close_stage(self):
        _service, _policy, lot, cycle = self._visit()
        self._proof(lot).action_confirmar()
        self.assertTrue(self._pending(cycle, "performance"))

    def test_selecting_already_confirmed_proof_reconciles_explicitly(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._proof(lot)
        rnd.action_confirmar()
        self.assertTrue(self._pending(cycle, "performance"))
        service._select_evidence(lot, rnd=rnd)
        self.assertFalse(self._pending(cycle, "performance"))

    def test_one_accepted_proof_does_not_create_fen(self):
        service, _policy, lot, cycle = self._visit()
        self._selected(service, lot).action_confirmar()
        self.assertFalse(self._stage_runs(cycle, "fen"))

    def test_both_accepted_proofs_create_one_fen_pending(self):
        service, _policy, lot, cycle = self._visit()
        self._accepted_pair(service, lot)
        service._reconcile(lot)
        self.assertEqual(len(self._pending(cycle, "fen")), 1)

    def test_approved_with_observations_is_eligible(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot)
        trn = self._selected(service, lot, "terreno")
        self.env["mc.rov.revision.hallazgo"].create(
            {
                "revision_id": rnd.id,
                "componente_id": self.env.ref("mc_rov.comp_umbilical").id,
                "hallazgo_id": self.env.ref("mc_rov.hallazgo_corrosion").id,
                "severidad": "informativo",
            }
        )
        (rnd | trn).action_confirmar()
        self.assertEqual(rnd.resultado, "aprobado_con_observaciones")
        self.assertTrue(self._pending(cycle, "fen"))

    def test_fen_draft_or_preview_does_not_close_emission(self):
        service, _policy, lot, cycle = self._visit()
        rnd, trn = self._accepted_pair(service, lot)
        fen = self._fen(lot, rnd, trn)
        fen.action_descargar()
        self.assertEqual(fen.estado, "borrador")
        self.assertTrue(self._pending(cycle, "fen"))

    def test_matching_real_pdf_emission_closes_cycle(self):
        service, _policy, lot, cycle = self._visit()
        rnd, trn = self._accepted_pair(service, lot)
        fen = self._fen(lot, rnd, trn)
        fen.action_emitir()
        self.assertTrue(fen.pdf_attachment_id.raw)
        self.assertEqual(self._stage_runs(cycle, "fen").outcome, "business_done")
        self.assertEqual(cycle.state, "done")

    def test_emission_of_different_selection_does_not_close_cycle(self):
        service, _policy, lot, cycle = self._visit()
        _rnd, trn = self._accepted_pair(service, lot)
        other = self._proof(lot)
        other.action_confirmar()
        self._fen(lot, other, trn).action_emitir()
        self.assertTrue(self._pending(cycle, "fen"))
        self.assertEqual(cycle.state, "open")

    def test_correction_withdraws_fen_eligibility(self):
        service, _policy, lot, cycle = self._visit()
        rnd, _trn = self._accepted_pair(service, lot)
        run = self._pending(cycle, "fen")
        rnd.action_volver_a_borrador()
        self.assertEqual(run.outcome, "cancelled")
        self.assertFalse(self._pending(cycle, "fen"))

    def test_restored_eligibility_creates_distinct_event_and_deadline(self):
        service, policy, lot, cycle = self._visit()
        rnd, _trn = self._accepted_pair(service, lot)
        first = self._pending(cycle, "fen")
        rnd.action_volver_a_borrador()
        instant = datetime(2026, 11, 9, 15)
        with patch("odoo.fields.Datetime.now", return_value=instant):
            rnd.action_confirmar()
        runs = self._stage_runs(cycle, "fen")
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs.mapped("occurrence"), [1, 2])
        current = self._pending(cycle, "fen")
        self.assertNotEqual(current, first)
        self.assertEqual(current.started_at, instant)
        self.assertEqual(current.original_deadline, policy._deadline(instant, policy.fen_days))

    def test_rejection_resolution_uses_its_own_event_date(self):
        service, policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        instant = datetime(2026, 11, 6, 15)
        with patch("odoo.fields.Datetime.now", return_value=instant):
            rnd.action_confirmar()
        run = self._pending(cycle, "rejection_performance")
        self.assertEqual(run.started_at, instant)
        self.assertEqual(run.original_deadline, policy._deadline(instant, policy.rejection_days))

    def test_manual_done_does_not_approve_test(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot)
        run = self._pending(cycle, "performance")
        run.activity_id.action_feedback(feedback="Revisar posteriormente")
        self.assertEqual(run.outcome, "manual_done")
        self.assertEqual(rnd.estado, "borrador")
        self.assertFalse(rnd.resultado)

    def test_manual_cancel_does_not_reject_or_close_business(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot)
        run = self._pending(cycle, "performance")
        run.activity_id.action_cancel()
        self.assertEqual(run.outcome, "cancelled")
        self.assertEqual(rnd.estado, "borrador")
        self.assertEqual(cycle.state, "open")

    def test_manual_fen_cancel_is_not_recreated_by_unrelated_edit(self):
        service, _policy, lot, cycle = self._visit()
        rnd, _trn = self._accepted_pair(service, lot)
        self._pending(cycle, "fen").activity_id.action_cancel()
        rnd.write({"condiciones_notas": "Nota sin cambiar requisitos"})
        service._reconcile(lot)
        self.assertEqual(len(self._stage_runs(cycle, "fen")), 1)
        self.assertFalse(self._pending(cycle, "fen"))

    def test_business_closure_is_not_overwritten_by_feedback_hook(self):
        service, _policy, lot, cycle = self._visit()
        self._selected(service, lot).action_confirmar()
        run = self._stage_runs(cycle, "performance")
        self.assertEqual(run.outcome, "business_done")
        self.assertTrue(run.finish_reason)

    def test_paused_policy_allows_existing_realization_to_close(self):
        service, policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot)
        policy.enabled = False
        rnd.action_confirmar()
        self.assertFalse(self._pending(cycle, "performance"))

    def test_paused_policy_prevents_new_rejection_activity(self):
        service, policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        policy.enabled = False
        rnd.action_confirmar()
        self.assertFalse(self._stage_runs(cycle, "rejection_performance"))
        self.assertFalse(self._pending(cycle, "performance"))

    def test_resume_and_edit_do_not_backfill_missed_resolution(self):
        service, policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        policy.enabled = False
        rnd.action_confirmar()
        policy.enabled = True
        rnd.condiciones_notas = "Nota posterior a la reactivación"
        service._reconcile(lot)
        self.assertFalse(self._stage_runs(cycle, "rejection_performance"))

    def test_general_pause_blocks_fen_but_not_realization_closure(self):
        service, _policy, lot, cycle = self._visit()
        control = self.env["mc.rov.automation.control"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        if control:
            control.enabled = False
        else:
            self.env["mc.rov.automation.control"].create(
                {"company_id": self.env.company.id, "enabled": False}
            )
        self._accepted_pair(service, lot)
        self.assertFalse(self._pending(cycle, "performance"))
        self.assertFalse(self._pending(cycle, "field"))
        self.assertFalse(self._stage_runs(cycle, "fen"))

    def test_emitted_pdf_and_closed_cycle_survive_later_correction(self):
        service, _policy, lot, cycle = self._visit()
        rnd, trn = self._accepted_pair(service, lot)
        fen = self._fen(lot, rnd, trn)
        fen.action_emitir()
        original = fen.pdf_attachment_id.raw
        rnd.action_volver_a_borrador()
        service._reconcile(lot)
        self.assertEqual(cycle.state, "done")
        self.assertEqual(fen.pdf_attachment_id.raw, original)
        self.assertFalse(self._pending(cycle, "fen"))

    def test_stock_only_actor_can_confirm_and_open_resolution(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        user = new_test_user(
            self.env, login="qa_acceptance_test_operator", groups="stock.group_stock_user"
        )
        self.assertFalse(user.has_group("mrp.group_mrp_user"))
        rnd.with_user(user).action_confirmar()
        self.assertTrue(self._pending(cycle, "rejection_performance"))
        self.assertEqual(
            self._pending(cycle, "rejection_performance").activity_id.user_id,
            self._pending(cycle, "field").activity_id.user_id,
        )

    def test_direct_confirmation_write_also_reconciles(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot)
        rnd.write({"estado": "confirmado"})
        self.assertFalse(self._pending(cycle, "performance"))

    def test_failure_during_new_stage_rolls_back_confirmation(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._selected(service, lot, rejected=True)
        with self.assertRaises(RuntimeError), self.cr.savepoint():
            with patch.object(
                type(service), "_start_stage", side_effect=RuntimeError("QA rollback")
            ):
                rnd.action_confirmar()
        self.assertEqual(rnd.estado, "borrador")
        self.assertTrue(self._pending(cycle, "performance"))
        self.assertFalse(self._stage_runs(cycle, "rejection_performance"))
