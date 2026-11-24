"""El ciclo de la base temporal solo opera sobre el nombre que generó."""

import unittest
from unittest.mock import Mock, call

from odoo_ci_database import database_name, run_isolated


class TestDatabaseLifecycle(unittest.TestCase):
    """Verifica los límites y la limpieza del destino temporal."""

    def test_drops_owned_database_after_failure(self):
        name = database_name()
        create, drop = Mock(), Mock()
        execute = Mock(side_effect=RuntimeError("falla de Odoo"))
        with self.assertRaisesRegex(RuntimeError, "falla de Odoo"):
            run_isolated(name, create, execute, drop)
        self.assertEqual(create.mock_calls, [call(name)])
        self.assertEqual(execute.mock_calls, [call(name)])
        self.assertEqual(drop.mock_calls, [call(name)])

    def test_does_not_drop_database_when_create_failed(self):
        name = database_name()
        create = Mock(side_effect=RuntimeError("ya existe"))
        execute, drop = Mock(), Mock()
        with self.assertRaisesRegex(RuntimeError, "ya existe"):
            run_isolated(name, create, execute, drop)
        execute.assert_not_called()
        drop.assert_not_called()

    def test_rejects_non_ci_names_before_any_action(self):
        create, execute, drop = Mock(), Mock(), Mock()
        for name in ("odoo_prod", "odoo_staging", "odoo_test"):
            with self.assertRaises(ValueError):
                run_isolated(name, create, execute, drop)
        create.assert_not_called()
        execute.assert_not_called()
        drop.assert_not_called()
