from datetime import date, datetime

import pytz
from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .manufacturing_activity_common import ManufacturingActivityCommon


@tagged("post_install", "-at_install")
class TestManufacturingActivityPolicy(ManufacturingActivityCommon):
    """Cuatro semanas comerciales son fechas corridas, no jornadas ni horas UTC."""

    def test_defaults_are_enabled_and_twenty_eight_days(self):
        policy = self._policy()
        self.assertTrue(policy.enabled)
        self.assertEqual(policy.lead_days, 28)

    def test_four_weeks_from_friday_include_weekends(self):
        policy = self._policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15)), date(2026, 11, 13))

    def test_utc_midnight_uses_previous_chilean_date(self):
        policy = self._policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 1)), date(2026, 11, 12))

    def test_daylight_change_keeps_twenty_eight_local_dates(self):
        policy = self._policy()
        self.assertEqual(policy._deadline(datetime(2026, 8, 22, 3, 30)), date(2026, 9, 18))

    def test_saturday_deadline_is_not_moved_to_monday(self):
        policy = self._policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 17, 15)), date(2026, 11, 14))

    def test_global_holiday_does_not_extend_calendar_days(self):
        policy = self._policy()
        zone = pytz.timezone(policy.calendar_id.tz)
        start = zone.localize(datetime(2026, 11, 13)).astimezone(pytz.utc).replace(tzinfo=None)
        stop = zone.localize(datetime(2026, 11, 14)).astimezone(pytz.utc).replace(tzinfo=None)
        self.env["resource.calendar.leaves"].create(
            {
                "name": "QA día sin trabajo",
                "calendar_id": policy.calendar_id.id,
                "company_id": self.env.company.id,
                "date_from": start,
                "date_to": stop,
                "resource_id": False,
            }
        )
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15)), date(2026, 11, 13))

    def test_earlier_explicit_deadline_wins(self):
        policy = self._policy()
        self.assertEqual(
            policy._deadline(datetime(2026, 10, 16, 15), datetime(2026, 10, 30, 15)),
            date(2026, 10, 30),
        )
        self.assertEqual(
            policy._deadline(datetime(2026, 10, 16, 15), datetime(2026, 10, 30, 1)),
            date(2026, 10, 29),
        )

    def test_later_explicit_deadline_does_not_extend_four_weeks(self):
        policy = self._policy()
        self.assertEqual(
            policy._deadline(datetime(2026, 10, 16, 15), datetime(2026, 11, 20, 15)),
            date(2026, 11, 13),
        )
        self.assertEqual(
            policy._deadline(datetime(2026, 10, 16, 15), datetime(2026, 11, 13, 15)),
            date(2026, 11, 13),
        )

    def test_past_deadline_is_not_shifted_to_today(self):
        policy = self._policy()
        self.assertEqual(
            policy._deadline(datetime(2026, 10, 16, 15), datetime(2026, 10, 10, 15)),
            date(2026, 10, 10),
        )

    def test_configurable_duration_and_invalid_range(self):
        policy = self._policy(lead_days=14)
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15)), date(2026, 10, 30))
        for days in (0, 366, True):
            with self.subTest(days=days), self.assertRaises(ValidationError), self.cr.savepoint():
                policy.write({"lead_days": days})

    def test_missing_start_or_calendar_does_not_invent_deadline(self):
        policy = self._policy()
        with self.assertRaises(ValidationError):
            policy._deadline(False)
        policy.calendar_id = False
        with self.assertRaises(ValidationError):
            policy._deadline(datetime(2026, 10, 16, 15))

    def test_calendar_without_working_hours_is_valid_for_calendar_days(self):
        policy = self._policy()
        self.assertFalse(policy.calendar_id.attendance_ids)
        self.assertFalse(policy._configuration_error(self._production()))

    def test_missing_or_archived_account_is_incomplete(self):
        policy = self._policy()
        production = self._production()
        user = policy.user_id
        policy.user_id = False
        self.assertTrue(policy._configuration_error(production))
        policy.user_id = user
        user.active = False
        self.assertTrue(policy._configuration_error(production))
        portal = new_test_user(
            self.env, login="qa_manufacturing_portal", groups="base.group_portal"
        )
        self.assertTrue(portal.share)
        policy.user_id = portal
        self.assertTrue(policy._configuration_error(production))

    def test_account_without_manufacturing_access_is_incomplete(self):
        policy = self._policy()
        policy.user_id = new_test_user(
            self.env, login="qa_no_manufacturing_access", groups="base.group_user"
        )
        self.assertTrue(policy._configuration_error(self._production()))

    def test_calendar_from_another_company_is_rejected(self):
        policy = self._policy()
        other = self.env["res.company"].create({"name": "QA calendario fabricación ajena"})
        calendar = self._calendar(company_id=other.id)
        with self.assertRaises(UserError), self.cr.savepoint():
            policy.calendar_id = calendar

    def test_policy_is_unique_for_each_company(self):
        policy = self._policy()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            policy.create({"company_id": self.env.company.id})

    def test_policy_is_under_followup_and_keeps_public_employee(self):
        model = self._policy_model()
        menu = self.env.ref("mc_rov.menu_manufacturing_activity_policy", raise_if_not_found=False)
        self.assertTrue(menu, "Missing manufacturing policy menu")
        self.assertEqual(menu.parent_id, self.env.ref("mc_rov.menu_work_automation"))
        self.assertEqual(model._fields["employee_id"].comodel_name, "hr.employee.public")

    def test_history_has_source_parent_deadline_and_outcome(self):
        model = self._run_model()
        fields = {
            "company_id",
            "production_id",
            "cycle",
            "parent_run_id",
            "activity_id",
            "started_at",
            "original_deadline",
            "calendar_id",
            "calendar_tz",
            "outcome",
            "finished_at",
            "finished_by_id",
            "finish_reason",
        }
        self.assertTrue(fields <= set(model._fields))
        self.assertEqual(model._fields["production_id"].ondelete, "restrict")
        self.assertEqual(model._fields["activity_id"].ondelete, "set null")
        self.assertEqual(model._fields["parent_run_id"].comodel_name, model._name)

    def test_history_is_unique_per_production_cycle(self):
        self._run_model()
        policy = self._policy()
        production = self._production()
        self._run(policy, production)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._run(policy, production)

    def test_history_is_not_readable_by_operational_account(self):
        model = self._run_model()
        user = new_test_user(
            self.env, login="qa_manufacturing_private_history", groups="mrp.group_mrp_user"
        )
        self.assertFalse(model.with_user(user).has_access("read"))
