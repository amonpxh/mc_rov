"""Prepara los mismos 45 contratos y diez carreras después del RED de movimientos."""

# Marcadores CLI; no conecta por SSH.
# pylint: disable=unknown-option-value,print-used
import argparse
import base64
import json
from pathlib import Path
import re
import uuid

from ci.verify_detention_events import validate
from prepare_detention_red import ROOT, sha
from prepare_detention_races import _cancel_revision, _with_races


def verified_probe(folder):
    """No permite probar una corrección inventada sin el RED nativo observado."""
    manifest = json.loads((folder / "prepared.json").read_text())
    receipt = json.loads((folder / "verified-characterization.json").read_text())
    assert manifest["phase"] == "events-characterization" and manifest["tests"] == 45
    assert receipt["characterization_confirmed"] and receipt["access_revoked"]
    assert receipt["product_green"] is False and receipt["passed"] == 43 and receipt["errors"] == 0
    for name, digest in manifest["files"].items():
        assert sha((folder / name).read_bytes()) == digest, name
    private = folder / "temporary-access"
    for name, digest in (
        ("log", "log_sha256"),
        ("response", "response_sha256"),
        ("revocation_response", "revocation_sha256"),
    ):
        assert sha((private / receipt[name]).read_bytes()) == receipt[digest]
    failures = validate(
        json.loads((folder / "expected.json").read_text()),
        (private / receipt["log"]).read_text(encoding="utf-8-sig"),
        1,
    )
    assert failures == [
        (
            "TestDetentionManufacturingEvents",
            "test_direct_finished_move_cancellation_closes_detention",
        ),
        (
            "TestDetentionManufacturingEvents",
            "test_direct_stock_completion_closes_detention",
        ),
    ]
    response = (private / receipt["response"]).read_text(encoding="utf-8-sig")
    for marker in (
        "SOURCE_FILES_UNCHANGED=True",
        "COPY_CONNECTIONS_BLOCKED=True",
        "PRIVATE_POSTGRES_STOPPED=True",
        "STAGING_PID_UNCHANGED=True",
        "=PASSED",
    ):
        assert re.search(
            "(?m)^"
            + re.escape("DETENTION_EVENTS" + ("" if marker.startswith("=") else "_") + marker)
            + r"\r?$",
            response,
        )
    return manifest


def prepare(source, output):
    manifest = verified_probe(source)
    assert output.name == "kpi-detentions-events-green"
    output.mkdir(parents=True, exist_ok=False)
    files = {
        name: (source / name).read_bytes()
        for name in manifest["files"]
        if name != "verify_detention_events.py"
    }
    _cancel_revision(files, manifest)
    manifest["product_revision"] = "mrp-stock-move-events-v1"
    files["verify_detention_events_green.py"] = (
        ROOT / "scripts/ci/verify_detention_events_green.py"
    ).read_bytes()
    files["verify_detention_green.py"] = (
        ROOT / "scripts/ci/verify_detention_green.py"
    ).read_bytes()
    for name in ("detention_concurrency.py", "detention_retry_log.py"):
        files[name] = (ROOT / "scripts/qa" / name).read_bytes()
    files["verify_detention_races.py"] = (
        ROOT / "scripts/ci/verify_detention_races.py"
    ).read_bytes()
    runner = (
        files["run.sh"]
        .decode()
        .replace("verify_detention_events.py", "verify_detention_events_green.py")
    )
    runner = _with_races(runner).replace("DETENTION_RACES", "DETENTION_EVENTS")
    runner = runner.replace(
        "eight-independent-connection-races", "ten-independent-connection-races"
    )
    check = 'python3 "$PAYLOAD/verify_detention_races.py" "$WORK/races.log" "$RACE_RC"'
    assert runner.count(check) == 1
    runner = runner.replace(check, check + " --extended")
    files["run.sh"] = runner.encode()
    remote = "/var/tmp/mc-rov-detention-races-" + uuid.uuid4().hex
    wire = "set -euo pipefail\numask 077\nmkdir '" + remote + "'\n"
    for name, data in files.items():
        if name != "source.tar":
            assert b"\r" not in data and data.endswith(b"\n")
        (output / name).write_bytes(data)
        wire += (
            "printf '%s' '"
            + base64.b64encode(data).decode()
            + "' | base64 -d > '"
            + remote
            + "/"
            + name
            + "'\n"
        )
        wire += (
            "printf '%s  %s\\n' '"
            + sha(data)
            + "' '"
            + remote
            + "/"
            + name
            + "' | sha256sum -c -\n"
        )
    wire += "bash '" + remote + "/run.sh' '" + remote + "'\n"
    (output / "wire.sh").write_bytes(wire.encode())
    manifest.update(
        phase="events-green",
        tests=45,
        races=10,
        expected_missing=0,
        native_controls=45,
        executed=False,
        characterization=False,
        red_receipt_sha256=sha((source / "verified-characterization.json").read_bytes()),
        files={name: sha(data) for name, data in files.items()},
        wire_sha256=sha(wire.encode()),
    )
    (output / "prepared.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    print("DETENTION_EVENTS_GREEN_PREPARED=True TESTS=45 RACES=10 SSH_EXECUTED=False")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    prepare(options.source.resolve(), options.output.resolve())
