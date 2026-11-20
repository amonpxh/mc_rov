"""Q2 conserva alcance temporal y cuenta visitas originales una sola vez."""

from datetime import date, timedelta
from unittest import TestCase

from business_kpi_metrics import observed_return_summary


class TestObservedReturnSummary(TestCase):
    """Los contadores descriptivos conservan la ventana acordada."""

    def test_records_pending_and_other_cause_and_keeps_late_returns(self):
        departed = date(2026, 1, 1)
        rows = [
            {
                "event_id": 1,
                "visit_id": 7,
                "returned_on": departed + timedelta(days=179),
                "relation": "confirmed",
            },
            {
                "event_id": 2,
                "visit_id": 7,
                "returned_on": departed + timedelta(days=180),
                "relation": "confirmed",
            },
            {
                "event_id": 3,
                "visit_id": 7,
                "returned_on": departed + timedelta(days=181),
                "relation": "confirmed",
            },
            {
                "event_id": 4,
                "visit_id": 7,
                "returned_on": departed + timedelta(days=31),
                "relation": "pending",
            },
            {
                "event_id": 5,
                "visit_id": 7,
                "returned_on": departed + timedelta(days=11),
                "relation": "unrelated",
            },
        ]
        result = observed_return_summary({7: departed}, rows, as_of=departed + timedelta(days=365))
        self.assertEqual(
            result,
            {
                "window_days": 180,
                "observed_returns": 5,
                "observed_related_returns": 3,
                "observed_pending_returns": 1,
                "observed_unrelated_returns": 1,
                "confirmed_originals_within_window": 1,
                "outside_window": 1,
            },
        )
