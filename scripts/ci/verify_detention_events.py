"""Caracterización MRP: población fija, errores prohibidos y fallos de cierre acotados."""

# Marcadores del sondeo; no equivale a declarar el producto GREEN.
# pylint: disable=unknown-option-value,print-used
from collections import Counter
import json
from pathlib import Path
import re
import sys


CLOSURE_CASES = {
    "test_button_completion_closes_detention",
    "test_shop_floor_completion_closes_detention",
    "test_native_partial_closes_only_completed_origin",
    "test_direct_finished_move_cancellation_closes_detention",
    "test_direct_stock_completion_closes_detention",
}
NEW_CASES = CLOSURE_CASES | {
    "test_native_serial_completion_fixture",
    "test_native_backorder_prompt_fixture",
    "test_pending_backorder_prompt_keeps_detention",
    "test_ready_to_close_keeps_detention",
    "test_completion_rollback_preserves_open_source_and_evidence",
}


def validate(expected, log, code):
    """No fuerza un fallo: informa lo observado sobre el producto v3 congelado."""
    required = Counter(tuple(case) for case in expected)
    assert len(required) == sum(required.values()) == 45
    new = {(cls, name) for cls, name in required if cls == "TestDetentionManufacturingEvents"}
    assert new == {("TestDetentionManufacturingEvents", name) for name in NEW_CASES}
    assert Counter(re.findall(r"Starting (\w+)\.(test_\w+)", log)) == required
    observed = Counter(re.findall(r"FAIL: (\w+)\.(test_\w+)", log))
    allowed = {("TestDetentionManufacturingEvents", name) for name in CLOSURE_CASES}
    assert set(observed) <= allowed and all(count == 1 for count in observed.values())
    assert not re.search(r"ERROR: \w+\.test_", log)
    summaries = re.findall(r"(\d+) failed, (\d+) error\(s\) of (\d+) tests", log)
    assert summaries and tuple(map(int, summaries[-1])) == (len(observed), 0, 45)
    assert code == (1 if observed else 0)
    for line in log.splitlines():
        if re.search(r" ERROR | CRITICAL ", line):
            known_failure = any("FAIL: " + cls + "." + name in line for cls, name in observed)
            # Odoo registra también el resumen de aserciones fallidas como ERROR.
            known_summary = re.search(
                r" ERROR .* odoo\.tests\.result: "
                + str(len(observed))
                + r" failed, 0 error\(s\) of 45 tests(?:\s|$)",
                line,
            )
            assert known_failure or known_summary, line
    blocks = re.split(r"\bFAIL: (\w+)\.(test_\w+)[^\n]*\n", log)
    assert len(blocks) == 1 + 3 * len(observed)
    for index in range(1, len(blocks), 3):
        assertions = re.findall(r"AssertionError:[^\n]*", blocks[index + 2])
        assert len(assertions) == 1
        assert "F2 debe cerrar al terminar Fabricación por evento nativo" in assertions[0]
    return sorted(observed)


if __name__ == "__main__":
    result = validate(
        json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")),
        Path(sys.argv[2]).read_text(encoding="utf-8"),
        int(sys.argv[3]),
    )
    print(
        "DETENTION_EVENTS_CHARACTERIZATION="
        + json.dumps({"tests": 45, "closure_failures": result}, sort_keys=True)
    )
