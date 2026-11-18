"""Rechaza evidencia incompleta o carreras sin dos conexiones independientes."""

import importlib.util
import json
from pathlib import Path
import unittest


class TestDetentionRaceVerification(unittest.TestCase):
    """El resumen no sustituye la población y las conexiones esperadas."""

    def setUp(self):
        super().setUp()
        path = Path(__file__).resolve().parents[2] / "scripts/ci/verify_detention_races.py"
        self.assertTrue(path.exists(), "Falta verificador de ocho carreras")
        spec = importlib.util.spec_from_file_location("detention_races", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.rows = [
            {
                "model": model,
                "phase": phase,
                "workers": [{"pid": 1, "attempts": 1}, {"pid": 2, "attempts": 2}],
                "identity_actor_chronology_verified": True,
            }
            for model in ("repair.order", "mrp.production")
            for phase in ("start_pair", "finish_pair", "start_cancel", "rollback_start")
        ]

    def log(self, rows=None):
        return (
            "\n".join(
                "DETENTION_RACE_CASE=" + json.dumps(row)
                for row in (self.rows if rows is None else rows)
            )
            + "\nDETENTION_RACE_PROBE=PASSED\n"
        )

    def test_exact_eight_pass(self):
        self.module.validate(self.log(), 0)

    def test_omission_or_duplicate_fails(self):
        for rows in (self.rows[:-1], [*self.rows[:-1], self.rows[0]]):
            with self.assertRaises(AssertionError):
                self.module.validate(self.log(rows), 0)

    def test_same_connection_fails(self):
        self.rows[0]["workers"][1]["pid"] = 1
        with self.assertRaises(AssertionError):
            self.module.validate(self.log(), 0)

    def test_process_or_application_error_fails(self):
        with self.assertRaises(AssertionError):
            self.module.validate(self.log(), 1)
        with self.assertRaises(AssertionError):
            self.module.validate(self.log() + " ERROR native error", 0)

    def test_extended_ten_requires_both_direct_stock_races(self):
        self.assertTrue(
            callable(getattr(self.module, "validate_extended", None)),
            "Falta verificador de diez carreras",
        )
        extra = [
            {**self.rows[0], "model": "mrp.production", "phase": phase}
            for phase in ("start_stock_done", "start_stock_cancel")
        ]
        self.module.validate_extended(self.log([*self.rows, *extra]), 0)
        with self.assertRaises(AssertionError):
            self.module.validate_extended(self.log(), 0)
        with self.assertRaises(AssertionError):
            self.module.validate(self.log([*self.rows, *extra]), 0)
