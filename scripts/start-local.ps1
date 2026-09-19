<#
.SYNOPSIS
Starts CampusMate: the API (which also ingests uploaded documents) and the UI, each in its own
window, then opens the browser. Close the two windows to stop.

.EXAMPLE
.\scripts\start-local.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Push-Location $frontend
    try { npm ci } finally { Pop-Location }
}
Start-Process powershell -WorkingDirectory $backend -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'CampusMate API'; .\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -WorkingDirectory $frontend -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'CampusMate UI'; npm run dev"

# Open the browser once the UI answers and the API behind it is ready (database reachable, migrated).
for ($i = 0; $i -lt 90; $i++) {
    try {
        $ready = Invoke-WebRequest "http://127.0.0.1:5173/api/v1/system/ready" -UseBasicParsing -TimeoutSec 2
        if ($ready.StatusCode -eq 200) { Start-Process "http://127.0.0.1:5173"; exit 0 }
    } catch { }
    Start-Sleep -Seconds 1
}
Write-Warning "CampusMate did not become ready within 90 seconds: look at the 'CampusMate API' window."
