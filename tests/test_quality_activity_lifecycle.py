from datetime import date, datetime
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from .quality_activity_common import QualityActivityCommon


@tagged("post_install", "-at_install")
# Cada caso representa un evento distinto o una decisión manual conservada.
# pylint: disable=too-many-public-methods
class TestQualityActivityLifecycle(QualityActivityCommon):
    """El pendiente sigue la alerta real; marcarlo hecho no resuelve el problema."""

    def _lifecycle(self):
        self.assertIn(
            "mc.rov.quality.activity.lifecycle",
            self.env.registry.models,
            "Missing Quality lifecycle",
        )
        service = self._quality_service()
        self.assertTrue(callable(getattr(service, "_start", None)))
        return service

    def _control(self, enabled):
        model = self.env["mc.rov.automation.control"]
        control = model.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = enabled
        else:
            control = model.create({"company_id": self.env.company.id, "enabled": enabled})
        return control

    def _stage(self, done=False):
        return self.env["quality.alert.stage"].create({"name": "QA estado propio", "done": done})

    def _runs(self, alert):
        return self.env["mc.rov.quality.activity.run"].search(
            [("alert_id", "=", alert.id)], order="cycle,id"
        )

    def _scenario(self, policy_values=None, alert_values=None, enabled=True):
        self._lifecycle()
        policy = self._quality_policy(**(policy_values or {}))
        self._control(enabled)
        alert = self._quality_alert(**(alert_values or {}))
        return policy, alert, self._runs(alert)

    def _check(self):
        team = self.env["quality.alert.team"].create(
            {"name": "QA controles propios", "company_id": self.env.company.id}
        )
        return self.env["quality.check"].create(
            {
                "product_id": self.product.id,
                "company_id": self.env.company.id,
                "team_id": team.id,
            }
        )

    def _check_scenario(self):
        self._lifecycle()
        self._quality_policy()
        self._control(True)
        check = self._check()
        check.do_fail()
        self.assertEqual(len(check.alert_ids), 1)
        return check, check.alert_ids, self._runs(check.alert_ids)

    def test_native_shared_stage_done_is_visible_on_all_alerts(self):
        stage = self._stage()
        alerts = self._quality_alert(stage_id=stage.id) | self._quality_alert(stage_id=stage.id)
        stage.done = True
        self.assertTrue(all(alert.stage_id.done for alert in alerts))

    def test_native_failed_check_keeps_one_open_alert_on_retry(self):
        check = self._check()
        check.do_fail()
        original = check.alert_ids
        self.assertEqual(len(original), 1)
        self.assertFalse(original.stage_id.done)
        check.do_fail()
        self.assertEqual(check.alert_ids, original)

    def test_native_passing_check_does_not_resolve_alert(self):
        check = self._check()
        check.do_fail()
        alert = check.alert_ids
        check.do_pass()
        self.assertEqual(check.alert_ids, alert)
        self.assertFalse(alert.stage_id.done)

    def test_open_alert_creates_one_pending_cycle(self):
        _policy, _alert, run = self._scenario()
        self.assertEqual(len(run), 1)
        self.assertEqual(run.cycle, 1)
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_activity_uses_native_quality_alert_origin_and_type(self):
        _policy, alert, run = self._scenario()
        self.assertEqual(run.activity_id.res_model, "quality.alert")
        self.assertEqual(run.activity_id.res_id, alert.id)
        self.assertEqual(
            run.activity_id.activity_type_id,
            self.env.ref("mc_rov.activity_type_quality_resolution"),
        )

    def test_deadline_uses_own_event_and_working_calendar(self):
        policy, _alert, run = self._scenario()
        self.assertEqual(run.original_deadline, policy._deadline(run.started_at))
        self.assertEqual(run.current_deadline, run.original_deadline)
        self.assertEqual(run.activity_id.date_deadline, run.original_deadline)
        self.assertEqual(run.calendar_id, policy.calendar_id)
        self.assertEqual(run.calendar_tz, "America/Santiago")

    def test_recipient_is_explicit_and_not_event_actor(self):
        policy, _alert, run = self._scenario()
        self.assertEqual(run.activity_id.user_id, policy.user_id)
        self.assertNotEqual(policy.user_id, self.env.user)
        self.assertFalse(run.activity_id.mc_employee_id)

    def test_employee_without_login_is_assigned_independently(self):
        policy, _alert, run = self._scenario(policy_values={"employee_id": self.empleado.id})
        self.assertEqual(run.activity_id.mc_employee_id.id, self.empleado.id)
        self.assertEqual(run.activity_id.user_id, policy.user_id)
        self.assertFalse(self.empleado.user_id)

    def test_created_closed_alert_has_no_pending(self):
        self._lifecycle()
        _policy, _alert, runs = self._scenario(alert_values={"stage_id": self._stage(True).id})
        self.assertFalse(runs)

    def test_component_without_rov_origin_has_no_pending(self):
        self._lifecycle()
        category = self.env["product.category"].create({"name": "QA componente independiente"})
        product = self.env["product.product"].create(
            {"name": "QA componente", "categ_id": category.id}
        )
        _policy, _alert, runs = self._scenario(
            alert_values={"product_id": product.id, "product_tmpl_id": product.product_tmpl_id.id}
        )
        self.assertFalse(runs)

    def test_missing_recipient_does_not_assign_actor(self):
        _policy, _alert, runs = self._scenario(policy_values={"user_id": False})
        self.assertFalse(runs)

    def test_disabled_policy_prevents_new_pending(self):
        _policy, _alert, runs = self._scenario(policy_values={"enabled": False})
        self.assertFalse(runs)

    def test_general_pause_prevents_new_pending(self):
        _policy, _alert, runs = self._scenario(enabled=False)
        self.assertFalse(runs)

    def test_open_edit_keeps_cycle_and_original_deadline(self):
        _policy, alert, run = self._scenario()
        before = run.started_at, run.original_deadline, run.activity_id
        alert.write({"description": "QA ampliación de la descripción"})
        self.assertEqual(self._runs(alert), run)
        self.assertEqual((run.started_at, run.original_deadline, run.activity_id), before)

    def test_move_between_open_stages_does_not_restart(self):
        _policy, alert, run = self._scenario()
        alert.stage_id = self._stage()
        self.assertEqual(self._runs(alert), run)
        self.assertEqual(run.outcome, "pending")

    def test_later_serials_do_not_duplicate_or_restart(self):
        _policy, alert, run = self._scenario()
        before = run.started_at, run.original_deadline, run.activity_id
        alert.lot_ids = [Command.link(self.lot.id)]
        self.assertEqual(self._runs(alert), run)
        self.assertEqual((run.started_at, run.original_deadline, run.activity_id), before)

    def test_done_stage_closes_pending_without_corrective_requirements(self):
        _policy, alert, run = self._scenario()
        alert.stage_id = self._stage(True)
        self.assertEqual(run.outcome, "business_done")
        self.assertFalse(run.activity_id and run.activity_id.active)
        self.assertTrue(run.finished_at)
        self.assertEqual(run.finished_by_id, self.env.user)
        self.assertTrue(run.finish_reason)

    def test_marking_shared_stage_done_closes_all_affected_alerts(self):
        _policy, alert, run = self._scenario()
        second = self._quality_alert(stage_id=alert.stage_id.id)
        alert.stage_id.done = True
        self.assertEqual((run | self._runs(second)).mapped("outcome"), ["business_done"] * 2)

    def test_reopen_creates_one_new_cycle_with_new_event_date(self):
        policy, alert, first = self._scenario()
        alert.stage_id = self._stage(True)
        instant = datetime(2026, 11, 6, 15)
        with patch("odoo.fields.Datetime.now", return_value=instant):
            alert.stage_id = self._stage()
        runs = self._runs(alert)
        self.assertEqual(runs.mapped("cycle"), [1, 2])
        self.assertEqual(first.outcome, "business_done")
        self.assertEqual(runs[-1].started_at, instant)
        self.assertEqual(runs[-1].original_deadline, policy._deadline(instant))
        self.assertEqual(runs[-1].outcome, "pending")

    def test_reopening_stage_flag_creates_new_cycle_for_each_alert(self):
        _policy, alert, first = self._scenario()
        second = self._quality_alert(stage_id=alert.stage_id.id)
        stage = alert.stage_id
        stage.done = True
        stage.done = False
        for record in alert | second:
            runs = self._runs(record)
            self.assertEqual(runs.mapped("cycle"), [1, 2])
            self.assertEqual(runs.mapped("outcome"), ["business_done", "pending"])
        self.assertEqual(first.outcome, "business_done")

    def test_repeated_start_is_idempotent(self):
        _policy, alert, run = self._scenario()
        self._quality_service()._start(alert, run.started_at)
        self._quality_service()._start(alert, run.started_at)
        self.assertEqual(self._runs(alert), run)

    def test_policy_pause_does_not_block_closing(self):
        policy, alert, run = self._scenario()
        policy.enabled = False
        alert.stage_id = self._stage(True)
        self.assertEqual(run.outcome, "business_done")

    def test_general_pause_does_not_block_closing(self):
        _policy, alert, run = self._scenario()
        self._control(False)
        alert.stage_id = self._stage(True)
        self.assertEqual(run.outcome, "business_done")

    def test_policy_paused_reopening_is_not_backfilled_on_resume(self):
        policy, alert, first = self._scenario()
        alert.stage_id = self._stage(True)
        policy.enabled = False
        alert.stage_id = self._stage()
        policy.enabled = True
        alert.write({"description": "QA edición posterior"})
        self.assertEqual(self._runs(alert), first)
        self.assertEqual(first.outcome, "business_done")

    def test_created_while_paused_is_not_backfilled_on_resume(self):
        policy, alert, runs = self._scenario(policy_values={"enabled": False})
        self.assertFalse(runs)
        policy.enabled = True
        alert.write({"description": "QA sin evento nuevo"})
        self.assertFalse(self._runs(alert))

    def test_manual_done_audits_without_resolving_or_recreating(self):
        _policy, alert, run = self._scenario()
        run.activity_id.action_feedback(feedback="QA decisión manual")
        self.assertEqual(run.outcome, "manual_done")
        self.assertFalse(alert.stage_id.done)
        self.assertEqual(run.finished_by_id, self.env.user)
        self.assertTrue(run.finished_at)
        self.assertTrue(run.finish_reason)
        alert.write({"description": "QA edición abierta"})
        self.assertEqual(self._runs(alert), run)

    def test_manual_cancel_audits_without_resolving_or_recreating(self):
        _policy, alert, run = self._scenario()
        run.activity_id.action_cancel()
        self.assertEqual(run.outcome, "cancelled")
        self.assertFalse(alert.stage_id.done)
        self.assertEqual(run.finished_by_id, self.env.user)
        self.assertTrue(run.finish_reason)
        alert.write({"description": "QA edición abierta"})
        self.assertEqual(self._runs(alert), run)

    def test_manual_archive_is_audited_without_resolving(self):
        _policy, alert, run = self._scenario()
        run.activity_id.write({"active": False})
        self.assertEqual(run.outcome, "cancelled")
        self.assertFalse(alert.stage_id.done)
        self.assertTrue(run.finish_reason)

    def test_manual_unlink_preserves_history_and_current_deadline(self):
        _policy, alert, run = self._scenario()
        changed = date(2026, 12, 4)
        run.activity_id.date_deadline = changed
        run.activity_id.unlink()
        self.assertEqual(run.outcome, "cancelled")
        self.assertFalse(run.activity_id)
        self.assertEqual(run.current_deadline, changed)
        self.assertFalse(alert.stage_id.done)
        self.assertTrue(run.finish_reason)

    def test_manual_homonymous_activity_is_not_closed(self):
        policy, alert, run = self._scenario()
        manual = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("quality.alert"),
                "res_id": alert.id,
                "activity_type_id": self.env.ref("mc_rov.activity_type_quality_resolution").id,
                "user_id": policy.user_id.id,
                "summary": run.activity_id.summary,
                "date_deadline": run.original_deadline,
            }
        )
        alert.stage_id = self._stage(True)
        self.assertEqual(run.outcome, "business_done")
        self.assertTrue(manual.active)

    def test_failed_check_and_retries_keep_one_alert_and_pending(self):
        check, alert, run = self._check_scenario()
        self.assertEqual(len(run), 1)
        check.do_fail()
        self.assertEqual(check.alert_ids, alert)
        self.assertEqual(self._runs(alert), run)

    def test_passing_check_keeps_resolution_pending_until_alert_done(self):
        check, alert, run = self._check_scenario()
        check.do_pass()
        self.assertFalse(alert.stage_id.done)
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_business_close_preserves_reprogrammed_deadline(self):
        _policy, alert, run = self._scenario()
        changed = date(2026, 12, 4)
        original = run.original_deadline
        run.activity_id.date_deadline = changed
        alert.stage_id = self._stage(True)
        self.assertEqual(run.current_deadline, changed)
        self.assertEqual(run.original_deadline, original)
        self.assertEqual(run.outcome, "business_done")

    def test_missing_recipient_does_not_block_existing_close(self):
        policy, alert, run = self._scenario()
        policy.user_id = False
        alert.stage_id = self._stage(True)
        self.assertEqual(run.outcome, "business_done")

    def test_manual_outcome_survives_close_and_reopen_starts_new_cycle(self):
        _policy, alert, first = self._scenario()
        first.activity_id.action_cancel()
        alert.stage_id = self._stage(True)
        self.assertEqual(first.outcome, "cancelled")
        alert.stage_id = self._stage()
        runs = self._runs(alert)
        self.assertEqual(runs.mapped("cycle"), [1, 2])
        self.assertEqual(runs.mapped("outcome"), ["cancelled", "pending"])

    def test_general_paused_reopen_is_not_backfilled_by_later_open_move(self):
        _policy, alert, first = self._scenario()
        alert.stage_id = self._stage(True)
        self._control(False)
        alert.stage_id = self._stage()
        self._control(True)
        alert.stage_id = self._stage()
        self.assertEqual(self._runs(alert), first)
