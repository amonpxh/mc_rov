"""Congela el producto de interfaz F2 sobre el RED nativo de 69 casos."""

import argparse
import io
import json
from pathlib import Path
import re
import tarfile

from ci.verify_detention_interface_red import validate
from prepare_detention_interface_red import verified_core
from prepare_detention_races import _with_races
from prepare_detention_red import ROOT, sha


PRODUCT = (
    "__manifest__.py",
    "models/__init__.py",
    "models/detention_presentation.py",
    "models/detention_kpi_service.py",
    "models/kpi_dashboard.py",
    "models/kpi_dashboard_catalog.py",
    "wizards/__init__.py",
    "wizards/detention_wizard.py",
    "security/ir.model.access.csv",
    "views/detention_views.xml",
    "static/src/kpi_dashboard/kpi_dashboard.js",
    "static/src/kpi_dashboard/kpi_dashboard.xml",
    "static/tests/kpi_dashboard.test.js",
)


def overlay(data, changes):
    """Sustituye únicamente los archivos definidos para la presentación F2."""
    result = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(data)) as original, tarfile.open(
        fileobj=result, mode="w"
    ) as revised:
        for member in original:
            if member.name not in changes:
                revised.addfile(member, original.extractfile(member) if member.isfile() else None)
        for name, content in changes.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            entry.mode = 0o644
            revised.addfile(entry, io.BytesIO(content))
    return result.getvalue()


def verify_red(source):
    """Comprueba el resultado del intento y el cierre antes de reutilizar sus pruebas."""
    manifest = json.loads((source / "prepared.json").read_text())
    assert (manifest["phase"], manifest["tests"]) == ("interface-red", 69)
    for name, digest in manifest["files"].items():
        assert sha((source / name).read_bytes()) == digest, name
    private = source / "temporary-access"
    for action, marker in (
        ("status", "F2_ACCESS_EXIT_CODE=0"),
        ("revoke", "F2_ACCESS_REVOKED=True"),
    ):
        responses = sorted(
            private.glob(action + "-f2-*.txt"), key=lambda path: path.stat().st_mtime
        )
        response = responses[-1].read_text(encoding="utf-8-sig")
        assert marker in response
        if action == "status":
            for flag in (
                "=PASSED",
                "_SOURCE_FILES_UNCHANGED=True",
                "_STAGING_PID_UNCHANGED=True",
                "_COPY_CONNECTIONS_BLOCKED=True",
                "_PRIVATE_POSTGRES_STOPPED=True",
            ):
                assert re.search(
                    r"(?m)^" + re.escape("DETENTION_INTERFACE_RED" + flag) + r"\r?$",
                    response,
                )
    log = max(private.glob("tests-*.log"), key=lambda path: path.stat().st_mtime)
    validate(
        json.loads((source / "expected.json").read_text()),
        log.read_text(encoding="utf-8-sig"),
        1,
    )
    return manifest, sha(log.read_bytes())


def prepare(source, core, output):
    manifest, red_hash = verify_red(source)
    core_manifest = verified_core(core)
    assert manifest["files"]["source.tar"] == core_manifest["files"]["source.tar"]
    files = {
        name: (source / name).read_bytes()
        for name in manifest["files"]
        if name != "verify_detention_interface_red.py"
    }
    changes = {name: (ROOT / name).read_bytes().replace(b"\r\n", b"\n") for name in PRODUCT}
    files["source.tar"] = overlay(files["source.tar"], changes)
    files["verify_detention_green.py"] = (
        ROOT / "scripts/ci/verify_detention_green.py"
    ).read_bytes()
    for name in (
        "detention_concurrency.py",
        "detention_retry_log.py",
        "verify_detention_races.py",
    ):
        files[name] = (core / name).read_bytes()
    verifier = (ROOT / "scripts/ci/verify_detention_events_green.py").read_text()
    files["verify_detention_interface_green.py"] = (
        verifier.replace("45", "69")
        .replace("DETENTION_EVENTS_GREEN_CONFIRMED", "DETENTION_INTERFACE_GREEN_CONFIRMED")
        .encode()
    )
    runner = (
        files["run.sh"]
        .decode()
        .replace("verify_detention_interface_red.py", "verify_detention_interface_green.py")
    )
    runner = _with_races(runner).replace(
        "eight-independent-connection-races", "ten-independent-connection-races"
    )
    runner = runner.replace(
        '"$WORK/races.log" "$RACE_RC"', '"$WORK/races.log" "$RACE_RC" --extended'
    )
    runner = runner.replace("DETENTION_INTERFACE_RED", "DETENTION_INTERFACE_GREEN").replace(
        "DETENTION_RACES", "DETENTION_INTERFACE_GREEN"
    )
    files["run.sh"] = runner.encode()
    assert output.name == "kpi-detentions-interface-green"
    output.mkdir(exist_ok=False)
    for name, content in files.items():
        (output / name).write_bytes(content)
    manifest.update(
        phase="interface-green",
        expected_missing=0,
        native_controls=69,
        races=10,
        files={name: sha(content) for name, content in files.items()},
        interface_files={name: sha(content) for name, content in changes.items()},
        red_log_sha256=red_hash,
    )
    manifest.pop("wire_sha256", None)
    (output / "prepared.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("source", "core", "output"):
        parser.add_argument(argument, type=Path)
    options = parser.parse_args()
    prepare(options.source, options.core, options.output)
