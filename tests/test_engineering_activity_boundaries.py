from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .engineering_activity_common import EngineeringActivityCommon
from .test_engineering_activity_events import _advance_native


@tagged("post_install", "-at_install")
# Las fronteras de origen, decisiones y permisos son contratos independientes.
# pylint: disable=too-many-public-methods
class TestEngineeringActivityBoundaries(EngineeringActivityCommon):
    """El pendiente se coordina sin aprobar el cambio ni exponer su auditoría privada."""

    def _policy(self, **values):
        controls = self.env["mc.rov.automation.control"]
        control = controls.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = True
        else:
            controls.create({"company_id": self.env.company.id, "enabled": True})
        return super()._policy(**values)

    def _runs(self, eco):
        return (
            self.env["mc.rov.engineering.activity.run"]
            .sudo()
            .search([("eco_id", "=", eco.id)], order="id")
        )

    def _visit(self, **values):
        policy = self._policy()
        eco = self._eco(**values)
        run = self._runs(eco)
        self.assertEqual(len(run), 1)
        return policy, eco, run

    def _source_service(self):
        service = self.env["mc.rov.engineering.activity.automation"]
        self.assertTrue(
            callable(getattr(service, "_runs", None)), "Missing engineering source service"
        )
        return service

    def _hide(self, model, record):
        self.env["ir.rule"].create(
            {
                "name": "QA Ingeniería origen restringido",
                "model_id": self.env["ir.model"]._get_id(model),
                "domain_force": repr([("id", "!=", record.id)]),
            }
        )
        self.env.invalidate_all()

    def _human_deletion_error(self, record):
        with self.assertRaisesRegex(UserError, "historial"), self.cr.savepoint():
            try:
                record.unlink()
            except IntegrityError:
                self.fail("Falta explicar la conservación del historial de Ingeniería")

    def _bom_visit(self):
        bom = self.env["mrp.bom"].create(
            {"product_tmpl_id": self.product.product_tmpl_id.id, "product_qty": 1.0}
        )
        return self._visit(type="bom", bom_id=bom.id)

    def _wizard(self, activity, **values):
        return (
            self.env["mc.rov.activity.assignment.wizard"]
            .with_user(self.coordinator)
            .create({"activity_ids": [Command.set(activity.ids)], **values})
        )

    def test_manual_done_records_actor_without_approving_or_applying(self):
        policy, eco, run = self._visit()
        approval = eco.approval_ids.read(["status", "user_id"])
        run.activity_id.with_user(policy.prepare_user_id).action_feedback(
            feedback="QA hecho manual"
        )
        self.assertEqual(run.outcome, "manual_done")
        self.assertEqual(run.finished_by_id, policy.prepare_user_id)
        self.assertTrue(run.finished_at)
        self.assertIn("QA hecho manual", run.finish_reason)
        self.assertEqual(eco.state, "confirmed")
        self.assertEqual(eco.approval_ids.read(["status", "user_id"]), approval)

    def test_manual_cancel_records_reason_without_changing_eco(self):
        _policy, eco, run = self._visit()
        run.activity_id.action_cancel()
        self.assertEqual(run.outcome, "cancelled")
        self.assertTrue(run.finish_reason)
        self.assertEqual(run.finished_by_id, self.env.user)
        self.assertEqual(eco.state, "confirmed")

    def test_manual_archive_records_cancellation(self):
        _policy, eco, run = self._visit()
        run.activity_id.write({"active": False})
        self.assertEqual(run.outcome, "cancelled")
        self.assertTrue(run.finish_reason)
        self.assertTrue(eco.active)

    def test_unlink_preserves_current_deadline_and_reason(self):
        _policy, _eco, run = self._visit()
        changed = run.original_deadline - timedelta(days=3)
        self._wizard(
            run.activity_id,
            apply_deadline=True,
            date_deadline=changed,
            reason="QA reprogramación antes de retirar la actividad",
        ).action_apply()
        run.activity_id.unlink()
        self.assertEqual(run.outcome, "cancelled")
        self.assertEqual(run.current_deadline, changed)
        self.assertFalse(run.activity_id)
        self.assertTrue(run.finish_reason)

    def test_reprogram_updates_run_and_cycle_without_replacing_original(self):
        _policy, _eco, run = self._visit()
        original = run.original_deadline
        changed = original - timedelta(days=3)
        self._wizard(
            run.activity_id,
            apply_deadline=True,
            date_deadline=changed,
            reason="QA adelantar entrega",
        ).action_apply()
        self.assertEqual(run.current_deadline, changed)
        self.assertEqual(run.cycle_id.current_deadline, changed)
        self.assertEqual(run.original_deadline, original)
        self.assertEqual(run.cycle_id.original_deadline, original)

    def test_removed_reprogrammed_activity_keeps_deadline_for_apply(self):
        _policy, eco, run = self._visit()
        changed = run.original_deadline - timedelta(days=3)
        self._wizard(
            run.activity_id,
            apply_deadline=True,
            date_deadline=changed,
            reason="QA conservar la reprogramación al cambiar de etapa",
        ).action_apply()
        run.activity_id.unlink()
        _advance_native(self, eco)
        apply_run = self._runs(eco).filtered(lambda row: row.stage == "apply")
        self.assertEqual(len(apply_run), 1)
        self.assertEqual(apply_run.activity_id.date_deadline, changed)

    def test_ordinary_edit_does_not_recreate_manually_finished_task(self):
        _policy, eco, run = self._visit()
        run.activity_id.action_feedback(feedback="QA decisión manual")
        eco.write({"name": "QA cambio editado"})
        self.assertEqual(self._runs(eco), run)
        self.assertFalse(run.activity_id.filtered("active"))
        self.assertEqual(eco.state, "confirmed")

    def test_future_applicable_event_after_manual_done_creates_only_apply(self):
        _policy, eco, first = self._visit()
        first.activity_id.action_feedback(feedback="QA terminado manualmente")
        _advance_native(self, eco)
        pending = self._runs(eco).filtered(lambda row: row.outcome == "pending")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending.stage, "apply")
        self.assertEqual(first.outcome, "manual_done")

    def test_homonymous_unlinked_activity_is_not_closed(self):
        policy, eco, run = self._visit()
        manual = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("mrp.eco"),
                "res_id": eco.id,
                "activity_type_id": run.activity_id.activity_type_id.id,
                "summary": run.activity_id.summary,
                "user_id": policy.prepare_user_id.id,
                "date_deadline": run.original_deadline,
            }
        )
        _advance_native(self, eco)
        eco.action_apply()
        self.assertTrue(manual.exists().active)
        self.assertEqual(run.outcome, "business_done")

    def test_pending_source_cannot_replace_product(self):
        _policy, eco, _run = self._visit()
        other = self.env["product.template"].create(
            {"name": "QA otro modelo de ingeniería", "categ_id": self.rov_category.id}
        )
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            eco.write({"product_tmpl_id": other.id})

    def test_pending_source_cannot_change_company(self):
        _policy, eco, _run = self._visit()
        other = self._other_company()
        with self.assertRaises(UserError), self.cr.savepoint():
            eco.write({"company_id": other.id})
        self.assertEqual(eco.company_id, self.env.company)

    def test_pending_source_cannot_replace_bom(self):
        _policy, eco, _run = self._bom_visit()
        other = eco.bom_id.copy()
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            eco.write({"bom_id": other.id})

    def test_pending_source_cannot_change_kind(self):
        _policy, eco, _run = self._bom_visit()
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            eco.write({"type": "product", "bom_id": False})

    def test_pending_source_cannot_replace_eco_type(self):
        _policy, eco, _run = self._visit()
        other = self.env["mrp.eco.type"].create({"name": "QA otro circuito"})
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            eco.write({"type_id": other.id})

    def test_same_source_values_are_allowed(self):
        _policy, eco, run = self._visit()
        eco.write(
            {
                "product_tmpl_id": eco.product_tmpl_id.id,
                "company_id": eco.company_id.id,
                "type_id": eco.type_id.id,
                "type": eco.type,
            }
        )
        self.assertEqual(self._runs(eco), run)
        self.assertEqual(run.outcome, "pending")

    def test_new_bom_content_can_be_edited_normally(self):
        _policy, eco, run = self._bom_visit()
        eco.action_new_revision()
        eco.new_bom_id.write({"product_qty": 2.0})
        self.assertEqual(eco.new_bom_id.product_qty, 2.0)
        self.assertEqual(run.outcome, "pending")

    def test_source_deletion_explains_history(self):
        _policy, eco, _run = self._visit()
        self._human_deletion_error(eco)

    def test_run_deletion_explains_history(self):
        _policy, _eco, run = self._visit()
        self._human_deletion_error(run)

    def test_cycle_deletion_explains_history(self):
        _policy, _eco, run = self._visit()
        self._human_deletion_error(run.cycle_id)

    def test_private_history_is_not_readable_or_exportable(self):
        _policy, _eco, run = self._visit()
        # Superar la puerta general de exportación permite probar la ACL del historial.
        self.prepare_user.group_ids = [Command.link(self.env.ref("base.group_allow_export").id)]
        with self.assertRaises(AccessError):
            run.with_user(self.prepare_user).read(["finish_reason"])
        with self.assertRaises(AccessError):
            run.with_user(self.prepare_user).export_data(["original_deadline"])

    def test_portal_cannot_query_source_history(self):
        _policy, eco, _run = self._visit()
        portal = new_test_user(self.env, login="qa_engineering_portal", groups="base.group_portal")
        service = self._source_service().with_user(portal)
        with self.assertRaises(AccessError), self.cr.savepoint():
            service._runs(eco, access="read")

    def test_restricted_source_cannot_query_history(self):
        _policy, eco, _run = self._visit()
        service = self._source_service().with_user(self.prepare_user)
        self._hide("mrp.eco", eco)
        with self.assertRaises(AccessError), self.cr.savepoint():
            service._runs(eco, access="read")

    def test_restricted_source_prevents_manual_feedback(self):
        policy, eco, run = self._visit()
        activity = run.activity_id
        self._hide("mrp.eco", eco)
        with self.assertRaises(AccessError), self.cr.savepoint():
            activity.with_user(policy.prepare_user_id).action_feedback(
                feedback="QA acceso perdido"
            )
        self.assertEqual(run.outcome, "pending")

    def test_foreign_recipient_is_skipped_without_expanding_membership(self):
        company = self._other_company()
        user = new_test_user(
            self.env,
            login="qa_engineering_foreign",
            groups="mrp_plm.group_plm_user",
            company_id=company.id,
            company_ids=[Command.set(company.ids)],
        )
        self._policy(prepare_user_id=user.id)
        eco = self._eco()
        self.assertFalse(self._runs(eco))
        self.assertEqual(user.company_ids, company)

    def test_archived_recipient_is_skipped(self):
        # El aprobador nativo sigue activo: solo el destinatario del seguimiento falla.
        self.apply_user.active = False
        self._policy(prepare_user_id=self.apply_user.id)
        self.assertFalse(self._runs(self._eco()))

    def test_foreign_employee_is_skipped(self):
        company = self._other_company()
        employee = self.env["hr.employee"].create(
            {"name": "QA empleado ajeno", "company_id": company.id}
        )
        policy = self._policy()
        # También se admite el rechazo nativo check_company antes de configurar.
        try:
            with self.cr.savepoint():
                policy.prepare_employee_id = employee.id
        except UserError:
            return
        self.assertFalse(self._runs(self._eco()))

    def test_archived_employee_is_skipped(self):
        employee = self.env["hr.employee"].create(
            {"name": "QA empleado archivado", "company_id": self.env.company.id, "active": False}
        )
        self._policy(prepare_employee_id=employee.id)
        self.assertFalse(self._runs(self._eco()))

    def test_multicompany_actor_does_not_expand_recipient_context(self):
        self._policy()
        company = self._other_company()
        self.coordinator.company_ids = [Command.link(company.id)]
        eco = (
            self.env["mrp.eco"]
            .with_user(self.coordinator)
            .with_context(allowed_company_ids=self.coordinator.company_ids.ids)
            .create(
                {
                    "name": "QA actor multiempresa",
                    "type": "product",
                    "type_id": self.eco_type.id,
                    "product_tmpl_id": self.product.product_tmpl_id.id,
                    "stage_id": self.prepare_stage.id,
                    "company_id": self.env.company.id,
                }
            )
        )
        self.assertEqual(len(self._runs(eco)), 1)
        self.assertEqual(self.prepare_user.company_ids, self.env.company)

    def test_temporary_without_origin_has_no_persistent_effects(self):
        _policy, eco, run = self._visit()
        temporary = eco.new({"active": True, "state": "confirmed"})
        self.env["mc.rov.engineering.activity.lifecycle"]._sync(
            temporary, {temporary.id: None}, fields.Datetime.now()
        )
        self.assertEqual(self._runs(eco), run)
        self.assertEqual(run.outcome, "pending")

    def test_temporary_activity_archive_does_not_cancel_real_run(self):
        _policy, _eco, run = self._visit()
        activity = run.activity_id
        activity.new({}, origin=activity).write({"active": False})
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(activity.active)

    def test_followed_activity_cannot_change_source(self):
        _policy, _eco, run = self._visit()
        other = self._eco()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            run.activity_id.write({"res_id": other.id})

    def test_followed_activity_cannot_change_type(self):
        _policy, _eco, run = self._visit()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            run.activity_id.write(
                {"activity_type_id": self.env.ref("mail.mail_activity_data_todo").id}
            )

    def test_reprogram_requires_reason(self):
        _policy, _eco, run = self._visit()
        with self.assertRaisesRegex(UserError, "motivo"), self.cr.savepoint():
            self._wizard(
                run.activity_id,
                apply_deadline=True,
                date_deadline=run.original_deadline - timedelta(days=2),
            ).action_apply()

    def test_coordinator_can_reassign_without_changing_source_or_original_deadline(self):
        _policy, eco, run = self._visit()
        original = run.original_deadline
        self._wizard(run.activity_id, apply_user=True, user_id=self.apply_user.id).action_apply()
        self.assertEqual(run.activity_id.user_id, self.apply_user)
        self.assertEqual(run.activity_id.res_id, eco.id)
        self.assertEqual(run.original_deadline, original)

    def test_paused_tracking_still_records_manual_decision(self):
        policy, eco, run = self._visit()
        policy.enabled = False
        run.activity_id.action_feedback(feedback="QA cierre bajo pausa")
        self.assertEqual(run.outcome, "manual_done")
        self.assertEqual(eco.state, "confirmed")
