from odoo.exceptions import UserError
from odoo.tests import tagged

from .quality_activity_common import QualityActivityCommon


@tagged("post_install", "-at_install")
class TestQualityActivityReview(QualityActivityCommon):
    """La orden explícita también forma parte del origen de una alerta seguida."""

    def _origin(self, field, component=False):
        product = self.product
        if component:
            category = self.env["product.category"].create({"name": "QA componente fuera de ROV"})
            product = self.env["product.product"].create(
                {"name": "QA componente", "categ_id": category.id}
            )
        values = {"product_id": product.id, "company_id": self.env.company.id}
        if field == "production_id":
            values.update(product_qty=1, product_uom_id=product.uom_id.id)
            return self.env["mrp.production"].create(values)
        if not component:
            values["lot_id"] = self.lot.id
        return self.env["repair.order"].create(values)

    def _follow(self, field):
        self._quality_policy()
        controls = self.env["mc.rov.automation.control"]
        control = controls.search([("company_id", "=", self.env.company.id)], limit=1)
        if control:
            control.enabled = True
        origin = self._origin(field)
        alert = self._quality_alert(product_id=False, product_tmpl_id=False, **{field: origin.id})
        self.assertFalse(alert.product_id or alert.product_tmpl_id or alert.lot_ids)
        runs = self.env["mc.rov.quality.activity.run"].search([("alert_id", "=", alert.id)])
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs.outcome, "pending")
        return alert, origin, runs

    def _reject_change(self, field, replace=False):
        alert, origin, run = self._follow(field)
        value = self._origin(field, component=True).id if replace else False
        with self.assertRaisesRegex(UserError, "seguimiento"), self.cr.savepoint():
            alert.write({field: value})
        self.assertEqual(alert[field], origin)
        self.assertEqual(run.outcome, "pending")
        self.assertTrue(run.activity_id.active)

    def test_pending_alert_cannot_clear_manufacturing_origin(self):
        self._reject_change("production_id")

    def test_pending_alert_cannot_replace_manufacturing_origin(self):
        self._reject_change("production_id", replace=True)

    def test_pending_alert_cannot_clear_repair_origin(self):
        self._reject_change("repair_id")

    def test_pending_alert_cannot_replace_repair_origin(self):
        self._reject_change("repair_id", replace=True)

    def test_manufacturing_origin_noop_preserves_cycle(self):
        alert, origin, run = self._follow("production_id")
        alert.write({"production_id": origin.id})
        self.assertEqual(run.outcome, "pending")
        self.assertEqual(
            self.env["mc.rov.quality.activity.run"].search_count([("alert_id", "=", alert.id)]), 1
        )

    def test_repair_origin_noop_preserves_cycle(self):
        alert, origin, run = self._follow("repair_id")
        alert.write({"repair_id": origin.id})
        self.assertEqual(run.outcome, "pending")
        self.assertEqual(
            self.env["mc.rov.quality.activity.run"].search_count([("alert_id", "=", alert.id)]), 1
        )
