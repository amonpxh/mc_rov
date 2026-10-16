from datetime import date, datetime

import pytz
from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .test_mc_rov_revision import RevisionCommon


@tagged("post_install", "-at_install")
class TestAcceptanceActivityPolicy(RevisionCommon):
    """Un día de taller por etapa, con cuenta y calendario explícitos."""

    def _model(self):
        self.assertIn(
            "mc.rov.acceptance.activity.policy",
            self.env.registry.models,
            "Missing acceptance activity policy",
        )
        return self.env["mc.rov.acceptance.activity.policy"]

    def _calendar(self):
        return self.env["resource.calendar"].create(
            {
                "name": "QA aceptación lunes a viernes",
                "tz": "America/Santiago",
                "company_id": self.env.company.id,
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

    def _policy(self, **values):
        model = self._model()
        user = new_test_user(
            self.env, login="qa_acceptance_policy_taller", groups="stock.group_stock_user"
        )
        configuration = {
            "enabled": True,
            "user_id": user.id,
            "employee_id": False,
            "calendar_id": self._calendar().id,
            **values,
        }
        policy = model.search([("company_id", "=", self.env.company.id)], limit=1)
        if policy:
            policy.write(configuration)
            return policy
        return model.create({"company_id": self.env.company.id, **configuration})

    def test_defaults_enabled_and_one_working_day_per_stage(self):
        policy = self._policy()
        self.assertTrue(policy.enabled)
        self.assertEqual(
            (policy.performance_days, policy.field_days, policy.rejection_days, policy.fen_days),
            (1, 1, 1, 1),
        )

    def test_friday_one_day_is_monday(self):
        policy = self._policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15), 1), date(2026, 10, 19))

    def test_utc_saturday_still_counts_from_chilean_friday(self):
        policy = self._policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 17, 1), 1), date(2026, 10, 19))

    def test_registered_holiday_is_excluded(self):
        policy = self._policy()
        zone = pytz.timezone(policy.calendar_id.tz)
        self.env["resource.calendar.leaves"].create(
            {
                "name": "QA feriado",
                "calendar_id": policy.calendar_id.id,
                "company_id": self.env.company.id,
                "resource_id": False,
                "date_from": zone.localize(datetime(2026, 10, 19))
                .astimezone(pytz.utc)
                .replace(tzinfo=None),
                "date_to": zone.localize(datetime(2026, 10, 20))
                .astimezone(pytz.utc)
                .replace(tzinfo=None),
            }
        )
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15), 1), date(2026, 10, 20))

    def test_empty_calendar_reports_incomplete_and_cannot_invent_deadline(self):
        policy = self._policy()
        policy.calendar_id.attendance_ids.unlink()
        self.assertTrue(policy._configuration_error(self.lot))
        with self.assertRaises(ValidationError):
            policy._deadline(datetime(2026, 10, 16, 15), 1)

    def test_flexible_calendar_cannot_invent_working_dates(self):
        policy = self._policy()
        policy.calendar_id.flexible_hours = True
        self.assertTrue(policy._configuration_error(self.lot))
        with self.assertRaises(ValidationError):
            policy._deadline(datetime(2026, 10, 16, 15), 1)

    def test_boolean_is_not_a_duration(self):
        policy = self._policy()
        for field in ("performance_days", "field_days", "rejection_days", "fen_days"):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                policy.write({field: True})

    def test_zero_duration_is_rejected(self):
        policy = self._policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.write({"performance_days": 0})

    def test_duration_above_year_is_rejected(self):
        policy = self._policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.write({"fen_days": 366})

    def test_stage_durations_can_be_configured_independently(self):
        policy = self._policy(field_days=2, rejection_days=3, fen_days=4)
        self.assertEqual(
            (policy.performance_days, policy.field_days, policy.rejection_days, policy.fen_days),
            (1, 2, 3, 4),
        )

    def test_company_policy_is_unique(self):
        policy = self._policy()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._model().create({"company_id": policy.company_id.id})

    def test_missing_account_reports_incomplete(self):
        policy = self._policy(user_id=False)
        self.assertTrue(policy._configuration_error(self.lot))

    def test_archived_account_reports_incomplete(self):
        policy = self._policy()
        user = new_test_user(
            self.env, login="qa_acceptance_archived", groups="stock.group_stock_user"
        )
        policy.user_id = user
        user.active = False
        self.assertTrue(policy._configuration_error(self.lot))

    def test_calendar_company_cannot_be_replaced_by_another(self):
        policy = self._policy()
        other = self.env["res.company"].create({"name": "QA otra empresa aceptación"})
        calendar = self._calendar()
        calendar.company_id = other
        with self.assertRaises(UserError), self.cr.savepoint():
            policy.calendar_id = calendar

    def test_person_without_login_is_supported(self):
        policy = self._policy(employee_id=self.empleado.id)
        self.assertFalse(self.empleado.user_id)
        self.assertFalse(policy._configuration_error(self.lot))
        self.assertEqual(policy._fields["employee_id"].comodel_name, "hr.employee.public")

    def test_workshop_user_cannot_read_configuration(self):
        policy = self._policy()
        user = new_test_user(
            self.env, login="qa_acceptance_operator", groups="stock.group_stock_user"
        )
        with self.assertRaises(AccessError):
            policy.with_user(user).read(["user_id", "calendar_id"])

    def test_coordinator_can_manage_configuration(self):
        policy = self._policy()
        user = new_test_user(
            self.env,
            login="qa_acceptance_coordinator",
            groups="stock.group_stock_user,mc_rov.group_work_assignment_coordinate",
        )
        policy.with_user(user).write({"fen_days": 2})
        self.assertEqual(policy.fen_days, 2)

    def test_shared_deadline_service_matches_policy(self):
        policy = self._policy()
        self.assertIn("mc.rov.work.deadline", self.env.registry.models)
        instant = datetime(2026, 10, 16, 15)
        expected = self.env["mc.rov.work.deadline"]._working_date(
            policy.calendar_id, policy.company_id, instant, 1
        )
        self.assertEqual(expected, policy._deadline(instant, 1))
