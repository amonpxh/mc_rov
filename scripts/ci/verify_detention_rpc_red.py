"""Exige un fallo adversarial concreto y conserva los24controles nativos verdes."""

# El marcador CLI acredita únicamente el diagnóstico, no la corrección del producto.
# pylint: disable=unknown-option-value,print-used

from collections import Counter
import json
from pathlib import Path
import re
import sys

TARGET = ("TestDetentionRPCDefaults", "test_rpc_defaults_cannot_forge_completion_during_start")


def validate(expected, log, exit_code):
    """Un cierre inyectado por contexto debe reproducirse sin ninguna regresión extra."""
    required = Counter(tuple(case) for case in expected)
    assert len(required) == sum(required.values()) == 25 and TARGET in required
    assert exit_code == 1
    assert Counter(re.findall(r"Starting (\w+)\.(test_\w+)", log)) == required
    assert Counter(re.findall(r"FAIL: (\w+)\.(test_\w+)", log)) == Counter([TARGET])
    assert not re.search(r"ERROR: \w+\.", log)
    summaries = re.findall(r"(\d+) failed, (\d+) error\(s\) of (\d+) tests", log)
    assert summaries and tuple(map(int, summaries[-1])) == (1, 0, 25)
    blocks = re.split(r"FAIL: (\w+)\.(test_\w+)[^\n]*\n", log)
    assert len(blocks) == 4 and (blocks[1], blocks[2]) == TARGET
    assertions = re.findall(r"AssertionError:[^\n]*", blocks[3])
    assert (
        len(assertions) == 1
        and "El contexto del cliente no puede cerrar un inicio F2" in assertions[0]
    )


if __name__ == "__main__":
    validate(
        json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")),
        Path(sys.argv[2]).read_text(encoding="utf-8"),
        int(sys.argv[3]),
    )
    print(
        "DETENTION_RPC_RED_CONFIRMED=1 exact RPC default assertion; 24 original contracts pass; exact=25"
    )
