from datetime import date, datetime

from odoo import Command
from odoo.tests.common import new_test_user

from .test_mc_rov_revision import RevisionCommon


class ManufacturingActivityCommon(RevisionCommon):
    """Fixtures sin tests: configuración explícita y órdenes nativas aisladas."""

    def _policy_model(self):
        self.assertIn(
            "mc.rov.manufacturing.activity.policy",
            self.env.registry.models,
            "Missing manufacturing activity policy",
        )
        return self.env["mc.rov.manufacturing.activity.policy"]

    def _run_model(self):
        self.assertIn(
            "mc.rov.manufacturing.activity.run",
            self.env.registry.models,
            "Missing manufacturing activity history",
        )
        return self.env["mc.rov.manufacturing.activity.run"]

    def _calendar(self, **values):
        return self.env["resource.calendar"].create(
            {
                "name": "QA fabricación días corridos",
                "company_id": self.env.company.id,
                "tz": "America/Santiago",
                "attendance_ids": [Command.clear()],
                **values,
            }
        )

    def _policy(self, calendar=None, **values):
        model = self._policy_model()
        user = new_test_user(
            self.env,
            login="qa_manufacturing_policy_taller",
            groups="mrp.group_mrp_user",
            company_id=self.env.company.id,
        )
        selected_calendar = self._calendar() if calendar is None else calendar
        configuration = {
            **model.default_get(["enabled", "lead_days"]),
            "user_id": user.id,
            "employee_id": False,
            "calendar_id": selected_calendar.id if selected_calendar else False,
            **values,
        }
        policy = model.search([("company_id", "=", self.env.company.id)], limit=1)
        if policy:
            policy.write(configuration)
            return policy
        return model.create({"company_id": self.env.company.id, **configuration})

    def _production(self, **values):
        return self.env["mrp.production"].create(
            {
                "product_id": self.product.id,
                "product_qty": 1.0,
                "product_uom_id": self.product.uom_id.id,
                "company_id": self.env.company.id,
                **values,
            }
        )

    def _runs(self, production):
        return self._run_model().search([("production_id", "=", production.id)])

    def _run(self, policy, production, **values):
        return self._run_model().create(
            {
                "company_id": self.env.company.id,
                "production_id": production.id,
                "cycle": 1,
                "started_at": datetime(2026, 10, 16, 15),
                "original_deadline": date(2026, 11, 13),
                "calendar_id": policy.calendar_id.id,
                "calendar_tz": policy.calendar_id.tz,
                **values,
            }
        )
