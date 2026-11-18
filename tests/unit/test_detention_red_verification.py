"""RED exige fallos concretos y controles ejecutados, no un código SSH exitoso."""

import importlib.util
from pathlib import Path
import unittest


class TestDetentionRedVerification(unittest.TestCase):
    """Los logs incompletos o con errores nunca acreditan un RED válido."""

    def setUp(self):
        super().setUp()
        path = Path(__file__).resolve().parents[2] / "scripts/ci/verify_detention_red.py"
        self.assertTrue(path.exists(), "Falta verificador exacto de RED F2")
        spec = importlib.util.spec_from_file_location("detention_red_verify", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.expected = [("TestDetentionCapture", f"test_new_{number}") for number in range(20)]
        self.expected += [
            ("TestDetentionCapture", f"test_native_control_{number}") for number in range(4)
        ]

    def log(self):
        lines = [f"Starting {case[0]}.{case[1]} ..." for case in self.expected]
        for case in self.expected[:20]:
            lines += [
                f"FAIL: {case[0]}.{case[1]}",
                "AssertionError: False is not true : Falta captura F2 autorizada",
            ]
        return "\n".join([*lines, "20 failed, 0 error(s) of 24 tests"])

    def test_expected_missing_service_is_valid_red(self):
        self.module.validate(self.expected, self.log(), 1)

    def test_incorrect_exit_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, self.log(), 0)

    def test_missing_control_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected,
                self.log().replace("Starting TestDetentionCapture.test_native_control_0 ...", ""),
                1,
            )

    def test_duplicate_execution_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected, self.log() + "\nStarting TestDetentionCapture.test_new_0 ...", 1
            )

    def test_native_failure_cannot_be_hidden(self):
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected, self.log() + "\nFAIL: TestDetentionCapture.test_native_control_0", 1
            )

    def test_setup_error_is_not_a_missing_feature(self):
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, self.log().replace("0 error(s)", "1 error(s)"), 1)

    def test_different_assertion_is_not_expected_red(self):
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected, self.log().replace("Falta captura F2 autorizada", "Otro fallo"), 1
            )

    def test_missing_messages_cannot_move_between_two_tests(self):
        marker = "AssertionError: False is not true : Falta captura F2 autorizada"
        log = self.log().replace(marker, "AssertionError: Otro fallo nativo", 1)
        log = log.replace(marker, marker + "\n" + marker, 1)
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, log, 1)
