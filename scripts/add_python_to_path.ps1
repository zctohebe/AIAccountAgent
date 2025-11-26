<#
Adds an installed Python interpreter to the current user's PATH.

Usage:
  - Open PowerShell (no admin required) and run:
      .\scripts\add_python_to_path.ps1

Notes:
  - The script tries several discovery methods (where.exe, py launcher, common install locations).
  - It updates the *User* PATH only via the Win32 environment API. Restart terminal to pick up changes.
  - If Python is not found, install Python from https://www.python.org/ and re-run.
#>

Write-Host "Detecting Python installations..."

$found = $null

try {
    $whereOut = & where.exe python 2>$null
    if ($whereOut) {
        $first = ($whereOut -split "\r?\n")[0].Trim()
        if (Test-Path $first) { $found = $first }
    }
} catch {}

if (-not $found) {
    try {
        $pyExe = & py -c "import sys;print(sys.executable)" 2>$null
        if ($pyExe) { $found = $pyExe.Trim() }
    } catch {}
}

if (-not $found) {
    $candidates = @(
        "$env:LocalAppData\Programs\Python\Python311\python.exe",
        "$env:LocalAppData\Programs\Python\Python310\python.exe",
        "$env:LocalAppData\Programs\Python\Python39\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "$env:ProgramFiles\Python310\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { $found = $p; break }
    }
}

if (-not $found) {
    Write-Host "Python executable not found on this system."
    Write-Host "Please install Python (https://www.python.org/downloads/windows/) and re-run this script."
    exit 1
}

$pythonExe = (Resolve-Path $found).ProviderPath
$pythonDir = Split-Path $pythonExe -Parent
$scriptsDir = Join-Path $pythonDir 'Scripts'

Write-Host "Found Python executable at: $pythonExe"
Write-Host "Python directory: $pythonDir"
Write-Host "Scripts directory: $scriptsDir"

# Read current user PATH (might be null)
$userPath = [Environment]::GetEnvironmentVariable('PATH','User')
if (-not $userPath) { $userPath = "" }

function PathContains($pathValue, $needle) {
    if (-not $pathValue) { return $false }
    $parts = $pathValue -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
    return $parts -contains $needle
}

if (PathContains $userPath $pythonDir -or PathContains $userPath $scriptsDir) {
    Write-Host "User PATH already contains the Python install location. No changes made."
    Write-Host "You may need to restart your terminal for changes to take effect."
    exit 0
}

# Prepend pythonDir and scriptsDir to user PATH so installed Python takes precedence over WindowsApps shim
$prepend = "$pythonDir;$scriptsDir"
$newUserPath = if ($userPath -ne '') { $prepend + ';' + $userPath } else { $prepend }

try {
    [Environment]::SetEnvironmentVariable('PATH', $newUserPath, 'User')
    Write-Host "Successfully added Python to User PATH."
    Write-Host "New (user) PATH entries appended: $append"
    Write-Host "Please restart PowerShell or open a new terminal to apply the change."
    Write-Host 'Verify with: python --version or where.exe python'
    exit 0
} catch {
    Write-Error "Failed to update User PATH: $_"
    exit 2
}
