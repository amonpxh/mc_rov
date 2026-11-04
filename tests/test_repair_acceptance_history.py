"""Native RED contracts for explicit final repair acceptance and durable evidence."""

import copy
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

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


@tagged("post_install", "-at_install", "repair_acceptance_history")
class TestRepairAcceptanceBoundaries(RevisionCommon):
    """Exercise source authorization and atomic evidence using transactional QA users."""

    _feature = TestRepairAcceptanceHistory._feature
    _native_revision = TestRepairAcceptanceHistory._native_revision
    _final = TestRepairAcceptanceHistory._final
    _history = TestRepairAcceptanceHistory._history

    def _operator(self, team=True):
        groups = "base.group_user,stock.group_stock_user"
        if team:
            groups += ",mc_rov.group_work_assignment_team"
        return new_test_user(self.env, login="qa_repair_acceptance_boundary", groups=groups)

    def _deny_source(self, model, record):
        return self.env["ir.rule"].create(
            {
                "name": "QA final acceptance source boundary",
                "model_id": self.env["ir.model"]._get_id(model),
                "domain_force": f"[('id', '!=', {record.id})]",
            }
        )

    def test_team_reader_can_read_authorized_history(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        reader = revision.with_user(self._operator())
        self.assertEqual(
            reader._get_repair_acceptance_attempts(reader.repair_id).ids,
            self._history(revision).ids,
        )

    def test_internal_reader_without_team_is_denied(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        reader = revision.with_user(self._operator(False))
        with self.assertRaises(AccessError):
            reader._get_repair_acceptance_attempts(reader.repair_id)

    def test_portal_cannot_start_or_read_history(self):
        revision = self._final()
        user = new_test_user(
            self.env, login="qa_repair_acceptance_portal", groups="base.group_portal"
        )
        reader = revision.with_user(user)
        with self.assertRaises(AccessError):
            reader.action_start_final_acceptance()
        with self.assertRaises(AccessError):
            reader._get_repair_acceptance_attempts(revision.repair_id)
        self.assertFalse(self._history(revision))

    def test_private_history_has_no_direct_read_acl(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        attempt = self._history(revision).with_user(self._operator())
        with self.assertRaises(AccessError):
            attempt.read(["verdict_snapshot"])

    def test_restricted_revision_cannot_read_history(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        user = self._operator()
        self._deny_source("mc.rov.revision", revision)
        with self.assertRaises(AccessError):
            revision.with_user(user)._get_repair_acceptance_attempts(revision.repair_id)

    def test_restricted_repair_cannot_read_history(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        user = self._operator()
        self._deny_source("repair.order", revision.repair_id)
        with self.assertRaises(AccessError):
            revision.with_user(user)._get_repair_acceptance_attempts(revision.repair_id)

    def test_restricted_lot_cannot_start_attempt(self):
        revision = self._final()
        user = self._operator()
        self._deny_source("stock.lot", revision.lot_id)
        with self.assertRaises(AccessError):
            revision.with_user(user).action_start_final_acceptance()
        self.assertFalse(self._history(revision))

    def test_history_from_another_repair_is_denied(self):
        revision = self._final()
        other = self._native_revision()
        reader = revision.with_user(self._operator())
        with self.assertRaises(AccessError):
            reader._get_repair_acceptance_attempts(other.repair_id)

    def test_selected_company_cannot_expose_foreign_history(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        other = self.env["res.company"].create({"name": "QA acceptance alternate company"})
        user = self._operator()
        user.write({"company_ids": [Command.link(other.id)]})
        reader = revision.with_user(user).with_context(allowed_company_ids=[other.id])
        with self.assertRaises(AccessError):
            reader._get_repair_acceptance_attempts(revision.repair_id)

    def test_pending_revision_cannot_replace_lot(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        other = self.env["stock.lot"].create(
            {"name": "QA-ACCEPTANCE-OTHER", "product_id": self.product.id}
        )
        with self.assertRaises(UserError):
            revision.write({"lot_id": other.id})
        self.assertEqual(revision.lot_id, self.lot)

    def test_pending_revision_cannot_change_purpose(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        with self.assertRaises(UserError):
            revision.write({"mc_acceptance_purpose": "diagnostic"})

    def test_parent_cannot_replace_series_after_start(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        with self.assertRaises(UserError):
            revision.repair_id.write({"lot_id": False})
        self.assertEqual(revision.repair_id.lot_id, self.lot)

    def test_pending_history_cannot_be_written_by_sudo(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        with self.assertRaises(UserError):
            self._history(revision).write({"ordinal": 2})

    def test_serializable_context_cannot_authorize_history_write(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        attempt = self._history(revision).with_context(mc_repair_acceptance_capability=True)
        with self.assertRaises(UserError):
            attempt.write({"state": "confirmed"})

    def test_history_cannot_be_copied_even_by_sudo(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        with self.assertRaises(UserError):
            self._history(revision).copy({"ordinal": 2})

    def test_confirmation_without_explicit_start_is_rejected(self):
        revision = self._final()
        with self.assertRaises(UserError):
            revision.action_confirmar()
        self.assertEqual(revision.estado, "borrador")
        self.assertFalse(self._history(revision))

    def test_failed_native_confirmation_keeps_pending_history(self):
        revision = self._final(False)
        revision.action_start_final_acceptance()
        attempt = self._history(revision)
        with self.assertRaises(UserError), self.env.cr.savepoint():
            revision.action_confirmar()
        self.assertEqual(revision.estado, "borrador")
        self.assertEqual(attempt.state, "pending")
        self.assertFalse(attempt.closed_at)

    def test_sealing_failure_rolls_back_native_confirmation(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        with self.assertRaises(RuntimeError), self.env.cr.savepoint():
            with patch.object(
                type(revision),
                "_seal_acceptance_attempt",
                side_effect=RuntimeError("QA transactional capture failure"),
            ):
                revision.action_confirmar()
        self.assertEqual(revision.estado, "borrador")
        self.assertEqual(self._history(revision).state, "pending")
        self.assertFalse(self._history(revision).closed_at)

    def test_outer_rollback_removes_new_attempt(self):
        revision = self._final()
        with self.assertRaises(RuntimeError), self.env.cr.savepoint():
            revision.action_start_final_acceptance()
            raise RuntimeError("QA outer transaction rollback")
        self.assertFalse(self._history(revision))
        revision.action_start_final_acceptance()
        self.assertEqual(self._history(revision).ordinal, 1)

    def test_informational_flags_and_unknown_are_preserved(self):
        revision = self._final()
        revision.write({"mc_correction_required": "unknown", "mc_retest_required": "yes"})
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        attempt = self._history(revision)
        self.assertEqual(attempt.correction_snapshot, "unknown")
        self.assertEqual(attempt.retest_snapshot, "yes")
