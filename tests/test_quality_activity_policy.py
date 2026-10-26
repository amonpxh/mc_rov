from datetime import date, datetime
from unittest.mock import patch

import pytz
from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .quality_activity_common import QualityActivityCommon


@tagged("post_install", "-at_install")
# Calendario, destinatario, privacidad y alcance son contratos independientes.
# pylint: disable=too-many-public-methods
class TestQualityActivityPolicy(QualityActivityCommon):
    """Calidad usa un día laboral propio y no depende de un ciclo de aceptación."""

    def _quality_alert(self, **values):
        # Estos casos prueban configuración e historial aislados del evento de creación;
        # los eventos reales se ejercitan por separado en la suite de ciclo de vida.
        service = self._quality_service()
        with patch.object(type(service), "_start", return_value=False, create=True):
            return super()._quality_alert(**values)

    def _other_company(self):
        with patch.object(
            type(self.env["res.company"]), "_create_internal_project_task", create=True
        ):
            return self.env["res.company"].create({"name": "QA otra empresa Calidad"})

    def test_defaults_enabled_with_one_working_day(self):
        model = self._quality_model()
        self.assertEqual(
            model.default_get(["enabled", "lead_days"]), {"enabled": True, "lead_days": 1}
        )

    def test_policy_is_unique_per_company(self):
        policy = self._quality_policy()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._quality_model().create({"company_id": policy.company_id.id})

    def test_boolean_duration_is_rejected_before_integer_conversion(self):
        policy = self._quality_policy()
        # La asignación al campo normaliza True a 1 antes de llamar a write.
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.write({"lead_days": True})
        self.assertEqual(policy.lead_days, 1)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._quality_model().create({"company_id": policy.company_id.id, "lead_days": True})

    def test_fractional_duration_is_rejected(self):
        policy = self._quality_policy()
        # Enviar el valor original; el descriptor Integer convertiría 1.5 a 1.
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.write({"lead_days": 1.5})
        self.assertEqual(policy.lead_days, 1)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._quality_model().create({"company_id": policy.company_id.id, "lead_days": 1.5})

    def test_zero_duration_is_rejected(self):
        policy = self._quality_policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.lead_days = 0

    def test_negative_duration_is_rejected(self):
        policy = self._quality_policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.lead_days = -1

    def test_duration_above_year_is_rejected(self):
        policy = self._quality_policy()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            policy.lead_days = 366

    def test_friday_deadline_is_monday(self):
        policy = self._quality_policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15)), date(2026, 10, 19))

    def test_utc_saturday_still_uses_chilean_friday(self):
        policy = self._quality_policy()
        self.assertEqual(policy._deadline(datetime(2026, 10, 17, 1)), date(2026, 10, 19))

    def test_registered_holiday_is_excluded(self):
        policy = self._quality_policy()
        zone = pytz.timezone(policy.calendar_id.tz)
        self.env["resource.calendar.leaves"].create(
            {
                "name": "QA feriado Calidad",
                "calendar_id": policy.calendar_id.id,
                "company_id": policy.company_id.id,
                "date_from": zone.localize(datetime(2026, 10, 19))
                .astimezone(pytz.utc)
                .replace(tzinfo=None),
                "date_to": zone.localize(datetime(2026, 10, 20))
                .astimezone(pytz.utc)
                .replace(tzinfo=None),
            }
        )
        self.assertEqual(policy._deadline(datetime(2026, 10, 16, 15)), date(2026, 10, 20))

    def test_empty_calendar_reports_incomplete(self):
        policy = self._quality_policy()
        policy.calendar_id.attendance_ids.unlink()
        self.assertTrue(policy._configuration_error(self._quality_alert()))
        with self.assertRaises(ValidationError):
            policy._deadline(datetime(2026, 10, 16, 15))

    def test_flexible_calendar_reports_incomplete(self):
        policy = self._quality_policy()
        policy.calendar_id.flexible_hours = True
        self.assertTrue(policy._configuration_error(self._quality_alert()))
        with self.assertRaises(ValidationError):
            policy._deadline(datetime(2026, 10, 16, 15))

    def test_foreign_calendar_is_rejected(self):
        policy = self._quality_policy()
        other = self._other_company()
        calendar = self._quality_calendar()
        calendar.company_id = other
        with self.assertRaises(UserError), self.cr.savepoint():
            policy.calendar_id = calendar

    def test_missing_account_is_not_inferred_from_actor(self):
        policy = self._quality_policy(user_id=False)
        self.assertTrue(policy._configuration_error(self._quality_alert()))

    def test_archived_account_reports_incomplete(self):
        policy = self._quality_policy()
        policy.user_id.active = False
        self.assertTrue(policy._configuration_error(self._quality_alert()))

    def test_recipient_in_another_company_does_not_expand_access(self):
        policy = self._quality_policy()
        other = self._other_company()
        user = new_test_user(
            self.env,
            login="qa_quality_foreign_recipient",
            groups="quality.group_quality_user",
            company_id=other.id,
            company_ids=[Command.set(other.ids)],
        )
        policy.user_id = user
        self.assertTrue(policy._configuration_error(self._quality_alert()))
        self.assertEqual(user.company_ids, other)

    def test_recipient_without_origin_permission_reports_incomplete(self):
        policy = self._quality_policy()
        alert = self._quality_alert()
        self.env["ir.rule"].create(
            {
                "name": "QA alerta no accesible",
                "model_id": self.env["ir.model"]._get_id("quality.alert"),
                "domain_force": repr([("id", "!=", alert.id)]),
            }
        )
        self.env.invalidate_all()
        self.assertTrue(policy._configuration_error(alert))

    def test_employee_without_login_uses_public_directory(self):
        policy = self._quality_policy(employee_id=self.empleado.id)
        self.assertEqual(policy._fields["employee_id"].comodel_name, "hr.employee.public")
        self.assertFalse(self.empleado.user_id)
        self.assertFalse(policy._configuration_error(self._quality_alert()))

    def test_workshop_cannot_read_policy(self):
        policy = self._quality_policy()
        with self.assertRaises(AccessError):
            policy.with_user(policy.user_id).read(["user_id", "calendar_id"])

    def test_coordinator_can_configure_policy(self):
        policy = self._quality_policy()
        policy.user_id.group_ids = [
            Command.link(self.env.ref("mc_rov.group_work_assignment_coordinate").id)
        ]
        policy.with_user(policy.user_id).write({"lead_days": 2})
        self.assertEqual(policy.lead_days, 2)

    def test_policy_cannot_be_read_in_inactive_company(self):
        policy = self._quality_policy()
        other = self._other_company()
        user = new_test_user(
            self.env,
            login="qa_quality_other_coordinator",
            groups="quality.group_quality_user,mc_rov.group_work_assignment_coordinate",
            company_id=other.id,
            company_ids=[Command.set(other.ids)],
        )
        with self.assertRaises(AccessError):
            policy.with_user(user).with_context(allowed_company_ids=other.ids).read(["lead_days"])

    def test_private_run_preserves_calendar_deadline_and_unique_cycle(self):
        policy = self._quality_policy()
        alert = self._quality_alert()
        run = self._quality_run(policy, alert)
        self.assertEqual(run.outcome, "pending")
        self.assertEqual(run.calendar_tz, "America/Santiago")
        self.assertEqual(run.original_deadline, date(2026, 10, 19))
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._quality_run(policy, alert)
        with self.assertRaises(AccessError):
            run.with_user(policy.user_id).read(["alert_id", "finished_by_id"])

    def test_shared_deadline_service_matches_policy(self):
        policy = self._quality_policy(lead_days=2)
        instant = datetime(2026, 10, 16, 15)
        self.assertEqual(
            policy._deadline(instant),
            self.env["mc.rov.work.deadline"]._working_date(
                policy.calendar_id, policy.company_id, instant, 2
            ),
        )

    def test_scope_includes_rov_product(self):
        service = self._quality_service()
        self.assertTrue(service._in_scope(self._quality_alert()))

    def test_scope_includes_explicit_rov_series(self):
        service = self._quality_service()
        self.assertTrue(
            service._in_scope(
                self._quality_alert(
                    product_id=False, product_tmpl_id=False, lot_ids=[Command.set(self.lot.ids)]
                )
            )
        )

    def test_scope_includes_rov_template_without_variant(self):
        service = self._quality_service()
        self.assertTrue(service._in_scope(self._quality_alert(product_id=False)))

    def test_scope_uses_explicit_manufacturing_equipment(self):
        service = self._quality_service()
        production = self.env["mrp.production"].create(
            {
                "product_id": self.product.id,
                "product_qty": 1,
                "product_uom_id": self.product.uom_id.id,
                "company_id": self.env.company.id,
            }
        )
        self.assertTrue(
            service._in_scope(
                self._quality_alert(
                    product_id=False, product_tmpl_id=False, production_id=production.id
                )
            )
        )

    def test_scope_uses_explicit_repair_equipment(self):
        service = self._quality_service()
        repair = self.env["repair.order"].create(
            {
                "product_id": self.product.id,
                "lot_id": self.lot.id,
                "company_id": self.env.company.id,
            }
        )
        self.assertTrue(
            service._in_scope(
                self._quality_alert(product_id=False, product_tmpl_id=False, repair_id=repair.id)
            )
        )

    def test_scope_excludes_component_without_explicit_equipment(self):
        service = self._quality_service()
        category = self.env["product.category"].create({"name": "QA componentes fuera de ROV"})
        product = self.env["product.product"].create(
            {"name": "QA componente", "categ_id": category.id}
        )
        self.assertFalse(
            service._in_scope(
                self._quality_alert(
                    product_id=product.id, product_tmpl_id=product.product_tmpl_id.id
                )
            )
        )

    def test_scope_does_not_read_foreign_alert_via_sudo(self):
        policy = self._quality_policy()
        company = self._other_company()
        alert = self._quality_alert(company_id=company.id)
        with self.assertRaises(AccessError):
            self._quality_service().with_user(policy.user_id).with_context(
                allowed_company_ids=self.env.company.ids
            )._in_scope(alert)

    def test_native_activity_type_has_quality_alert_origin_and_no_successor(self):
        self._quality_model()
        kind = self.env.ref("mc_rov.activity_type_quality_resolution")
        self.assertEqual(kind.res_model, "quality.alert")
        self.assertFalse(kind.triggered_next_type_id)
