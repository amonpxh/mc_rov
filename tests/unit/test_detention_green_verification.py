"""El GREEN de captura exige los mismos contratos ejecutados, sin fallos ni errores."""

import importlib.util
from pathlib import Path
import unittest


class TestDetentionGreenVerification(unittest.TestCase):
    """Un proceso exitoso o una suite vacía no acredita captura autorizada."""

    def setUp(self):
        super().setUp()
        path = Path(__file__).resolve().parents[2] / "scripts/ci/verify_detention_green.py"
        self.assertTrue(path.exists(), "Falta verificador GREEN de captura F2")
        spec = importlib.util.spec_from_file_location("verify_detention_green_test", path)
        self.verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.verifier)
        self.expected = [("TestDetentionCapture", f"test_case_{number}") for number in range(24)]
        self.log = "\n".join(
            [
                *(f"Starting {cls}.{name} ..." for cls, name in self.expected),
                "0 failed, 0 error(s) of 24 tests",
            ]
        )

    def test_all_expected_cases_are_accepted(self):
        self.verifier.validate(self.expected, self.log, 0)

    def test_explicit_25_case_positive_population_is_accepted(self):
        self.assertTrue(
            callable(getattr(self.verifier, "validate_population", None)),
            "Falta verificación positiva25",
        )
        expected = [*self.expected, ("TestRPC", "test_context")]
        log = (
            self.log.replace("of 24 tests", "of 25 tests") + "\nStarting TestRPC.test_context ..."
        )
        self.verifier.validate_population(expected, log, 0, 25)

    def test_explicit_25_case_population_cannot_omit_the_new_case(self):
        self.assertTrue(
            callable(getattr(self.verifier, "validate_population", None)),
            "Falta verificación positiva25",
        )
        with self.assertRaises(AssertionError):
            self.verifier.validate_population(
                [*self.expected, ("TestRPC", "test_context")], self.log, 0, 25
            )

    def test_explicit_35_boundary_population_is_accepted(self):
        expected = [("TestBoundaries", f"test_case_{n}") for n in range(35)]
        log = "\n".join(
            [
                *(f"Starting {cls}.{name} ..." for cls, name in expected),
                "0 failed, 0 error(s) of 35 tests",
            ]
        )
        self.verifier.validate_population(expected, log, 0, 35)

    def test_boundary_population_cannot_skip_a_case(self):
        expected = [("TestBoundaries", f"test_case_{n}") for n in range(35)]
        log = "\n".join(
            [
                *(f"Starting {cls}.{name} ..." for cls, name in expected[:-1]),
                "0 failed, 0 error(s) of 35 tests",
            ]
        )
        with self.assertRaises(AssertionError):
            self.verifier.validate_population(expected, log, 0, 35)

    def test_failed_process_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.verifier.validate(self.expected, self.log, 1)

    def test_missing_test_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.verifier.validate(
                self.expected,
                self.log.replace("Starting TestDetentionCapture.test_case_0 ...", ""),
                0,
            )

    def test_repeated_test_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.verifier.validate(
                self.expected,
                self.log + "\nStarting TestDetentionCapture.test_case_0 ...",
                0,
            )

    def test_failure_marker_is_rejected_even_with_success_summary(self):
        with self.assertRaises(AssertionError):
            self.verifier.validate(
                self.expected, self.log + "\nFAIL: TestDetentionCapture.test_case_0", 0
            )

    def test_error_marker_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.verifier.validate(
                self.expected, self.log + "\nERROR: TestDetentionCapture.test_case_0", 0
            )

    def test_wrong_summary_population_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.verifier.validate(
                self.expected, self.log.replace("of 24 tests", "of 23 tests"), 0
            )

    def test_application_error_cannot_hide_behind_successful_test_summary(self):
        for level in ("ERROR", "CRITICAL"):
            with self.subTest(level=level), self.assertRaises(AssertionError):
                self.verifier.validate(
                    self.expected,
                    self.log + f"\n2026-11-17 14:00:00 12 {level} db addon: error de carga",
                    0,
                )

    def test_event_green_requires_all_45_cases(self):
        expected = [("TestEvents", f"test_case_{n}") for n in range(45)]
        log = "\n".join(
            [
                *(f"Starting {cls}.{name} ..." for cls, name in expected),
                "0 failed, 0 error(s) of 45 tests",
            ]
        )
        self.verifier.validate_population(expected, log, 0, 45)
        with self.assertRaises(AssertionError):
            self.verifier.validate_population(
                expected, log + "\nFAIL: TestEvents.test_case_1", 0, 45
            )
