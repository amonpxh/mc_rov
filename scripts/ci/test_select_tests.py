"""Contratos de selección conservadora y enlaces de documentación."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from select_tests import check_links, profile


class TestSelection(unittest.TestCase):
    """Verifica los perfiles y la resolución de enlaces locales."""

    def test_docs_and_removals_keep_odoo_off(self):
        self.assertEqual(profile(["AGENTS.md", "README.md", "docs/runbooks/deploy.md"]), "docs")

    def test_metrics_only_select_related_odoo_suite(self):
        self.assertEqual(profile(["models/work_kpi_metrics.py", "docs/pendientes.md"]), "work_kpi")

    def test_only_pure_test_changes_do_not_need_odoo(self):
        self.assertEqual(profile(["tests/unit/test_work_kpi_metrics.py"]), "unit")

    def test_unknown_empty_mixed_and_sensitive_paths_keep_full(self):
        for paths in (
            [],
            ["docs/operator.py"],
            ["models/work_kpi_metrics.py", "security/ir.model.access.csv"],
            ["migrations/19.0.25.13.0/post-migrate.py"],
            ["tests/test_work_kpi.py"],
            [".github/workflows/test.yml"],
            ["static/src/work_center/example.md"],
        ):
            with self.subTest(paths=paths):
                self.assertEqual(profile(paths), "full")

    def test_added_relative_links_must_resolve(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.md").touch()
            check_links(root, "docs/page.md", ["[Inicio](../index.md#inicio)"])
            with self.assertRaises(ValueError):
                check_links(root, "docs/page.md", ["[Falta](../ausente.md)"])
            with self.assertRaises(ValueError):
                check_links(root, "index.md", ["[Fuera](../otro-repo.md)"])
