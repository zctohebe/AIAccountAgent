<#
Publish current project to GitHub.

Usage examples:
  # interactive (prompts for repo name)
  .\scripts\publish_to_github.ps1

  # non-interactive
  .\scripts\publish_to_github.ps1 -RepoName "YOUR_NAME/REPO" -Visibility public

Notes:
- If `gh` CLI is installed and authenticated, the script will use it to create the repo and push.
- If `gh` is not available, the script will show the manual git commands you can run after creating a repo on github.com.
- The script does NOT store tokens. If you use the REST API you must provide a PAT manually.
#>

param(
    [string]$RepoName = $(Read-Host 'Enter GitHub repo name (format: OWNER/REPO). Leave empty to use current directory name in your account'),
    [ValidateSet('public','private')][string]$Visibility = 'public'
)

function Write-ErrAndExit($msg){ Write-Host $msg -ForegroundColor Red; exit 1 }

Push-Location -Path (Resolve-Path .).Path

# default repo name if blank: use current folder name with no owner (user will provide owner if using gh)
if (-not $RepoName -or $RepoName.Trim() -eq ''){
    $folder = Split-Path -Leaf (Get-Location)
    $RepoName = "$folder"
}

Write-Host "Publishing project from: $(Get-Location)"
Write-Host "Target repo: $RepoName  (visibility: $Visibility)"

# Ensure git present
try{ & git --version > $null } catch { Write-ErrAndExit 'git is not installed or not in PATH. Install git first.' }

# Initialize repo if needed
if (-not (Test-Path .git)){
    Write-Host 'No git repo detected. Initializing...'
    git init
    git add --all
    git commit -m "Initial commit" 2>$null || git commit -m "Initial commit" --allow-empty
    git branch -M main 2>$null
} else {
    Write-Host 'Existing git repo detected.'
}

# If gh available, use it to create the repo and push
try{
    & gh --version > $null
    $hasGh = $true
} catch {
    $hasGh = $false
}

if ($hasGh){
    Write-Host 'gh CLI detected. Creating repository and pushing...'
    # If RepoName contains a slash assume owner/repo, else create repo under your account
    $createArgs = @()
    if ($RepoName -match '/'){ $createArgs += $RepoName } else { $createArgs += $RepoName }
    if ($Visibility -eq 'public'){ $createArgs += '--public' } else { $createArgs += '--private' }
    $createArgs += '--source=.'
    $createArgs += '--remote=origin'
    $createArgs += '--push'

    # Run gh create; gh will prompt for auth if needed
    $cmd = "gh repo create $($createArgs -join ' ')"
    Write-Host "Running: $cmd"
    iex $cmd
    Write-Host 'Done. Repository created and code pushed.' -ForegroundColor Green
    Pop-Location
    exit 0
}

Write-Host 'gh CLI not found. Please create a repository on github.com (use your account or organization).' -ForegroundColor Yellow
Write-Host "After creating the remote repository, run the following commands (replace URL with your repo HTTPS URL):`n"
Write-Host 'git remote add origin https://github.com/OWNER/REPO.git'
Write-Host 'git branch -M main'
Write-Host 'git push -u origin main'

Pop-Location
