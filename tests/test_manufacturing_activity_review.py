from datetime import date, datetime
from unittest.mock import patch

from odoo.tests import tagged

from .manufacturing_activity_common import ManufacturingActivityCommon


@tagged("post_install", "-at_install")
class TestManufacturingActivityReview(ManufacturingActivityCommon):
    """La nueva orden restante se confirma aunque la original no tuviera seguimiento."""

    def _paused_original(self, **values):
        policy = self._policy(enabled=False)
        production = self._production(product_qty=2, **values)
        with patch("odoo.fields.Datetime.now", return_value=datetime(2026, 10, 16, 15)):
            production.action_confirm()
        self.assertFalse(self._runs(production))
        policy.enabled = True
        return production

    def _remaining(self, production):
        with patch("odoo.fields.Datetime.now", return_value=datetime(2026, 10, 23, 15)):
            remaining = (
                production._split_productions(amounts={production: [1.0, 1.0]}) - production
            )
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining.state, "confirmed")
        self.assertFalse(self._runs(production), "No debe reconstruir el seguimiento original")
        return remaining

    def test_remaining_without_parent_uses_its_new_confirmation_date(self):
        production = self._paused_original()
        remaining = self._remaining(production)
        run = self._runs(remaining)
        self.assertEqual(len(run), 1, "La nueva orden confirmada quedó sin seguimiento")
        self.assertFalse(run.parent_run_id)
        self.assertEqual(run.started_at, datetime(2026, 10, 23, 15))
        self.assertEqual(run.activity_id.date_deadline, date(2026, 11, 20))
        self.assertEqual(run.cycle, 1)

    def test_remaining_without_parent_respects_earlier_explicit_deadline(self):
        production = self._paused_original(date_deadline=datetime(2026, 11, 10, 15))
        remaining = self._remaining(production)
        run = self._runs(remaining)
        self.assertEqual(len(run), 1, "La nueva orden confirmada quedó sin seguimiento")
        self.assertEqual(run.activity_id.date_deadline, date(2026, 11, 10))
        self.assertFalse(run.parent_run_id)

    def test_remaining_still_paused_does_not_create_pending(self):
        production = self._paused_original()
        self._policy_model().search([("company_id", "=", self.env.company.id)]).enabled = False
        remaining = self._remaining(production)
        self.assertFalse(self._runs(remaining))
