from datetime import datetime

from odoo import Command
from odoo.tests.common import new_test_user

from .test_mc_rov_revision import RevisionCommon


class QualityActivityCommon(RevisionCommon):
    """Alertas y configuración propias del test, sin destinatarios ni etapas de ejemplo."""

    def _quality_model(self):
        self.assertIn(
            "mc.rov.quality.activity.policy",
            self.env.registry.models,
            "Missing quality activity policy",
        )
        return self.env["mc.rov.quality.activity.policy"]

    def _quality_calendar(self):
        return self.env["resource.calendar"].create(
            {
                "name": "QA Calidad lunes a viernes",
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

    def _quality_policy(self, **values):
        model = self._quality_model()
        user = new_test_user(
            self.env,
            login="qa_quality_policy_taller",
            groups="quality.group_quality_user,stock.group_stock_user",
        )
        data = {
            "enabled": True,
            "user_id": user.id,
            "employee_id": False,
            "calendar_id": self._quality_calendar().id,
            **values,
        }
        policy = model.search([("company_id", "=", self.env.company.id)], limit=1)
        if policy:
            policy.write(data)
            return policy
        return model.create({"company_id": self.env.company.id, **data})

    def _quality_alert(self, **values):
        self._quality_model()
        team = self.env["quality.alert.team"].create(
            {
                "name": "QA equipo Calidad",
                "company_id": values.get("company_id", self.env.company.id),
            }
        )
        stage = self.env["quality.alert.stage"].create(
            {"name": "QA abierta propia", "done": False}
        )
        return self.env["quality.alert"].create(
            {
                "name": "QA seguimiento Calidad",
                "product_id": self.product.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "team_id": team.id,
                "stage_id": stage.id,
                "company_id": self.env.company.id,
                **values,
            }
        )

    def _quality_service(self):
        self._quality_model()
        self.assertIn("mc.rov.quality.activity.automation", self.env.registry.models)
        return self.env["mc.rov.quality.activity.automation"]

    def _quality_run(self, policy, alert, **values):
        self.assertIn("mc.rov.quality.activity.run", self.env.registry.models)
        instant = datetime(2026, 10, 16, 15)
        deadline = policy._deadline(instant)
        return self.env["mc.rov.quality.activity.run"].create(
            {
                "company_id": alert.company_id.id,
                "alert_id": alert.id,
                "cycle": 1,
                "started_at": instant,
                "original_deadline": deadline,
                "current_deadline": deadline,
                "calendar_id": policy.calendar_id.id,
                "calendar_tz": policy.calendar_id.tz,
                **values,
            }
        )
