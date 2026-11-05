"""Independent review regressions: defaults, frozen scope and mutable catalog metadata."""

import copy

from odoo.exceptions import UserError
from odoo.tests import tagged

from . import test_repair_acceptance_history as history
from .test_mc_rov_revision import RevisionCommon


class RepairAcceptanceReviewAssertion(AssertionError):
    """Convert the known catalog dead end into a precise review assertion."""


@tagged("post_install", "-at_install", "repair_acceptance_review")
class TestRepairAcceptanceReview(RevisionCommon):
    """Protect final evidence without making ordinary catalog edits block the visit."""

    _feature = history.TestRepairAcceptanceHistory._feature
    _native_revision = history.TestRepairAcceptanceHistory._native_revision
    _final = history.TestRepairAcceptanceHistory._final
    _history = history.TestRepairAcceptanceHistory._history

    def _finish_after_metadata_change(self, revision, abort=False):
        try:
            if abort:
                revision.action_abort_final_acceptance("Fallo real de revisión QA")
            else:
                revision.action_confirmar()
        except UserError as error:
            if "Los requisitos cambiaron durante el intento" not in str(error):
                raise
            raise RepairAcceptanceReviewAssertion(
                "Catalog metadata must not strand a captured final attempt"
            ) from error

    def _component_fixture(self):
        components = self.env["mc.rov.componente"].create(
            [
                {"name": "QA scope component A", "es_inspeccionable": True},
                {"name": "QA scope component B", "es_inspeccionable": True},
            ]
        )
        check = self._chequeo_catalogo(aplica_reparacion=True, por_componente=True)
        revision = self._final()
        line = revision.chequeo_ids.filtered(
            lambda row: row.chequeo_id == check and row.componente_id == components[0]
        ).ensure_one()
        inspection = revision.inspeccion_ids.filtered(
            lambda row: row.componente_id == components[0]
        ).ensure_one()
        return revision, components, line, inspection

    def _create_values(self, revision):
        return {
            "lot_id": revision.lot_id.id,
            "repair_id": revision.repair_id.id,
            "responsable_id": self.empleado.id,
            "tipo": "reparacion",
            "motivo": "otro",
        }

    def test_catalog_metadata_change_does_not_block_confirmation(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        attempt = self._history(revision)
        original = copy.deepcopy(attempt.requirements_snapshot["configuration"])
        digest = attempt.configuration_digest
        revision.chequeo_ids[0].chequeo_id.write(
            {"name": "QA renamed catalog check", "sequence": 902}
        )
        self._finish_after_metadata_change(revision)
        self.assertEqual(attempt.state, "confirmed")
        self.assertEqual(attempt.requirements_snapshot["configuration"], original)
        self.assertEqual(attempt.configuration_digest, digest)

    def test_catalog_metadata_change_does_not_block_real_failure(self):
        revision = self._final(False)
        revision.action_start_final_acceptance()
        revision.chequeo_ids[0].resultado = "no_ok"
        revision.chequeo_ids[0].chequeo_id.sequence += 1
        self._finish_after_metadata_change(revision, abort=True)
        self.assertEqual(self._history(revision).state, "aborted")
        self.assertEqual(self._history(revision).verdict_snapshot, "rechazado")
        self.assertEqual(revision.estado, "borrador")

    def test_pending_attempt_rejects_checklist_refresh(self):
        revision = self._final()
        revision.action_start_final_acceptance()
        extra = self._chequeo_catalogo(aplica_reparacion=True)
        with self.assertRaises(UserError), self.env.cr.savepoint():
            revision.action_actualizar_checklist()
        self.assertNotIn(extra, revision.chequeo_ids.chequeo_id)

    def test_pending_check_cannot_replace_component(self):
        revision, components, line, _inspection = self._component_fixture()
        revision.action_start_final_acceptance()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            line.write({"componente_id": components[1].id})
        self.assertEqual(line.componente_id, components[0])

    def test_pending_inspection_cannot_replace_component(self):
        revision, components, _line, inspection = self._component_fixture()
        revision.action_start_final_acceptance()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            inspection.write({"componente_id": components[1].id})
        self.assertEqual(inspection.componente_id, components[0])

    def test_check_snapshot_keeps_original_component_after_reopen(self):
        revision, components, line, _inspection = self._component_fixture()
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        snapshot = copy.deepcopy(self._history(revision).requirements_snapshot)
        revision.action_volver_a_borrador()
        line.write({"componente_id": components[1].id})
        captured = next(
            row for row in snapshot["configuration"]["checks"] if row["line_id"] == line.id
        )
        self.assertEqual(captured.get("component_id"), components[0].id)
        evidence = next(row for row in snapshot["evidence"]["checks"] if row["id"] == line.id)
        self.assertEqual(evidence.get("componente_id"), components[0].id)
        self.assertEqual(self._history(revision).requirements_snapshot, snapshot)

    def test_inspection_snapshot_keeps_original_component_after_reopen(self):
        revision, components, _line, inspection = self._component_fixture()
        revision.action_start_final_acceptance()
        revision.action_confirmar()
        snapshot = copy.deepcopy(self._history(revision).requirements_snapshot)
        revision.action_volver_a_borrador()
        inspection.write({"componente_id": components[1].id})
        captured = [
            row
            for row in snapshot["configuration"].get("inspections", [])
            if row["line_id"] == inspection.id
        ]
        self.assertEqual(len(captured), 1, "Inspection scope must be frozen")
        self.assertEqual(captured[0].get("component_id"), components[0].id)
        evidence = next(
            row for row in snapshot["evidence"]["inspections"] if row["id"] == inspection.id
        )
        self.assertEqual(evidence.get("componente_id"), components[0].id)
        self.assertEqual(self._history(revision).requirements_snapshot, snapshot)

    def test_context_default_purpose_cannot_create_confirmed_final(self):
        revision = self._native_revision(False)
        values = {**self._create_values(revision), "estado": "confirmado"}
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self.env["mc.rov.revision"].with_context(default_mc_acceptance_purpose="final").create(
                values
            )

    def test_context_default_state_cannot_create_confirmed_final(self):
        revision = self._native_revision(False)
        values = {**self._create_values(revision), "mc_acceptance_purpose": "final"}
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self.env["mc.rov.revision"].with_context(default_estado="confirmado").create(values)

    def test_native_checklist_refresh_before_attempt_remains_available(self):
        revision = self._final()
        extra = self._chequeo_catalogo(aplica_reparacion=True)
        revision.action_actualizar_checklist()
        self.assertIn(extra, revision.chequeo_ids.chequeo_id)
        self.assertFalse(self._history(revision))

    def test_native_unclassified_creation_remains_draft(self):
        revision = self._native_revision(False)
        created = self.env["mc.rov.revision"].create(self._create_values(revision))
        self.assertEqual(created.mc_acceptance_purpose, "unset")
        self.assertEqual(created.estado, "borrador")
        self.assertFalse(self._history(created))
