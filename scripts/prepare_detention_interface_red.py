"""Prepara RED nativo de asistentes y KPI sobre la captura GREEN 45+10."""

# Marcadores CLI; no conecta ni genera claves.
# pylint: disable=unknown-option-value,print-used
import argparse
import ast
import base64
import json
from pathlib import Path
import re
import uuid

from ci.verify_detention_green import validate_population
from ci.verify_detention_races import validate_extended
from prepare_detention_red import ROOT, sha


def verified_core(folder):
    """Exige el resultado del mismo candidato, copia cerrada y clave revocada."""
    manifest = json.loads((folder / "prepared.json").read_text())
    receipt = json.loads((folder / "verified-result.json").read_text())
    assert (
        manifest["phase"] == "events-green"
        and manifest["product_revision"] == "mrp-stock-move-events-v1"
    )
    assert receipt["passed"] and receipt["access_revoked"]
    assert (receipt["tests"], receipt["races"]) == (45, 10)
    for name, digest in manifest["files"].items():
        assert sha((folder / name).read_bytes()) == digest, name
    private = folder / "temporary-access"
    for name, digest in (
        ("log", "log_sha256"),
        ("response", "response_sha256"),
        ("revocation_response", "revocation_sha256"),
    ):
        assert sha((private / receipt[name]).read_bytes()) == receipt[digest]
    assert receipt["source_archive_sha256"] == manifest["files"]["source.tar"]
    assert receipt["candidate_files"] == manifest["candidate_files"]
    log = (private / receipt["log"]).read_text(encoding="utf-8-sig")
    validate_population(json.loads((folder / "expected.json").read_text()), log, 0, 45)
    validate_extended(log, 0)
    response = (private / receipt["response"]).read_text(encoding="utf-8-sig")
    for flag in (
        "SOURCE_FILES_UNCHANGED=True",
        "COPY_CONNECTIONS_BLOCKED=True",
        "PRIVATE_POSTGRES_STOPPED=True",
        "STAGING_PID_UNCHANGED=True",
        "=PASSED",
    ):
        marker = "DETENTION_EVENTS" + ("" if flag.startswith("=") else "_") + flag
        assert re.search("(?m)^" + re.escape(marker) + r"\r?$", response)
    assert re.search(r"(?m)^F2_ACCESS_EXIT_CODE=0\r?$", response)
    return manifest


def red_runner(original):
    """Carga solo contratos nuevos; conserva el transporte y aislamiento ya probados."""
    begin = original.index("echo DETENTION_EVENTS_PHASE=ten-independent-connection-races")
    boundary = (
        'python3 "$PAYLOAD/check_baseline.py" "$ADDON" "$PAYLOAD/baseline.json" '
        '"$PAYLOAD/observed-source.json" "$WORK/source-before.json" after'
    )
    end = original.index(boundary, begin)
    runner = original[:begin] + original[end:]
    insertion = "with (root / '__init__.py').open('a') as output:"
    assert runner.count(insertion) == 1
    runner = runner.replace(
        insertion,
        "for name in ('test_detention_presentation.py', 'test_detention_kpi_service.py'):\n"
        "    (root / name).write_bytes((payload / name).read_bytes())\n" + insertion,
    )
    tail = "from . import test_detention_manufacturing_events\\n')"
    assert runner.count(tail) == 1
    runner = runner.replace(
        tail,
        "from . import test_detention_manufacturing_events\\n"
        "from . import test_detention_presentation\\nfrom . import test_detention_kpi_service\\n')",
    )
    tag = "--test-tags detention_capture,detention_rpc_defaults,detention_boundaries,detention_manufacturing_events"
    assert runner.count(tag) == 1
    return (
        runner.replace(tag, tag + ",detention_presentation,detention_kpi_service")
        .replace("verify_detention_events_green.py", "verify_detention_interface_red.py")
        .replace("DETENTION_EVENTS", "DETENTION_INTERFACE_RED")
    )


def prepare(source, output):
    manifest = verified_core(source)
    assert output.name == "kpi-detentions-interface-red"
    output.mkdir(parents=True, exist_ok=False)
    omitted = {
        "detention_concurrency.py",
        "detention_retry_log.py",
        "verify_detention_races.py",
        "verify_detention_events_green.py",
        "verify_detention_green.py",
        "run.sh",
        "expected.json",
    }
    files = {
        name: (source / name).read_bytes() for name in manifest["files"] if name not in omitted
    }
    expected = json.loads((source / "expected.json").read_text())
    for name in ("test_detention_presentation.py", "test_detention_kpi_service.py"):
        files[name] = (ROOT / "tests" / name).read_bytes()
        tree = ast.parse(files[name].decode())
        cases = [
            (node.name, item.name)
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            for item in node.body
            if isinstance(item, ast.FunctionDef) and item.name.startswith("test_")
        ]
        assert len(cases) == 12
        expected.extend(cases)
    assert len(expected) == 69
    files["expected.json"] = (json.dumps(expected, indent=2) + "\n").encode()
    files["verify_detention_interface_red.py"] = (
        ROOT / "scripts/ci/verify_detention_interface_red.py"
    ).read_bytes()
    files["run.sh"] = red_runner((source / "run.sh").read_text()).encode()
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
        phase="interface-red",
        tests=69,
        races=0,
        expected_missing=24,
        native_controls=45,
        executed=False,
        source_receipt_sha256=sha((source / "verified-result.json").read_bytes()),
        files={name: sha(data) for name, data in files.items()},
        wire_sha256=sha(wire.encode()),
    )
    (output / "prepared.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    print(
        "DETENTION_INTERFACE_RED_PREPARED=True TESTS=69 PRODUCT_UNCHANGED=True SSH_EXECUTED=False"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    prepare(options.source.resolve(), options.output.resolve())
