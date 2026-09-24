param(
    [string]$ProjectRoot = "",
    [string]$PythonPath = "",
    [string]$LogDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $PythonPath = $venvPython
    } else {
        $PythonPath = "python"
    }
}

if ([string]::IsNullOrWhiteSpace($LogDir)) {
    $LogDir = Join-Path $ProjectRoot "logs\ops"
}
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $LogDir "sync_notificaciones_vencidas_$timestamp.log"

Push-Location $ProjectRoot
try {
    "[$(Get-Date -Format 's')] START sync_notificaciones_vencidas" | Tee-Object -FilePath $logFile -Append
    "ProjectRoot=$ProjectRoot" | Tee-Object -FilePath $logFile -Append
    "PythonPath=$PythonPath" | Tee-Object -FilePath $logFile -Append
    "Command=$PythonPath -m app.domains.actuaciones.pipelines.sync_notificaciones_vencidas" | Tee-Object -FilePath $logFile -Append

    & $PythonPath -m app.domains.actuaciones.pipelines.sync_notificaciones_vencidas 2>&1 | Tee-Object -FilePath $logFile -Append
    $exitCode = $LASTEXITCODE

    "[$(Get-Date -Format 's')] END exit_code=$exitCode" | Tee-Object -FilePath $logFile -Append
    Write-Host "Sync finalizado. exit_code=$exitCode log=$logFile"
    exit $exitCode
}
catch {
    $message = $_.Exception.Message
    "[$(Get-Date -Format 's')] ERROR $message" | Tee-Object -FilePath $logFile -Append
    Write-Error "Error ejecutando sync_notificaciones_vencidas. log=$logFile"
    exit 1
}
finally {
    Pop-Location
}
