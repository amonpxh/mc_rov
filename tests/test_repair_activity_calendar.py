from datetime import date, datetime

import pytz

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestRepairActivityCalendar(TransactionCase):
    """Plazos por fechas laborables locales, independientes de horas o franjas."""

    def _calendar(self, days=range(5), split=False, two_weeks=False):
        entries = []
        for day in days:
            for week in ["0", "1"] if two_weeks else [False]:
                for start, stop, period in (
                    [(8, 12, "morning"), (13, 17, "afternoon")] if split else [(8, 17, "morning")]
                ):
                    entries.append(
                        Command.create(
                            {
                                "name": "QA jornada",
                                "dayofweek": str(day),
                                "hour_from": start,
                                "hour_to": stop,
                                "day_period": period,
                                "week_type": week,
                            }
                        )
                    )
        return self.env["resource.calendar"].create(
            {
                "name": "QA calendario del piloto",
                "tz": "America/Santiago",
                "company_id": self.env.company.id,
                "two_weeks_calendar": two_weeks,
                "attendance_ids": [Command.clear(), *entries],
            }
        )

    def _policy(self, calendar=None, **values):
        self.assertIn(
            "mc.rov.repair.activity.policy",
            self.env.registry.models,
            "Missing repair activity policy and deadline service",
        )
        return self.env["mc.rov.repair.activity.policy"].create(
            {
                "company_id": self.env.company.id,
                "calendar_id": (calendar or self._calendar()).id,
                "user_id": self.env.user.id,
                **values,
            }
        )

    def _leave(self, calendar, start, end):
        zone = pytz.timezone(calendar.tz)
        return self.env["resource.calendar.leaves"].create(
            {
                "name": "QA ausencia global",
                "calendar_id": calendar.id,
                "company_id": self.env.company.id,
                "resource_id": False,
                "date_from": zone.localize(start).astimezone(pytz.utc).replace(tzinfo=None),
                "date_to": zone.localize(end).astimezone(pytz.utc).replace(tzinfo=None),
            }
        )

    def test_default_enabled_and_two_days_each(self):
        policy = self._policy()
        self.assertTrue(policy.enabled)
        self.assertEqual((policy.diagnosis_days, policy.repair_days), (2, 2))

    def test_monday_excludes_event_day(self):
        policy = self._policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 19, 15), 2), date(2026, 10, 21))

    def test_friday_skips_weekend(self):
        policy = self._policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15), 2), date(2026, 10, 20))

    def test_utc_saturday_is_still_friday_in_chile(self):
        policy = self._policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 17, 1), 2), date(2026, 10, 20))

    def test_full_day_global_absence_is_excluded(self):
        policy = self._policy()
        self._leave(policy.calendar_id, datetime(2026, 10, 19), datetime(2026, 10, 20))
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15), 2), date(2026, 10, 21))

    def test_partial_absence_still_counts_working_day(self):
        policy = self._policy()
        self._leave(policy.calendar_id, datetime(2026, 10, 19, 8), datetime(2026, 10, 19, 12))
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15), 2), date(2026, 10, 20))

    def test_two_shifts_count_once(self):
        policy = self._policy(calendar=self._calendar(split=True))
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15), 2), date(2026, 10, 20))

    def test_alternate_week_attendances_are_respected(self):
        policy = self._policy(calendar=self._calendar(two_weeks=True))
        # Remove the week's Monday in the native parity of the event week.
        attendance = policy.calendar_id.attendance_ids
        week = self.env["resource.calendar.attendance"].get_week_type(date(2026, 10, 19))
        attendance.filtered(
            lambda line: line.dayofweek == "0" and line.week_type == str(week)
        ).unlink()
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15), 2), date(2026, 10, 21))

    def test_empty_calendar_does_not_invent_deadline(self):
        policy = self._policy()
        policy.calendar_id.attendance_ids.unlink()
        with self.assertRaises(ValidationError):
            policy._deadline(datetime(2026, 10, 16, 15), 2)

    def test_flexible_calendar_does_not_invent_days(self):
        policy = self._policy()
        policy.calendar_id.flexible_hours = True
        with self.assertRaises(ValidationError):
            policy._deadline(datetime(2026, 10, 16, 15), 2)

    def test_nonpositive_duration_is_rejected(self):
        policy = self._policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.write({"diagnosis_days": 0})

    def test_archived_account_reports_incomplete_configuration(self):
        policy = self._policy()
        user = new_test_user(
            self.env, login="qa_repair_deadline_user", groups="stock.group_stock_user"
        )
        policy.user_id = user
        user.active = False
        order = self.env["repair.order"].create({"company_id": self.env.company.id})
        self.assertTrue(policy._configuration_error(order))

    def test_missing_account_reports_incomplete_configuration(self):
        policy = self._policy(user_id=False)
        order = self.env["repair.order"].create({"company_id": self.env.company.id})
        self.assertTrue(policy._configuration_error(order))

    def test_calendar_of_another_company_is_rejected(self):
        policy = self._policy()
        other = self.env["res.company"].create({"name": "QA calendario otra empresa"})
        calendar = self._calendar()
        calendar.company_id = other
        with self.assertRaises(UserError), self.cr.savepoint():
            policy.calendar_id = calendar
