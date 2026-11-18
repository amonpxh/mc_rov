"""Distingue conflictos SQL reintentables de errores inesperados durante el sondeo."""

import logging


class RetryLogFilter(logging.Filter):
    """Reclasifica solo la excepción tipada que el worker volverá a intentar."""

    def __init__(self, state, retryable):
        super().__init__()
        self.state = state
        self.retryable = retryable

    def filter(self, record):
        if not getattr(self.state, "active", False) or record.name != "odoo.sql_db":
            return True
        if (
            record.msg == "bad query: %s\nERROR: %s"
            and isinstance(record.args, tuple)
            and len(record.args) == 2
            and isinstance(record.args[1], self.retryable)
        ):
            self.state.retry_logs += 1
            record.levelno = logging.WARNING
            record.levelname = "WARNING"
            record.msg = "F2_RETRYABLE_SQL sqlstate=%s"
            record.args = (record.args[1].pgcode,)
        return True
