from datetime import date, datetime

import pytz
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .engineering_activity_common import EngineeringActivityCommon


@tagged("post_install", "-at_install")
class TestEngineeringNativeFixtures(EngineeringActivityCommon):
    """Contratos de PLM real que deben pasar incluso antes de añadir seguimiento."""

    def test_native_approval_creates_activity_and_blocks_advance(self):
        eco = self._eco()
        self.assertEqual(len(eco.approval_ids), 1)
        native_type = self.env.ref("mail.mail_activity_data_todo")
        activities = eco.activity_ids.filtered(
            lambda row: row.user_id == self.prepare_user and row.activity_type_id == native_type
        )
        self.assertEqual(len(activities), 1)
        self.assertFalse(eco.allow_change_stage)
        with self.assertRaises(UserError), self.cr.savepoint():
            eco.write({"stage_id": self.apply_stage.id})

    def test_native_approval_allows_stage_after_approve(self):
        eco = self._eco()
        eco.with_user(self.prepare_user).approve()
        self.assertEqual(eco.approval_ids.status, "approved")
        eco.write({"stage_id": self.apply_stage.id})
        self.assertEqual(eco.stage_id, self.apply_stage)
        self.assertTrue(eco.allow_apply_change)

    def test_native_rejection_keeps_advance_blocked(self):
        eco = self._eco()
        eco.with_user(self.prepare_user).reject()
        self.assertEqual(eco.approval_ids.status, "rejected")
        self.assertFalse(eco.allow_change_stage)
        with self.assertRaises(UserError), self.cr.savepoint():
            eco.write({"stage_id": self.apply_stage.id})


@tagged("post_install", "-at_install")
# Son contratos de configuración, aniversario y permisos independientes.
# pylint: disable=too-many-public-methods
class TestEngineeringActivityPolicy(EngineeringActivityCommon):
    """El plazo anual no cuenta días laborables ni reinicia por etapa."""

    def test_defaults_disabled_and_one_calendar_year(self):
        self.assertEqual(
            self._policy_model().default_get(["enabled", "lead_years"]),
            {"enabled": False, "lead_years": 1},
        )

    def test_boolean_years_rejected_on_create(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._policy_model().create({"lead_years": True})

    def test_boolean_years_rejected_on_write(self):
        policy = self._policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.write({"lead_years": True})
        self.assertEqual(policy.lead_years, 1)

    def test_fractional_years_rejected_on_create(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._policy_model().create({"lead_years": 1.5})

    def test_fractional_years_rejected_on_write(self):
        policy = self._policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.write({"lead_years": 1.5})
        self.assertEqual(policy.lead_years, 1)

    def test_zero_years_rejected(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._policy_model().create({"lead_years": 0})

    def test_negative_years_rejected(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._policy_model().create({"lead_years": -1})

    def test_policy_unique_per_company(self):
        policy = self._policy()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._policy_model().create({"company_id": policy.company_id.id})

    def test_anniversary_uses_calendar_year(self):
        self.assertEqual(self._policy()._deadline(datetime(2023, 3, 1, 15)), date(2024, 3, 1))

    def test_leap_day_uses_february_28_next_year(self):
        self.assertEqual(self._policy()._deadline(datetime(2024, 2, 29, 15)), date(2025, 2, 28))

    def test_local_creation_date_precedes_utc_date(self):
        self.assertEqual(self._policy()._deadline(datetime(2026, 10, 28, 1)), date(2027, 10, 27))

    def test_actor_timezone_does_not_replace_policy_timezone(self):
        policy = self._policy().with_context(tz="Asia/Tokyo")
        self.assertEqual(policy._deadline(datetime(2026, 10, 28, 1)), date(2027, 10, 27))

    def test_aware_datetime_preserves_instant(self):
        created = pytz.utc.localize(datetime(2026, 10, 28, 1))
        self.assertEqual(self._policy()._deadline(created), date(2027, 10, 27))

    def test_two_year_configuration_uses_anniversary(self):
        self.assertEqual(
            self._policy(lead_years=2)._deadline(datetime(2023, 3, 1, 15)), date(2025, 3, 1)
        )

    def test_missing_timezone_is_configuration_error(self):
        self.assertTrue(self._policy(tz=False)._configuration_error(self._eco(), "prepare"))

    def test_missing_prepare_account_is_configuration_error(self):
        policy = self._policy(prepare_user_id=False)
        self.assertTrue(policy._configuration_error(self._eco(), "prepare"))

    def test_missing_apply_account_is_configuration_error(self):
        policy = self._policy(apply_user_id=False)
        self.assertTrue(policy._configuration_error(self._eco(), "apply"))

    def test_inactive_account_is_configuration_error(self):
        policy = self._policy()
        self.prepare_user.active = False
        self.assertTrue(policy._configuration_error(self._eco(), "prepare"))

    def test_portal_account_is_configuration_error(self):
        self._policy_model()
        portal = new_test_user(self.env, login="qa_engineering_portal", groups="base.group_portal")
        policy = self._policy(prepare_user_id=portal.id)
        self.assertTrue(policy._configuration_error(self._eco(), "prepare"))

    def test_account_without_plm_access_is_configuration_error(self):
        policy = self._policy(prepare_user_id=self.outsider.id)
        self.assertTrue(policy._configuration_error(self._eco(), "prepare"))

    def test_eco_without_company_has_no_implicit_company(self):
        policy = self._policy()
        self.assertTrue(policy._configuration_error(self._eco(company_id=False), "prepare"))

    def test_other_company_does_not_expand_recipient_context(self):
        policy = self._policy()
        other = self._other_company()
        policy.company_id = other
        eco = self._eco(company_id=other.id)
        self.assertTrue(policy._configuration_error(eco, "prepare"))
        self.assertNotIn(other, self.prepare_user.company_ids)

    def test_valid_recipient_can_prepare_and_apply(self):
        policy = self._policy()
        eco = self._eco()
        self.assertFalse(policy._configuration_error(eco, "prepare"))
        self.assertFalse(policy._configuration_error(eco, "apply"))

    def test_archived_employee_is_configuration_error(self):
        policy = self._policy()
        employee = self.env["hr.employee"].create(
            {"name": "QA Ingeniería archivado", "company_id": self.env.company.id, "active": False}
        )
        policy.write({"prepare_employee_id": employee.id})
        self.assertTrue(policy._configuration_error(self._eco(), "prepare"))

    def test_non_coordinator_cannot_read_configuration(self):
        policy = self._policy()
        with self.assertRaises(AccessError):
            policy.with_user(self.prepare_user).read(["lead_years"])

    def test_coordinator_can_read_configuration(self):
        policy = self._policy()
        self.assertEqual(
            policy.with_user(self.coordinator).read(["lead_years"])[0]["lead_years"], 1
        )

    def test_cycle_history_has_no_public_access(self):
        self._policy_model()
        self.assertIn("mc.rov.engineering.activity.cycle", self.env.registry.models)
        with self.assertRaises(AccessError):
            self.env["mc.rov.engineering.activity.cycle"].with_user(self.prepare_user).search([])

    def test_run_history_has_no_public_access(self):
        self._policy_model()
        self.assertIn("mc.rov.engineering.activity.run", self.env.registry.models)
        with self.assertRaises(AccessError):
            self.env["mc.rov.engineering.activity.run"].with_user(self.prepare_user).search([])

    def test_policy_does_not_rewrite_company_calendar(self):
        self._policy_model()
        calendar = self.env.company.resource_calendar_id
        before = calendar.read(["tz", "attendance_ids", "write_date"])
        policy = self._policy()
        policy.write({"tz": "UTC", "lead_years": 2})
        self.assertEqual(calendar.read(["tz", "attendance_ids", "write_date"]), before)
