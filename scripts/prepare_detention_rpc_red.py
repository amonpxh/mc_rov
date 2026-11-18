"""Reproduce defaults RPC sobre el candidato congelado que aprobó24casos reales."""

# Marcadores CLI usados por el operador; no es logging de modelos.
# pylint: disable=unknown-option-value,print-used

import argparse
import ast
import base64
import json
from pathlib import Path
import uuid

from ci.verify_detention_green import validate as validate_green
from prepare_detention_red import ROOT, sha


def _verified_green(folder):
    manifest = json.loads((folder / "prepared.json").read_text())
    assert manifest["phase"] == "green" and manifest["isolated_test_version"] == "19.0.25.9.0"
    for name, expected in manifest["files"].items():
        assert sha((folder / name).read_bytes()) == expected
    responses = list(folder.glob("response-*.txt"))
    assert len(responses) == 1
    response = responses[0].read_text(encoding="utf-8-sig")
    assert "DETENTION_GREEN=PASSED" in response
    for marker in (
        "SOURCE_FILES_UNCHANGED",
        "COPY_CONNECTIONS_BLOCKED",
        "PRIVATE_POSTGRES_STOPPED",
        "STAGING_PID_UNCHANGED",
    ):
        assert "DETENTION_GREEN_" + marker + "=True" in response
    logs = list(folder.glob("tests-*.log"))
    assert len(logs) == 1
    validate_green(
        json.loads((folder / "expected.json").read_text()),
        logs[0].read_text(encoding="utf-8-sig"),
        0,
    )
    return manifest


def prepare(green, output):
    manifest = _verified_green(green)
    assert output.name == "kpi-detentions-rpc-red"
    output.mkdir(parents=True, exist_ok=False)
    files = {
        name: (green / name).read_bytes()
        for name in manifest["files"]
        if name not in ("expected.json", "verify_detention_green.py")
    }
    files["test_detention_rpc_defaults.py"] = (
        ROOT / "tests/test_detention_rpc_defaults.py"
    ).read_bytes()
    files["verify_detention_rpc_red.py"] = (
        ROOT / "scripts/ci/verify_detention_rpc_red.py"
    ).read_bytes()
    expected = json.loads((green / "expected.json").read_text())
    expected.append(
        ["TestDetentionRPCDefaults", "test_rpc_defaults_cannot_forge_completion_during_start"]
    )
    assert len(expected) == 25
    files["expected.json"] = (json.dumps(expected, indent=2) + "\n").encode()
    runner = files["run.sh"].decode()
    runner = (
        runner.replace("DETENTION_GREEN", "DETENTION_RPC_RED")
        .replace("detention-green", "detention-rpc-red")
        .replace("detention_green_", "detention_rpc_red_")
        .replace("verify_detention_green.py", "verify_detention_rpc_red.py")
    )
    assert runner.count("--test-tags detention_capture") == 1
    runner = runner.replace(
        "--test-tags detention_capture", "--test-tags detention_capture,detention_rpc_defaults"
    )
    insertion = "with (root / '__init__.py').open('a') as output:"
    assert runner.count(insertion) == 1
    runner = runner.replace(
        insertion,
        "(root / 'test_detention_rpc_defaults.py').write_bytes("
        "(payload / 'test_detention_rpc_defaults.py').read_bytes())\n" + insertion,
    )
    imports = "output.write('\\nfrom . import test_detention_capture\\n')"
    assert runner.count(imports) == 1
    runner = runner.replace(
        imports,
        "output.write('\\nfrom . import test_detention_capture\\nfrom . import test_detention_rpc_defaults\\n')",
    )
    files["run.sh"] = runner.encode()
    remote = "/var/tmp/mc-rov-detention-rpc-red-" + uuid.uuid4().hex
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
        phase="rpc-red",
        tests=25,
        expected_missing=1,
        native_controls=24,
        executed=False,
        files={name: sha(data) for name, data in files.items()},
        wire_sha256=sha(wire.encode()),
    )
    (output / "prepared.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    wrapper = (
        (green.parent / "staging-detentions-green.ps1")
        .read_text()
        .replace("kpi-detentions-green", "kpi-detentions-rpc-red")
        .replace("DETENTION_GREEN", "DETENTION_RPC_RED")
        .replace("F2 GREEN", "F2 RPC RED")
        .replace(
            "24 contratos nativos; exige todos verdes",
            "25 casos: un fallo RPC esperado y24contratos anteriores verdes",
        )
        .replace("GREEN no confirmado", "Sondeo RPC no confirmado")
    )
    target = output.parent / "staging-detentions-rpc-red.ps1"
    assert not target.exists()
    target.write_bytes(wrapper.encode())
    ast.parse(files["test_detention_rpc_defaults.py"].decode())
    print("DETENTION_RPC_RED_PREPARED=True TESTS=25 CODE_UNCHANGED=True SSH_EXECUTED=False")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("green", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    prepare(options.green.resolve(), options.output.resolve())
