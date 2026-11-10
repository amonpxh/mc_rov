"""Contratos del versionado Odoo; repositorios temporales sin servidor ni red."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from odoo_release import next_version, plan_release, apply_plan


class VersionTests(unittest.TestCase):
    """Reglas de los tres segmentos de producto bajo el prefijo Odoo fijo."""

    def test_patch(self):
        self.assertEqual(next_version("19.0.25.6.0", ["fix"]), "19.0.25.6.1")

    def test_feature_dominates_patch(self):
        self.assertEqual(next_version("19.0.25.6.4", ["fix", "feat"]), "19.0.25.7.0")

    def test_breaking_dominates_feature(self):
        self.assertEqual(next_version("19.0.25.6.4", ["feat", "breaking"]), "19.0.26.0.0")

    def test_invalid_versions(self):
        for value in ["1.2.3", "18.0.25.6.0", "19.0.025.6.0", "19.0.25.6.0; bad"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                next_version(value, ["fix"])

    def test_no_product_change_has_no_version(self):
        self.assertIsNone(next_version("19.0.25.6.0", []))


class PlannerTests(unittest.TestCase):
    """Ejercita Git real y archivos de entrega en un repositorio desechable."""

    def setUp(self):
        # TestCase.enterContext posee y cierra el recurso incluso ante errores.
        # pylint: disable=consider-using-with
        # enterContext registra la limpieza aunque falle setUp.
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self._git("init", "-q")
        self._git("config", "user.name", "Prueba QA")
        self._git("config", "user.email", "qa@example.invalid")
        self._write("__manifest__.py", '{"name": "QA", "version": "19.0.25.6.0"}\n')
        self._write("CHANGELOG.md", "# Changelog\n\n## Historial conservado\n\nTexto anterior.\n")
        self.base = self._commit("feat: base acreditada")
        self.state = {"schema": 1, "version": "19.0.25.6.0", "source": self.base, "overrides": {}}
        self._save_state()
        self._commit("ci: configurar entregas")

    def _git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.root), *args], text=True, encoding="utf-8"
        ).strip()

    def _write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _save_state(self):
        self._write(".odoo-release.json", json.dumps(self.state))

    def _commit(self, message):
        self._git("add", ".")
        self._git("commit", "-q", "-m", message)
        return self._git("rev-parse", "HEAD")

    def _product(self, message="feat: agregar función"):
        self._write("models/example.py", "value = 1\n")
        return self._commit(message)

    def _plan(self):
        return plan_release(self.root, "2026-11-10")

    def test_docs_only_does_not_release(self):
        self._write("docs/example.md", "Cambio documental\n")
        self._commit("docs: ampliar explicación")
        self.assertIsNone(self._plan())

    def test_real_history_and_readonly_plan(self):
        head = self._product()
        before = self._git("status", "--porcelain")
        plan = self._plan()
        self.assertEqual(plan["version"], "19.0.25.7.0")
        self.assertEqual(plan["source"], head)
        self.assertEqual(self._git("status", "--porcelain"), before)
        self.assertIn("Texto anterior.", plan["files"]["CHANGELOG.md"])
        self.assertEqual(plan["notes"].count("agregar función"), 1)

    def test_unknown_product_title_rejected(self):
        self._product("Título histórico sin tipo")
        with self.assertRaisesRegex(ValueError, "clasific"):
            self._plan()

    def test_explicit_historical_override(self):
        sha = self._product("Título histórico sin tipo")
        self.state["overrides"][sha] = "feat"
        self._save_state()
        self._commit("ci: clasificar excepción histórica")
        self.assertEqual(self._plan()["version"], "19.0.25.7.0")

    def test_breaking_footer(self):
        self._product("fix: ajustar esquema\n\nBREAKING CHANGE: requiere migración")
        self.assertEqual(self._plan()["version"], "19.0.26.0.0")

    def test_breaking_subject(self):
        self._product("feat(datos)!: reemplazar esquema")
        self.assertEqual(self._plan()["version"], "19.0.26.0.0")

    def test_product_disguised_as_docs_rejected(self):
        self._product("docs: cambiar producto")
        with self.assertRaises(ValueError):
            self._plan()

    def test_manifest_divergence_rejected(self):
        self._write("__manifest__.py", '{"version": "19.0.25.7.0"}\n')
        self._commit("feat: cambio manual de versión")
        with self.assertRaisesRegex(ValueError, "versión"):
            self._plan()

    def test_invalid_base_rejected(self):
        self.state["source"] = "a" * 40
        self._save_state()
        self._commit("ci: base incorrecta")
        with self.assertRaises(ValueError):
            self._plan()

    def test_apply_limits_files_and_repeated_release_is_noop(self):
        self._product()
        plan = self._plan()
        apply_plan(self.root, plan)
        self.assertEqual(
            set(self._git("diff", "--name-only").splitlines()),
            {"__manifest__.py", "CHANGELOG.md", ".odoo-release.json"},
        )
        self._commit(plan["title"])
        self.assertIsNone(self._plan())

    def test_apply_rejects_stale_source(self):
        self._product()
        plan = self._plan()
        self._write("docs/new.md", "Main avanzó\n")
        self._commit("docs: avanzar main")
        with self.assertRaises(ValueError):
            apply_plan(self.root, plan)

    def test_github_squash_release_commit_does_not_release_again(self):
        self._product()
        plan = self._plan()
        apply_plan(self.root, plan)
        self._commit(plan["title"] + " (#120)")
        self.assertIsNone(self._plan())

    def test_apply_rejects_extra_file(self):
        self._product()
        plan = self._plan()
        plan["files"]["models/example.py"] = "malicious = True\n"
        with self.assertRaises(ValueError):
            apply_plan(self.root, plan)

    def test_ci_change_and_tests_are_not_product(self):
        self._write("scripts/ci/helper.py", "pass\n")
        self._write("static/tests/example.test.js", "// QA\n")
        self._commit("ci: ampliar controles")
        self.assertIsNone(self._plan())

    def test_root_hook_and_controller_are_product(self):
        for name in ["hooks.py", "controllers/portal.py", "static/lib/widget.js"]:
            with self.subTest(name=name):
                self._write(name, "// cambio\n" if name.endswith(".js") else "pass\n")
        self._commit("fix: corregir puntos de entrada")
        self.assertEqual(self._plan()["version"], "19.0.25.6.1")


if __name__ == "__main__":
    unittest.main()
