"""La cancelación del sondeo usa la acción pública propia de cada origen."""

# Solo ejecuta el AST de una función propia contra dobles, sin cargar Odoo.
# pylint: disable=exec-used

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


class TestRaceCancellation(unittest.TestCase):
    """Reproduce la ausencia de action_cancel en repair.order sin cargar Odoo."""

    def test_each_native_model_uses_its_own_action(self):
        path = Path(__file__).resolve().parents[2] / "scripts/qa/detention_concurrency.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        functions = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "cancel_source"
        ]
        self.assertEqual(len(functions), 1, "Falta delegación de cancelación por origen")
        namespace = {}
        # Solo función propia y dobles mínimos con las APIs nativas comprobadas.
        exec(
            compile(ast.Module(body=functions, type_ignores=[]), "cancel-test", "exec"),
            namespace,
        )  # pylint: disable=exec-used
        calls = []
        repair = SimpleNamespace(
            _name="repair.order", action_repair_cancel=lambda: calls.append("repair")
        )
        manufacturing = SimpleNamespace(
            _name="mrp.production", action_cancel=lambda: calls.append("manufacturing")
        )
        namespace["cancel_source"](repair)
        namespace["cancel_source"](manufacturing)
        self.assertEqual(calls, ["repair", "manufacturing"])
