import json

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install")
# Contratos independientes de selección, navegación y protección del origen.
# pylint: disable=too-many-public-methods
class TestAcceptanceActivityEvidence(AcceptanceActivityCommon):
    """La evidencia se elige para un ciclo; no se adivina por fecha o responsable."""

    def _evidence_service(self):
        service = self.env["mc.rov.acceptance.activity.automation"]
        self.assertTrue(
            callable(getattr(service, "_select_evidence", None)),
            "Missing acceptance evidence selection service",
        )
        return service

    def _visit(self):
        service = self._evidence_service()
        policy = self._acceptance_policy()
        production = self._finished_production()
        lot = service._produced_lots(production)
        cycle = self.env["mc.rov.acceptance.activity.cycle"].search(
            [("production_id", "=", production.id), ("lot_id", "=", lot.id)]
        )
        self.assertEqual(len(cycle), 1)
        return service, policy, lot, cycle

    def _proof(self, lot, kind="rendimiento"):
        return self._revision(lot_id=lot.id, tipo=kind)

    def _history(self, cycle):
        return self.env["mc.rov.acceptance.evidence.history"].search([("cycle_id", "=", cycle.id)])

    def _hide(self, model, record, operation="read"):
        self.env["ir.rule"].create(
            {
                "name": "QA evidencia restringida",
                "model_id": self.env["ir.model"]._get_id(model),
                "domain_force": str([("id", "!=", record.id)]),
                "perm_read": operation == "read",
                "perm_write": operation == "write",
                "perm_create": False,
                "perm_unlink": False,
            }
        )

    def test_selected_proofs_belong_to_exact_cycle(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._proof(lot)
        trn = self._proof(lot, "terreno")
        service._select_evidence(lot, rnd=rnd, trn=trn)
        self.assertEqual(cycle.rnd_id, rnd)
        self.assertEqual(cycle.trn_id, trn)
        self.assertEqual(len(self._history(cycle)), 2)

    def test_unrelated_newer_proof_is_not_selected(self):
        service, _policy, lot, cycle = self._visit()
        chosen = self._proof(lot)
        service._select_evidence(lot, rnd=chosen)
        self._proof(lot)
        self.assertEqual(cycle.rnd_id, chosen)

    def test_omitting_one_type_preserves_previous_selection(self):
        service, _policy, lot, cycle = self._visit()
        trn = self._proof(lot, "terreno")
        service._select_evidence(lot, trn=trn)
        rnd = self._proof(lot)
        service._select_evidence(lot, rnd=rnd)
        self.assertEqual(cycle.trn_id, trn)
        self.assertEqual(cycle.rnd_id, rnd)

    def test_replacing_evidence_requires_reason(self):
        service, _policy, lot, cycle = self._visit()
        old = self._proof(lot)
        service._select_evidence(lot, rnd=old)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            service._select_evidence(lot, rnd=self._proof(lot))
        self.assertEqual(cycle.rnd_id, old)

    def test_replacement_keeps_previous_proof_and_actor(self):
        service, policy, lot, cycle = self._visit()
        old = self._proof(lot)
        replacement = self._proof(lot)
        service._select_evidence(lot, rnd=old)
        service.with_user(policy.user_id)._select_evidence(
            lot, rnd=replacement, reason="QA repetición elegida"
        )
        self.assertEqual(cycle.rnd_id, replacement)
        history = self._history(cycle).sorted("id")[-1]
        self.assertEqual(history.previous_revision_id, old)
        self.assertEqual(history.revision_id, replacement)
        self.assertEqual(history.actor_id, policy.user_id)
        self.assertEqual(history.reason, "QA repetición elegida")
        self.assertTrue(old.exists())

    def test_clearing_is_explicit_and_audited(self):
        service, _policy, lot, cycle = self._visit()
        old = self._proof(lot)
        service._select_evidence(lot, rnd=old)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            service._select_evidence(lot, rnd=False)
        service._select_evidence(lot, rnd=False, reason="QA corregir selección")
        self.assertFalse(cycle.rnd_id)
        self.assertEqual(self._history(cycle).sorted("id")[-1].previous_revision_id, old)

    def test_reselecting_same_record_is_idempotent(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._proof(lot)
        service._select_evidence(lot, rnd=rnd)
        before = self._history(cycle)
        service._select_evidence(lot, rnd=rnd)
        self.assertEqual(self._history(cycle), before)

    def test_other_equipment_cannot_supply_evidence(self):
        service, _policy, lot, cycle = self._visit()
        foreign = self._proof(self._serials())
        with self.assertRaises(ValidationError), self.cr.savepoint():
            service._select_evidence(lot, rnd=foreign)
        self.assertFalse(cycle.rnd_id)

    def test_wrong_test_type_is_rejected(self):
        service, _policy, lot, _cycle = self._visit()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            service._select_evidence(lot, rnd=self._proof(lot, "terreno"))

    def test_repair_test_cannot_accredit_new_equipment(self):
        service, _policy, lot, _cycle = self._visit()
        order = self.env["repair.order"].create(
            {"product_id": self.product.id, "lot_id": lot.id, "company_id": self.env.company.id}
        )
        revision = self._revision(lot_id=lot.id, tipo="rendimiento", repair_id=order.id)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            service._select_evidence(lot, rnd=revision)

    def test_hidden_proof_is_not_read_through_private_cycle(self):
        service, policy, lot, _cycle = self._visit()
        revision = self._proof(lot)
        self._hide("mc.rov.revision", revision)
        with self.assertRaises(AccessError):
            service.with_user(policy.user_id)._select_evidence(lot, rnd=revision)

    def test_hidden_lot_cannot_be_used_as_selection_origin(self):
        service, policy, lot, _cycle = self._visit()
        revision = self._proof(lot)
        self._hide("stock.lot", lot)
        with self.assertRaises(AccessError):
            service.with_user(policy.user_id)._select_evidence(lot, rnd=revision)

    def test_origin_without_write_access_cannot_be_changed(self):
        service, policy, lot, _cycle = self._visit()
        revision = self._proof(lot)
        self._hide("stock.lot", lot, operation="write")
        with self.assertRaises(AccessError):
            service.with_user(policy.user_id)._select_evidence(lot, rnd=revision)

    def test_cycle_without_pending_acceptance_is_not_inferred(self):
        service = self._evidence_service()
        self._acceptance_policy()
        lot = self._serials()
        with self.assertRaises(UserError):
            service._select_evidence(lot, rnd=self._proof(lot))

    def test_unreadable_private_history_is_not_exposed_to_workshop(self):
        service, policy, lot, cycle = self._visit()
        service._select_evidence(lot, rnd=self._proof(lot))
        with self.assertRaises(AccessError):
            self._history(cycle).with_user(policy.user_id).read(["revision_id"])
        with self.assertRaises(AccessError):
            cycle.with_user(policy.user_id).read(["lot_id"])

    def test_native_action_is_serializable_without_ledger_identity(self):
        _service, policy, lot, _cycle = self._visit()
        action = lot.with_user(policy.user_id).action_mc_acceptance_evidence()
        self.assertEqual(action["res_model"], "mc.rov.acceptance.evidence.wizard")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_lot_id"], lot.id)
        self.assertNotIn("default_cycle_id", action["context"])
        json.dumps(action)

    def test_default_get_shows_explicit_selection_not_latest(self):
        service, policy, lot, _cycle = self._visit()
        chosen = self._proof(lot)
        service._select_evidence(lot, rnd=chosen)
        self._proof(lot)
        model = self.env["mc.rov.acceptance.evidence.wizard"].with_user(policy.user_id)
        defaults = model.with_context(default_lot_id=lot.id).default_get(
            ["lot_id", "rnd_id", "trn_id", "summary"]
        )
        self.assertEqual(defaults["rnd_id"], chosen.id)
        self.assertFalse(defaults.get("trn_id"))

    def test_onchange_with_cold_cache_loads_only_authorized_evidence(self):
        service, policy, lot, _cycle = self._visit()
        chosen = self._proof(lot)
        service._select_evidence(lot, rnd=chosen)
        self.env.invalidate_all()
        model = self.env["mc.rov.acceptance.evidence.wizard"].with_user(policy.user_id)
        result = model.onchange(
            {"lot_id": lot.id},
            ["lot_id"],
            {
                "lot_id": {"fields": {"display_name": {}}},
                "rnd_id": {"fields": {"display_name": {}}},
                "trn_id": {},
                "summary": {},
            },
        )
        self.assertIn("rnd_id", result["value"])

    def test_wizard_applies_selection_without_technical_group(self):
        _service, policy, lot, cycle = self._visit()
        revision = self._proof(lot)
        wizard = (
            self.env["mc.rov.acceptance.evidence.wizard"]
            .with_user(policy.user_id)
            .create({"lot_id": lot.id, "rnd_id": revision.id})
        )
        wizard.action_apply()
        self.assertEqual(cycle.rnd_id, revision)

    def test_wizard_can_create_and_select_a_draft_without_inventing_results(self):
        _service, policy, lot, cycle = self._visit()
        wizard = (
            self.env["mc.rov.acceptance.evidence.wizard"]
            .with_user(policy.user_id)
            .create({"lot_id": lot.id})
        )
        action = wizard.action_new_performance()
        self.assertEqual(action["res_model"], "mc.rov.revision")
        revision = self.env["mc.rov.revision"].browse(action["res_id"])
        self.assertEqual(cycle.rnd_id, revision)
        self.assertEqual(revision.lot_id, lot)
        self.assertEqual(revision.tipo, "rendimiento")
        self.assertEqual(revision.estado, "borrador")
        self.assertFalse(revision.resultado)
        self.assertFalse(revision.responsable_id)

    def test_existing_manual_test_button_does_not_silently_bind(self):
        _service, _policy, lot, cycle = self._visit()
        action = lot.action_nueva_revision_rendimiento()
        self.assertEqual(action["res_model"], "mc.rov.revision")
        self.assertFalse(cycle.rnd_id)

    def test_both_selections_fail_atomically_if_one_is_wrong(self):
        service, _policy, lot, cycle = self._visit()
        rnd = self._proof(lot)
        wrong = self._proof(self._serials(), "terreno")
        with self.assertRaises(ValidationError), self.cr.savepoint():
            service._select_evidence(lot, rnd=rnd, trn=wrong)
        self.assertFalse(cycle.rnd_id)
        self.assertFalse(self._history(cycle))

    def test_context_cannot_override_cycle_or_publish_ledger(self):
        _service, policy, lot, cycle = self._visit()
        model = self.env["mc.rov.acceptance.evidence.wizard"].with_user(policy.user_id)
        defaults = model.with_context(
            default_lot_id=lot.id, default_cycle_id=cycle.id
        ).default_get(["lot_id", "rnd_id", "trn_id", "summary"])
        self.assertNotIn("cycle_id", defaults)
        self.assertNotIn("cycle_id", model._fields)
        self.assertEqual(defaults["lot_id"], lot.id)
