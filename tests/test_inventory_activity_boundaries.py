"""Permisos y decisiones sobre actividades no sustituyen las operaciones de stock."""

from datetime import timedelta
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .automatic_completion_assertions import assert_automatic_close_rejected
from .test_inventory_activity_events import InventoryEventCommon


@tagged("post_install", "-at_install")
# Cada frontera protege un contrato de uso o privacidad diferente.
# pylint: disable=too-many-public-methods
class TestInventoryActivityBoundaries(InventoryEventCommon):
    """Coordinar pendientes conserva identidad, acceso real y compromisos capturados."""

    def _policy(self, **values):
        controls = self.env["mc.rov.automation.control"]
        control = controls.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = True
        else:
            controls.create({"company_id": self.env.company.id, "enabled": True})
        return super()._policy(**values)

    def _runs(self, picking):
        return self.env["mc.rov.inventory.activity.run"].search(
            [("picking_id", "=", picking.id)], order="id"
        )

    def _visit(self):
        policy = self._policy()
        self._rule(policy=policy)
        picking = self._confirm(self._prepared())
        run = self._runs(picking)
        self.assertEqual(len(run), 1)
        self.assertEqual(run.outcome, "pending")
        return policy, picking, run

    def _source(self):
        service = self.env["mc.rov.inventory.activity.automation"]
        self.assertTrue(
            callable(getattr(service, "_runs", None)), "Missing inventory source service"
        )
        return service

    def _hide(self, picking):
        self.env["ir.rule"].create(
            {
                "name": "QA Inventario acceso revocado",
                "model_id": self.env["ir.model"]._get_id("stock.picking"),
                "domain_force": repr([("id", "!=", picking.id)]),
            }
        )
        self.env.invalidate_all()

    def _wizard(self, activity, **values):
        return (
            self.env["mc.rov.activity.assignment.wizard"]
            .with_user(self.coordinator)
            .create({"activity_ids": [Command.set(activity.ids)], **values})
        )

    def _reprogram(self, run):
        deadline = run.original_deadline + timedelta(days=2)
        self._wizard(
            run.activity_id,
            apply_deadline=True,
            date_deadline=deadline,
            reason="QA nuevo compromiso autorizado",
        ).action_apply()
        return deadline

    def _human_deletion(self, record):
        with self.assertRaisesRegex(UserError, "historial"), self.cr.savepoint():
            try:
                record.unlink()
            except IntegrityError:
                self.fail("Falta explicar la conservación del historial de inventario")

    def test_manual_done_is_blocked_without_validating_stock(self):
        _policy, picking, run = self._visit()
        state = picking.state
        with assert_automatic_close_rejected(self, run):
            run.activity_id.with_user(self.operator).action_feedback(
                feedback="QA realizado manualmente"
            )
        self.assertEqual(run.outcome, "pending")
        self.assertFalse(run.finished_by_id)
        self.assertFalse(run.finished_at)
        self.assertFalse(run.finish_reason)
        self.assertEqual(picking.state, state)
        self.assertNotEqual(picking.state, "done")

    def test_manual_cancel_is_blocked_without_cancelling_stock(self):
        _policy, picking, run = self._visit()
        state = picking.state
        with assert_automatic_close_rejected(self, run):
            run.activity_id.with_user(self.operator).action_cancel()
        self.assertEqual(run.outcome, "pending")
        self.assertFalse(run.finished_by_id)
        self.assertFalse(run.finish_reason)
        self.assertEqual(picking.state, state)

    def test_manual_archive_is_blocked_and_keeps_pending(self):
        _policy, picking, run = self._visit()
        with assert_automatic_close_rejected(self, run):
            run.activity_id.with_user(self.operator).write({"active": False})
        self.assertEqual(run.outcome, "pending")
        self.assertFalse(run.finish_reason)
        self.assertNotEqual(picking.state, "cancel")

    def test_blocked_unlink_preserves_pending_and_deadline(self):
        _policy, picking, run = self._visit()
        deadline = self._reprogram(run)
        with assert_automatic_close_rejected(self, run):
            run.activity_id.with_user(self.coordinator).unlink()
        self.assertEqual(run.outcome, "pending")
        self.assertEqual(run.current_deadline, deadline)
        self.assertEqual(run.cycle_id.current_deadline, deadline)
        self.assertTrue(run.activity_id.active)
        self.assertNotEqual(picking.state, "done")

    def test_reprogram_updates_run_cycle_without_replacing_original(self):
        _policy, _picking, run = self._visit()
        original = run.original_deadline
        deadline = self._reprogram(run)
        self.assertEqual(run.current_deadline, deadline)
        self.assertEqual(run.cycle_id.current_deadline, deadline)
        self.assertEqual(run.original_deadline, original)
        self.assertEqual(run.cycle_id.original_deadline, original)

    def test_partial_inherits_authorized_reprogram(self):
        _policy, picking, run = self._visit()
        deadline = self._reprogram(run)
        remaining = self._finish(picking, 1)
        child = self._runs(remaining)
        self.assertEqual(child.current_deadline, deadline)
        self.assertEqual(child.activity_id.date_deadline, deadline)
        self.assertEqual(child.original_deadline, run.original_deadline)

    def test_authorized_reprogram_cannot_smuggle_archive_and_rolls_back(self):
        _policy, _picking, run = self._visit()
        activity = run.activity_id
        deadline = run.original_deadline + timedelta(days=2)
        model = type(self.env["mail.activity"])
        native_write = model.write

        def combined_write(records, values):
            # Se conserva permiso/motivo del asistente y la escritura real completa.
            if activity.id in records.ids and "date_deadline" in values:
                values = {**values, "active": False}
            return native_write(records, values)

        with patch.object(model, "write", combined_write), assert_automatic_close_rejected(
            self, run
        ):
            self._wizard(
                activity,
                apply_deadline=True,
                date_deadline=deadline,
                reason="QA reprogramar y archivar",
            ).action_apply()
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(activity.active)
        self.assertEqual(run.current_deadline, run.original_deadline)
        self.assertEqual(run.cycle_id.current_deadline, run.original_deadline)

    def test_reprogrammed_activity_after_blocked_removal_keeps_remaining_commitment(self):
        _policy, picking, run = self._visit()
        deadline = self._reprogram(run)
        with assert_automatic_close_rejected(self, run):
            run.activity_id.with_user(self.coordinator).unlink()
        remaining = self._finish(picking, 1)
        self.assertEqual(self._runs(remaining).current_deadline, deadline)
        self.assertEqual(run.outcome, "business_done")

    def test_assignee_cannot_extend_deadline_directly(self):
        _policy, _picking, run = self._visit()
        with self.assertRaises(UserError), self.cr.savepoint():
            run.activity_id.with_user(self.operator).write(
                {"date_deadline": run.original_deadline + timedelta(days=2)}
            )

    def test_coordinator_cannot_reprogram_without_validated_reason(self):
        _policy, _picking, run = self._visit()
        with self.assertRaises(UserError), self.cr.savepoint():
            run.activity_id.with_user(self.coordinator).write(
                {"date_deadline": run.original_deadline + timedelta(days=2)}
            )

    def test_rpc_context_cannot_forge_reprogram_authorization(self):
        _policy, _picking, run = self._visit()
        deadline = run.original_deadline + timedelta(days=2)
        fake = (True, self.coordinator.id, tuple(run.activity_id.ids), deadline, "QA falso")
        with self.assertRaises(UserError), self.cr.savepoint():
            run.activity_id.with_user(self.coordinator).with_context(
                _mc_activity_deadline_authorization=fake
            ).write({"date_deadline": deadline})

    def test_wizard_requires_reason_when_reprogramming(self):
        _policy, _picking, run = self._visit()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(
                run.activity_id,
                apply_deadline=True,
                date_deadline=run.original_deadline + timedelta(days=2),
            ).action_apply()

    def test_assignment_keeps_source_and_posts_reason(self):
        _policy, picking, run = self._visit()
        user = new_test_user(
            self.env, login="qa_inventory_reparto", groups="stock.group_stock_user"
        )
        self._wizard(
            run.activity_id, apply_user=True, user_id=user.id, reason="QA repartir logística"
        ).action_apply()
        self.assertEqual(run.activity_id.user_id, user)
        self.assertEqual(run.activity_id.res_id, picking.id)
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(
            any("QA repartir logística" in str(message.body) for message in picking.message_ids)
        )

    def test_reassignment_rejects_account_without_source_access(self):
        _policy, _picking, run = self._visit()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(
                run.activity_id,
                apply_user=True,
                user_id=self.outsider.id,
                reason="QA cuenta sin stock",
            ).action_apply()

    def test_employee_assignment_keeps_account(self):
        _policy, _picking, run = self._visit()
        employee = self.env["hr.employee"].create(
            {"name": "QA Operador logístico", "company_id": self.env.company.id}
        )
        self._wizard(
            run.activity_id,
            apply_employee=True,
            employee_id=employee.id,
            reason="QA repartir a persona",
        ).action_apply()
        self.assertEqual(run.activity_id.mc_employee_id, employee)
        self.assertEqual(run.activity_id.user_id, self.operator)

    def test_blocked_feedback_then_reservation_keeps_one_pending(self):
        _policy, picking, run = self._visit()
        with assert_automatic_close_rejected(self, run):
            run.activity_id.with_user(self.operator).action_feedback(
                feedback="QA terminado manualmente"
            )
        picking.with_user(self.operator).action_assign()
        self.assertEqual(self._runs(picking), run)
        self.assertTrue(run.activity_id.filtered("active"))

    def test_schedule_edit_preserves_captured_deadline(self):
        _policy, picking, run = self._visit()
        before = run.current_deadline
        picking.scheduled_date = picking.scheduled_date + timedelta(days=60)
        self.assertEqual(run.current_deadline, before)
        self.assertEqual(self._runs(picking), run)

    def test_confirmed_before_policy_is_not_backfilled_by_edit(self):
        picking = self._confirm(self._prepared())
        self._rule(policy=self._policy())
        picking.write({"origin": "QA activación posterior"})
        picking.with_user(self.operator).action_assign()
        self.assertFalse(self._runs(picking))

    def test_pending_source_cannot_replace_type(self):
        _policy, picking, _run = self._visit()
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            picking.write({"picking_type_id": self.types["internal"].id})

    def test_pending_source_cannot_replace_company(self):
        _policy, picking, _run = self._visit()
        other = self._other_company()
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            picking.write({"company_id": other.id})

    def test_pending_source_cannot_replace_source_location(self):
        _policy, picking, _run = self._visit()
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            picking.write({"location_id": self.locations["other_stock"].id})

    def test_pending_source_cannot_replace_destination(self):
        _policy, picking, _run = self._visit()
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            picking.write({"location_dest_id": self.locations["other_stock"].id})

    def test_same_identity_values_are_allowed(self):
        _policy, picking, run = self._visit()
        picking.write(
            {
                "company_id": picking.company_id.id,
                "picking_type_id": picking.picking_type_id.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
            }
        )
        self.assertEqual(self._runs(picking), run)
        self.assertEqual(run.outcome, "pending")

    def test_quantities_and_reservation_are_allowed(self):
        _policy, picking, run = self._visit()
        picking.move_ids.with_user(self.operator).write({"product_uom_qty": 3})
        picking.with_user(self.operator).action_assign()
        self.assertEqual(picking.move_ids.product_uom_qty, 3)
        self.assertEqual(self._runs(picking), run)
        self.assertEqual(run.outcome, "pending")

    def test_additional_component_does_not_replace_document_identity(self):
        _policy, picking, run = self._visit()
        product = self.env["product.product"].create(
            {
                "name": "QA Repuesto adicional",
                "type": "consu",
                "is_storable": True,
                "categ_id": self.product.categ_id.id,
                "company_id": self.env.company.id,
            }
        )
        self.assertTrue(product.exists(), "El repuesto QA debe tener una variante persistente")
        picking.move_ids = [
            Command.create(
                {
                    "product_id": product.id,
                    "product_uom_qty": 1,
                    "product_uom": product.uom_id.id,
                    "location_id": picking.location_id.id,
                    "location_dest_id": picking.location_dest_id.id,
                }
            )
        ]
        self.assertEqual(len(picking.move_ids), 2)
        self.assertEqual(self._runs(picking), run)
        self.assertEqual(run.outcome, "pending")

    def test_activity_cannot_replace_source(self):
        _policy, _picking, run = self._visit()
        other = self._prepared()
        with self.assertRaises(UserError), self.cr.savepoint():
            run.activity_id.write({"res_id": other.id})

    def test_activity_cannot_replace_type(self):
        _policy, _picking, run = self._visit()
        with self.assertRaises(UserError), self.cr.savepoint():
            run.activity_id.write(
                {"activity_type_id": self.env.ref("mail.mail_activity_data_todo").id}
            )

    def test_source_deletion_explains_history(self):
        _policy, picking, _run = self._visit()
        self._human_deletion(picking)

    def test_cycle_deletion_explains_history(self):
        _policy, _picking, run = self._visit()
        self._human_deletion(run.cycle_id)

    def test_run_deletion_explains_history(self):
        _policy, _picking, run = self._visit()
        self._human_deletion(run)

    def test_portal_cannot_query_source_history(self):
        _policy, picking, _run = self._visit()
        portal = new_test_user(
            self.env, login="qa_inventory_boundary_portal", groups="base.group_portal"
        )
        service = self._source().with_user(portal)
        with self.assertRaises(AccessError), self.cr.savepoint():
            service._runs(picking, access="read")

    def test_restricted_source_cannot_query_history(self):
        _policy, picking, _run = self._visit()
        service = self._source().with_user(self.operator)
        self._hide(picking)
        with self.assertRaises(AccessError), self.cr.savepoint():
            service._runs(picking, access="read")

    def test_company_context_cannot_query_foreign_history(self):
        _policy, picking, _run = self._visit()
        other = self._other_company()
        self.coordinator.company_ids = [Command.link(other.id)]
        service = (
            self._source().with_user(self.coordinator).with_context(allowed_company_ids=other.ids)
        )
        with self.assertRaises(AccessError), self.cr.savepoint():
            service._runs(picking, access="read")

    def test_private_history_cannot_be_read_or_exported(self):
        _policy, _picking, run = self._visit()
        self.operator.group_ids = [Command.link(self.env.ref("base.group_allow_export").id)]
        with self.assertRaises(AccessError):
            run.with_user(self.operator).read(["finish_reason"])
        with self.assertRaises(AccessError):
            run.with_user(self.operator).export_data(["original_deadline"])

    def test_restricted_source_blocks_manual_feedback(self):
        _policy, picking, run = self._visit()
        activity = run.activity_id
        self._hide(picking)
        with self.assertRaises(AccessError), self.cr.savepoint():
            activity.with_user(self.operator).action_feedback(feedback="QA acceso revocado")
        self.assertEqual(run.outcome, "pending")

    def test_multicompany_actor_does_not_expand_recipient_context(self):
        self._rule(policy=self._policy())
        other = self._other_company()
        self.coordinator.company_ids = [Command.link(other.id)]
        picking = self._prepared()
        picking.with_user(self.coordinator).with_context(
            allowed_company_ids=self.coordinator.company_ids.ids
        ).action_confirm()
        self.assertEqual(len(self._runs(picking)), 1)
        self.assertEqual(self.operator.company_ids, self.env.company)

    def test_recipient_without_company_membership_is_skipped(self):
        other = self._other_company()
        user = new_test_user(
            self.env,
            login="qa_inventory_boundary_foreign",
            groups="stock.group_stock_user",
            company_id=other.id,
            company_ids=[Command.set(other.ids)],
        )
        self._rule(policy=self._policy(), user_id=user.id)
        picking = self._confirm(self._prepared())
        self.assertFalse(self._runs(picking))
        self.assertEqual(user.company_ids, other)

    def test_paused_policy_still_blocks_manual_completion(self):
        policy, picking, run = self._visit()
        policy.enabled = False
        with assert_automatic_close_rejected(self, run):
            run.activity_id.with_user(self.operator).action_feedback(
                feedback="QA decisión durante pausa"
            )
        self.assertEqual(run.outcome, "pending")
        self.assertNotEqual(picking.state, "done")

    def test_paused_partial_closes_parent_without_new_pending(self):
        policy, picking, run = self._visit()
        policy.enabled = False
        remaining = self._finish(picking, 1)
        self.assertEqual(run.outcome, "business_done")
        self.assertFalse(self._runs(remaining))

    def test_reactivation_does_not_rebuild_skipped_partial(self):
        policy, picking, _run = self._visit()
        policy.enabled = False
        remaining = self._finish(picking, 1)
        policy.enabled = True
        remaining.write({"origin": "QA pausa terminada"})
        remaining.with_user(self.operator).action_assign()
        self.assertFalse(self._runs(remaining))

    def test_temporary_picking_without_origin_creates_nothing(self):
        _policy, picking, run = self._visit()
        temporary = self.env["stock.picking"].new(
            {
                "picking_type_id": picking.picking_type_id.id,
                "company_id": picking.company_id.id,
                "state": "assigned",
            }
        )
        self.env["mc.rov.inventory.activity.lifecycle"]._sync(
            temporary, {temporary.id: None}, fields.Datetime.now()
        )
        self.assertEqual(self._runs(picking), run)
        self.assertEqual(run.outcome, "pending")

    def test_temporary_activity_archive_does_not_cancel_real_run(self):
        _policy, _picking, run = self._visit()
        activity = run.activity_id
        activity.new({}, origin=activity).write({"active": False})
        self.assertTrue(activity.active)
        self.assertEqual(run.outcome, "pending")

    def test_homonymous_unlinked_activity_remains_independent(self):
        _policy, picking, run = self._visit()
        manual = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("stock.picking"),
                "res_id": picking.id,
                "activity_type_id": run.activity_id.activity_type_id.id,
                "summary": run.activity_id.summary,
                "user_id": self.operator.id,
                "date_deadline": run.original_deadline,
            }
        )
        self._finish(picking)
        self.assertEqual(run.outcome, "business_done")
        self.assertTrue(manual.exists().active)
