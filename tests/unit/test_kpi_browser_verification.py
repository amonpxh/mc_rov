"""Un proceso verde o una suite vacía no prueban la interfaz en navegador."""

from contextlib import redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


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

    def test_rejects_native_skip_with_other_reason(self):
        with self.assertRaises(RuntimeError):
            RUNNER.verify_result(
                self._log() + "\nskipped TestKPIDashboardBrowser.test_mobile_layout : other",
                0,
                105,
            )

    def test_addons_directory_warning_is_not_a_skipped_test(self):
        with redirect_stdout(io.StringIO()):
            RUNNER.verify_result(
                self._log() + "\ninvalid addons directory '/unused', skipped", 0, 105
            )

    def test_rejects_failed_process(self):
        with self.assertRaises(RuntimeError):
            RUNNER.verify_result(self._log(), 1, 105)

    def test_download_checks_reviewed_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive"
            with patch.object(RUNNER.urllib.request, "urlopen", return_value=io.BytesIO(b"abc")):
                RUNNER.download_verified(
                    "https://example.invalid/tool",
                    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                    path,
                )
            self.assertEqual(path.read_bytes(), b"abc")

    def test_download_rejects_changed_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                RUNNER.urllib.request, "urlopen", return_value=io.BytesIO(b"changed")
            ):
                with self.assertRaises(RuntimeError):
                    RUNNER.download_verified(
                        "https://example.invalid/tool", "0" * 64, Path(directory) / "archive"
                    )

    def test_unreviewed_libraries_are_rejected(self):
        result = RUNNER.subprocess.CompletedProcess([], 0, "libunknown.so => not found\n")
        with patch.object(RUNNER.subprocess, "run", return_value=result):
            with self.assertRaises(RuntimeError):
                RUNNER.browser_launcher(Path("unused"), Path("unused/chrome"))

    def test_temporary_library_does_not_modify_odoo_environment(self):
        result = RUNNER.subprocess.CompletedProcess([], 0, "libasound.so.2 => not found\n")
        before = dict(os.environ)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with redirect_stdout(io.StringIO()), patch.object(
                RUNNER.subprocess, "run", return_value=result
            ), patch.object(
                RUNNER.platform,
                "freedesktop_os_release",
                return_value={"ID": "ubuntu", "VERSION_ID": "24.04"},
            ), patch.object(
                RUNNER, "download_verified"
            ):
                launcher = RUNNER.browser_launcher(root, root / "chrome")
            self.assertIn('"$@"', launcher.read_text(encoding="utf-8"))
            self.assertIn("LD_LIBRARY_PATH=", launcher.read_text(encoding="utf-8"))
        self.assertEqual(dict(os.environ), before)

    def test_websocket_wheel_is_limited_to_test_process(self):
        before = dict(os.environ)
        with tempfile.TemporaryDirectory() as directory, patch.object(RUNNER, "download_verified"):
            root = Path(directory)
            environment = RUNNER.browser_environment(root, root / "chrome")
            self.assertEqual(environment["ODOO_BROWSER_BIN"], str(root / "chrome"))
            self.assertTrue(
                environment["PYTHONPATH"].startswith(
                    str(root / "websocket_client-1.9.0-py3-none-any.whl")
                )
            )
        self.assertEqual(dict(os.environ), before)
