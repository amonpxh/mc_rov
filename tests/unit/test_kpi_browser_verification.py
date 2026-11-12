"""Un proceso verde o una suite vacía no prueban la interfaz en navegador."""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import unittest


PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "run_kpi_browser_tests.py"
SPEC = importlib.util.spec_from_file_location("kpi_browser_runner", PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class TestKPIBrowserVerification(unittest.TestCase):
    """Exige casos nativos, ejecución real de HOOT y ausencia de skips."""

    def _log(self):
        names = (
            "test_desktop_layout",
            "test_mobile_layout",
            "test_hoot_dashboard_and_existing_controls",
        )
        return "\n".join(
            [f"Starting TestKPIDashboardBrowser.{name}" for name in names]
            + [
                "0 failed, 0 error(s) of 3 tests",
                "[HOOT] Passed 105 tests (300 assertions)",
                "[HOOT] Test suite succeeded",
            ]
        )

    def test_accepts_complete_native_evidence(self):
        with redirect_stdout(io.StringIO()):
            RUNNER.verify_result(self._log(), 0, 105)

    def test_rejects_empty_hoot_even_with_success_signal(self):
        with self.assertRaises(RuntimeError):
            RUNNER.verify_result(self._log().replace("Passed 105", "Passed 0"), 0, 105)

    def test_rejects_missing_native_case(self):
        with self.assertRaises(RuntimeError):
            RUNNER.verify_result(
                self._log().replace("Starting TestKPIDashboardBrowser.test_mobile_layout", ""),
                0,
                105,
            )

    def test_rejects_skipped_browser(self):
        with self.assertRaises(RuntimeError):
            RUNNER.verify_result(self._log() + "\nskipped: Chrome executable not found", 0, 105)

    def test_rejects_failed_process(self):
        with self.assertRaises(RuntimeError):
            RUNNER.verify_result(self._log(), 1, 105)
