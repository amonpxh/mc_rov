param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$package = Join-Path $PSScriptRoot 'kpi-detentions-browser'
$folder = Join-Path $package 'temporary-access'
$metadata = Get-Content -LiteralPath (Join-Path $package 'prepared.json') -Raw | ConvertFrom-Json
$access = Get-Content -LiteralPath (Join-Path $folder 'access.json') -Raw | ConvertFrom-Json
$token = $access.token
if ($metadata.phase -ne 'interface-browser' -or $token -cnotmatch '\A[a-f0-9]{32}\z') {
    throw 'Identificador de lote inválido.'
}
$payload = @'
import fcntl
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

token = sys.argv[1]
assert re.fullmatch(r"[a-f0-9]{32}", token) and os.geteuid() == 0
root = Path("/root/mc-rov-f2-access-" + token)


def guarded(path, kind):
    info = path.lstat()
    assert kind(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
    return info


guarded(root, stat.S_ISDIR)
log, status = root / "result.txt", root / "exit-code"
guarded(status, stat.S_ISREG)
assert guarded(log, stat.S_ISREG).st_size <= 12000000
code = status.read_text().strip()
evidence = log.read_text()
assert re.fullmatch(r"-?[0-9]+", code)
assert "F2_ACCESS_EXIT_CODE=" + code in evidence.splitlines()
assert "DETENTION_BROWSER_PHASE=source-preflight" in evidence.splitlines()
print(evidence, end="", flush=True)

auth = Path("/root/.ssh/authorized_keys")
guarded(auth.parent, stat.S_ISDIR)
guarded(root / "authorized-line", stat.S_ISREG)
line = (root / "authorized-line").read_bytes().rstrip(b"\r\n")
assert line.startswith(b'restrict,expiry-time="')
assert ('/root/mc-rov-f2-access-' + token + '/run.py" ').encode() in line
lock_path = auth.parent / "mc-rov-f2-access.lock"
descriptor = os.open(lock_path, os.O_CREAT | os.O_NOFOLLOW | os.O_WRONLY, 0o600)
with os.fdopen(descriptor, "wb") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    guarded(auth, stat.S_ISREG)
    current = auth.read_bytes()
    remaining = b"".join(row for row in current.splitlines(keepends=True) if row.rstrip(b"\r\n") != line)
    if current != remaining:
        fd, temporary = tempfile.mkstemp(prefix=".f2-revoke-", dir=auth.parent)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(remaining)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, auth)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
print("F2_ACCESS_REVOKED=True", flush=True)
'@
if ($CheckOnly) {
    Write-Host 'F2_BROWSER_RECOVERY_LOCAL=PASSED SSH_EXECUTED=False'
    return
}
Write-Host 'Recupera solo el resultado del lote F2 existente y retira su clave caducada.'
Write-Host 'Introduce SSH solo aqui. No vuelve a ejecutar las pruebas.'
if ($env:MC_ROV_QA_SSH_TARGET -cnotmatch '\Aroot@[A-Za-z0-9.-]+\z') { throw 'Configura MC_ROV_QA_SSH_TARGET con el destino de QA autorizado.' }
$previous = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    $response = $payload | & ssh -T -o StrictHostKeyChecking=yes -o ConnectTimeout=30 $env:MC_ROV_QA_SSH_TARGET "/usr/bin/python3 -I - $token" 2>&1
    $exit = $LASTEXITCODE
} finally { $ErrorActionPreference = $previous }
$output = ($response | ForEach-Object { $_.ToString() }) -join "`n"
$attempt = [Guid]::NewGuid().ToString('N')
$path = Join-Path $folder "recovery-$attempt.txt"
[IO.File]::WriteAllText($path, $output, [Text.UTF8Encoding]::new($false))
$log = [regex]::Match($output, '(?m)^DETENTION_BROWSER_LOG_BEGIN\r?\n([A-Za-z0-9+/=]+)\r?\nDETENTION_BROWSER_LOG_END')
if ($log.Success) {
    [IO.File]::WriteAllBytes((Join-Path $folder "tests-$attempt.log"), [Convert]::FromBase64String($log.Groups[1].Value))
}
$output -split "`n" | Where-Object {
    $_ -match '^(F2_ACCESS|DETENTION_BROWSER|CI_KPI_BROWSER|CI_ODOO_DISCOVERY)' -and $_ -notmatch '^DETENTION_BROWSER_LOG_'
} | Write-Host
if ($exit -ne 0 -or $output -notmatch '(?m)^F2_ACCESS_REVOKED=True\r?$') {
    throw "Recuperación no confirmada ($exit). Evidencia guardada en $path."
}
Write-Host 'F2_BROWSER_RECOVERY=PASSED'
