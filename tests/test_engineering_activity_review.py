from odoo.tests import tagged

from .engineering_activity_common import EngineeringActivityCommon
from .test_engineering_activity_events import _advance_native


@tagged("post_install", "-at_install")
class TestEngineeringActivityReview(EngineeringActivityCommon):
    """El cierre conserva enlaces a actividades que Odoo archiva en vez de borrar."""

    def _visit(self):
        controls = self.env["mc.rov.automation.control"]
        control = controls.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = True
        else:
            controls.create({"company_id": self.env.company.id, "enabled": True})
        self._policy()
        eco = self._eco()
        runs = self.env["mc.rov.engineering.activity.run"].search([("eco_id", "=", eco.id)])
        self.assertEqual(len(runs), 1)
        return eco, runs

    def _assert_no_orphans(self, eco):
        runs = self.env["mc.rov.engineering.activity.run"].search([("eco_id", "=", eco.id)])
        types = self.env.ref("mc_rov.activity_type_engineering_prepare") | self.env.ref(
            "mc_rov.activity_type_engineering_apply"
        )
        activities = (
            self.env["mail.activity"]
            .with_context(active_test=False)
            .search(
                [
                    ("res_model", "=", "mrp.eco"),
                    ("res_id", "=", eco.id),
                    ("activity_type_id", "in", types.ids),
                ]
            )
        )
        self.assertEqual(set(activities.ids), set(runs.activity_id.ids))

    def test_preparation_completion_keeps_archived_activity_link(self):
        eco, run = self._visit()
        activity = run.activity_id
        _advance_native(self, eco)
        self.assertEqual(run.outcome, "business_done")
        self.assertEqual(run.activity_id, activity.exists())
        self.assertFalse(activity.exists().active)
        self._assert_no_orphans(eco)

    def test_application_completion_keeps_archived_activity_link(self):
        eco, _run = self._visit()
        _advance_native(self, eco)
        run = self.env["mc.rov.engineering.activity.run"].search(
            [
                ("eco_id", "=", eco.id),
                ("stage", "=", "apply"),
            ]
        )
        self.assertEqual(len(run), 1)
        activity = run.activity_id
        eco.action_apply()
        self.assertEqual(run.outcome, "business_done")
        self.assertEqual(run.activity_id, activity.exists())
        self.assertFalse(activity.exists().active)
        self._assert_no_orphans(eco)
