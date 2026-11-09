"""Business quality rules exercised without Odoo, database or wall-clock changes."""

import copy
import unittest
from datetime import date, datetime, timedelta

try:
    import business_kpi_metrics as metrics
except ModuleNotFoundError as exc:
    if exc.name != "business_kpi_metrics":
        raise
    metrics = None


DAY = date(2026, 1, 1)


def visit(key=1, **values):
    """Declare the observed interval rather than assuming elapsed time proves coverage."""
    return {
        "visit_id": key,
        "delivered_on": DAY,
        "coverage_from": DAY,
        "coverage_until": DAY + timedelta(days=180),
        **values,
    }


def returned(key=1, **values):
    return {
        "event_id": key,
        "visit_id": 1,
        "returned_on": DAY + timedelta(days=30),
        "relation": "confirmed",
        **values,
    }


def attempt(ordinal=1, **values):
    return {
        "ordinal": ordinal,
        "validity": "valid",
        "verdict": "passed",
        "required_passed": True,
        "required_failure": False,
        "correction_required": False,
        "retest_required": False,
        **values,
    }


class BusinessMetricsTest(unittest.TestCase):
    """Missing functions fail assertions during RED, not test-module preparation."""

    def call_metric(self, name, *args, **kwargs):
        function = getattr(metrics, name, None)
        self.assertTrue(callable(function), "Missing business KPI function: " + name)
        return function(*args, **kwargs)


class TestReturnCohort(BusinessMetricsTest):
    """Visits, return events and mature observations have different denominators."""

    def calculate(self, visits, events=(), **values):
        return self.call_metric(
            "related_return_metrics",
            visits,
            events,
            **{"as_of": DAY + timedelta(days=180), **values},
        )

    def test_empty_cohort_has_no_rate(self):
        result = self.calculate([])
        self.assertEqual(result["eligible"], 0)
        self.assertEqual(result["mature"], 0)
        self.assertIsNone(result["value"])

    def test_multiple_returns_do_not_multiply_affected_visits(self):
        mature = [visit(key) for key in range(1, 11)]
        recent = [visit(key, delivered_on=DAY + timedelta(days=170)) for key in range(11, 15)]
        events = [returned(1), returned(2), returned(3, visit_id=2)]
        result = self.calculate(mature + recent, events)
        self.assertEqual(result["window_days"], 180)
        self.assertEqual(result["mature"], 10)
        self.assertEqual(result["following"], 4)
        self.assertEqual(result["affected_mature"], 2)
        self.assertEqual(result["observed_related_returns"], 3)
        self.assertEqual(result["value"], 20)

    def test_day_179_is_following_and_returns_are_already_visible(self):
        result = self.calculate([visit()], [returned()], as_of=DAY + timedelta(days=179))
        self.assertEqual(result["following"], 1)
        self.assertEqual(result["recent_affected"], 1)
        self.assertIsNone(result["value"])

    def test_day_180_matures_and_return_on_boundary_is_included(self):
        result = self.calculate([visit()], [returned(returned_on=DAY + timedelta(days=180))])
        self.assertEqual(result["mature"], 1)
        self.assertEqual(result["value"], 100)

    def test_return_after_day_180_remains_observed_but_outside_rate(self):
        result = self.calculate(
            [visit()],
            [returned(returned_on=DAY + timedelta(days=181))],
            as_of=DAY + timedelta(days=181),
        )
        self.assertEqual(result["observed_related_returns"], 1)
        self.assertEqual(result["affected_mature"], 0)
        self.assertEqual(result["value"], 0)

    def test_missing_start_or_end_coverage_does_not_prove_maturity(self):
        rows = [
            visit(1, coverage_from=None),
            visit(2, coverage_until=None),
            visit(3, coverage_from=DAY + timedelta(days=1)),
            visit(4, coverage_until=DAY + timedelta(days=179)),
        ]
        result = self.calculate(rows)
        self.assertEqual(result["coverage_unknown"], 4)
        self.assertEqual(result["mature"], 0)
        self.assertIsNone(result["value"])

    def test_missing_or_future_delivery_date_is_not_a_zero_failure_visit(self):
        result = self.calculate(
            [visit(1, delivered_on=None), visit(2, delivered_on=DAY + timedelta(days=181))]
        )
        self.assertEqual(result["coverage_unknown"], 2)
        self.assertEqual(result["mature"], 0)

    def test_pending_relation_labels_confirmed_rate_as_minimum(self):
        result = self.calculate(
            [visit(1), visit(2)], [returned(1), returned(2, visit_id=2, relation="pending")]
        )
        self.assertEqual(result["value"], 50)
        self.assertEqual(result["pending_relation_mature"], 1)
        self.assertEqual(result.get("observed_pending_returns"), 1)
        self.assertTrue(result["is_minimum"])

    def test_unrelated_return_is_not_a_related_failure(self):
        result = self.calculate([visit()], [returned(relation="unrelated")])
        self.assertEqual(result.get("observed_returns"), 1)
        self.assertEqual(result.get("observed_unrelated_returns"), 1)
        self.assertEqual(result["value"], 0)
        self.assertFalse(result["is_minimum"])

    def test_undated_return_cannot_be_assumed_outside_window(self):
        result = self.calculate([visit()], [returned(returned_on=None)])
        self.assertEqual(result["observed_related_returns"], 1)
        self.assertEqual(result["unknown_return_dates"], 1)
        self.assertTrue(result["is_minimum"])

    def test_undated_unrelated_return_keeps_existence_and_classification(self):
        result = self.calculate([visit()], [returned(returned_on=None, relation="unrelated")])
        self.assertEqual(result.get("observed_returns"), 1)
        self.assertEqual(
            result.get("undated_returns_by_relation"),
            {"confirmed": 0, "pending": 0, "unrelated": 1},
        )
        self.assertEqual(result["value"], 0)
        self.assertFalse(result["is_minimum"])

    def test_future_return_is_not_anticipated(self):
        result = self.calculate([visit()], [returned(returned_on=DAY + timedelta(days=181))])
        self.assertEqual(result["observed_related_returns"], 0)
        self.assertEqual(result["affected_mature"], 0)

    def test_identical_event_join_is_deduplicated(self):
        event = returned()
        result = self.calculate([visit()], [event, dict(event)])
        self.assertEqual(result["observed_related_returns"], 1)
        self.assertEqual(result["affected_mature"], 1)

    def test_conflicting_duplicate_or_foreign_identity_is_rejected(self):
        for rows, events in (
            ([visit(), visit()], []),
            ([visit()], [returned(visit_id=99)]),
            ([visit()], [returned(), returned(relation="unrelated")]),
        ):
            with self.subTest(rows=rows, events=events):
                with self.assertRaises(ValueError):
                    self.calculate(rows, events)

    def test_invalid_dates_relation_or_window_are_rejected(self):
        for kwargs in ({"as_of": datetime(2026, 1, 1)}, {"window_days": 0}, {"window_days": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.calculate([visit()], **kwargs)
        with self.assertRaises(ValueError):
            self.calculate([visit()], [returned(relation="guessed")])

    def test_inputs_are_not_changed(self):
        rows, events = [visit()], [returned()]
        before = copy.deepcopy((rows, events))
        self.calculate(rows, events)
        self.assertEqual((rows, events), before)


class TestFirstPass(BusinessMetricsTest):
    """The original adjudicable attempt wins over later editing and approval."""

    def status(self, attempts):
        return self.call_metric("first_pass_status", attempts)

    def test_informational_observations_with_no_pending_work_pass(self):
        self.assertEqual(self.status([attempt(observations="informational")]), "passed")

    def test_correction_or_retest_requirement_fails_first_pass(self):
        for flag in ("correction_required", "retest_required"):
            with self.subTest(flag=flag):
                self.assertEqual(self.status([attempt(**{flag: True})]), "failed")

    def test_later_approval_does_not_erase_first_failure(self):
        rows = [attempt(2), attempt(1, verdict="failed")]
        before = copy.deepcopy(rows)
        self.assertEqual(self.status(rows), "failed")
        self.assertEqual(rows, before)

    def test_real_failure_can_abort_incomplete_protocol(self):
        self.assertEqual(
            self.status([attempt(verdict="pending", required_passed=None, required_failure=True)]),
            "failed",
        )

    def test_pending_first_attempt_is_not_skipped(self):
        self.assertEqual(self.status([attempt(1, verdict="pending"), attempt(2)]), "pending")

    def test_confirmed_invalidation_allows_next_valid_attempt(self):
        invalid = attempt(
            validity="invalid",
            invalidation_confirmed=True,
            invalid_reason="Instrumento fuera de calibración",
        )
        self.assertEqual(self.status([invalid, attempt(2)]), "passed")
        self.assertEqual(self.status([invalid]), "invalid_only")

    def test_unconfirmed_or_unexplained_invalidation_is_unknown(self):
        for values in (
            {"invalidation_confirmed": False, "invalid_reason": "Motivo"},
            {"invalidation_confirmed": True, "invalid_reason": "  "},
        ):
            with self.subTest(values=values):
                self.assertEqual(
                    self.status([attempt(validity="invalid", **values), attempt(2)]), "unknown"
                )

    def test_contradictory_invalidation_cannot_hide_a_real_failure(self):
        invalid = attempt(
            validity="invalid",
            invalidation_confirmed=True,
            invalid_reason="Revisar instrumento",
            required_failure=True,
        )
        self.assertEqual(self.status([invalid, attempt(2)]), "failed")

    def test_non_boolean_attempt_evidence_is_rejected(self):
        for flag, value in (
            ("required_failure", 1),
            ("correction_required", "no"),
            ("retest_required", 0),
            ("required_passed", "yes"),
        ):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                self.status([attempt(**{flag: value})])

    def test_missing_required_or_pending_evidence_is_not_success(self):
        self.assertEqual(self.status([]), "unknown")
        for flag in ("required_passed", "correction_required", "retest_required"):
            with self.subTest(flag=flag):
                self.assertEqual(self.status([attempt(**{flag: None})]), "unknown")

    def test_duplicate_attempt_ordinal_is_rejected(self):
        with self.assertRaises(ValueError):
            self.status([attempt(), attempt()])


class TestRelease(BusinessMetricsTest):
    """A release decision never records physical dispatch or replaces evidence."""

    def status(self, **values):
        return self.call_metric(
            "release_status",
            **{
                "tests_passed": True,
                "documentation_complete": True,
                "blocking_nc_count": 0,
                **values,
            },
        )

    def test_all_three_known_requirements_are_ready(self):
        self.assertEqual(self.status(), "ready")

    def test_failed_tests_block_release(self):
        self.assertEqual(self.status(tests_passed=False), "blocked")

    def test_missing_required_documentation_blocks_release(self):
        self.assertEqual(self.status(documentation_complete=False), "blocked")

    def test_blocking_nc_prevents_release(self):
        self.assertEqual(self.status(blocking_nc_count=1), "blocked")

    def test_unknown_requirement_is_not_ready(self):
        for key in ("tests_passed", "documentation_complete", "blocking_nc_count"):
            with self.subTest(key=key):
                self.assertEqual(self.status(**{key: None}), "unknown")

    def test_known_blocker_wins_over_unknown_requirement(self):
        self.assertEqual(self.status(tests_passed=None, blocking_nc_count=1), "blocked")

    def test_invalid_boolean_or_counter_is_rejected(self):
        for values in (
            {"tests_passed": "yes"},
            {"documentation_complete": 1},
            {"blocking_nc_count": True},
            {"blocking_nc_count": -1},
            {"blocking_nc_count": 1.5},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.status(**values)
