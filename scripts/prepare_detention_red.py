"""Prepara RED aislado contra fuente fija; no conecta ni instala producto."""

# Los marcadores son el protocolo de salida de esta herramienta CLI.
# pylint: disable=unknown-option-value,print-used

import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import uuid


ROOT = Path(__file__).resolve().parents[1]
BASE = "f67f9971947a473d7c0ade312361d2d81aa544f0"
CANDIDATE_FILES = (
    "__manifest__.py",
    "models/__init__.py",
    "models/detention_history.py",
    "models/detention_capture.py",
    "models/detention_kpi_metrics.py",
)


def git(*arguments):
    return subprocess.check_output(
        ["git", "-c", "safe.directory=" + ROOT.as_posix(), "-C", str(ROOT), *arguments]
    )


def sha(data):
    return hashlib.sha256(data).hexdigest()


def candidate_archive(base_bytes, overlay):
    """Cinco archivos explícitos; conserva todos los demás objetos de la base fija."""
    assert set(overlay) == set(CANDIDATE_FILES)
    assert all(b"\r" not in data and data.endswith(b"\n") for data in overlay.values())
    output = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(base_bytes)) as original:
        manifest = ast.literal_eval(original.extractfile("__manifest__.py").read().decode())
        candidate = ast.literal_eval(overlay["__manifest__.py"].decode())
        assert manifest["version"] == "19.0.25.8.0"
        assert candidate == {**manifest, "version": "19.0.25.9.0"}
        imports = original.extractfile("models/__init__.py").read().replace(b"\r\n", b"\n")
        assert (
            overlay["models/__init__.py"]
            == imports.rstrip()
            + b"\nfrom . import detention_history\nfrom . import detention_capture\n"
        )
        with tarfile.open(fileobj=output, mode="w") as archive:
            for member in original.getmembers():
                if member.name not in overlay:
                    archive.addfile(
                        member, original.extractfile(member) if member.isfile() else None
                    )
            for name, data in overlay.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mode = 0o644
                archive.addfile(member, io.BytesIO(data))
    return output.getvalue()


def _candidate_files():
    return {name: (ROOT / name).read_bytes().replace(b"\r\n", b"\n") for name in CANDIDATE_FILES}


def _archive_candidate_hashes(data):
    """El recibo describe el archivo congelado, no una segunda lectura del checkout."""
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        return {name: sha(archive.extractfile(name).read()) for name in CANDIDATE_FILES}


def _baseline_hashes():
    baseline = {}
    for name in git("ls-tree", "-r", "--name-only", BASE).decode().splitlines():
        if name.startswith(
            ("models/", "wizards/", "views/", "data/", "security/", "reports/", "static/src/")
        ) or name in ("__manifest__.py", "__init__.py"):
            data = git("show", BASE + ":" + name)
            if Path(name).suffix not in (".ttf", ".png", ".jpg", ".woff", ".woff2"):
                data = data.replace(b"\r\n", b"\n")
            baseline[name] = sha(data)
    return baseline


BASELINE_CHECK = '''"""Conserva origen diagnosticado; nunca confunde ese origen con código de prueba."""
import ast, hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
expected = json.loads(pathlib.Path(sys.argv[2]).read_text())
observed = json.loads(pathlib.Path(sys.argv[3]).read_text())
snapshot_file = pathlib.Path(sys.argv[4])
phase = sys.argv[5]
assert phase in ('before', 'after')
assert ast.literal_eval((root / '__manifest__.py').read_text(encoding='utf-8'))['version'] == observed['manifest_version']
allowed = {row['file']: row['status'] for row in observed['product_mismatches']}
assert len(allowed) == len(observed['product_mismatches'])
actual, differences = {}, {}
for name, digest in expected.items():
    file = root / name
    assert file.resolve().is_relative_to(root), 'Ruta fuera del módulo'
    if not file.exists():
        actual[name] = {'kind': 'missing'}
        differences[name] = 'missing_or_external'
        continue
    assert file.is_file()
    data = file.read_bytes()
    if file.suffix not in ('.ttf', '.png', '.jpg', '.woff', '.woff2'):
        data = data.replace(b'\\r\\n', b'\\n')
    actual[name] = {'kind': 'file', 'sha256': hashlib.sha256(data).hexdigest()}
    if actual[name]['sha256'] != digest:
        differences[name] = 'different_hash'
assert differences == allowed, 'Las diferencias no coinciden con el diagnóstico'
if phase == 'before':
    assert not snapshot_file.exists()
    snapshot_file.write_bytes(json.dumps(actual, sort_keys=True).encode())
else:
    assert json.loads(snapshot_file.read_text()) == actual, 'Cambió un archivo del origen durante la prueba'
'''


def prepare(output, observed_source, phase="red"):
    assert phase in ("red", "green")
    output.mkdir(parents=True, exist_ok=False)
    diagnosis = json.loads(observed_source.read_text(encoding="utf-8-sig"))
    assert diagnosis["read_only"] is True
    assert diagnosis["staging_service"] == {"exit_code": 0, "stdout": "active"}
    assert diagnosis["database_version"] == {"exit_code": 0, "stdout": "19.0.25.2.0"}
    assert diagnosis["manifest_version"] == "19.0.25.2.0"
    assert diagnosis["product_files_checked"] == 168
    assert len(diagnosis["product_mismatches"]) == 28
    source = (ROOT / "tests/test_detention_capture.py").read_bytes()
    cases = [
        (item.name, method.name)
        for item in ast.parse(source.decode("utf-8")).body
        if isinstance(item, ast.ClassDef)
        for method in item.body
        if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
    ]
    assert len(cases) == len(set(cases)) == 24
    assert sum(not name.startswith("test_native_control_") for _, name in cases) == 20
    baseline = _baseline_hashes()
    files = {
        "source.tar": git("archive", "--format=tar", BASE),
        "test_detention_capture.py": source,
        f"verify_detention_{phase}.py": (
            ROOT / f"scripts/ci/verify_detention_{phase}.py"
        ).read_bytes(),
        "run.sh": (ROOT / "scripts/qa/run_detention_red_isolated.sh").read_bytes(),
        "check_baseline.py": BASELINE_CHECK.encode(),
        "baseline.json": (json.dumps(baseline, indent=2) + "\n").encode(),
        "expected.json": (json.dumps(cases, indent=2) + "\n").encode(),
        "observed-source.json": (
            json.dumps(
                {
                    "manifest_version": diagnosis["manifest_version"],
                    "database_version": diagnosis["database_version"]["stdout"],
                    "product_mismatches": diagnosis["product_mismatches"],
                },
                indent=2,
            )
            + "\n"
        ).encode(),
    }
    if phase == "green":
        files["source.tar"] = candidate_archive(files["source.tar"], _candidate_files())
        files["run.sh"] = (
            files["run.sh"]
            .replace(b"DETENTION_RED", b"DETENTION_GREEN")
            .replace(b"detention-red", b"detention-green")
            .replace(b"detention_red_", b"detention_green_")
            .replace(b"verify_detention_red.py", b"verify_detention_green.py")
        )
    remote = f"/var/tmp/mc-rov-detention-{phase}-" + uuid.uuid4().hex
    wire = "set -euo pipefail\numask 077\nmkdir '" + remote + "'\n"
    for name, data in files.items():
        if name != "source.tar":
            assert b"\r" not in data and data.endswith(b"\n"), name + " requiere LF"
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
    receipt = {
        "base": BASE,
        "phase": phase,
        "source_staging_version": "19.0.25.2.0",
        "isolated_test_version": "19.0.25.9.0" if phase == "green" else "19.0.25.8.0",
        "candidate_files": (
            _archive_candidate_hashes(files["source.tar"]) if phase == "green" else {}
        ),
        "tests": 24,
        "expected_missing": 20 if phase == "red" else 0,
        "native_controls": 4,
        "executed": False,
        "files": {name: sha(data) for name, data in files.items()},
        "wire_sha256": sha(wire.encode()),
        "source_product_files": len(baseline),
    }
    (output / "prepared.json").write_bytes((json.dumps(receipt, indent=2) + "\n").encode())
    wrapper = r"""param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$package = Join-Path $PSScriptRoot 'kpi-detentions-red'
$prepared = [IO.File]::ReadAllText((Join-Path $package 'prepared.json')) | ConvertFrom-Json
foreach ($property in $prepared.files.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $package $property.Name)).Hash.ToLowerInvariant() -ne $property.Value) { throw "Cambio el paquete: $($property.Name)" }
}
$wirePath = Join-Path $package 'wire.sh'
if ((Get-FileHash -LiteralPath $wirePath).Hash.ToLowerInvariant() -ne $prepared.wire_sha256) { throw 'Cambio el transporte; no se conecto por SSH.' }
if ($CheckOnly) { Write-Host 'DETENTION_RED_LOCAL=PASSED SSH_EXECUTED=False'; return }
$attempt = [Guid]::NewGuid().ToString('N')
Write-Host 'F2 RED: copia nueva de STAGING y filestore; 20 ausencias y 4 controles nativos.'
Write-Host 'Fuente de datos STAGING 19.0.25.2.0; actualiza solo la copia aislada a codigo validado 19.0.25.8.0.'
Write-Host 'PostgreSQL temporal propio por socket; al terminar bloquea la copia y detiene ese PostgreSQL.'
Write-Host 'Conserva respaldo/copia. Sin red, correo, cron ni HTTP en pruebas.'
Write-Host 'No instala ni reinicia STAGING/produccion; no abre copias QA previas.'
Write-Host 'Introduce SSH solo aqui; no repitas el intento sin diagnosticar.'
$wire = [IO.File]::ReadAllText($wirePath)
if ($env:MC_ROV_QA_SSH_TARGET -cnotmatch '\Aroot@[A-Za-z0-9.-]+\z') { throw 'Configura MC_ROV_QA_SSH_TARGET con el destino de QA autorizado.' }
$previous = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    $response = $wire | & ssh -T -o StrictHostKeyChecking=yes -o ConnectTimeout=30 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 $env:MC_ROV_QA_SSH_TARGET "tr -d '\015' | bash -s 2>&1" 2>&1
    $code = $LASTEXITCODE
} finally { $ErrorActionPreference = $previous }
$output = ($response | ForEach-Object { $_.ToString() }) -join "`n"
[IO.File]::WriteAllText((Join-Path $package "response-$attempt.txt"), $output, [Text.UTF8Encoding]::new($false))
$log = [regex]::Match($output, '(?m)^DETENTION_RED_LOG_BEGIN\r?\n([A-Za-z0-9+/=]+)\r?\nDETENTION_RED_LOG_END')
if ($log.Success) { [IO.File]::WriteAllBytes((Join-Path $package "tests-$attempt.log"), [Convert]::FromBase64String($log.Groups[1].Value)) }
$output -split "`n" | Where-Object { $_ -match '^DETENTION_RED' -and $_ -notmatch '^DETENTION_RED_LOG_' } | Write-Host
if ($code -ne 0 -or $output -notmatch '(?m)^DETENTION_RED=PASSED\r?$' -or $output -notmatch '(?m)^DETENTION_RED_COPY_CONNECTIONS_BLOCKED=True\r?$' -or $output -notmatch '(?m)^DETENTION_RED_PRIVATE_POSTGRES_STOPPED=True\r?$' -or $output -notmatch '(?m)^DETENTION_RED_STAGING_PID_UNCHANGED=True\r?$' -or -not $log.Success) { throw "RED no confirmado. Revisar response-$attempt.txt y tests-$attempt.log; no repetir." }
"""
    if phase == "green":
        wrapper = (
            wrapper.replace("DETENTION_RED", "DETENTION_GREEN")
            .replace("kpi-detentions-red", "kpi-detentions-green")
            .replace("F2 RED", "F2 GREEN")
            .replace(
                "20 ausencias y 4 controles nativos", "24 contratos nativos; exige todos verdes"
            )
            .replace("19.0.25.8.0", "19.0.25.9.0")
            .replace("codigo validado", "candidato F2")
            .replace("RED no confirmado", "GREEN no confirmado")
        )
    if output.name != f"kpi-detentions-{phase}":
        raise ValueError("Nombre de paquete incoherente con la fase")
    wrapper_path = output.parent / f"staging-detentions-{phase}.ps1"
    if wrapper_path.exists():
        raise FileExistsError(wrapper_path)
    wrapper_path.write_bytes(wrapper.encode())
    print(f"DETENTION_{phase.upper()}_PREPARED=True TESTS=24 SSH_EXECUTED=False")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--observed-source", type=Path, required=True)
    parser.add_argument("--phase", choices=("red", "green"), default="red")
    cli_options = parser.parse_args()
    prepare(cli_options.output.resolve(), cli_options.observed_source.resolve(), cli_options.phase)
