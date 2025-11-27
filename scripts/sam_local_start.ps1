# Start SAM local API for development (PowerShell)
# Usage: .\scripts\sam_local_start.ps1 [-Port <port>] [-EnvFile <path>]
param(
  [int]$Port = 8000,
  [string]$EnvFile = ''
)

function Check-Command($name){
  return (Get-Command $name -ErrorAction SilentlyContinue) -ne $null
}

if (-not (Check-Command 'sam')){
  Write-Error "SAM CLI not found. Install from https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
  exit 1
}
if (-not (Check-Command 'docker')){
  Write-Warning "Docker not found or not in PATH. SAM local requires Docker to run Lambda functions. Install and start Docker Desktop."
}

Write-Host "Building SAM application..."
sam build
if ($LASTEXITCODE -ne 0){
  Write-Error "sam build failed"
  exit $LASTEXITCODE
}

$cmd = "sam local start-api --port $Port"
if ($EnvFile -ne ''){
  if (-not (Test-Path $EnvFile)){
    Write-Warning "Env file not found: $EnvFile. Ignoring."
  } else {
    $cmd += " --env-vars `"$EnvFile`""
  }
}

Write-Host "Starting SAM local API on port $Port"
Write-Host "Command: $cmd"
Invoke-Expression $cmd
