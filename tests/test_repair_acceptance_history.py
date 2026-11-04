"""Native RED contracts for explicit final repair acceptance and durable evidence."""

import copy

from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_mc_rov_revision import RevisionCommon


class MissingRepairAcceptanceHistory(AssertionError):
    """Expected RED assertion, separated from native fixture errors."""


@tagged("post_install", "-at_install", "repair_acceptance_history")
class TestRepairAcceptanceHistory(RevisionCommon):
    """Final acceptance must survive editing without confirming incomplete documents."""

    def _feature(self):
        revision = self.env["mc.rov.revision"]
        if (
            "mc.rov.repair.acceptance.attempt" not in self.env.registry.models
            or not {"mc_acceptance_purpose", "mc_correction_required", "mc_retest_required"}
            <= set(revision._fields)
            or not all(
                callable(getattr(revision, name, None))
                for name in (
                    "action_start_final_acceptance",
                    "action_abort_final_acceptance",
                    "_get_repair_acceptance_attempts",
                )
            )
        ):
            raise MissingRepairAcceptanceHistory("Missing repair acceptance history")

    def _native_revision(self, complete=True):
        repair = self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "product_qty": 1,
                "product_uom": self.product.uom_id.id,
                "lot_id": self.lot.id,
            }
        )
        revision = self._revision(tipo="reparacion", repair_id=repair.id, motivo="otro")
        if complete:
            self._corrida_completa(revision)
            self._responder_todo(revision)
            self._responder_sellos(revision)
        return revision

    def _final(self, complete=True):
        self._feature()
        revision = self._native_revision(complete)
        revision.write(
            {
                "mc_acceptance_purpose": "final",
                "mc_correction_required": "no",
                "mc_retest_required": "no",
            }
        )
        return revision

    def _history(self, revision):
        return (
            self.env["mc.rov.repair.acceptance.attempt"]
            .sudo()
            .search([("repair_id", "=", revision.repair_id.id)], order="ordinal")
        )

    def test_native_complete_revision_can_confirm(self):
        revision = self._native_revision()
        revision.action_confirmar()
        self.assertEqual(revision.estado, "confirmado")

    def test_native_incomplete_revision_stays_draft(self):
        revision = self._native_revision(False)
        with self.assertRaises(UserError):
            revision.action_confirmar()
        self.assertEqual(revision.estado, "borrador")

    def test_native_checklist_uses_repair_applicability(self):
        revision = self._native_revision(False)
        expected = self.env["mc.rov.chequeo"].search([("aplica_reparacion", "=", True)])
        self.assertTrue(expected)
        self.assertEqual(set(revision.chequeo_ids.chequeo_id.ids), set(expected.ids))

    def test_capture_contract_is_explicit(self):
        self._feature()
        field = self.env["mc.rov.revision"]._fields["mc_acceptance_purpose"]
        self.assertEqual(field.type, "selection")

    def test_diagnostic_confirmation_has_no_final_attempt(self):
        self._feature()
        revision = self._native_revision()
        revision.write({"mc_acceptance_purpose": "diagnostic"})
        revision.action_confirmar()
        self.assertFalse(self._history(revision))

    def test_diagnostic_cannot_start_final_acceptance(self):
        self._feature()
        revision = self._native_revision()
        revision.write({"mc_acceptance_purpose": "diagnostic"})
        with self.assertRaises(UserError):
            revision.action_start_final_acceptance()

    def test_final_start_requires_repair_identity(self):
        self._feature()
        revision = self._revision(tipo="reparacion")
        with self.assertRaises(UserError):
            revision.write({"mc_acceptance_purpose": "final"})
            revision.action_start_final_acceptance()

    def test_start_is_idempotent(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        original = self._history(revision)
        revision.action_start_final_acceptance()
        self.assertEqual(self._history(revision), original)
        self.assertEqual(len(original), 1)
        self.assertEqual(original.ordinal, 1)

    def test_confirmation_captures_evidence_and_actor(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        attempt = self._history(revision)
        self.assertEqual(len(attempt), 1)
        self.assertEqual(attempt.verdict_snapshot, revision.resultado)
        self.assertEqual(attempt.actor_id, self.env.user)
        self.assertEqual(attempt.responsable_id, self.empleado)
        self.assertTrue(attempt.requirements_snapshot)
        self.assertTrue(attempt.configuration_digest)

    def test_duplicate_confirmation_does_not_create_attempt(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        original = self._history(revision)
        revision.action_confirmar()
        self.assertEqual(self._history(revision), original)

    def test_reopen_and_pass_preserve_first_failed_verdict(self):
        revision = self._final()
        self._responder_todo(revision, "no_ok")
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        first = self._history(revision)
        self.assertEqual(first.verdict_snapshot, "rechazado")
        revision.action_volver_a_borrador()
        self._responder_todo(revision)
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        history = self._history(revision)
        self.assertEqual(history.mapped("ordinal"), [1, 2])
        self.assertEqual(first.verdict_snapshot, "rechazado")

    def test_catalog_edit_does_not_rewrite_snapshot(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        attempt = self._history(revision)
        original = copy.deepcopy(attempt.requirements_snapshot)
        digest = attempt.configuration_digest
        check = revision.chequeo_ids[0].chequeo_id
        check.sequence += 1
        self.assertEqual(attempt.requirements_snapshot, original)
        self.assertEqual(attempt.configuration_digest, digest)

    def test_real_failure_can_abort_incomplete_attempt(self):
        revision = self._final(False)
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        revision.action_abort_final_acceptance("Fallo real: se detiene la comprobación")
        self.assertEqual(revision.estado, "borrador")
        self.assertEqual(self._history(revision).verdict_snapshot, "rechazado")

    def test_abort_requires_real_evidence(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        with self.assertRaises(UserError):
            revision.action_abort_final_acceptance("Solo una nota no acredita fallo")

    def test_raw_state_write_cannot_forge_final_confirmation(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        with self.assertRaises(UserError):
            revision.with_context(mc_acceptance_capture=True).write({"estado": "confirmado"})
        self.assertEqual(revision.estado, "borrador")

    def test_sealed_history_cannot_be_written_or_deleted(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        attempt = self._history(revision)
        with self.assertRaises(UserError):
            attempt.write({"verdict_snapshot": "rechazado"})
        with self.assertRaises(UserError):
            attempt.unlink()
