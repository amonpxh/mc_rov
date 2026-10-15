from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestRepairActivityGeneration(RevisionCommon):
    """Los eventos reales generan una sola actividad por etapa de la visita."""

    def _policy(self, **values):
        self.assertIn(
            "mc.rov.repair.activity.automation",
            self.env.registry.models,
            "Missing repair activity generation service",
        )
        self.assertIn("mc.rov.repair.activity.run", self.env.registry.models)
        calendar = self.env["resource.calendar"].create(
            {
                "name": "QA generación de pendientes",
                "company_id": self.env.company.id,
                "tz": "America/Santiago",
                "attendance_ids": [
                    Command.clear(),
                    *[
                        Command.create(
                            {
                                "name": "QA jornada",
                                "dayofweek": str(day),
                                "hour_from": 8,
                                "hour_to": 17,
                                "day_period": "morning",
                            }
                        )
                        for day in range(5)
                    ],
                ],
            }
        )
        policy = self.env["mc.rov.repair.activity.policy"].search(
            [
                ("company_id", "=", self.env.company.id),
            ]
        )
        user = new_test_user(
            self.env,
            login="qa_repair_automation_taller",
            groups="stock.group_stock_user",
            company_id=self.env.company.id,
        )
        configuration = {
            "enabled": True,
            "user_id": user.id,
            "employee_id": False,
            "calendar_id": calendar.id,
            "diagnosis_days": 2,
            "repair_days": 2,
            **values,
        }
        if policy:
            policy.write(configuration)
        else:
            policy = self.env["mc.rov.repair.activity.policy"].create(
                {
                    "company_id": self.env.company.id,
                    **configuration,
                }
            )
        return policy

    def _order(self, **values):
        return self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "company_id": self.env.company.id,
                **values,
            }
        )

    def _runs(self, order):
        return (
            self.env["mc.rov.repair.activity.run"]
            .sudo()
            .search(
                [
                    ("repair_id", "=", order.id),
                ]
            )
        )

    def test_confirmed_creates_only_diagnosis(self):
        self._policy()
        order = self._order()
        order.write({"state": "confirmed"})
        run = self._runs(order)
        self.assertEqual(len(run), 1)
        self.assertEqual(run.stage, "diagnosis")
        self.assertEqual(run.revision_id.repair_id, order)
        self.assertEqual(run.revision_id.tipo, "reparacion")
        self.assertEqual(run.activity_id.res_model, "repair.order")
        self.assertEqual(run.activity_id.res_id, order.id)

    def test_start_creates_repair_after_diagnosis(self):
        self._policy()
        order = self._order()
        order.write({"state": "confirmed"})
        order.action_repair_start()
        self.assertEqual(set(self._runs(order).mapped("stage")), {"diagnosis", "repair"})
        self.assertTrue(all(self._runs(order).mapped("activity_id.active")))

    def test_direct_start_processes_both_events(self):
        self._policy()
        order = self._order()
        order.write({"state": "under_repair"})
        self.assertEqual(set(self._runs(order).mapped("stage")), {"diagnosis", "repair"})

    def test_repeated_states_do_not_duplicate(self):
        self._policy()
        order = self._order()
        order.action_repair_start()
        original = self._runs(order)
        order.write({"state": "under_repair"})
        order.write({"state": "under_repair"})
        self.assertEqual(self._runs(order), original)
        self.assertEqual(len(original.mapped("activity_id")), 2)

    def test_draft_has_no_automatic_activity(self):
        self._policy()
        order = self._order()
        self.assertFalse(self._runs(order))

    def test_component_without_rov_lot_is_excluded(self):
        self._policy()
        product = self.env["product.product"].create({"name": "QA componente sin serie"})
        order = self._order(product_id=product.id, lot_id=False)
        order.action_repair_start()
        self.assertFalse(self._runs(order))

    def test_disabled_policy_creates_nothing(self):
        self._policy(enabled=False)
        order = self._order()
        order.action_repair_start()
        self.assertFalse(self._runs(order))

    def test_missing_account_does_not_block_order(self):
        self._policy(user_id=False)
        order = self._order()
        order.action_repair_start()
        self.assertEqual(order.state, "under_repair")
        self.assertFalse(self._runs(order))

    def test_missing_calendar_does_not_invent_deadline(self):
        self._policy(calendar_id=False)
        order = self._order()
        order.action_repair_start()
        self.assertEqual(order.state, "under_repair")
        self.assertFalse(self._runs(order))

    def test_first_existing_revision_is_reused(self):
        self._policy()
        order = self._order()
        first = self._revision(tipo="reparacion", repair_id=order.id)
        self._revision(tipo="reparacion", repair_id=order.id)
        order.write({"state": "confirmed"})
        self.assertEqual(self._runs(order).revision_id, first)

    def test_already_confirmed_diagnosis_is_not_pending(self):
        self._policy()
        order = self._order()
        revision = self._revision(tipo="reparacion", repair_id=order.id)
        self._emitir(revision)
        order.write({"state": "confirmed"})
        self.assertFalse(self._runs(order))

    def test_historical_confirmed_order_has_no_retroactive_diagnosis(self):
        self._policy()
        order = self._order(state="confirmed")
        order.action_repair_start()
        self.assertEqual(self._runs(order).mapped("stage"), ["repair"])

    def test_manual_employee_and_deadline_are_preserved(self):
        self._policy()
        order = self._order()
        self._revision(tipo="reparacion", repair_id=order.id)
        order.write({"state": "confirmed"})
        run = self._runs(order)
        activity = run.activity_id
        self.assertFalse(activity.mc_employee_id)
        original_deadline = run.original_deadline
        activity.write({"mc_employee_id": self.empleado.id, "date_deadline": "2027-01-29"})
        order.action_repair_start()
        self.assertEqual(activity.mc_employee_id, self.empleado)
        self.assertEqual(activity.date_deadline.isoformat(), "2027-01-29")
        self.assertEqual(run.original_deadline, original_deadline)

    def test_failed_business_transaction_leaves_no_activity(self):
        self._policy()
        order = self._order()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            order.action_repair_start()
            self.assertEqual(len(self._runs(order)), 2)
            raise ValidationError("QA fallo posterior al inicio")
        order.invalidate_recordset()
        self.assertEqual(order.state, "draft")
        self.assertFalse(self._runs(order))
        self.assertFalse(order.activity_ids)
