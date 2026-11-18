param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$package = Join-Path $PSScriptRoot 'kpi-detentions-races'
$python = $(if ($env:MC_ROV_QA_PYTHON) { $env:MC_ROV_QA_PYTHON } else { "python" })
$seal = [IO.File]::ReadAllText((Join-Path $package 'access-files.json')) | ConvertFrom-Json
foreach ($file in $seal.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $package $file.Name)).Hash.ToLowerInvariant() -ne $file.Value) { throw 'Cambio el acceso; no se conecto por SSH.' }
}
& $python (Join-Path $package 'access_prepare.py') --check
if ($LASTEXITCODE -ne 0) { throw 'Paquete modificado; no se conecto por SSH.' }
if ($CheckOnly) { return }
$metadata = [IO.File]::ReadAllText((Join-Path $package 'prepared.json')) | ConvertFrom-Json
if ($metadata.phase -eq 'events-characterization') {
    Write-Host 'Autoriza acceso F2 temporal: dos horas, sondeo de 45 casos de cierre MRP. Producto v3 intacto.'
    Write-Host 'Caracteriza ausencias concretas; no instala una correccion ni repite las ocho carreras ya aprobadas.'
} elseif ($metadata.phase -eq 'events-green') {
    Write-Host 'Autoriza acceso F2 temporal: dos horas, los mismos 45 contratos y diez carreras.'
    Write-Host 'Prueba la correccion de cierre por movimientos solo en otra copia; no activa datos reales.'
} elseif ($metadata.phase -eq 'interface-red') {
    Write-Host 'Autoriza acceso F2 temporal: dos horas, RED de interfaz y tablero; 69 casos exactos.'
    Write-Host 'Exige 24 ausencias concretas y 45 controles verdes. No instala interfaz ni repite carreras aprobadas.'
} elseif ($metadata.phase -eq 'interface-green') {
    Write-Host 'Autoriza acceso F2 temporal: dos horas, 69 contratos y diez carreras en copia privada.'
    Write-Host 'Valida registro, historial y tablero F2 con el codigo candidato.'
} elseif ($metadata.phase -eq 'interface-browser') {
    Write-Host 'Autoriza acceso F2 temporal: dos horas, siete pruebas de navegador, HOOT y regresion integral.'
    Write-Host 'Descarga herramientas verificadas a la copia temporal. Odoo y el navegador usan solo loopback en una red privada.'
} else { Write-Host 'Autoriza acceso F2 temporal: dos horas, un lote de 35 controles y ocho carreras.' }
Write-Host 'Solo copia nueva con PostgreSQL privado. Sin consola ni tuneles; no instala ni reinicia STAGING/produccion.'
Write-Host 'Este paso solo prepara el acceso. Introduce SSH aqui una vez; no pegues la clave en el chat.'
& $python (Join-Path $package 'access_prepare.py') --activate
if ($LASTEXITCODE -ne 0) { throw 'Preparacion fallida; no se conecto por SSH. No repetir sin diagnosticar.' }
$folder = Join-Path $package 'temporary-access'
$wire = [IO.File]::ReadAllText((Join-Path $folder 'bootstrap.sh'))
if ($env:MC_ROV_QA_SSH_TARGET -cnotmatch '\Aroot@[A-Za-z0-9.-]+\z') { throw 'Configura MC_ROV_QA_SSH_TARGET con el destino de QA autorizado.' }
$previous = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    $result = $wire | & ssh -T -o StrictHostKeyChecking=yes -o ConnectTimeout=30 $env:MC_ROV_QA_SSH_TARGET "tr -d '\015' | bash -s 2>&1" 2>&1
    $code = $LASTEXITCODE
} finally { $ErrorActionPreference = $previous }
$output = ($result | ForEach-Object { $_.ToString() }) -join "`n"
[IO.File]::WriteAllText((Join-Path $folder 'activation-response.txt'), $output, [Text.UTF8Encoding]::new($false))
$output -split "`n" | Where-Object { $_ -match '^F2_TEMPORARY_ACCESS_READY=' } | Write-Host
if ($code -ne 0 -or $output -notmatch '(?m)^F2_TEMPORARY_ACCESS_READY=True ') { throw 'Acceso no confirmado; revisar activation-response.txt. No repetir sin diagnosticar.' }
