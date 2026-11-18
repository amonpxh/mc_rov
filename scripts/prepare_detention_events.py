"""Congela un sondeo de diez eventos MRP sobre el candidato v3 ya probado."""

# Marcadores CLI del paquete local; nunca conecta por SSH.
# pylint: disable=unknown-option-value,print-used
import argparse
import ast
import base64
import json
from pathlib import Path
import re
import uuid

from ci.verify_detention_green import validate_population
from ci.verify_detention_races import validate as validate_races
from prepare_detention_red import ROOT, sha


def verified_source(folder):
    """Vincula el producto congelado a su resultado real 35+8 y su cierre."""
    manifest = json.loads((folder / "prepared.json").read_text())
    receipt = json.loads((folder / "verified-result.json").read_text())
    assert manifest["product_revision"] == "mrp-native-cancel-v1"
    assert receipt["passed"] and receipt["access_revoked"]
    assert receipt["tests"] == 35 and receipt["races"] == 8
    for name, digest in manifest["files"].items():
        assert sha((folder / name).read_bytes()) == digest, name
    private = folder / "temporary-access"
    for name, digest in (
        ("response", "response_sha256"),
        ("log", "log_sha256"),
        ("revocation_response", "revocation_sha256"),
    ):
        assert sha((private / receipt[name]).read_bytes()) == receipt[digest]
    assert receipt["source_archive_sha256"] == manifest["files"]["source.tar"]
    assert receipt["candidate_files"] == manifest["candidate_files"]
    response = (private / receipt["response"]).read_text(encoding="utf-8-sig")
    assert re.search(r"(?m)^F2_ACCESS_EXIT_CODE=0\r?$", response)
    assert re.search(r"(?m)^DETENTION_RACES=PASSED\r?$", response)
    log = (private / receipt["log"]).read_text(encoding="utf-8-sig")
    validate_population(json.loads((folder / "expected.json").read_text()), log, 0, 35)
    validate_races(log, 0)
    for flag in (
        "source_files_unchanged",
        "staging_pid_unchanged",
        "copy_connections_blocked",
        "private_postgres_stopped",
    ):
        assert receipt[flag] is True
    return manifest


def event_runner(original):
    """Conserva aislamiento y compara fuentes; no repite las ocho carreras de v3."""
    start = original.index("echo DETENTION_RACES_PHASE=eight-independent-connection-races")
    boundary = (
        'python3 "$PAYLOAD/check_baseline.py" "$ADDON" "$PAYLOAD/baseline.json" '
        '"$PAYLOAD/observed-source.json" "$WORK/source-before.json" after'
    )
    stop = original.index(boundary, start)
    runner = (original[:start] + original[stop:]).replace("DETENTION_RACES", "DETENTION_EVENTS")
    assert (
        runner.count("--test-tags detention_capture,detention_rpc_defaults,detention_boundaries")
        == 1
    )
    runner = runner.replace(
        "--test-tags detention_capture,detention_rpc_defaults,detention_boundaries",
        "--test-tags detention_capture,detention_rpc_defaults,detention_boundaries,detention_manufacturing_events",
    )
    insertion = "with (root / '__init__.py').open('a') as output:"
    assert runner.count(insertion) == 1
    runner = runner.replace(
        insertion,
        "(root / 'test_detention_manufacturing_events.py').write_bytes("
        "(payload / 'test_detention_manufacturing_events.py').read_bytes())\n" + insertion,
    )
    import_line = "from . import test_detention_boundaries\\n')"
    assert runner.count(import_line) == 1
    runner = runner.replace(
        import_line,
        "from . import test_detention_boundaries\\nfrom . import test_detention_manufacturing_events\\n')",
    )
    return runner.replace("verify_detention_boundaries.py", "verify_detention_events.py")


def prepare(source, output):
    manifest = verified_source(source)
    assert output.name == "kpi-detentions-events-probe"
    output.mkdir(parents=True, exist_ok=False)
    files = {
        name: (source / name).read_bytes()
        for name in manifest["files"]
        if name
        not in (
            "detention_concurrency.py",
            "detention_retry_log.py",
            "verify_detention_races.py",
            "verify_detention_boundaries.py",
            "verify_detention_green.py",
            "expected.json",
            "run.sh",
        )
    }
    files["test_detention_manufacturing_events.py"] = (
        ROOT / "tests/test_detention_manufacturing_events.py"
    ).read_bytes()
    files["verify_detention_events.py"] = (
        ROOT / "scripts/ci/verify_detention_events.py"
    ).read_bytes()
    files["run.sh"] = event_runner((source / "run.sh").read_text()).encode()
    expected = json.loads((source / "expected.json").read_text())
    tree = ast.parse(files["test_detention_manufacturing_events.py"].decode())
    cases = [
        (node.name, item.name)
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        for item in node.body
        if isinstance(item, ast.FunctionDef) and item.name.startswith("test_")
    ]
    assert len(cases) == 10
    expected.extend(cases)
    assert len(expected) == 45
    files["expected.json"] = (json.dumps(expected, indent=2) + "\n").encode()
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
        phase="events-characterization",
        tests=45,
        races=0,
        expected_missing=None,
        native_controls=40,
        executed=False,
        characterization=True,
        source_receipt_sha256=sha((source / "verified-result.json").read_bytes()),
        files={name: sha(data) for name, data in files.items()},
        wire_sha256=sha(wire.encode()),
    )
    (output / "prepared.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    print("DETENTION_EVENTS_PREPARED=True TESTS=45 PRODUCT_UNCHANGED=True SSH_EXECUTED=False")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    prepare(options.source.resolve(), options.output.resolve())
