"""Pure KPI arithmetic; no Odoo installation, database or credentials required."""

import copy
import unittest
from datetime import date, datetime, timedelta

from work_kpi_metrics import build_metrics


def row(**values):
    result = {
        "outcome": "business_done",
        "in_period": True,
        "started_at": datetime(2026, 11, 3, 8),
        "finished_at": datetime(2026, 11, 3, 12),
        "finished_date": date(2026, 11, 3),
        "original_deadline": date(2026, 11, 3),
        "current_deadline": date(2026, 11, 3),
        "pending_deadline": date(2026, 11, 3),
        "as_of_date": date(2026, 11, 3),
        "activity_active": True,
    }
    return {**result, **values}


class TestWorkKPIMetrics(unittest.TestCase):
    """Known results distinguish absent evidence from legitimate zero values."""

    def test_empty_has_zero_counts_and_unknown_rates(self):
        result = build_metrics([])
        self.assertEqual(result["pending"], 0)
        self.assertEqual(result["completed"], 0)
        self.assertIsNone(result["original_compliance"]["value"])
        self.assertIsNone(result["current_compliance"]["value"])
        self.assertIsNone(result["duration_hours"]["value"])

    def test_due_today_is_not_overdue(self):
        result = build_metrics(
            [row(outcome="pending"), row(outcome="pending", pending_deadline=date(2026, 11, 2))]
        )
        self.assertEqual(result["pending"], 2)
        self.assertEqual(result["overdue"], 1)
        self.assertEqual(result["completed"], 0)

    def test_unknown_pending_deadline_does_not_look_on_time(self):
        result = build_metrics([row(outcome="pending", pending_deadline=None)])
        self.assertEqual(result["pending"], 1)
        self.assertEqual(result["overdue"], 0)
        self.assertEqual(result["pending_timing_unknown"], 1)

    def test_missing_activity_keeps_pending_obligation(self):
        result = build_metrics([row(outcome="pending", activity_active=False)])
        self.assertEqual(result["pending"], 1)
        self.assertEqual(result["pending_activity_missing"], 1)

    def test_only_real_business_closure_is_completed(self):
        result = build_metrics(
            [row(), row(outcome="cancelled"), row(outcome="manual_done"), row(outcome="withdrawn")]
        )
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["cancelled"], 1)
        self.assertEqual(result["manual_history"], 2)
        self.assertEqual(result["original_compliance"]["known"], 1)
        self.assertEqual(result["duration_hours"]["known"], 1)

    def test_period_filters_closures_but_not_current_pending(self):
        result = build_metrics(
            [
                row(in_period=False),
                row(outcome="cancelled", in_period=False),
                row(outcome="pending", in_period=False),
            ]
        )
        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["cancelled"], 0)
        self.assertEqual(result["pending"], 1)

    def test_reprogrammed_deadline_does_not_rewrite_original_compliance(self):
        result = build_metrics([row(original_deadline=date(2026, 11, 2))])
        self.assertEqual(result["original_compliance"]["value"], 0)
        self.assertEqual(result["current_compliance"]["value"], 100)

    def test_missing_final_deadline_is_not_replaced_by_original(self):
        result = build_metrics([row(current_deadline=None)])
        self.assertEqual(result["original_compliance"]["value"], 100)
        self.assertEqual(result["current_compliance"]["unknown"], 1)
        self.assertIsNone(result["current_compliance"]["value"])

    def test_missing_local_closure_date_is_visible_in_both_denominators(self):
        result = build_metrics([row(finished_date=None)])
        self.assertEqual(result["completed"], 1)
        for name in ("original_compliance", "current_compliance"):
            self.assertEqual(result[name]["known"], 0)
            self.assertEqual(result[name]["unknown"], 1)
            self.assertIsNone(result[name]["value"])

    def test_rate_reports_known_and_unknown_coverage(self):
        result = build_metrics(
            [row(), row(original_deadline=date(2026, 11, 2)), row(original_deadline=None)]
        )
        self.assertEqual(
            result["original_compliance"], {"value": 50.0, "on_time": 1, "known": 2, "unknown": 1}
        )
        self.assertEqual(result["completed"], 3)

    def test_odd_median_uses_elapsed_hours_not_working_days(self):
        start = datetime(2026, 11, 3, 8)
        result = build_metrics([row(finished_at=start + timedelta(hours=h)) for h in (1, 2, 100)])
        self.assertEqual(result["duration_hours"], {"value": 2.0, "known": 3, "unknown": 0})

    def test_even_median_averages_middle_values(self):
        start = datetime(2026, 11, 3, 8)
        result = build_metrics(
            [row(finished_at=start + timedelta(hours=h)) for h in (1, 3, 5, 100)]
        )
        self.assertEqual(result["duration_hours"]["value"], 4.0)

    def test_zero_duration_is_known(self):
        result = build_metrics([row(finished_at=datetime(2026, 11, 3, 8))])
        self.assertEqual(result["duration_hours"], {"value": 0.0, "known": 1, "unknown": 0})

    def test_negative_and_missing_durations_are_unknown(self):
        result = build_metrics(
            [
                row(started_at=None),
                row(finished_at=None),
                row(finished_at=datetime(2026, 11, 3, 7)),
            ]
        )
        self.assertEqual(result["completed"], 3)
        self.assertEqual(result["duration_hours"], {"value": None, "known": 0, "unknown": 3})

    def test_input_rows_are_not_changed(self):
        rows = [row(), row(outcome="pending")]
        original = copy.deepcopy(rows)
        build_metrics(rows)
        self.assertEqual(rows, original)

    def test_unknown_outcome_is_rejected_instead_of_silently_counted(self):
        with self.assertRaises(ValueError):
            build_metrics([row(outcome="native_done_guess")])


if __name__ == "__main__":
    unittest.main()
