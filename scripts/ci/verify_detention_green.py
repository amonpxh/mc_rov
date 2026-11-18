"""Verifica GREEN de la misma población nativa que reprodujo el RED."""

# El marcador CLI es consumido por el ejecutor de la copia aislada.
# pylint: disable=unknown-option-value,print-used

from collections import Counter
import json
from pathlib import Path
import re
import sys


def validate_population(expected, log, exit_code, population):
    """Ni saltos, duplicados, errores ni procesos fallidos acreditan el incremento."""
    required = Counter(tuple(case) for case in expected)
    assert population in (24, 25, 35, 45, 69)
    assert len(required) == sum(required.values()) == population
    assert exit_code == 0, "El proceso nativo no aprobó GREEN"
    actual = Counter(re.findall(r"Starting (\w+)\.(test_\w+)", log))
    assert actual == required, (required - actual, actual - required)
    assert not re.search(r"(?:FAIL|ERROR): \w+\.", log)
    assert not re.search(
        r" ERROR | CRITICAL ", log
    ), "Error de aplicación fuera del resumen nativo"
    summary = re.findall(r"(\d+) failed, (\d+) error\(s\) of (\d+) tests", log)
    assert summary and tuple(map(int, summary[-1])) == (0, 0, population), summary


def validate(expected, log, exit_code):
    """El ejecutor GREEN original conserva el contrato fijo de24casos."""
    validate_population(expected, log, exit_code, 24)


if __name__ == "__main__":
    validate(
        json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")),
        Path(sys.argv[2]).read_text(encoding="utf-8"),
        int(sys.argv[3]),
    )
    print("DETENTION_GREEN_CONFIRMED=24 native capture contracts pass; exact=24")
