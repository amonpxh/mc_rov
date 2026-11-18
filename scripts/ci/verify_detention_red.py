"""Verifica identidad exacta y motivo de los fallos RED, sin aceptar errores nativos."""

# El llamador consume este marcador CLI; no es logging de un modelo Odoo.
# pylint: disable=unknown-option-value,print-used

from collections import Counter
import json
from pathlib import Path
import re
import sys


def validate(expected, log, exit_code):
    """La ausencia del servicio debe ser el único fallo de los veinte contratos."""
    required = Counter(tuple(case) for case in expected)
    failures = Counter(case for case in required if not case[1].startswith("test_native_control_"))
    assert len(required) == sum(required.values()) == 24
    assert len(failures) == 20
    assert exit_code == 1, "El proceso nativo no terminó como RED esperado"
    actual = Counter(re.findall(r"Starting (\w+)\.(test_\w+)", log))
    assert actual == required, (required - actual, actual - required)
    observed = Counter(re.findall(r"FAIL: (\w+)\.(test_\w+)", log))
    assert observed == failures, (failures - observed, observed - failures)
    assert not re.search(r"ERROR: \w+\.test_", log)
    summary = re.findall(r"(\d+) failed, (\d+) error\(s\) of (\d+) tests", log)
    assert summary and tuple(map(int, summary[-1])) == (20, 0, 24), summary
    blocks = re.split(r"\bFAIL: (\w+)\.(test_\w+)[^\n]*\n", log)
    assert len(blocks) == 61, "Faltan bloques de fallo identificados"
    for offset in range(1, len(blocks), 3):
        identity = (blocks[offset], blocks[offset + 1])
        body = blocks[offset + 2]
        assertions = re.findall(r"AssertionError:[^\n]*", body)
        assert identity in failures and len(assertions) == 1, identity
        assert "Falta captura F2 autorizada" in assertions[0], identity


if __name__ == "__main__":
    validate(
        json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")),
        Path(sys.argv[2]).read_text(encoding="utf-8"),
        int(sys.argv[3]),
    )
    print(
        "DETENTION_RED_CONFIRMED=20 missing capture assertions; 4 native controls pass; exact=24"
    )
