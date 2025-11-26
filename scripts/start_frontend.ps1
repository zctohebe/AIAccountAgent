# Start frontend dev server (PowerShell)
# Usage: .\scripts\start_frontend.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Join-Path $scriptDir '..'
$frontendDir = Join-Path $repoRoot 'frontend'

if (-not (Test-Path $frontendDir)) {
    Write-Error "Frontend directory not found: $frontendDir"
    exit 1
}

Set-Location $frontendDir
$port = 8080
Write-Host "Starting simple HTTP server at http://0.0.0.0:$port"

# Prefer python3 if available
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    python3 -m http.server $port
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m http.server $port
} else {
    Write-Error "No python executable found in PATH. Install Python or add it to PATH."
    exit 1
}
