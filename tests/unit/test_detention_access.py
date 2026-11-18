"""Ejecuta el comando forzado con procesos simulados: nunca toca SSH ni root."""

# TemporaryDirectory se cierra con addCleanup; exec prueba solo código propio.
# pylint: disable=consider-using-with,exec-used

import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class TestDetentionAccess(unittest.TestCase):
    """El ejecutor generado no recibe una consola ni reejecuta paquetes."""

    def setUp(self):
        super().setUp()
        path = Path(__file__).resolve().parents[2] / "scripts/qa/detention_access.py"
        spec = importlib.util.spec_from_file_location("f2_access", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "control"
        self.payload = Path(self.temporary.name) / "payload"
        self.root.mkdir()
        self.payload.mkdir()
        (self.root / "expires").write_text(str(int(time.time()) + 60))
        (self.payload / "run.sh").write_bytes(b"reviewed")
        self.source = self.module.runner_source(
            "a" * 32, {"run.sh": hashlib.sha256(b"reviewed").hexdigest()}
        )
        self.source = self.source.replace(
            "/root/mc-rov-f2-access-" + "a" * 32, str(self.root).replace("\\", "/")
        ).replace(
            "/var/tmp/mc-rov-detention-races-" + "a" * 32,
            str(self.payload).replace("\\", "/"),
        )

    def execute(self, command):
        with patch.dict(sys.modules, {"fcntl": MagicMock()}), patch.dict(
            os.environ, {"SSH_ORIGINAL_COMMAND": command}
        ), patch("subprocess.Popen") as process, patch(
            "pathlib.Path.lstat",
            return_value=SimpleNamespace(st_uid=0, st_mode=0o40700),
        ), contextlib.redirect_stdout(
            io.StringIO()
        ):
            try:
                # Código propio generado, procesos simulados y rutas temporales.
                exec(
                    compile(self.source, "forced-access", "exec"), {}
                )  # pylint: disable=exec-used
            except SystemExit as error:
                return error.code, process.call_count
            return 0, process.call_count

    def test_shell_and_arbitrary_commands_never_start_process(self):
        for command in ("bash", "run-f2; reboot", "", "scp -t /tmp/x"):
            result, calls = self.execute(command)
            self.assertEqual(result, "Comando no autorizado")
            self.assertEqual(calls, 0)

    def test_expired_access_never_executes(self):
        (self.root / "expires").write_text("1")
        self.assertEqual(self.execute("run-f2"), ("Acceso caducado", 0))

    def test_modified_payload_is_rejected_before_execution(self):
        (self.payload / "run.sh").write_bytes(b"modified")
        self.assertEqual(self.execute("run-f2"), ("Paquete modificado", 0))

    def test_one_attempt_only(self):
        self.assertEqual(self.execute("run-f2"), (0, 1))
        result, calls = self.execute("run-f2")
        self.assertIn("Intento consumido", result)
        self.assertEqual(calls, 0)

    def test_status_never_executes(self):
        self.assertEqual(self.execute("status-f2"), (0, 0))
