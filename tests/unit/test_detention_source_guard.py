"""La fuente antigua diagnosticada y el código de prueba fijo son identidades distintas."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class TestDetentionSourceGuard(unittest.TestCase):
    """Una diferencia diagnosticada no permite nuevas mutaciones durante la prueba."""

    def setUp(self):
        super().setUp()
        path = Path(__file__).resolve().parents[2] / "scripts/prepare_detention_red.py"
        spec = importlib.util.spec_from_file_location("prepare_detention_test", path)
        self.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.builder)

    def scenario(self, diagnostic=True, after_change=False, unknown_change=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            addon = root / "addon"
            (addon / "models").mkdir(parents=True)
            (addon / "__manifest__.py").write_bytes(b"{'version': '19.0.25.2.0'}\n")
            (addon / "models/sample.py").write_bytes(b"old staging\n")
            baseline = {
                "__manifest__.py": hashlib.sha256(
                    (addon / "__manifest__.py").read_bytes()
                ).hexdigest(),
                "models/sample.py": hashlib.sha256(b"reviewed test code\n").hexdigest(),
            }
            expected = root / "baseline.json"
            expected.write_text(json.dumps(baseline))
            observed = root / "observed.json"
            observed.write_text(
                json.dumps(
                    {
                        "manifest_version": "19.0.25.2.0",
                        "database_version": "19.0.25.2.0",
                        "product_mismatches": (
                            [{"file": "models/sample.py", "status": "different_hash"}]
                            if diagnostic
                            else []
                        ),
                    }
                )
            )
            script = root / "check.py"
            script.write_bytes(self.builder.BASELINE_CHECK.encode("utf-8"))
            snapshot = root / "source-before.json"
            args = [
                sys.executable,
                str(script),
                str(addon),
                str(expected),
                str(observed),
                str(snapshot),
            ]
            before = subprocess.run([*args, "before"], capture_output=True, text=True, check=False)
            if unknown_change:
                self.assertNotEqual(before.returncode, 0)
                return
            self.assertEqual(before.returncode, 0, before.stderr)
            self.assertTrue(snapshot.exists(), "Falta huella estricta del origen real")
            if after_change:
                (addon / "models/sample.py").write_bytes(b"different old staging\n")
            after = subprocess.run([*args, "after"], capture_output=True, text=True, check=False)
            self.assertEqual(after.returncode == 0, not after_change, after.stderr)

    def test_diagnosed_source_difference_is_sealed_and_preserved(self):
        self.scenario()

    def test_diagnosed_path_cannot_change_again_during_test(self):
        self.scenario(after_change=True)

    def test_undiagnosed_difference_is_rejected(self):
        self.scenario(diagnostic=False, unknown_change=True)
