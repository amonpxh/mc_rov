from datetime import date
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .quality_activity_common import QualityActivityCommon


@tagged("post_install", "-at_install")
# Identidad, permisos, consulta y registros temporales son fronteras independientes.
# pylint: disable=too-many-public-methods
class TestQualityActivityBoundaries(QualityActivityCommon):
    """El Centro permite coordinar sin exponer o trasladar el historial privado."""

    _qa_coordinator = None

    def _visit(self, **values):
        policy = self._quality_policy()
        controls = self.env["mc.rov.automation.control"]
        control = controls.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = True
        alert = self._quality_alert(**values)
        run = self.env["mc.rov.quality.activity.run"].search([("alert_id", "=", alert.id)])
        self.assertEqual(len(run), 1)
        return policy, alert, run

    def _other_company(self):
        with patch.object(
            type(self.env["res.company"]), "_create_internal_project_task", create=True
        ):
            return self.env["res.company"].create({"name": "QA otra empresa fronteras Calidad"})

    def _coordinator(self):
        user = getattr(self, "_qa_coordinator", None)
        if not user:
            user = new_test_user(
                self.env,
                login="qa_quality_boundary_coordinator",
                groups="quality.group_quality_user,stock.group_stock_user,"
                "mc_rov.group_work_assignment_coordinate,mc_rov.group_work_assignment_team",
            )
            self._qa_coordinator = user
        return user

    def _hide(self, model, record, write_only=False):
        self.env["ir.rule"].create(
            {
                "name": "QA frontera Calidad restringida",
                "model_id": self.env["ir.model"]._get_id(model),
                "domain_force": repr([("id", "!=", record.id)]),
                "perm_read": not write_only,
                "perm_write": True,
                "perm_create": not write_only,
                "perm_unlink": not write_only,
            }
        )
        self.env.invalidate_all()

    def _assignment(self, user):
        return self.env["mc.rov.work.assignment"].with_user(user)

    def _ids(self, action, user):
        return self.env[action["res_model"]].with_user(user).search(action["domain"]).ids

    def _wizard(self, activity, **values):
        return (
            self.env["mc.rov.activity.assignment.wizard"]
            .with_user(self._coordinator())
            .create({"activity_ids": [Command.set(activity.ids)], **values})
        )

    def _human_deletion_error(self, record):
        with self.assertRaisesRegex(UserError, "historial"), self.cr.savepoint():
            try:
                record.unlink()
            except IntegrityError:
                self.fail("Falta explicar por qué se conserva el historial de Calidad")

    def test_pending_alert_cannot_replace_product(self):
        _policy, alert, _run = self._visit()
        other = self.env["product.product"].create(
            {"name": "QA otro equipo", "categ_id": self.product.categ_id.id}
        )
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            alert.write({"product_id": other.id, "product_tmpl_id": other.product_tmpl_id.id})
        self.assertEqual(alert.product_id, self.product)

    def test_pending_alert_cannot_replace_template(self):
        _policy, alert, _run = self._visit()
        other = self.env["product.template"].create(
            {"name": "QA otro modelo", "categ_id": self.product.categ_id.id}
        )
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            alert.write({"product_tmpl_id": other.id})

    def test_pending_alert_cannot_move_to_another_company(self):
        _policy, alert, _run = self._visit()
        company = self._other_company()
        team = self.env["quality.alert.team"].create(
            {"name": "QA equipo otra compañía", "company_id": company.id}
        )
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            alert.write({"company_id": company.id, "team_id": team.id})

    def test_pending_alert_cannot_remove_followed_serial(self):
        _policy, alert, _run = self._visit(lot_ids=[Command.set(self.lot.ids)])
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            alert.write({"lot_ids": [Command.clear()]})
        self.assertEqual(alert.lot_ids, self.lot)

    def test_alert_deletion_has_human_history_explanation(self):
        _policy, alert, _run = self._visit()
        self._human_deletion_error(alert)

    def test_private_run_deletion_has_human_history_explanation(self):
        _policy, _alert, run = self._visit()
        self._human_deletion_error(run)

    def test_lost_source_read_prevents_manual_feedback(self):
        policy, alert, run = self._visit()
        activity = run.activity_id
        self._hide("quality.alert", alert)
        with self.assertRaises(AccessError), self.cr.savepoint():
            activity.with_user(policy.user_id).action_feedback(feedback="QA acceso retirado")
        self.assertEqual(run.outcome, "pending")

    def test_lost_source_write_prevents_explicit_start(self):
        policy, alert, run = self._visit()
        self._hide("quality.alert", alert, write_only=True)
        with self.assertRaises(AccessError), self.cr.savepoint():
            self._quality_service().with_user(policy.user_id)._start(alert, fields.Datetime.now())
        self.assertEqual(run.outcome, "pending")

    def test_recipient_in_foreign_company_does_not_receive_activity(self):
        policy, _alert, _run = self._visit()
        company = self._other_company()
        user = new_test_user(
            self.env,
            login="qa_quality_boundary_foreign_recipient",
            groups="quality.group_quality_user",
            company_id=company.id,
            company_ids=[Command.set(company.ids)],
        )
        policy.user_id = user
        alert = self._quality_alert()
        self.assertFalse(
            self.env["mc.rov.quality.activity.run"].search([("alert_id", "=", alert.id)])
        )
        self.assertEqual(user.company_ids, company)

    def test_multicompany_actor_does_not_expand_recipient_context(self):
        policy, seed, _run = self._visit()
        policy.employee_id = self.empleado.id
        company = self._other_company()
        actor = self._coordinator()
        actor.company_ids = [Command.link(company.id)]
        alert = (
            self.env["quality.alert"]
            .with_user(actor)
            .with_context(allowed_company_ids=actor.company_ids.ids)
            .create(
                {
                    "name": "QA evento de actor multiempresa",
                    "product_id": self.product.id,
                    "product_tmpl_id": self.product.product_tmpl_id.id,
                    "team_id": seed.team_id.id,
                    "stage_id": seed.stage_id.id,
                    "company_id": self.env.company.id,
                }
            )
        )
        self.assertEqual(
            self.env["mc.rov.quality.activity.run"].search_count([("alert_id", "=", alert.id)]), 1
        )
        self.assertEqual(policy.user_id.company_ids, self.env.company)

    def test_foreign_source_cannot_expand_actor_active_companies(self):
        policy, _alert, _run = self._visit()
        company = self._other_company()
        foreign = self._quality_alert(company_id=company.id)
        user = policy.user_id
        user.company_ids = [Command.link(company.id)]
        with self.assertRaises(AccessError), self.cr.savepoint():
            self._quality_service().with_user(user).with_context(
                allowed_company_ids=self.env.company.ids
            )._start(foreign, fields.Datetime.now())
        self.assertFalse(
            self.env["mc.rov.quality.activity.run"].search([("alert_id", "=", foreign.id)])
        )

    def test_private_history_is_not_readable_or_exportable(self):
        policy, _alert, run = self._visit()
        policy.user_id.group_ids = [Command.link(self.env.ref("base.group_allow_export").id)]
        with self.assertRaises(AccessError):
            run.with_user(policy.user_id).read(["finish_reason"])
        with self.assertRaises(AccessError):
            run.with_user(policy.user_id).export_data(["original_deadline"])

    def test_restricted_employee_name_is_not_exported(self):
        policy, _alert, run = self._visit()
        run.activity_id.mc_employee_id = self.empleado.id
        policy.user_id.group_ids = [Command.link(self.env.ref("base.group_allow_export").id)]
        self._hide("hr.employee.public", self.env["hr.employee.public"].browse(self.empleado.id))
        rows = run.activity_id.with_user(policy.user_id).export_data(["mc_employee_id"])
        self.assertNotIn(self.empleado.name, str(rows))
        self.assertIn("Sin acceso al nombre", str(rows))

    def test_center_mine_quality_contains_generated_pending(self):
        policy, _alert, run = self._visit()
        action = self._assignment(policy.user_id).action_activities(process="quality")
        self.assertIn(run.activity_id.id, self._ids(action, policy.user_id))
        self.assertNotIn("mc.rov.quality.activity.run", str(action))

    def test_center_team_quality_is_available_to_authorized_coordinator(self):
        _policy, _alert, run = self._visit()
        actor = self._coordinator()
        action = self._assignment(actor).action_activities(scope="team", process="quality")
        self.assertIn(run.activity_id.id, self._ids(action, actor))

    def test_center_team_requires_explicit_team_permission(self):
        policy, _alert, _run = self._visit()
        with self.assertRaises(AccessError):
            self._assignment(policy.user_id).action_activities(scope="team", process="quality")

    def test_center_employee_and_account_filters_cross(self):
        policy, _alert, run = self._visit()
        run.activity_id.mc_employee_id = self.empleado.id
        action = self._assignment(policy.user_id).action_activities(
            process="quality", employee_id=self.empleado.id
        )
        self.assertEqual(self._ids(action, policy.user_id), run.activity_id.ids)

    def test_center_domain_remains_live_for_later_alerts(self):
        policy, _alert, _run = self._visit()
        action = self._assignment(policy.user_id).action_activities(process="quality")
        second = self._quality_alert()
        run = self.env["mc.rov.quality.activity.run"].search([("alert_id", "=", second.id)])
        self.assertIn(run.activity_id.id, self._ids(action, policy.user_id))

    def test_hidden_alert_cannot_be_opened_or_exported(self):
        policy, alert, run = self._visit()
        activity = run.activity_id
        policy.user_id.group_ids = [Command.link(self.env.ref("base.group_allow_export").id)]
        self._hide("quality.alert", alert)
        with self.assertRaises(AccessError):
            activity.with_user(policy.user_id).export_data(["summary"])
        with self.assertRaises(AccessError):
            self._assignment(policy.user_id).action_open_source(activity.id)

    def test_portal_cannot_open_work_assignment(self):
        _policy, _alert, _run = self._visit()
        portal = new_test_user(
            self.env, login="qa_quality_boundary_portal", groups="base.group_portal"
        )
        with self.assertRaises(AccessError):
            self._assignment(portal).action_activities(process="quality")

    def test_employee_only_assignment_preserves_account_and_date(self):
        _policy, _alert, run = self._visit()
        before = run.activity_id.user_id, run.activity_id.date_deadline
        self._wizard(
            run.activity_id, apply_employee=True, employee_id=self.empleado.id
        ).action_apply()
        self.assertEqual(run.activity_id.mc_employee_id.id, self.empleado.id)
        self.assertEqual((run.activity_id.user_id, run.activity_id.date_deadline), before)

    def test_account_only_assignment_preserves_employee_and_date(self):
        _policy, _alert, run = self._visit()
        run.activity_id.mc_employee_id = self.empleado.id
        before = run.activity_id.mc_employee_id, run.activity_id.date_deadline
        actor = self._coordinator()
        self._wizard(run.activity_id, apply_user=True, user_id=actor.id).action_apply()
        self.assertEqual(run.activity_id.user_id, actor)
        self.assertEqual((run.activity_id.mc_employee_id, run.activity_id.date_deadline), before)

    def test_reprogramming_requires_reason(self):
        _policy, _alert, run = self._visit()
        before = run.activity_id.date_deadline
        with self.assertRaisesRegex(UserError, "motivo"), self.cr.savepoint():
            self._wizard(
                run.activity_id, apply_deadline=True, date_deadline=date(2027, 1, 8)
            ).action_apply()
        self.assertEqual(run.activity_id.date_deadline, before)

    def test_reprogramming_is_audited_on_alert(self):
        _policy, alert, run = self._visit()
        self._wizard(
            run.activity_id,
            apply_deadline=True,
            date_deadline=date(2027, 1, 8),
            reason="QA nueva fecha acordada de Calidad",
        ).action_apply()
        self.assertEqual(run.activity_id.date_deadline, date(2027, 1, 8))
        self.assertTrue(
            alert.message_ids.filtered(
                lambda message: "QA nueva fecha acordada" in (message.body or "")
            )
        )

    def test_temporary_alert_copy_cannot_close_real_pending(self):
        _policy, alert, run = self._visit()
        closed = self.env["quality.alert.stage"].create(
            {"name": "QA cerrada temporal", "done": True}
        )
        temporary = alert.new({"stage_id": closed.id}, origin=alert)
        self.env["mc.rov.quality.activity.lifecycle"]._reconcile(
            temporary, {temporary.id: False}, fields.Datetime.now()
        )
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)
        self.assertFalse(alert.stage_id.done)

    def test_temporary_alert_without_origin_has_no_persistent_effects(self):
        _policy, alert, run = self._visit()
        temporary = self.env["quality.alert"].new(
            {
                "product_id": self.product.id,
                "company_id": self.env.company.id,
                "stage_id": alert.stage_id.id,
            }
        )
        before = self.env["mc.rov.quality.activity.run"].search_count([])
        self.env["mc.rov.quality.activity.lifecycle"]._reconcile(
            temporary, {temporary.id: None}, fields.Datetime.now()
        )
        self.assertEqual(self.env["mc.rov.quality.activity.run"].search_count([]), before)
        self.assertEqual(run.outcome, "pending")

    def test_temporary_activity_archive_does_not_cancel_real_pending(self):
        _policy, _alert, run = self._visit()
        temporary = run.activity_id.new({}, origin=run.activity_id)
        temporary.write({"active": False})
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_followed_activity_cannot_change_source(self):
        _policy, _alert, run = self._visit()
        other = self._quality_alert()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            run.activity_id.write({"res_id": other.id})

    def test_owner_can_finish_pending_without_private_ledger_permission(self):
        policy, alert, run = self._visit()
        run.activity_id.with_user(policy.user_id).action_feedback(
            feedback="QA decisión del taller"
        )
        self.assertEqual(run.outcome, "manual_done")
        self.assertEqual(run.finished_by_id, policy.user_id)
        self.assertFalse(alert.stage_id.done)
        self.assertFalse(run.with_user(policy.user_id).has_access("read"))

    def test_closed_alert_keeps_preventive_lesson_accessible(self):
        policy, alert, run = self._visit()
        closed = self.env["quality.alert.stage"].create(
            {"name": "QA lección cerrada", "done": True}
        )
        alert.write(
            {"action_preventive": "<p>QA mejora del procedimiento</p>", "stage_id": closed.id}
        )
        self.assertEqual(run.outcome, "business_done")
        values = alert.with_user(policy.user_id).read(["action_preventive"])
        self.assertIn("QA mejora del procedimiento", values[0]["action_preventive"])
