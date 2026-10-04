# Wrapper para scheduler: limpieza Media PENDING vencidos.
$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $BackendRoot
$env:FLASK_APP = "run.py"
& python -m app.domains.media.pipelines.cleanup_pending_media @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
