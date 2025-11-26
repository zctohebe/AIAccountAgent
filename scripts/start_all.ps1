# Start both backend and frontend (PowerShell)
# Opens two separate PowerShell windows and runs backend and frontend servers.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backendScript = Join-Path $scriptDir 'start_backend.ps1'
$frontendScript = Join-Path $scriptDir 'start_frontend.ps1'

if (Test-Path $backendScript) {
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-File", $backendScript
} else {
    Write-Warning "Backend start script not found: $backendScript"
}

if (Test-Path $frontendScript) {
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-File", $frontendScript
} else {
    Write-Warning "Frontend start script not found: $frontendScript"
}

Write-Host "Started backend and frontend in separate windows. Backend: http://0.0.0.0:8000, Frontend: http://0.0.0.0:8080£¬ UI: http://localhost:8080 "
