"""Los reintentos tipados se distinguen; un error SQL ajeno nunca se oculta."""

import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest


class Retryable(Exception):
    """Excepción ficticia con SQLSTATE; no requiere PostgreSQL local."""

    pgcode = "40001"


class TestRetryLog(unittest.TestCase):
    """Contrato del único filtro usado por el sondeo aislado."""

    def test_only_known_worker_conflict_changes_level(self):
        path = Path(__file__).resolve().parents[2] / "scripts/qa/detention_retry_log.py"
        spec = importlib.util.spec_from_file_location("retry_filter", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        state = SimpleNamespace(active=True, retry_logs=0)
        filtering = module.RetryLogFilter(state, (Retryable,))
        for exception, active, expected in (
            (ValueError("unexpected"), True, logging.ERROR),
            (Retryable(), False, logging.ERROR),
            (Retryable(), True, logging.WARNING),
        ):
            state.active = active
            record = logging.LogRecord(
                "odoo.sql_db",
                logging.ERROR,
                "native",
                1,
                "bad query: %s\nERROR: %s",
                ("UPDATE", exception),
                None,
            )
            self.assertTrue(filtering.filter(record))
            self.assertEqual(record.levelno, expected)
        self.assertEqual(state.retry_logs, 1)
