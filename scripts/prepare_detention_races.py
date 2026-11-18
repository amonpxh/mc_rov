"""Congela un lote F2 de 35 contratos y ocho carreras para acceso temporal."""

# Marcadores CLI usados por el operador; no es logging de modelos.
# pylint: disable=unknown-option-value,print-used

import argparse
import ast
import base64
import io
import json
from pathlib import Path
import tarfile
import uuid

from prepare_detention_red import (
    BASE,
    ROOT,
    _archive_candidate_hashes,
    _candidate_files,
    candidate_archive,
    git,
    sha,
)
from prepare_detention_rpc_red import _verified_green


def _with_races(runner):
    """Inserta el sondeo antes de comprobar conservación de STAGING."""
    before = (
        'python3 "$PAYLOAD/check_baseline.py" "$ADDON" "$PAYLOAD/baseline.json" '
        '"$PAYLOAD/observed-source.json" "$WORK/source-before.json" after'
    )
    assert runner.count(before) == 1
    probe = "\n".join(
        [
            "echo DETENTION_RACES_PHASE=eight-independent-connection-races",
            'install -o odoo -g odoo -m 600 "$PAYLOAD/detention_retry_log.py" "$WORK/data/detention_retry_log.py"',
            "set +e",
            (
                "unshare --net -- runuser -u odoo -- timeout --signal=TERM --kill-after=20s 600s "
                'odoo shell -c "$WORK/isolated.conf" -d "$DB" --db-filter "^$DB$" '
                "--no-http --workers 0 --max-cron-threads 0 --log-level warn "
                '--logfile "$WORK/evidence/race-odoo.log" '
                '< "$PAYLOAD/detention_concurrency.py" > "$WORK/races.log" 2>&1'
            ),
            "RACE_RC=$?",
            "set -e",
            'echo "DETENTION_RACES_RC=$RACE_RC"',
            'if test -f "$WORK/evidence/race-odoo.log"; then '
            'cat "$WORK/evidence/race-odoo.log" >> "$WORK/races.log"; fi',
            'cat "$WORK/races.log" >> "$WORK/tests.log"',
            'python3 "$PAYLOAD/verify_detention_races.py" "$WORK/races.log" "$RACE_RC"',
            before,
        ]
    )
    return runner.replace(before, probe)


def _cancel_revision(files, manifest):
    """V3 cambia solo la captura de cancelación; no sustituye contratos anteriores."""
    overlays = _candidate_files()
    target = "models/detention_capture.py"
    for name, data in overlays.items():
        if name != target:
            assert sha(data) == manifest["candidate_files"][name], name
    original = files["source.tar"]
    revised = candidate_archive(git("archive", "--format=tar", BASE), overlays)
    with tarfile.open(fileobj=io.BytesIO(original)) as before, tarfile.open(
        fileobj=io.BytesIO(revised)
    ) as after:
        previous = {
            item.name: sha(before.extractfile(item).read()) for item in before if item.isfile()
        }
        current = {
            item.name: sha(after.extractfile(item).read()) for item in after if item.isfile()
        }
    assert previous.keys() == current.keys()
    assert [name for name in previous if previous[name] != current[name]] == [target]
    files["source.tar"] = revised
    manifest["previous_candidate_files"] = manifest["candidate_files"]
    manifest["candidate_files"] = _archive_candidate_hashes(revised)
    manifest["product_revision"] = "mrp-native-cancel-v1"


def prepare(green, output):
    manifest = _verified_green(green)
    assert output.name in (
        "kpi-detentions-races",
        "kpi-detentions-races-v2",
        "kpi-detentions-races-v3",
    )
    output.mkdir(parents=True, exist_ok=False)
    files = {
        name: (green / name).read_bytes()
        for name in manifest["files"]
        if name not in ("expected.json", "verify_detention_green.py")
    }
    if output.name == "kpi-detentions-races-v3":
        _cancel_revision(files, manifest)
    files["test_detention_rpc_defaults.py"] = (
        ROOT / "tests/test_detention_rpc_defaults.py"
    ).read_bytes()
    files["verify_detention_boundaries.py"] = (
        ROOT / "scripts/ci/verify_detention_boundaries.py"
    ).read_bytes()
    files["verify_detention_green.py"] = (
        ROOT / "scripts/ci/verify_detention_green.py"
    ).read_bytes()
    files["test_detention_boundaries.py"] = (
        ROOT / "tests/test_detention_boundaries.py"
    ).read_bytes()
    expected = json.loads((green / "expected.json").read_text())
    expected.append(
        [
            "TestDetentionRPCDefaults",
            "test_rpc_defaults_cannot_forge_completion_during_start",
        ]
    )
    cases = [
        (node.name, item.name)
        for node in ast.parse(files["test_detention_boundaries.py"].decode()).body
        if isinstance(node, ast.ClassDef)
        for item in node.body
        if isinstance(item, ast.FunctionDef) and item.name.startswith("test_")
    ]
    assert len(cases) == 10
    expected.extend(cases)
    assert len(expected) == 35
    files["expected.json"] = (json.dumps(expected, indent=2) + "\n").encode()
    runner = files["run.sh"].decode()
    runner = (
        runner.replace("DETENTION_GREEN", "DETENTION_RACES")
        .replace("detention-green", "detention-races")
        .replace("detention_green_", "detention_races_")
        .replace("verify_detention_green.py", "verify_detention_boundaries.py")
    )
    assert runner.count("--test-tags detention_capture") == 1
    runner = runner.replace(
        "--test-tags detention_capture",
        "--test-tags detention_capture,detention_rpc_defaults,detention_boundaries",
    )
    insertion = "with (root / '__init__.py').open('a') as output:"
    assert runner.count(insertion) == 1
    runner = runner.replace(
        insertion,
        "(root / 'test_detention_rpc_defaults.py').write_bytes("
        "(payload / 'test_detention_rpc_defaults.py').read_bytes())\n"
        "(root / 'test_detention_boundaries.py').write_bytes((payload / 'test_detention_boundaries.py').read_bytes())\n"
        + insertion,
    )
    imports = "output.write('\\nfrom . import test_detention_capture\\n')"
    assert runner.count(imports) == 1
    runner = runner.replace(
        imports,
        "output.write('\\nfrom . import test_detention_capture\\n"
        "from . import test_detention_rpc_defaults\\nfrom . import test_detention_boundaries\\n')",
    )
    files["detention_concurrency.py"] = (ROOT / "scripts/qa/detention_concurrency.py").read_bytes()
    files["detention_retry_log.py"] = (ROOT / "scripts/qa/detention_retry_log.py").read_bytes()
    files["verify_detention_races.py"] = (
        ROOT / "scripts/ci/verify_detention_races.py"
    ).read_bytes()
    runner = _with_races(runner)
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
        phase="races-green",
        races=8,
        tests=35,
        expected_missing=0,
        native_controls=35,
        executed=False,
        files={name: sha(data) for name, data in files.items()},
        wire_sha256=sha(wire.encode()),
    )
    (output / "prepared.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    wrapper = (
        (green.parent / "staging-detentions-green.ps1")
        .read_text()
        .replace("kpi-detentions-green", output.name)
        .replace("DETENTION_GREEN", "DETENTION_RACES")
        .replace("F2 GREEN", "F2 CONCURRENCIA")
        .replace(
            "24 contratos nativos; exige todos verdes",
            "35 contratos y ocho carreras; exige todos verdes",
        )
        .replace("GREEN no confirmado", "Fronteras no confirmadas")
    )
    target = output.parent / (output.name.replace("kpi-", "staging-", 1) + ".ps1")
    assert not target.exists()
    target.write_bytes(wrapper.encode())
    ast.parse(files["test_detention_rpc_defaults.py"].decode())
    print(
        "DETENTION_RACES_PREPARED=True TESTS=35 RACES=8 CODE_UNCHANGED="
        + str(output.name != "kpi-detentions-races-v3")
        + " SSH_EXECUTED=False"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("green", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    prepare(options.green.resolve(), options.output.resolve())
