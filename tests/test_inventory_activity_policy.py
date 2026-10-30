"""Contratos de la política logística; fixtures nativos deben pasar durante RED."""

from datetime import date, datetime

import pytz
from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .inventory_activity_common import InventoryActivityCommon


@tagged("post_install", "-at_install")
class TestInventoryNativeFixtures(InventoryActivityCommon):
    """La existencia del producto nuevo no condiciona las operaciones de stock."""

    def test_native_three_operation_codes_confirm_and_cancel(self):
        for code in ("incoming", "outgoing", "internal"):
            picking = self._picking(code)
            self.assertEqual(picking.state, "draft")
            picking.with_user(self.operator).action_confirm()
            self.assertIn(picking.state, ("confirmed", "waiting", "assigned"))
            self.assertEqual(picking.picking_type_id.code, code)
            picking.with_user(self.operator).action_cancel()
            self.assertEqual(picking.state, "cancel")

    def test_native_other_company_operation_type(self):
        other = self._other_company()
        self.assertEqual(self._other_type(other).company_id, other)

    def test_existing_working_date_friday_excludes_event_day(self):
        self.assertEqual(
            self.env["mc.rov.work.deadline"]._working_date(
                self.calendar, self.env.company, datetime(2026, 10, 30, 15), 3
            ),
            date(2026, 11, 4),
        )

    def test_existing_working_date_respects_calendar_exception(self):
        self._holiday()
        self.assertEqual(
            self.env["mc.rov.work.deadline"]._working_date(
                self.calendar, self.env.company, datetime(2026, 10, 30, 15), 3
            ),
            date(2026, 11, 5),
        )


@tagged("post_install", "-at_install")
# Cada frontera es un contrato independiente, no una variación de la implementación.
# pylint: disable=too-many-public-methods
class TestInventoryActivityPolicy(InventoryActivityCommon):
    """Tres días laborables desde el ancla inicial, sin ampliar permisos ni compromisos."""

    def test_defaults_disabled_and_three_working_days(self):
        self.assertEqual(
            self._policy_model().default_get(["enabled", "lead_days"]),
            {"enabled": False, "lead_days": 3},
        )

    def test_boolean_duration_rejected_on_create(self):
        model = self._policy_model()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            model.create({"lead_days": True})

    def test_boolean_duration_rejected_on_write(self):
        policy = self._policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.write({"lead_days": True})

    def test_fraction_duration_rejected_on_create(self):
        model = self._policy_model()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            model.create({"lead_days": 1.5})

    def test_fraction_duration_rejected_on_write(self):
        policy = self._policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.write({"lead_days": 1.5})

    def test_zero_negative_and_366_rejected(self):
        model = self._policy_model()
        for value in (0, -1, 366):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                model.create({"lead_days": value})

    def test_maximum_365_can_be_configured(self):
        self.assertEqual(self._policy(lead_days=365).lead_days, 365)

    def test_policy_unique_per_company(self):
        policy = self._policy()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._policy_model().create({"company_id": policy.company_id.id})

    def test_rule_unique_per_policy_and_operation_type(self):
        policy = self._policy()
        self._rule(policy=policy)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._rule(policy=policy)

    def test_friday_confirmation_uses_next_three_working_days(self):
        self.assertEqual(self._policy()._deadline(datetime(2026, 10, 30, 15)), date(2026, 11, 4))

    def test_future_schedule_is_initial_anchor(self):
        self.assertEqual(
            self._policy()._deadline(datetime(2026, 10, 30, 15), datetime(2026, 11, 5, 15)),
            date(2026, 11, 10),
        )

    def test_past_schedule_does_not_precede_confirmation_anchor(self):
        self.assertEqual(
            self._policy()._deadline(datetime(2026, 10, 30, 15), datetime(2026, 10, 29, 15)),
            date(2026, 11, 4),
        )

    def test_same_day_schedule_does_not_count_event_day(self):
        self.assertEqual(
            self._policy()._deadline(datetime(2026, 10, 30, 15), datetime(2026, 10, 30, 18)),
            date(2026, 11, 4),
        )

    def test_calendar_exception_skips_monday(self):
        policy = self._policy()
        self._holiday()
        self.assertEqual(policy._deadline(datetime(2026, 10, 30, 15)), date(2026, 11, 5))

    def test_dst_weekend_uses_local_working_dates(self):
        self.assertEqual(self._policy()._deadline(datetime(2026, 9, 4, 15)), date(2026, 9, 9))

    def test_actor_timezone_does_not_replace_calendar_timezone(self):
        self.assertEqual(
            self._policy().with_context(tz="Asia/Tokyo")._deadline(datetime(2026, 10, 30, 15)),
            date(2026, 11, 4),
        )

    def test_aware_confirmation_preserves_instant(self):
        self.assertEqual(
            self._policy()._deadline(pytz.utc.localize(datetime(2026, 10, 30, 15))),
            date(2026, 11, 4),
        )

    def test_aware_future_schedule_preserves_instant(self):
        self.assertEqual(
            self._policy()._deadline(
                datetime(2026, 10, 30, 15), pytz.utc.localize(datetime(2026, 11, 5, 15))
            ),
            date(2026, 11, 10),
        )

    def test_earlier_native_deadline_is_preserved(self):
        self.assertEqual(
            self._policy()._deadline(datetime(2026, 10, 30, 15), False, datetime(2026, 11, 3, 15)),
            date(2026, 11, 3),
        )

    def test_overdue_native_deadline_is_not_extended(self):
        self.assertEqual(
            self._policy()._deadline(
                datetime(2026, 10, 30, 15), False, datetime(2026, 10, 29, 15)
            ),
            date(2026, 10, 29),
        )

    def test_later_native_deadline_does_not_extend_three_days(self):
        self.assertEqual(
            self._policy()._deadline(
                datetime(2026, 10, 30, 15), False, datetime(2026, 11, 20, 15)
            ),
            date(2026, 11, 4),
        )

    def test_native_deadline_uses_calendar_local_date(self):
        self.assertEqual(
            self._policy()._deadline(datetime(2026, 10, 30, 15), False, datetime(2026, 11, 4, 1)),
            date(2026, 11, 3),
        )

    def test_rule_matches_only_selected_type(self):
        policy = self._policy()
        rule = self._rule(policy=policy)
        self.assertEqual(policy._rule_for(self._picking()), rule)
        self.assertFalse(policy._rule_for(self._picking("outgoing")))

    def test_selected_types_include_components_outside_rov_category(self):
        policy, picking = self._configured()
        self.assertEqual(picking.move_ids.product_id, self.product)
        self.assertFalse(policy._configuration_error(picking))

    def test_missing_rule_is_configuration_error(self):
        self.assertTrue(self._policy()._configuration_error(self._picking()))

    def test_missing_account_is_configuration_error(self):
        policy = self._policy()
        self._rule(policy=policy, user_id=False)
        self.assertTrue(policy._configuration_error(self._picking()))

    def test_inactive_account_is_configuration_error(self):
        policy, picking = self._configured()
        self.operator.active = False
        self.assertTrue(policy._configuration_error(picking))

    def test_portal_account_is_configuration_error(self):
        policy = self._policy()
        portal = new_test_user(self.env, login="qa_inventory_portal", groups="base.group_portal")
        self._rule(policy=policy, user_id=portal.id)
        self.assertTrue(policy._configuration_error(self._picking()))

    def test_account_without_stock_access_is_configuration_error(self):
        policy = self._policy()
        self._rule(policy=policy, user_id=self.outsider.id)
        self.assertTrue(policy._configuration_error(self._picking()))

    def test_recipient_specific_record_denial_is_respected(self):
        policy, picking = self._configured()
        self.env["ir.rule"].create(
            {
                "name": "QA denegar solo al destinatario",
                "model_id": self.env["ir.model"]._get_id("stock.picking"),
                "domain_force": f"[('id', '!=', {picking.id})] if user.id == {self.operator.id} else [(1, '=', 1)]",
            }
        )
        self.assertTrue(picking.has_access("read"))
        self.assertFalse(picking.with_user(self.operator).has_access("read"))
        self.assertTrue(policy._configuration_error(picking))

    def test_other_company_operation_type_rejected(self):
        policy = self._policy()
        kind = self._other_type(self._other_company())
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._rule(kind, policy=policy)

    def test_recipient_context_does_not_expand_companies(self):
        policy, picking = self._configured()
        other = self._other_company()
        self.operator.write({"company_id": other.id, "company_ids": [Command.set(other.ids)]})
        self.assertTrue(policy._configuration_error(picking))
        self.assertNotIn(policy.company_id, self.operator.company_ids)

    def test_missing_calendar_is_configuration_error(self):
        policy, picking = self._configured(calendar_id=False)
        self.assertTrue(policy._configuration_error(picking))

    def test_empty_calendar_is_configuration_error(self):
        policy, picking = self._configured()
        self.calendar.attendance_ids.unlink()
        self.assertTrue(policy._configuration_error(picking))

    def test_other_company_calendar_rejected(self):
        self._policy_model()
        other = self._other_company()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._policy(calendar_id=other.resource_calendar_id.id)

    def test_other_company_employee_rejected(self):
        policy = self._policy()
        other = self._other_company()
        employee = self.env["hr.employee"].create(
            {
                "name": "QA Empleado otra empresa",
                "company_id": other.id,
            }
        )
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._rule(policy=policy, employee_id=employee.id)

    def test_archived_employee_is_configuration_error(self):
        policy = self._policy()
        employee = self.env["hr.employee"].create(
            {
                "name": "QA Inventario archivado",
                "company_id": self.env.company.id,
                "active": False,
            }
        )
        self._rule(policy=policy, employee_id=employee.id)
        self.assertTrue(policy._configuration_error(self._picking()))

    def test_operator_cannot_read_policy_configuration(self):
        policy = self._policy()
        with self.assertRaises(AccessError):
            policy.with_user(self.operator).read(["lead_days"])

    def test_operator_cannot_read_rule_configuration(self):
        rule = self._rule(policy=self._policy())
        with self.assertRaises(AccessError):
            rule.with_user(self.operator).read(["user_id"])

    def test_coordinator_can_read_policy_and_rule(self):
        policy = self._policy()
        rule = self._rule(policy=policy)
        self.assertEqual(policy.with_user(self.coordinator).read(["lead_days"])[0]["lead_days"], 3)
        self.assertEqual(
            rule.with_user(self.coordinator).read(["user_id"])[0]["user_id"][0], self.operator.id
        )

    def test_cycle_history_has_no_public_access(self):
        self._policy_model()
        self.assertIn("mc.rov.inventory.activity.cycle", self.env.registry.models)
        with self.assertRaises(AccessError):
            self.env["mc.rov.inventory.activity.cycle"].with_user(self.operator).search([])

    def test_run_history_has_no_public_access(self):
        self._policy_model()
        self.assertIn("mc.rov.inventory.activity.run", self.env.registry.models)
        with self.assertRaises(AccessError):
            self.env["mc.rov.inventory.activity.run"].with_user(self.operator).search([])

    def test_policy_does_not_rewrite_existing_company_calendar(self):
        self._policy_model()
        calendar = self.env.company.resource_calendar_id
        before = calendar.read(["tz", "attendance_ids", "write_date"])
        policy = self._policy()
        policy.write({"lead_days": 4})
        self.assertEqual(calendar.read(["tz", "attendance_ids", "write_date"]), before)
