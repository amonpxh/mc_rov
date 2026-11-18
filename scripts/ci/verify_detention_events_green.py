"""Los mismos 45 contratos del sondeo deben pasar sin excepciones."""

# pylint: disable=unknown-option-value,print-used
import json
from pathlib import Path
import sys

from verify_detention_green import validate_population


if __name__ == "__main__":
    validate_population(
        json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")),
        Path(sys.argv[2]).read_text(encoding="utf-8"),
        int(sys.argv[3]),
        45,
    )
    print("DETENTION_EVENTS_GREEN_CONFIRMED=45")
