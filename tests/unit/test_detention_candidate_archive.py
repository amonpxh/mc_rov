"""Un candidato F2 solo puede añadir captura privada y cambiar la versión prevista."""

import importlib.util
import io
from pathlib import Path
import tarfile
import unittest


class TestDetentionCandidateArchive(unittest.TestCase):
    """La copia de prueba no recibe cambios ajenos ocultos en un tar generado."""

    def setUp(self):
        super().setUp()
        path = Path(__file__).resolve().parents[2] / "scripts/prepare_detention_red.py"
        spec = importlib.util.spec_from_file_location("detention_candidate_builder", path)
        self.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.builder)
        self.assertTrue(
            callable(getattr(self.builder, "candidate_archive", None)),
            "Falta sellado del candidato F2",
        )
        base = io.BytesIO()
        with tarfile.open(fileobj=base, mode="w") as archive:
            for name, data in {
                "models/__init__.py": b"from . import base\n",
                "__manifest__.py": b"{'name': 'ROV', 'version': '19.0.25.8.0'}\n",
                "reports/issued.xml": b"unchanged\n",
            }.items():
                row = tarfile.TarInfo(name)
                row.size = len(data)
                archive.addfile(row, io.BytesIO(data))
        self.base = base.getvalue()
        self.overlay = {
            "models/__init__.py": (
                b"from . import base\nfrom . import detention_history\n"
                b"from . import detention_capture\n"
            ),
            "__manifest__.py": b"{'name': 'ROV', 'version': '19.0.25.9.0'}\n",
            "models/detention_history.py": b"# history\n",
            "models/detention_capture.py": b"# capture\n",
            "models/detention_kpi_metrics.py": b"# metrics\n",
        }

    def test_only_explicit_overlay_changes(self):
        data = self.builder.candidate_archive(self.base, self.overlay)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            self.assertEqual(archive.extractfile("reports/issued.xml").read(), b"unchanged\n")
            for name, content in self.overlay.items():
                self.assertEqual(archive.extractfile(name).read(), content)

    def test_extra_product_change_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.builder.candidate_archive(
                self.base, {**self.overlay, "reports/issued.xml": b"changed\n"}
            )

    def test_missing_capture_file_is_rejected(self):
        overlay = dict(self.overlay)
        overlay.pop("models/detention_capture.py")
        with self.assertRaises(AssertionError):
            self.builder.candidate_archive(self.base, overlay)

    def test_altering_unrelated_manifest_field_is_rejected(self):
        self.overlay["__manifest__.py"] = b"{'name': 'different', 'version': '19.0.25.9.0'}\n"
        with self.assertRaises(AssertionError):
            self.builder.candidate_archive(self.base, self.overlay)

    def test_dropping_existing_import_is_rejected(self):
        self.overlay["models/__init__.py"] = (
            b"from . import detention_history\nfrom . import detention_capture\n"
        )
        with self.assertRaises(AssertionError):
            self.builder.candidate_archive(self.base, self.overlay)
