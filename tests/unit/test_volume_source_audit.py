"""La consulta técnica rechaza otras bases y conserva rollback ante fallos."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


PATH = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "audit_volume_sources.py"
SPEC = importlib.util.spec_from_file_location("volume_source_audit", PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class TestVolumeSourceAudit(unittest.TestCase):
    """El reporte de fuentes no autoriza consultas de registros o acciones de negocio."""

    def _environment(self, database="odoo_test", readonly="on"):
        cursor = Mock()
        cursor.dbname = database
        cursor.fetchone.return_value = (readonly,)
        return SimpleNamespace(cr=cursor)

    def test_foreign_database_is_rejected_before_any_query(self):
        environment = self._environment(database="other_database")
        with self.assertRaises(RuntimeError):
            AUDIT.run_audit(environment)
        environment.cr.execute.assert_not_called()
        environment.cr.rollback.assert_not_called()

    def test_missing_readonly_prevents_inspection(self):
        environment = self._environment(readonly="off")
        with patch.dict(os.environ, {"KPI_SOURCE_REPO": str(PATH.parent)}), patch.object(
            AUDIT, "collect"
        ) as collect:
            with self.assertRaises(RuntimeError):
                AUDIT.run_audit(environment)
            collect.assert_not_called()
        self.assertEqual(environment.cr.rollback.call_count, 2)

    def test_inspection_failure_rolls_back_without_success_receipt(self):
        environment = self._environment()
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"KPI_SOURCE_REPO": directory, "RUNNER_TEMP": directory}
        ), patch.object(AUDIT, "collect", side_effect=RuntimeError("missing source")):
            with self.assertRaises(RuntimeError):
                AUDIT.run_audit(environment)
            self.assertFalse(list(Path(directory).glob("*.log")))
        self.assertEqual(environment.cr.rollback.call_count, 2)

    def test_receipt_requires_readonly_and_completed_rollback(self):
        environment = self._environment()
        report = {
            "models": {},
            "business_actions_invoked": False,
            "individual_business_records_included": False,
        }
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"KPI_SOURCE_REPO": directory, "RUNNER_TEMP": directory}
        ), patch.object(AUDIT, "collect", return_value=report), redirect_stdout(io.StringIO()):
            AUDIT.run_audit(environment)
            saved = json.loads(next(Path(directory).glob("*.log")).read_text(encoding="utf-8"))
        self.assertTrue(saved["readonly_rolled_back"])
        self.assertFalse(saved["business_actions_invoked"])
        self.assertFalse(saved["individual_business_records_included"])
        self.assertEqual(environment.cr.rollback.call_count, 2)
