"""Contratos de F6 con períodos de Santiago y precisión de la evidencia."""

from datetime import date, datetime
import unittest

import repair_lead_time_metrics as f6


class RepairLeadTime(unittest.TestCase):
    """Comprueba la población y la precisión de la duración."""

    def test_uses_calendar_days_and_includes_long_visits(self):
        result = f6.summarize(
            [
                (datetime(2026, 10, 1, 12), date(2026, 10, 11)),
                (datetime(2026, 8, 12, 12), date(2026, 10, 11)),
            ]
        )
        self.assertEqual((result["samples"], result["median_days"]), (2, 35))
        self.assertEqual(result["distribution"][-1]["count"], 1)
        self.assertIsNone(result["p80_days"])

    def test_missing_and_reversed_are_coverage_not_zero_days(self):
        result = f6.summarize(
            [
                (None, date(2026, 10, 11)),
                (datetime(2026, 10, 12, 12), date(2026, 10, 11)),
                (datetime(2026, 10, 11, 19), datetime(2026, 10, 11, 18)),
            ]
        )
        self.assertEqual(result["missing_arrival"], 1)
        self.assertEqual(result["invalid_chronology"], 2)
        self.assertEqual(result["samples"], 0)
        self.assertIsNone(result["median_days"])

    def test_utc_midnight_uses_santiago_calendar_day(self):
        result = f6.summarize([(datetime(2026, 10, 11, 1), date(2026, 10, 11))])
        self.assertEqual(result["median_days"], 1)

    def test_p80_requires_ten_observations(self):
        result = f6.summarize(
            [(datetime(2026, 10, 1, 12), date(2026, 10, day)) for day in range(1, 11)]
        )
        self.assertEqual(result["p80_days"], 7)
