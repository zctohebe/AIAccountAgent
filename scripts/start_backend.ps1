# Start backend dev server (PowerShell)
# Usage: .\scripts\start_backend.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Join-Path $scriptDir '..'
$backendDir = Join-Path $repoRoot 'backend'
$reqFile = Join-Path $backendDir 'requirements.txt'

if (Test-Path $reqFile) {
    Write-Host "Installing Python requirements from $reqFile..."
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        python3 -m pip install -r $reqFile
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python -m pip install -r $reqFile
    } else {
        Write-Warning "No python executable found in PATH. Skipping requirements install."
    }
} else {
    Write-Host "No requirements file found at $reqFile. Skipping install."
}

# Run the backend handler from repository root so relative paths resolve
if (-not (Test-Path $backendDir)) {
    Write-Error "Backend directory not found: $backendDir"
    exit 1
}

Set-Location $repoRoot

if (Get-Command python3 -ErrorAction SilentlyContinue) {
    python3 backend/handler.py
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python backend/handler.py
} else {
    Write-Error "No python executable found in PATH. Install Python or add it to PATH."
    exit 1
}
