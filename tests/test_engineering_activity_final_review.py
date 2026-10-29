from datetime import timedelta
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .engineering_activity_common import EngineeringActivityCommon
from .test_engineering_activity_events import _advance_native


@tagged("post_install", "-at_install")
class TestEngineeringActivityFinalReview(EngineeringActivityCommon):
    """Reproduce límites de reprogramación y acceso hallados por la revisión independiente."""

    def _policy(self, **values):
        controls = self.env["mc.rov.automation.control"]
        control = controls.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = True
        else:
            controls.create({"company_id": self.env.company.id, "enabled": True})
        return super()._policy(**values)

    def _visit(self):
        self._policy()
        eco = self._eco()
        run = self.env["mc.rov.engineering.activity.run"].search([("eco_id", "=", eco.id)])
        self.assertEqual(len(run), 1)
        return eco, run

    def _wizard(self, activity, deadline):
        return (
            self.env["mc.rov.activity.assignment.wizard"]
            .with_user(self.coordinator)
            .create(
                {
                    "activity_ids": [Command.set(activity.ids)],
                    "apply_deadline": True,
                    "date_deadline": deadline,
                    "reason": "QA reprogramación autorizada de revisión",
                }
            )
        )

    def test_assignee_cannot_extend_captured_deadline_directly(self):
        _eco, run = self._visit()
        original = run.original_deadline
        with self.assertRaises(AccessError), self.cr.savepoint():
            run.activity_id.with_user(self.prepare_user).write(
                {
                    "date_deadline": original + timedelta(days=7),
                }
            )
        self.assertEqual(run.current_deadline, original)
        self.assertEqual(run.cycle_id.current_deadline, original)

    def test_coordinator_cannot_reprogram_without_validated_reason(self):
        _eco, run = self._visit()
        with self.assertRaisesRegex(UserError, "motivo"), self.cr.savepoint():
            run.activity_id.with_user(self.coordinator).write(
                {
                    "date_deadline": run.original_deadline + timedelta(days=3),
                }
            )

    def test_rpc_context_cannot_forge_deadline_authorization(self):
        _eco, run = self._visit()
        changed = run.original_deadline + timedelta(days=3)
        forged = [
            "rpc-token",
            self.coordinator.id,
            run.activity_id.ids,
            changed.isoformat(),
            "QA motivo",
        ]
        with self.assertRaisesRegex(UserError, "motivo"), self.cr.savepoint():
            run.activity_id.with_user(self.coordinator).with_context(
                _mc_activity_deadline_authorization=forged,
            ).write({"date_deadline": changed})

    def test_recipient_without_product_read_gets_no_own_pending(self):
        self._policy()
        self.env["ir.rule"].create(
            {
                "name": "QA producto oculto solo al destinatario de ingeniería",
                "model_id": self.env["ir.model"]._get_id("product.template"),
                "domain_force": (
                    f"[('id', '!=', {self.product.product_tmpl_id.id})] "
                    f"if user.id == {self.prepare_user.id} else []"
                ),
            }
        )
        self.env.invalidate_all()
        template = self.product.product_tmpl_id
        self.assertTrue(template.with_user(self.coordinator).has_access("read"))
        self.assertFalse(template.with_user(self.prepare_user).has_access("read"))
        eco = (
            self.env["mrp.eco"]
            .with_user(self.coordinator)
            .create(
                {
                    "name": "QA destinatario sin acceso al producto",
                    "type": "product",
                    "type_id": self.eco_type.id,
                    "stage_id": self.prepare_stage.id,
                    "product_tmpl_id": template.id,
                    "company_id": self.env.company.id,
                }
            )
        )
        self.assertTrue(eco.with_user(self.prepare_user).has_access("read"))
        self.assertTrue(eco.with_user(self.prepare_user).has_access("write"))
        self.assertFalse(
            self.env["mc.rov.engineering.activity.run"].search_count(
                [
                    ("eco_id", "=", eco.id),
                ]
            )
        )

    def test_archive_with_authorized_reprogram_keeps_final_deadline(self):
        eco, run = self._visit()
        activity = run.activity_id
        changed = run.original_deadline - timedelta(days=2)
        model = type(self.env["mail.activity"])
        native_write = model.write

        def combined_write(records, values):
            # El asistente sigue validando permiso y motivo; se prueba la escritura
            # compuesta en el punto donde llega al ciclo, sin simular sus efectos.
            if activity.id in records.ids and "date_deadline" in values:
                values = {**values, "active": False}
            return native_write(records, values)

        with patch.object(model, "write", combined_write):
            self._wizard(activity, changed).action_apply()
        self.assertEqual(run.outcome, "cancelled")
        self.assertFalse(activity.active)
        self.assertEqual(activity.date_deadline, changed)
        self.assertEqual(run.current_deadline, changed)
        self.assertEqual(run.cycle_id.current_deadline, changed)
        _advance_native(self, eco)
        pending = self.env["mc.rov.engineering.activity.run"].search(
            [
                ("eco_id", "=", eco.id),
                ("outcome", "=", "pending"),
            ]
        )
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending.stage, "apply")
        self.assertEqual(pending.activity_id.date_deadline, changed)
