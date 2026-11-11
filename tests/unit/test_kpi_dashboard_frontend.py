"""Ejecuta contratos JS sin instalar dependencias ni iniciar Odoo o navegador."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest


class TestKPIDashboardFrontend(unittest.TestCase):
    """El CI existente descubre estos contratos junto con los núcleos KPI puros."""

    def _node(self):
        executable = shutil.which("node")
        if executable:
            return executable
        # El runner que ejecuta checkout7 ya incorpora Node24; no requiere apt/npm.
        temporary = os.environ.get("RUNNER_TEMP")
        if temporary:
            root = Path(temporary).resolve().parent.parent
            for version in ("node24", "node20"):
                candidate = root / "externals" / version / "bin" / "node"
                if candidate.is_file():
                    return str(candidate)
        raise AssertionError("Falta Node en PATH o en las herramientas existentes del runner.")

    def _run(self, name):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [self._node(), "--experimental-vm-modules", "--test", str(root / "scripts" / name)],
            cwd=root,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=45,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_presentacion_preserva_base_y_cobertura(self):
        self._run("test_kpi_dashboard_presentation.mjs")

    def test_cargador_rechaza_respuestas_obsoletas(self):
        self._run("test_kpi_dashboard_loader.mjs")

    def test_componente_conserva_seleccion_y_acciones(self):
        self._run("test_kpi_dashboard_component.mjs")
