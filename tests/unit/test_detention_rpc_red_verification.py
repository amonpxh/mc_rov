"""El sondeo RPC no acepta regresiones de los24contratos que ya pasaron."""

import importlib.util
from pathlib import Path
import unittest


class TestDetentionRPCRedVerification(unittest.TestCase):
    """Solo acredita la aserción adversarial concreta, nunca errores de preparación."""

    def setUp(self):
        super().setUp()
        path = Path(__file__).resolve().parents[2] / "scripts/ci/verify_detention_rpc_red.py"
        self.assertTrue(path.exists(), "Falta verificador del sondeo RPC")
        spec = importlib.util.spec_from_file_location("rpc_red_test", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.expected = [("TestDetentionCapture", f"test_{number}") for number in range(24)] + [
            self.module.TARGET
        ]
        self.log = "\n".join(
            [
                *(f"Starting {cls}.{name} ..." for cls, name in self.expected),
                f"FAIL: {self.module.TARGET[0]}.{self.module.TARGET[1]}",
                "AssertionError: cierre falso : El contexto del cliente no puede cerrar un inicio F2",
                "1 failed, 0 error(s) of 25 tests",
            ]
        )

    def test_expected_context_assertion_is_accepted(self):
        self.module.validate(self.expected, self.log, 1)

    def test_green_exit_is_not_claimed_as_reproduced_bug(self):
        with self.assertRaises(AssertionError):
            self.module.validate(self.expected, self.log, 0)

    def test_unrelated_failure_reason_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected,
                self.log.replace(
                    "El contexto del cliente no puede cerrar un inicio F2", "Otro fallo"
                ),
                1,
            )

    def test_original_contract_regression_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected, self.log + "\nFAIL: TestDetentionCapture.test_0", 1
            )

    def test_missing_original_case_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.module.validate(
                self.expected, self.log.replace("Starting TestDetentionCapture.test_0 ...", ""), 1
            )
