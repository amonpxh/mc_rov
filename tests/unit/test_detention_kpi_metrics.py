"""F2 mide horas-orden registradas; dos causas simultáneas no crean dos horas."""

import copy
from datetime import datetime, timedelta, timezone
import unittest

# Los métodos son casos independientes del contrato, no una interfaz de producto.
# pylint: disable=too-many-public-methods

try:
    import detention_kpi_metrics as metrics
except ModuleNotFoundError:
    metrics = None


class TestDetentionMetrics(unittest.TestCase):
    """Ejemplos de negocio y entradas inválidas independientes del ORM."""

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(metrics, "Falta el motor F2 de intervalos")
        self.start = datetime(2026, 11, 17, 8)
        self.end = self.start + timedelta(hours=8)
        self.key = ("repair.order", 1)

    def order(self, identity=None, **values):
        return {"identity": identity or self.key, "open_at_cutoff": True, **values}

    def interval(self, identity="stop:1", **values):
        return {
            "identity": identity,
            "order": self.key,
            "cause": "materials",
            "start": self.start,
            "end": None,
            **values,
        }

    def summary(self, intervals=(), orders=None, **values):
        return metrics.summarize_detentions(
            orders if orders is not None else [self.order()],
            intervals,
            values.get("start", self.start),
            values.get("end", self.end),
            values.get("cutoff", self.end),
        )

    def test_empty_population_has_no_rate(self):
        result = self.summary(orders=[])
        self.assertEqual(result["open_orders"], 0)
        self.assertIsNone(result["registered_stopped_percent"])

    def test_unmarked_order_is_not_historical_evidence_of_no_detention(self):
        result = self.summary()
        self.assertEqual(result["orders_without_recorded_intervals"], 1)
        self.assertEqual(result["coverage_basis"], "recorded_intervals_only")

    def test_open_interval_stops_at_cutoff(self):
        result = self.summary([self.interval()], cutoff=self.start + timedelta(hours=2))
        self.assertEqual(result["recorded_seconds"], 7200)
        self.assertEqual(result["registered_stopped_orders"], 1)

    def test_future_reporting_end_cannot_add_time_beyond_cutoff(self):
        result = self.summary([self.interval()], end=self.end + timedelta(days=1))
        self.assertEqual(result["recorded_seconds"], 8 * 3600)

    def test_interval_is_clipped_at_period_start(self):
        result = self.summary(
            [
                self.interval(
                    start=self.start - timedelta(days=2), end=self.start + timedelta(hours=1)
                )
            ]
        )
        self.assertEqual(result["recorded_seconds"], 3600)

    def test_interval_is_clipped_at_period_end(self):
        result = self.summary([self.interval(end=self.end + timedelta(hours=1))])
        self.assertEqual(result["recorded_seconds"], 8 * 3600)

    def test_two_overlapping_causes_do_not_double_total(self):
        rows = [
            self.interval(end=self.start + timedelta(hours=2)),
            self.interval(
                "b",
                cause="client",
                start=self.start + timedelta(hours=1),
                end=self.start + timedelta(hours=3),
            ),
        ]
        result = self.summary(rows)
        self.assertEqual(result["recorded_seconds"], 3 * 3600)
        self.assertEqual(result["by_cause"]["materials"]["recorded_seconds"], 2 * 3600)
        self.assertEqual(result["by_cause"]["client"]["recorded_seconds"], 2 * 3600)
        self.assertFalse(result["causes_additive"])

    def test_nested_intervals_preserve_outer_duration(self):
        result = self.summary(
            [
                self.interval(end=self.end),
                self.interval(
                    "b", start=self.start + timedelta(hours=1), end=self.start + timedelta(hours=2)
                ),
            ]
        )
        self.assertEqual(result["recorded_seconds"], 8 * 3600)

    def test_disjoint_intervals_add_within_one_order(self):
        result = self.summary(
            [
                self.interval(end=self.start + timedelta(hours=1)),
                self.interval("b", start=self.end - timedelta(hours=1), end=self.end),
            ]
        )
        self.assertEqual(result["recorded_seconds"], 7200)

    def test_adjacent_intervals_are_not_overcounted(self):
        middle = self.start + timedelta(hours=1)
        result = self.summary(
            [
                self.interval(end=middle),
                self.interval("b", start=middle, end=middle + timedelta(hours=1)),
            ]
        )
        self.assertEqual(result["recorded_seconds"], 7200)

    def test_parallel_orders_sum_order_time(self):
        other = ("mrp.production", 1)
        result = self.summary(
            [self.interval(), self.interval("b", order=other)],
            orders=[self.order(), self.order(other)],
        )
        self.assertEqual(result["recorded_seconds"], 16 * 3600)
        self.assertEqual(result["duration_unit"], "order_seconds")

    def test_same_numeric_id_from_two_models_is_not_one_order(self):
        result = self.summary(
            [self.interval()], orders=[self.order(), self.order(("mrp.production", 1))]
        )
        self.assertEqual(result["registered_stopped_percent"], 50)

    def test_closed_source_is_not_in_current_open_denominator(self):
        result = self.summary(
            [self.interval(end=self.end)], orders=[self.order(open_at_cutoff=False)]
        )
        self.assertEqual(result["open_orders"], 0)
        self.assertEqual(result["recorded_seconds"], 8 * 3600)

    def test_closed_source_with_unbounded_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            self.summary([self.interval()], orders=[self.order(open_at_cutoff=False)])

    def test_interval_closed_exactly_at_cutoff_is_not_currently_stopped(self):
        result = self.summary([self.interval(end=self.end)])
        self.assertEqual(result["registered_stopped_orders"], 0)
        self.assertEqual(result["recorded_seconds"], 8 * 3600)

    def test_interval_starting_exactly_at_cutoff_counts_currently_not_elapsed(self):
        result = self.summary([self.interval(start=self.end)])
        self.assertEqual(result["registered_stopped_orders"], 1)
        self.assertEqual(result["recorded_seconds"], 0)

    def test_future_interval_does_not_count(self):
        result = self.summary([self.interval(start=self.end + timedelta(hours=1))])
        self.assertEqual(result["registered_stopped_orders"], 0)
        self.assertEqual(result["recorded_seconds"], 0)

    def test_closed_interval_ending_at_period_start_adds_no_time(self):
        result = self.summary(
            [self.interval(start=self.start - timedelta(hours=1), end=self.start)]
        )
        self.assertEqual(result["recorded_interval_count"], 0)

    def test_join_duplicates_do_not_increase_counts(self):
        row = self.interval()
        result = self.summary([row, dict(row)])
        self.assertEqual(result["recorded_interval_count"], 1)
        self.assertEqual(result["recorded_seconds"], 8 * 3600)

    def test_conflicting_duplicate_cannot_rewrite_evidence(self):
        with self.assertRaises(ValueError):
            self.summary([self.interval(), self.interval(cause="client")])

    def test_duplicate_order_is_rejected(self):
        with self.assertRaises(ValueError):
            self.summary(orders=[self.order(), self.order()])

    def test_foreign_order_interval_is_not_silently_omitted(self):
        with self.assertRaises(ValueError):
            self.summary([self.interval(order=("repair.order", 99))])

    def test_unknown_cause_is_rejected(self):
        with self.assertRaises(ValueError):
            self.summary([self.interval(cause="invented")])

    def test_all_agreed_causes_are_supported(self):
        causes = {
            "materials",
            "client",
            "engineering",
            "documentation",
            "resources",
            "external",
            "other",
        }
        self.assertEqual(set(metrics.CAUSES), causes)
        for cause in causes:
            with self.subTest(cause=cause):
                self.assertEqual(
                    self.summary([self.interval(cause=cause)])["by_cause"][cause][
                        "recorded_seconds"
                    ],
                    8 * 3600,
                )

    def test_missing_start_remains_unknown_not_zero(self):
        result = self.summary([self.interval(start=None)])
        self.assertEqual(result["unknown_duration_intervals"], 1)
        self.assertEqual(result["registered_stopped_orders"], 0)

    def test_unknown_start_does_not_hide_valid_duration(self):
        result = self.summary([self.interval(start=None), self.interval("b", end=self.end)])
        self.assertEqual(result["unknown_duration_intervals"], 1)
        self.assertEqual(result["recorded_seconds"], 8 * 3600)

    def test_end_before_start_is_rejected(self):
        with self.assertRaises(ValueError):
            self.summary([self.interval(end=self.start - timedelta(seconds=1))])

    def test_zero_length_interval_is_valid_and_adds_no_time(self):
        result = self.summary([self.interval(end=self.start)])
        self.assertEqual(result["recorded_seconds"], 0)

    def test_naive_and_utc_aware_represent_same_instant(self):
        result = self.summary(
            [
                self.interval(
                    start=self.start.replace(tzinfo=timezone.utc),
                    end=self.end.replace(tzinfo=timezone.utc),
                )
            ]
        )
        self.assertEqual(result["recorded_seconds"], 8 * 3600)

    def test_offset_timestamp_is_normalized_not_compared_as_local_wall_time(self):
        offset = timezone(timedelta(hours=-3))
        result = self.summary(
            [
                self.interval(
                    start=datetime(2026, 11, 17, 5, tzinfo=offset),
                    end=datetime(2026, 11, 17, 6, tzinfo=offset),
                )
            ]
        )
        self.assertEqual(result["recorded_seconds"], 3600)

    def test_civil_date_cannot_be_invented_as_midnight(self):
        with self.assertRaises(ValueError):
            self.summary([self.interval(start="2026-11-17")])

    def test_invalid_timestamp_types_are_rejected(self):
        for value in (True, 123, "not a timestamp"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.summary([self.interval(start=value)])

    def test_odoo_timestamp_strings_are_supported(self):
        result = self.summary(
            [self.interval(start="2026-11-17 08:00:00", end="2026-11-17 09:00:00")]
        )
        self.assertEqual(result["recorded_seconds"], 3600)

    def test_invalid_reporting_bounds_are_rejected(self):
        for values in (
            {"start": self.end, "end": self.start},
            {"start": self.end, "end": self.end},
            {"cutoff": None},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.summary(**values)

    def test_period_after_cutoff_has_no_elapsed_duration(self):
        result = self.summary(
            [self.interval()],
            start=self.end,
            end=self.end + timedelta(hours=1),
            cutoff=self.start + timedelta(hours=1),
        )
        self.assertEqual(result["recorded_seconds"], 0)
        self.assertEqual(result["registered_stopped_orders"], 1)

    def test_boolean_order_identity_cannot_alias_integer(self):
        with self.assertRaises(ValueError):
            self.summary(orders=[self.order(("repair.order", True))])

    def test_open_state_must_be_explicit_boolean(self):
        with self.assertRaises(ValueError):
            self.summary(orders=[self.order(open_at_cutoff="false")])

    def test_blank_interval_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.summary([self.interval(identity="")])

    def test_inputs_are_not_mutated(self):
        rows = [self.interval()]
        orders = [self.order()]
        before = copy.deepcopy((rows, orders))
        self.summary(rows, orders=orders)
        self.assertEqual((rows, orders), before)

    def test_reverse_input_order_does_not_change_aggregation(self):
        rows = [
            self.interval(end=self.end),
            self.interval("b", cause="client", end=self.start + timedelta(hours=1)),
        ]
        self.assertEqual(self.summary(rows), self.summary(list(reversed(rows))))

    def test_coverage_of_undated_evidence_is_population_history_not_period_rate(self):
        result = self.summary([self.interval(start=None, end=self.start - timedelta(days=10))])
        self.assertEqual(result["unknown_duration_intervals"], 1)
        self.assertEqual(result["recorded_seconds"], 0)
        self.assertEqual(result.get("coverage_scope"), "population_history")

    def test_same_cause_overlap_is_unioned_within_cause(self):
        result = self.summary(
            [
                self.interval(end=self.end),
                self.interval("b", start=self.start + timedelta(hours=2), end=self.end),
            ]
        )
        self.assertEqual(result["by_cause"]["materials"]["recorded_seconds"], 8 * 3600)
        self.assertEqual(result["by_cause"]["materials"]["recorded_interval_count"], 2)

    def test_current_count_is_explicitly_separate_from_elapsed_reporting_period(self):
        result = self.summary([self.interval()], end=self.start + timedelta(hours=1))
        self.assertEqual(result["recorded_seconds"], 3600)
        self.assertEqual(result["registered_stopped_orders"], 1)
