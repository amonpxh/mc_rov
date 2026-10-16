import json
from datetime import date
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .manufacturing_activity_common import ManufacturingActivityCommon


@tagged("post_install", "-at_install")
# Contratos independientes de autorización, identidad y reparto sobre el mismo flujo.
# pylint: disable=too-many-public-methods
class TestManufacturingActivityBoundaries(ManufacturingActivityCommon):
    """El seguimiento conserva el documento y los permisos de quien trabaja sobre él."""

    def _visit(self):
        policy = self._policy()
        production = self._production()
        production.action_confirm()
        run = self._runs(production)
        self.assertEqual(len(run), 1)
        return policy, production, run

    def _coordinator(self):
        return new_test_user(
            self.env,
            login="qa_manufacturing_coordinate",
            groups="mrp.group_mrp_user,mc_rov.group_work_assignment_coordinate",
            company_id=self.env.company.id,
        )

    def _hide(self, production):
        self.env["ir.rule"].create(
            {
                "name": "QA fabricación restringida",
                "model_id": self.env["ir.model"]._get_id("mrp.production"),
                "domain_force": f"[('id', '!=', {production.id})]",
            }
        )

    def _wizard(self, activity, **values):
        return (
            self.env["mc.rov.activity.assignment.wizard"]
            .with_user(self._coordinator())
            .create({"activity_ids": [Command.set(activity.ids)], **values})
        )

    def test_operator_can_create_and_confirm_without_technical_group(self):
        policy = self._policy()
        try:
            with self.cr.savepoint():
                production = (
                    self.env["mrp.production"]
                    .with_user(policy.user_id)
                    .create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "product_uom_id": self.product.uom_id.id,
                            "company_id": self.env.company.id,
                        }
                    )
                )
                production.action_confirm()
        except AccessError as error:
            self.fail(f"El operario perdió acceso a la creación/confirmación nativa: {error}")
        self.assertEqual(production.state, "confirmed")
        self.assertEqual(len(self._runs(production)), 1)

    def test_multicompany_actor_does_not_expand_recipient_context(self):
        self._policy(employee_id=self.empleado.id)
        company = self.env["res.company"].create({"name": "QA otra empresa del coordinador"})
        actor = self._coordinator()
        actor.company_ids = [Command.set((self.env.company | company).ids)]
        production = self._production()
        production.with_user(actor).with_context(
            allowed_company_ids=actor.company_ids.ids
        ).action_confirm()
        self.assertEqual(len(self._runs(production)), 1)

    def test_recipient_without_source_access_gets_no_pending(self):
        self._policy()
        production = self._production()
        self._hide(production)
        production.action_confirm()
        self.assertFalse(self._runs(production))
        self.assertEqual(production.state, "confirmed")

    def test_lost_source_access_hides_native_activity_query(self):
        policy, production, run = self._visit()
        self._hide(production)
        self.assertFalse(
            self.env["mail.activity"]
            .with_user(policy.user_id)
            .search([("id", "=", run.activity_id.id)])
        )

    def test_lost_source_access_blocks_manual_completion(self):
        policy, production, run = self._visit()
        self._hide(production)
        with self.assertRaises(AccessError), self.cr.savepoint():
            run.activity_id.with_user(policy.user_id).action_feedback(feedback="QA")
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_private_history_cannot_be_read_or_exported(self):
        policy, _production, run = self._visit()
        policy.user_id.write(
            {"group_ids": [Command.link(self.env.ref("base.group_allow_export").id)]}
        )
        with self.assertRaises(AccessError):
            run.with_user(policy.user_id).read(["finish_reason"])
        with self.assertRaises(AccessError):
            run.with_user(policy.user_id).export_data(["original_deadline"])

    def test_coordinator_cannot_read_other_company_policy(self):
        company = self.env["res.company"].create({"name": "QA política ajena fabricación"})
        policy = self._policy_model().create({"company_id": company.id})
        actor = self._coordinator()
        with self.assertRaises(AccessError):
            policy.with_user(actor).with_context(allowed_company_ids=actor.company_ids.ids).read(
                ["lead_days"]
            )

    def test_operator_cannot_read_policy(self):
        policy = self._policy()
        with self.assertRaises(AccessError):
            policy.with_user(policy.user_id).read(["lead_days"])

    def test_manual_audit_identifies_actor_without_changing_employee(self):
        policy, _production, run = self._visit()
        run.activity_id.mc_employee_id = self.empleado
        run.activity_id.with_user(policy.user_id).action_feedback(feedback="QA cierre propio")
        self.assertEqual(run.finished_by_id, policy.user_id)
        self.assertEqual(run.outcome, "manual_done")
        self.assertEqual(run.finish_reason, "QA cierre propio")

    def test_pending_production_cannot_change_product(self):
        _policy, production, run = self._visit()
        other = self.env["product.product"].create(
            {"name": "QA otro modelo", "categ_id": self.product.categ_id.id}
        )
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            production.write({"product_id": other.id})
        self.assertEqual(run.production_id.product_id, self.product)

    def test_pending_production_cannot_change_company(self):
        _policy, production, _run = self._visit()
        company = self.env["res.company"].create({"name": "QA cambio de empresa fabricación"})
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            production.write({"company_id": company.id})

    def test_history_deletion_has_human_explanation(self):
        _policy, production, _run = self._visit()
        production.action_cancel()
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            try:
                production.unlink()
            except IntegrityError:
                self.fail("Falta explicar por qué se conserva una fabricación con historial")

    def test_parent_identity_cannot_be_written(self):
        _policy, production, run = self._visit()
        with self.assertRaises(AccessError), self.cr.savepoint():
            production.with_context(_mc_manufacturing_split=True).write(
                {"mc_manufacturing_parent_run_key": run.id}
            )

    def test_parent_identity_cannot_be_created(self):
        _policy, _production, run = self._visit()
        with self.assertRaises(AccessError), self.cr.savepoint():
            self._production(mc_manufacturing_parent_run_key=run.id)

    def test_context_defaults_do_not_forge_parent(self):
        _policy, _production, run = self._visit()
        copied = (
            self.env["mrp.production"]
            .with_context(
                default_mc_manufacturing_parent_run_key=run.id,
                _mc_manufacturing_split="internal",
            )
            .create(
                {
                    "product_id": self.product.id,
                    "product_qty": 1,
                    "product_uom_id": self.product.uom_id.id,
                }
            )
        )
        self.assertFalse(copied.mc_manufacturing_parent_run_key)

    def test_pending_activity_cannot_change_source(self):
        _policy, _production, run = self._visit()
        other = self._production()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            run.activity_id.write({"res_id": other.id})

    def test_temporary_activity_archive_does_not_cancel_real_run(self):
        _policy, _production, run = self._visit()
        temporary = self.env["mail.activity"].new(origin=run.activity_id)
        temporary.write({"active": False})
        run.invalidate_recordset()
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_temporary_production_does_not_cancel_real_run(self):
        _policy, production, run = self._visit()
        temporary = self.env["mrp.production"].new(origin=production)
        temporary.write({"state": "cancel"})
        run.invalidate_recordset()
        self.assertEqual(run.outcome, "pending")
        self.assertEqual(production.state, "confirmed")

    def test_temporary_production_without_origin_has_no_effects(self):
        _policy, production, run = self._visit()
        temporary = self.env["mrp.production"].new(
            {"product_id": self.product.id, "product_uom_id": self.product.uom_id.id}
        )
        previous = self._run_model().search_count([])
        temporary.write({"state": "cancel"})
        self.assertEqual(self._run_model().search_count([]), previous)
        self.assertEqual(run.outcome, "pending")
        self.assertEqual(production.state, "confirmed")

    def test_copied_activity_has_no_followup_identity(self):
        _policy, production, run = self._visit()
        copied = run.activity_id.copy()
        copied.action_feedback(feedback="QA actividad independiente")
        self.assertEqual(self._runs(production), run)
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_assignment_changes_only_employee(self):
        _policy, _production, run = self._visit()
        activity = run.activity_id
        previous = activity.user_id, activity.date_deadline
        self._wizard(activity, apply_employee=True, employee_id=self.empleado.id).action_apply()
        self.assertEqual(activity.mc_employee_id, self.empleado)
        self.assertEqual((activity.user_id, activity.date_deadline), previous)
        self.assertEqual(run.outcome, "pending")

    def test_assignment_changes_only_user(self):
        _policy, _production, run = self._visit()
        activity = run.activity_id
        activity.mc_employee_id = self.empleado
        previous = activity.mc_employee_id, activity.date_deadline
        user = new_test_user(self.env, login="qa_manufacturing_other", groups="mrp.group_mrp_user")
        self._wizard(activity, apply_user=True, user_id=user.id).action_apply()
        self.assertEqual(activity.user_id, user)
        self.assertEqual((activity.mc_employee_id, activity.date_deadline), previous)

    def test_reprogramming_requires_reason_and_is_atomic(self):
        _policy, _production, run = self._visit()
        before = run.activity_id.date_deadline
        wizard = self._wizard(
            run.activity_id, apply_deadline=True, date_deadline=date(2026, 11, 6)
        )
        with self.assertRaisesRegex(UserError, "motivo"), self.cr.savepoint():
            wizard.action_apply()
        self.assertEqual(run.activity_id.date_deadline, before)

    def test_reprogramming_with_reason_is_audited_on_production(self):
        _policy, production, run = self._visit()
        previous = run.activity_id.user_id, run.activity_id.mc_employee_id
        self._wizard(
            run.activity_id,
            apply_deadline=True,
            date_deadline=date(2026, 11, 6),
            reason="QA atraso de proveedor",
        ).action_apply()
        self.assertEqual(run.activity_id.date_deadline, date(2026, 11, 6))
        self.assertEqual((run.activity_id.user_id, run.activity_id.mc_employee_id), previous)
        self.assertTrue(
            production.message_ids.filtered(
                lambda message: "QA atraso de proveedor" in str(message.body)
            )
        )

    def test_policy_changes_do_not_reprogram_existing_pending(self):
        policy, production, run = self._visit()
        before = run.activity_id.date_deadline
        policy.lead_days = 7
        production.write({"origin": "QA edición sin evento"})
        self.assertEqual(run.activity_id.date_deadline, before)
        self.assertEqual(self._runs(production), run)
        other = self._production()
        other.action_confirm()
        self.assertLess(self._runs(other).activity_id.date_deadline, before)

    def test_partial_returns_environment_without_private_token(self):
        self._policy()
        production = self._production(product_qty=2)
        production.action_confirm()
        result = production._split_productions(amounts={production: [1.0, 1.0]})
        self.assertNotIn("_mc_manufacturing_split", result.env.context)
        json.dumps(dict(result.env.context))

    def test_manufacturing_filter_keeps_native_activity_query_live(self):
        policy, _production, first = self._visit()
        service = self.env["mc.rov.work.assignment"].with_user(policy.user_id)
        action = service.action_activities(process="manufacturing")
        other = self._production()
        other.action_confirm()
        second = self._runs(other)
        activities = self.env["mail.activity"].with_user(policy.user_id).search(action["domain"])
        self.assertTrue((first.activity_id | second.activity_id).ids)
        self.assertTrue(set((first.activity_id | second.activity_id).ids) <= set(activities.ids))
        with self.assertRaises(AccessError):
            service.action_activities(scope="team", process="manufacturing")

    def test_cancellation_and_resume_do_not_recreate_history_on_edit(self):
        policy, production, run = self._visit()
        production.action_cancel()
        policy.enabled = False
        policy.enabled = True
        production.write({"origin": "QA edición de fabricación cancelada"})
        self.assertEqual(self._runs(production), run)
        self.assertEqual(run.outcome, "cancelled")
        self.assertFalse(production.activity_ids)

    def test_stock_movements_reconcile_actual_completion_without_done_button(self):
        self._policy()
        production = self._production()
        component = self.env["product.product"].create({"name": "QA componente consumido"})
        raw = self.env["stock.move"].create(
            production._get_move_raw_values(component, 1, component.uom_id)
        )
        production.action_confirm()
        run = self._runs(production)
        production.write({"lot_producing_ids": [Command.set(self.lot.ids)], "qty_producing": 1})
        raw.write({"quantity": 1, "picked": True})
        raw._action_done()
        finished = production.move_finished_ids.filtered(
            lambda move: move.product_id == self.product
        )
        finished.write({"lot_ids": [Command.set(self.lot.ids)], "quantity": 1, "picked": True})
        finished._action_done()
        self.assertEqual(production.state, "done")
        self.assertEqual(run.outcome, "business_done")
        self.assertFalse(run.activity_id and run.activity_id.active)

    def test_failure_in_batch_confirmation_rolls_back_both_productions(self):
        self._policy()
        first, second = self._production(), self._production()
        service = self.env["mc.rov.manufacturing.activity.automation"]
        original = type(service)._start

        def fail_second(model, production, *args, **kwargs):
            if production == second:
                raise RuntimeError("QA fallo en segunda fabricación")
            return original(model, production, *args, **kwargs)

        with self.assertRaises(RuntimeError), self.cr.savepoint(), patch.object(
            type(service), "_start", new=fail_second
        ):
            (first | second).action_confirm()
        self.assertEqual(set((first | second).mapped("state")), {"draft"})
        self.assertFalse(self._runs(first) | self._runs(second))
