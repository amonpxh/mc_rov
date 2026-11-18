"""El RED de presentación y KPI conserva los 45 controles nativos anteriores."""

import importlib.util
from pathlib import Path
import unittest


class TestInterfaceRedVerification(unittest.TestCase):
    """Identidades y motivos exactos; los errores no son ausencia esperada."""

    def setUp(self):
        super().setUp()
        path = Path(__file__).resolve().parents[2] / "scripts/ci/verify_detention_interface_red.py"
        self.assertTrue(path.exists(), "Falta verificador RED de interfaz/KPI")
        spec = importlib.util.spec_from_file_location("interface_red", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.expected = [("TestCore", f"test_core_{n}") for n in range(45)] + [
            (cls, f"test_new_{n}") for cls in self.module.REASONS for n in range(12)
        ]
        self.log = "\n".join(f"Starting {cls}.{name} ..." for cls, name in self.expected)
        for cls, name in self.expected[45:]:
            self.log += f"\n2026 ERROR db tests: FAIL: {cls}.{name}\nAssertionError: {self.module.REASONS[cls]}\n"
        self.log += "2026 ERROR db odoo.tests.result: 24 failed, 0 error(s) of 69 tests"

    def test_exact_red_is_accepted(self):
        self.module.validate(self.expected, self.log, 1)

    def test_error_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected,
                self.log.replace("24 failed, 0 error(s)", "23 failed, 1 error(s)"),
                1,
            )
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, self.log + "\n2026 ERROR db loader: unexpected", 1)

    def test_reason_cannot_be_shared_between_features(self):
        reason = self.module.REASONS["TestDetentionKPIService"]
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected,
                self.log.replace(reason, "Falta interfaz nativa F2", 1),
                1,
            )

    def test_missing_control_or_wrong_process_result_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected,
                self.log.replace("Starting TestCore.test_core_0 ...", ""),
                1,
            )
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, self.log, 0)
