"""El cierre calculado por movimientos debe reconciliar el historial F2."""

# Solo clase propia y dobles nativos; no ejecuta Odoo ni consultas.
# pylint: disable=exec-used
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class TestManufacturingCancelHook(unittest.TestCase):
    """Reproduce que un cambio nativo de estado no llama a write(state)."""

    def test_native_cancellation_reconciles_after_super_without_replacing_return(self):
        calls = []

        class Native:
            """La acción nativa cambia estado sin llamar al write heredado."""

            def __init__(self):
                self.state = "confirmed"
                self.assert_predicate = False

            def _action_cancel(self):
                calls.append("native")
                self.state = "cancel"
                return "native-return"

            def filtered(self, predicate):
                self.assert_predicate = predicate(self)
                return self

        path = Path(__file__).resolve().parents[2] / "models/detention_capture.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "ManufacturingDetentionCapture"
        ]
        scope = {
            "models": SimpleNamespace(Model=Native),
            "lock_source": lambda order: calls.append("lock"),
        }
        exec(
            compile(ast.Module(body=classes, type_ignores=[]), "cancel-hook", "exec"),
            scope,
        )
        order = scope["ManufacturingDetentionCapture"]()
        service = Mock()
        service._finish_closed_sources.side_effect = lambda source: calls.append("history")
        order.env = {"mc.rov.detention.service": service}
        order.state = "confirmed"
        self.assertEqual(order._action_cancel(), "native-return")
        self.assertEqual(calls, ["lock", "native", "history"])
        service._finish_closed_sources.assert_called_once_with(order)
        self.assertTrue(order.assert_predicate)
