<#
.SYNOPSIS
Starts the CampusMate API (which also ingests uploaded documents) in its own window, then opens
its interactive documentation. Close the window to stop. There is no UI yet: the frontend was
removed on 2026-09-19 to be rebuilt from scratch.

.EXAMPLE
.\scripts\start-local.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"

Start-Process powershell -WorkingDirectory $backend -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'CampusMate API'; .\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

# Open the API docs once the API is ready (database reachable, migrated).
for ($i = 0; $i -lt 90; $i++) {
    try {
        $ready = Invoke-WebRequest "http://127.0.0.1:8000/api/v1/system/ready" -UseBasicParsing -TimeoutSec 2
        if ($ready.StatusCode -eq 200) { Start-Process "http://127.0.0.1:8000/docs"; exit 0 }
    } catch { }
    Start-Sleep -Seconds 1
}
Write-Warning "CampusMate did not become ready within 90 seconds: look at the 'CampusMate API' window."
