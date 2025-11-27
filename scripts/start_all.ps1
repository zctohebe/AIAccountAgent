# Single Windows starter: starts backend in a new PowerShell window and runs frontend in the current window
# Usage: .\scripts\start_all.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Join-Path $scriptDir '..'
$envFile = Join-Path $repoRoot 'env.json'
$backendScript = Join-Path $scriptDir 'start_backend.ps1'
$frontendScript = Join-Path $scriptDir 'start_frontend.ps1'

# Load env.json if present and set environment variables for the process so child processes inherit them
if (Test-Path $envFile) {
    try {
        $jsonText = Get-Content $envFile -Raw
        $envObj = $jsonText | ConvertFrom-Json
        if ($envObj.ChatFunction) {
            Write-Host "Loading environment variables from $envFile (ChatFunction)"
            foreach ($prop in $envObj.ChatFunction.PSObject.Properties) {
                $name = $prop.Name
                $value = $prop.Value
                if ($null -ne $value -and $value -ne '') {
                    Write-Host "  Setting $name"
                    [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
                }
            }
        } else {
            Write-Warning "env.json does not contain a ChatFunction object. Skipping environment injection."
        }
    } catch {
        Write-Warning "Failed to parse env.json: $_. Exception.Message"
    }
} else {
    Write-Warning "env.json not found at $envFile. Ensure environment variables are set or create env.json."
}

# Start backend in a new window (keeps backend logs separate)
if (Test-Path $backendScript) {
    Write-Host "Starting backend in new PowerShell window..."
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-File", $backendScript
} else {
    Write-Warning "Backend start script not found: $backendScript"
}

# Run frontend in the current window to avoid opening a third window
if (Test-Path $frontendScript) {
    Write-Host "Starting frontend in the current PowerShell window..."
    & $frontendScript
} else {
    Write-Warning "Frontend start script not found: $frontendScript"
}

Write-Host "Started services. Backend window opened; frontend running in this window. Backend: http://0.0.0.0:8000, Frontend UI: http://localhost:8080"
