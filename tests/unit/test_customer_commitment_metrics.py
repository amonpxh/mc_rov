"""Contratos de F3 para promesas y entregas con evidencia."""

import json
import unittest
from datetime import date, datetime

# pylint: disable=too-many-public-methods

try:
    from customer_commitment_metrics import summarize_commitments
except ModuleNotFoundError as error:
    if error.name != "customer_commitment_metrics":
        raise
    summarize_commitments = None


def _day(number):
    return date(2026, 11, number)


def _stamp(number, hour=12):
    return datetime(2026, 11, number, hour)


def _movement(identity, lot, day, *, kind="outbound", at=None, **values):
    return {
        "id": identity,
        "lot_id": lot,
        "kind": kind,
        "effective_date": _day(day) if day else None,
        "effective_at": at,
        "recorded_at": _stamp(day or 15, 23),
        **values,
    }


def _commitment(identity=1, **values):
    return {
        "id": identity,
        "quantity": 1,
        "lot_ids": [11],
        "promised_date": _day(15),
        "promised_at": None,
        "agreed_at": _stamp(1),
        "changes": [],
        "movements": [],
        **values,
    }


class TestCustomerCommitmentMetrics(unittest.TestCase):
    """Poblaciones del tablero y reconciliación temporal sin el ORM."""

    def setUp(self):
        super().setUp()
        self.assertIsNotNone(summarize_commitments, "Falta el cálculo puro de F3")

    def _summary(self, *commitments, as_of=None, date_from=None, date_to=None):
        return summarize_commitments(
            commitments,
            date_from=date_from or _day(10),
            date_to=date_to or _day(19),
            as_of=as_of or _stamp(20),
        )

    def test_due_and_completed_populations_match_examples(self):
        commitments = [
            _commitment(identity, movements=[_movement(identity, 11, 15)])
            for identity in range(1, 9)
        ]
        commitments += [
            _commitment(9, movements=[_movement(9, 11, 16)]),
            _commitment(10),
        ]
        result = self._summary(*commitments)
        self.assertEqual(
            result["due"],
            {
                "denominator": 10,
                "on_time": 8,
                "late": 1,
                "overdue": 1,
                "unknown": 0,
                "cancelled": 0,
                "percentage": 80,
            },
        )
        self.assertEqual(result["completed"]["denominator"], 9)
        self.assertEqual(result["completed"]["overdue"], 0)
        self.assertAlmostEqual(result["completed"]["percentage"], 800 / 9)
        json.dumps(result)

    def test_due_uses_original_date_and_completed_uses_effective_date(self):
        commitment = _commitment(promised_date=_day(9), movements=[_movement(1, 11, 10)])
        result = self._summary(commitment, date_to=_day(10))
        self.assertIsNone(result["due"]["percentage"])
        self.assertEqual(result["completed"]["late"], 1)

    def test_same_commitment_identity_counts_once_in_both_populations(self):
        commitment = _commitment(movements=[_movement(1, 11, 15)])
        result = self._summary(commitment, dict(commitment))
        self.assertEqual(result["due"]["denominator"], 1)
        self.assertEqual(result["completed"]["denominator"], 1)
        self.assertEqual(len(result["rows"]), 1)

    def test_conflicting_data_for_one_commitment_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            self._summary(_commitment(), _commitment(promised_date=_day(16)))

    def test_returns_before_completion_require_another_outbound(self):
        result = self._summary(
            _commitment(
                quantity=2,
                lot_ids=[11, 12],
                movements=[
                    _movement(5, 11, 16),
                    _movement(3, 12, 14),
                    _movement(2, 11, 13, kind="return"),
                    _movement(1, 11, 12),
                    _movement(1, 11, 12),
                    _movement(4, 13, 15),
                ],
            )
        )
        self.assertEqual(result["completed"]["late"], 1)
        self.assertEqual(result["rows"][0]["completed_date"], "2026-11-16")

    def test_return_after_completion_preserves_first_completion(self):
        result = self._summary(
            _commitment(
                movements=[
                    _movement(1, 11, 14),
                    _movement(2, 11, 16, kind="return"),
                    _movement(3, 11, 18),
                ],
            )
        )
        self.assertEqual(result["rows"][0]["completed_date"], "2026-11-14")
        self.assertTrue(result["rows"][0]["returned_after_completion"])
        self.assertEqual(result["completed"]["denominator"], 1)
        self.assertEqual(result["completed"]["on_time"], 1)

    def test_undated_reoutbound_linked_to_later_return_preserves_first_completion(self):
        result = self._summary(
            _commitment(
                movements=[
                    _movement(3, 11, None, after_id=2),
                    _movement(2, 11, 14, kind="return"),
                    _movement(1, 11, 13),
                ],
            )
        )
        row = result["rows"][0]
        self.assertEqual(row["completed_date"], "2026-11-13")
        self.assertTrue(row["returned_after_completion"])
        self.assertEqual(result["completed"]["on_time"], 1)

    def test_undated_reoutbound_linked_to_later_return_on_same_day_stays_on_time(self):
        result = self._summary(
            _commitment(
                movements=[
                    _movement(1, 11, 14, at=_stamp(14, 15)),
                    _movement(2, 11, 14, kind="return", at=_stamp(14, 16)),
                    _movement(3, 11, None, after_id=2),
                ],
            )
        )
        self.assertEqual(result["completed"]["on_time"], 1)

    def test_links_without_a_later_dated_return_keep_coverage_unknown(self):
        cases = [
            [_movement(2, 11, 14, kind="return"), _movement(3, 11, None)],
            [_movement(2, 12, 14, kind="return"), _movement(3, 11, None, after_id=2)],
            [_movement(2, 11, 12, kind="return"), _movement(3, 11, None, after_id=2)],
            [_movement(2, 11, 14), _movement(3, 11, None, after_id=2)],
            [_movement(2, 11, None, kind="return"), _movement(3, 11, None, after_id=2)],
        ]
        for extra_movements in cases:
            with self.subTest(extra_movements=extra_movements):
                result = self._summary(
                    _commitment(movements=[_movement(1, 11, 13), *extra_movements])
                )
                self.assertEqual(result["due"]["unknown"], 1)
                self.assertEqual(result["completed"]["on_time"], 0)

    def test_linked_return_at_completion_timestamp_cannot_prove_later_reoutbound(self):
        result = self._summary(
            _commitment(
                movements=[
                    _movement(1, 11, 14, at=_stamp(14, 15)),
                    _movement(2, 11, 14, kind="return", at=_stamp(14, 15)),
                    _movement(3, 11, None, after_id=2),
                ],
            )
        )
        self.assertEqual(result["due"]["unknown"], 1)
        self.assertEqual(result["completed"]["on_time"], 0)

    def test_unspecified_series_count_distinct_lots(self):
        result = self._summary(
            _commitment(
                quantity=2,
                lot_ids=[],
                movements=[_movement(1, 11, 14), _movement(2, 11, 15)],
            )
        )
        self.assertEqual(result["due"]["overdue"], 1)
        self.assertEqual(result["completed"]["denominator"], 0)

    def test_partially_assigned_series_require_frozen_lot_and_total_quantity(self):
        result = self._summary(
            _commitment(
                quantity=2,
                lot_ids=[11],
                movements=[
                    _movement(1, 12, 13),
                    _movement(2, 13, 14),
                    _movement(3, 11, 16),
                ],
            )
        )
        self.assertEqual(result["completed"]["late"], 1)
        self.assertEqual(result["rows"][0]["completed_date"], "2026-11-16")

    def test_partial_with_undated_outbound_stays_unadjudicated(self):
        result = self._summary(
            _commitment(
                movements=[_movement(1, 11, 15), _movement(2, 12, None)],
                lot_ids=[11, 12],
                quantity=2,
            ),
            _commitment(2, coverage_unknown=True),
        )
        self.assertEqual(result["due"]["unknown"], 2)
        self.assertIsNone(result["due"]["percentage"])
        self.assertEqual(result["completed"]["denominator"], 0)

    def test_future_capture_does_not_rewrite_the_query_cutoff(self):
        commitment = _commitment(movements=[_movement(1, 11, 15, recorded_at=_stamp(19))])
        self.assertEqual(self._summary(commitment, as_of=_stamp(18))["due"]["overdue"], 1)
        self.assertEqual(self._summary(commitment)["due"]["on_time"], 1)

    def test_day_comparison_uses_santiago_across_utc_midnight(self):
        result = self._summary(_commitment(movements=[_movement(1, 11, 15, at=_stamp(16, 2))]))
        self.assertEqual(result["due"]["on_time"], 1)
        self.assertEqual(result["rows"][0]["completed_date"], "2026-11-15")

    def test_day_only_exit_cannot_resolve_same_day_promise_hour(self):
        result = self._summary(
            _commitment(promised_at=_stamp(15, 15), movements=[_movement(1, 11, 15)])
        )
        self.assertEqual(result["rows"][0]["status"], "unknown")
        self.assertEqual(result["due"]["unknown"], 1)
        self.assertEqual(result["completed"]["unknown"], 1)
        self.assertIsNone(result["completed"]["percentage"])

    def test_return_with_ambiguous_same_day_order_keeps_coverage(self):
        result = self._summary(
            _commitment(
                movements=[
                    _movement(1, 11, 15, at=_stamp(15, 15)),
                    _movement(2, 11, 15, kind="return"),
                ],
            )
        )
        self.assertEqual(result["rows"][0]["status"], "unknown")
        self.assertEqual(result["completed"]["denominator"], 0)

    def test_return_of_another_series_may_precede_day_only_completion(self):
        result = self._summary(
            _commitment(
                quantity=2,
                lot_ids=[11, 12],
                movements=[
                    _movement(1, 11, 14),
                    _movement(2, 12, 15),
                    _movement(3, 11, 15, kind="return", at=_stamp(15, 15)),
                ],
            )
        )
        self.assertEqual(result["due"]["unknown"], 1)
        self.assertIsNone(result["rows"][0]["completed_date"])

    def test_due_day_without_exit_stays_pending_until_santiago_midnight(self):
        self.assertEqual(
            self._summary(_commitment(), as_of=_stamp(16, 2))["rows"][0]["status"],
            "pending",
        )
        self.assertEqual(self._summary(_commitment(), as_of=_stamp(16, 3))["due"]["overdue"], 1)

    def test_undefined_promise_stays_visible_even_when_completed(self):
        result = self._summary(_commitment(promised_date=None, movements=[_movement(1, 11, 15)]))
        self.assertEqual(result["rows"][0]["status"], "undefined")
        self.assertEqual(result["completed"]["unknown"], 1)
        self.assertIsNone(result["completed"]["percentage"])

    def test_reprogramming_after_complete_does_not_change_comparison(self):
        result = self._summary(
            _commitment(
                movements=[_movement(1, 11, 16, at=_stamp(16, 14))],
                changes=[
                    {"kind": "reprogram", "promised_date": _day(18), "agreed_at": _stamp(16, 15)},
                    {"kind": "reprogram", "promised_date": _day(17), "agreed_at": _stamp(14)},
                ],
            )
        )
        row = result["rows"][0]
        self.assertEqual(row["status"], "late")
        self.assertEqual(row["secondary_promised_date"], "2026-11-17")
        self.assertEqual(row["secondary_status"], "on_time")

    def test_open_commitment_uses_last_agreement_visible_at_cutoff(self):
        result = self._summary(
            _commitment(
                changes=[
                    {"kind": "reprogram", "promised_date": _day(20), "agreed_at": _stamp(18)},
                    {"kind": "reprogram", "promised_date": _day(14), "agreed_at": _stamp(19)},
                ],
            ),
            as_of=_stamp(18, 15),
        )
        row = result["rows"][0]
        self.assertEqual(row["status"], "overdue")
        self.assertEqual(row["secondary_status"], "pending")
        self.assertEqual(row["secondary_promised_date"], "2026-11-20")

    def test_future_capture_of_agreement_keeps_historical_query_unchanged(self):
        result = self._summary(
            _commitment(
                changes=[
                    {
                        "kind": "reprogram",
                        "promised_date": _day(20),
                        "agreed_at": _stamp(15),
                        "recorded_at": _stamp(19),
                    },
                ],
            ),
            _commitment(2, recorded_at=_stamp(19)),
            as_of=_stamp(18),
        )
        self.assertEqual([row["id"] for row in result["rows"]], [1])
        self.assertIsNone(result["rows"][0]["secondary_promised_date"])

    def test_cancellation_before_due_leaves_percentage_base(self):
        result = self._summary(
            _commitment(changes=[{"kind": "cancel", "agreed_at": _stamp(15, 20)}])
        )
        self.assertEqual(result["due"]["cancelled"], 1)
        self.assertIsNone(result["due"]["percentage"])

    def test_cancellation_after_due_preserves_overdue(self):
        result = self._summary(
            _commitment(changes=[{"kind": "cancel", "agreed_at": _stamp(16, 3)}])
        )
        row = result["rows"][0]
        self.assertEqual(row["status"], "overdue")
        self.assertEqual(row["cancelled_at"], "2026-11-16T03:00:00")
        self.assertEqual(result["due"]["denominator"], 1)

    def test_cancellation_after_accredited_outbound_preserves_completion(self):
        result = self._summary(
            _commitment(
                movements=[_movement(1, 11, 14)],
                changes=[{"kind": "cancel", "agreed_at": _stamp(15)}],
            ),
        )
        self.assertEqual(result["due"]["on_time"], 1)
        self.assertEqual(result["completed"]["on_time"], 1)

    def test_return_still_visible_after_post_completion_cancellation(self):
        result = self._summary(
            _commitment(
                movements=[
                    _movement(1, 11, 14),
                    _movement(2, 11, 16, kind="return"),
                ],
                changes=[{"kind": "cancel", "agreed_at": _stamp(15)}],
            )
        )
        self.assertTrue(result["rows"][0]["returned_after_completion"])
