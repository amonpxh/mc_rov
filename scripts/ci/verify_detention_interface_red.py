"""Exige 24 ausencias de interfaz/KPI, 45 controles verdes y cero errores."""

# pylint: disable=unknown-option-value,print-used
from collections import Counter
import json
from pathlib import Path
import re
import sys


REASONS = {
    "TestDetentionPresentation": "Falta interfaz nativa F2",
    "TestDetentionKPIService": "Falta consulta KPI F2 autorizada",
}


def validate(expected, log, code):
    """Una ausencia de un componente no puede justificar el fallo del otro."""
    required = Counter(tuple(case) for case in expected)
    assert len(required) == sum(required.values()) == 69
    failures = Counter(case for case in required if case[0] in REASONS)
    assert Counter(cls for cls, _name in failures) == Counter(dict.fromkeys(REASONS, 12))
    assert Counter(re.findall(r"Starting (\w+)\.(test_\w+)", log)) == required
    assert Counter(re.findall(r"FAIL: (\w+)\.(test_\w+)", log)) == failures
    assert not re.search(r"ERROR: \w+\.test_", log)
    summary = re.findall(r"(\d+) failed, (\d+) error\(s\) of (\d+) tests", log)
    assert code == 1 and summary and tuple(map(int, summary[-1])) == (24, 0, 69)
    for line in log.splitlines():
        if re.search(r" ERROR | CRITICAL ", line):
            known_failure = any("FAIL: " + cls + "." + name in line for cls, name in failures)
            known_summary = re.search(
                r" ERROR .* odoo\.tests\.result: 24 failed, 0 error\(s\) of 69 tests(?:\s|$)",
                line,
            )
            assert known_failure or known_summary, line
    blocks = re.split(r"\bFAIL: (\w+)\.(test_\w+)[^\n]*\n", log)
    assert len(blocks) == 73
    for index in range(1, len(blocks), 3):
        cls, name = blocks[index : index + 2]
        assertions = re.findall(r"AssertionError:[^\n]*", blocks[index + 2])
        assert (cls, name) in failures and len(assertions) == 1
        assert REASONS[cls] in assertions[0]


if __name__ == "__main__":
    validate(
        json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")),
        Path(sys.argv[2]).read_text(encoding="utf-8"),
        int(sys.argv[3]),
    )
    print(
        "DETENTION_INTERFACE_RED_CONFIRMED=24 missing presentation/KPI assertions; 45 previous controls pass; exact=69"
    )
