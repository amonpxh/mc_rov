"""Exige captura24, control RPC y diez fronteras nativas, todos verdes."""

# Marcador CLI consumido por el ejecutor aislado.
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
        35,
    )
    print("DETENTION_BOUNDARIES_CONFIRMED=35 native contracts pass; exact=35")
