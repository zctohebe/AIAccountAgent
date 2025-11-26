# Start frontend dev server (PowerShell)
# Usage: .\scripts\start_frontend.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Join-Path $scriptDir '..'
$frontendDir = Join-Path $repoRoot 'frontend'

if (-not (Test-Path $frontendDir)) {
    Write-Error "Frontend directory not found: $frontendDir"
    exit 1
}

# Start server from frontend directory but do not change current process working directory
$port = 8080
Write-Host "Starting simple HTTP server at http://0.0.0.0:$port (launched in background)"

# Use Start-Process to run server with working directory set, but leave current directory unchanged
$pythonCmd = $null
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = 'python3'
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = 'python'
} else {
    Write-Error "No python executable found in PATH. Install Python or add it to PATH."
    exit 1
}

Start-Process -FilePath $pythonCmd -ArgumentList '-m','http.server',$port -WorkingDirectory $frontendDir
Write-Host "Frontend server started in background. Current directory remains: $(Get-Location)"
