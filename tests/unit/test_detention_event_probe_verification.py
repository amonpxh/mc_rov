"""El sondeo admite únicamente fallos concretos del cierre F2, nunca regresiones."""

import importlib.util
from pathlib import Path
import unittest


class TestEventProbeVerification(unittest.TestCase):
    """Una caracterización verde también es válida; no se inventa un RED."""

    def setUp(self):
        super().setUp()
        path = Path(__file__).resolve().parents[2] / "scripts/ci/verify_detention_events.py"
        self.assertTrue(path.exists(), "Falta verificador del sondeo MRP")
        spec = importlib.util.spec_from_file_location("event_probe", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.expected = [("TestOld", f"test_control_{n}") for n in range(35)] + [
            ("TestDetentionManufacturingEvents", name) for name in sorted(self.module.NEW_CASES)
        ]
        self.log = "\n".join(f"Starting {cls}.{name} ..." for cls, name in self.expected)

    def failure(self, name, reason="F2 debe cerrar al terminar Fabricación por evento nativo"):
        return (
            "\n2026 ERROR db tests: FAIL: TestDetentionManufacturingEvents."
            + name
            + "\nTraceback...\nAssertionError: False is not true : "
            + reason
            + "\n"
        )

    def test_all_green_is_a_valid_characterization(self):
        result = self.module.validate(
            self.expected, self.log + "\n0 failed, 0 error(s) of 45 tests", 0
        )
        self.assertEqual(result, [])

    def test_known_closure_failure_is_reported(self):
        log = (
            self.log
            + self.failure("test_direct_stock_completion_closes_detention")
            + "2026 ERROR db odoo.tests.result: 1 failed, 0 error(s) of 45 tests"
        )
        result = self.module.validate(self.expected, log, 1)
        self.assertEqual(len(result), 1)

    def test_wrong_reason_is_not_an_expected_failure(self):
        log = (
            self.log
            + self.failure("test_direct_stock_completion_closes_detention", "wrong actor")
            + "1 failed, 0 error(s) of 45 tests"
        )
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, log, 1)

    def test_pending_wizard_regression_is_rejected(self):
        log = (
            self.log
            + self.failure("test_pending_backorder_prompt_keeps_detention")
            + "1 failed, 0 error(s) of 45 tests"
        )
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, log, 1)

    def test_incomplete_population_and_application_error_rejected(self):
        log = self.log + "\n0 failed, 0 error(s) of 45 tests"
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected, log.replace("Starting TestOld.test_control_0 ...", ""), 0
            )
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, log + "\n2026 ERROR db loader: unexpected", 0)

    def test_errors_and_failed_process_are_rejected(self):
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, self.log + "\n0 failed, 1 error(s) of 45 tests", 1)
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, self.log + "\n0 failed, 0 error(s) of 45 tests", 1)
