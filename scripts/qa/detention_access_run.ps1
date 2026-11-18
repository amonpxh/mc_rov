param([Parameter(Mandatory=$true)][ValidateSet('run-f2','status-f2','revoke-f2')][string]$Action)
$ErrorActionPreference = 'Stop'
$package = Join-Path $PSScriptRoot 'kpi-detentions-races'
$folder = Join-Path $package 'temporary-access'
$key = Join-Path $folder 'id_ed25519'
if (-not (Test-Path -LiteralPath $key -PathType Leaf)) { throw 'Falta activar el acceso temporal.' }
if ($env:MC_ROV_QA_SSH_TARGET -cnotmatch '\Aroot@[A-Za-z0-9.-]+\z') { throw 'Configura MC_ROV_QA_SSH_TARGET con el destino de QA autorizado.' }
$previous = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    $response = & ssh -T -i $key -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=30 $env:MC_ROV_QA_SSH_TARGET $Action 2>&1
    $code = $LASTEXITCODE
} finally { $ErrorActionPreference = $previous }
$output = ($response | ForEach-Object { $_.ToString() }) -join "`n"
$attempt = [Guid]::NewGuid().ToString('N')
[IO.File]::WriteAllText((Join-Path $folder "$Action-$attempt.txt"), $output, [Text.UTF8Encoding]::new($false))
$log = [regex]::Match($output, '(?m)^DETENTION_RACES_LOG_BEGIN\r?\n([A-Za-z0-9+/=]+)\r?\nDETENTION_RACES_LOG_END')
if ($log.Success) { [IO.File]::WriteAllBytes((Join-Path $folder "tests-$attempt.log"), [Convert]::FromBase64String($log.Groups[1].Value)) }
$output -split "`n" | Where-Object { $_ -match '^(F2_ACCESS|DETENTION_RACES)' -and $_ -notmatch '^DETENTION_RACES_LOG_' } | Write-Host
if ($code -ne 0) { throw "Acceso remoto fallo: $code. Revisar evidencia de este intento; no repetir run-f2." }
if ($Action -eq 'run-f2' -and $output -notmatch '(?m)^F2_ACCESS_STARTED=True\r?$') { throw 'Inicio no confirmado; consultar estado antes de cualquier otra accion.' }
if ($Action -eq 'revoke-f2' -and $output -notmatch '(?m)^F2_ACCESS_REVOKED=True\r?$') { throw 'Revocacion no confirmada.' }
