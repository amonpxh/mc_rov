"""Verifica ocho carreras exactas y el resultado real del proceso aislado."""

# pylint: disable=unknown-option-value,print-used
from collections import Counter
import json
from pathlib import Path
import re
import sys


def _validate(log, code, extended):
    """No acepta omisiones, duplicados, errores ni una sola conexión reciclada."""
    assert code == 0
    assert not re.search(r" ERROR | CRITICAL |Traceback \(most recent", log)
    assert log.count("DETENTION_RACE_PROBE=PASSED") == 1
    rows = [
        json.loads(line.split("=", 1)[1])
        for line in log.splitlines()
        if line.startswith("DETENTION_RACE_CASE=")
    ]
    required = Counter(
        (model, phase)
        for model in ("repair.order", "mrp.production")
        for phase in ("start_pair", "finish_pair", "start_cancel", "rollback_start")
    )
    if extended:
        required.update(
            ("mrp.production", phase) for phase in ("start_stock_done", "start_stock_cancel")
        )
    assert Counter((row["model"], row["phase"]) for row in rows) == required
    for row in rows:
        assert row["identity_actor_chronology_verified"] is True
        assert len(row["workers"]) == 2
        assert len({worker["pid"] for worker in row["workers"]}) == 2
        assert all(1 <= worker["attempts"] <= 5 for worker in row["workers"])
    return rows


def validate(log, code):
    """El recibo original conserva ocho carreras exactas."""
    return _validate(log, code, False)


def validate_extended(log, code):
    """Las dos carreras directas de movimientos se añaden a las ocho previas."""
    return _validate(log, code, True)


if __name__ == "__main__":
    assert len(sys.argv) == 3 or (len(sys.argv) == 4 and sys.argv[3] == "--extended")
    verifier = validate_extended if len(sys.argv) == 4 else validate
    verifier(Path(sys.argv[1]).read_text(encoding="utf-8"), int(sys.argv[2]))
    print("DETENTION_RACES_CONFIRMED=" + ("10" if len(sys.argv) == 4 else "8"))
