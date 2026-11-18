"""Frontera adicional: el contexto RPC no puede transformar un inicio en un cierre."""

from odoo.tests import tagged

from . import test_detention_capture as capture_contracts
from .acceptance_activity_common import AcceptanceActivityCommon


@tagged("post_install", "-at_install", "detention_rpc_defaults")
class TestDetentionRPCDefaults(AcceptanceActivityCommon):
    """Agrega inyección de defaults; los24contratos originales se seleccionan aparte."""

    # Reutiliza preparación ya probada, sin heredar ni duplicar los24métodos de test.
    _service = capture_contracts.TestDetentionCapture._service
    _workshop = capture_contracts.TestDetentionCapture._workshop
    _order = capture_contracts.TestDetentionCapture._order
    _start = capture_contracts.TestDetentionCapture._start
    _history = capture_contracts.TestDetentionCapture._history

    def test_rpc_defaults_cannot_forge_completion_during_start(self):
        service = self._service()
        order = self._order()
        service = service.with_context(
            default_ended_at="2099-01-01 00:00:00",
            default_closed_by_id=service.env.uid,
            default_end_kind="resumed",
            default_closing_explanation="Cierre falso enviado en contexto QA",
        )
        self._start(service, order)
        row = self._history(service, order)[0]
        self.assertFalse(row["ended_at"], "El contexto del cliente no puede cerrar un inicio F2")
        self.assertFalse(row["closed_by_id"])
        self.assertFalse(row["end_kind"])
