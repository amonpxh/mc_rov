"""Prepara diez fronteras y el control RPC sobre el producto GREEN24 congelado."""

# Marcadores CLI usados por el operador; no es logging de modelos.
# pylint: disable=unknown-option-value,print-used

import argparse
import ast
import base64
import json
from pathlib import Path
import uuid

from prepare_detention_red import ROOT, sha
from prepare_detention_rpc_red import _verified_green


def prepare(green, output):
    manifest = _verified_green(green)
    assert output.name == "kpi-detentions-boundaries"
    output.mkdir(parents=True, exist_ok=False)
    files = {
        name: (green / name).read_bytes()
        for name in manifest["files"]
        if name not in ("expected.json", "verify_detention_green.py")
    }
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
        runner.replace("DETENTION_GREEN", "DETENTION_BOUNDARIES")
        .replace("detention-green", "detention-boundaries")
        .replace("detention_green_", "detention_boundaries_")
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
    files["run.sh"] = runner.encode()
    remote = "/var/tmp/mc-rov-detention-boundaries-" + uuid.uuid4().hex
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
        phase="boundaries-green",
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
        .replace("kpi-detentions-green", "kpi-detentions-boundaries")
        .replace("DETENTION_GREEN", "DETENTION_BOUNDARIES")
        .replace("F2 GREEN", "F2 FRONTERAS GREEN")
        .replace(
            "24 contratos nativos; exige todos verdes",
            "35 contratos nativos; exige todos verdes",
        )
        .replace("GREEN no confirmado", "Fronteras no confirmadas")
    )
    target = output.parent / "staging-detentions-boundaries.ps1"
    assert not target.exists()
    target.write_bytes(wrapper.encode())
    ast.parse(files["test_detention_rpc_defaults.py"].decode())
    print("DETENTION_BOUNDARIES_PREPARED=True TESTS=35 CODE_UNCHANGED=True SSH_EXECUTED=False")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("green", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    prepare(options.green.resolve(), options.output.resolve())
