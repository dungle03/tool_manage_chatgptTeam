param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir 'backend'
$frontendDir = Join-Path $scriptDir 'frontend'
$backendPython = Join-Path $backendDir 'venv\Scripts\python.exe'

if (-not $SkipBackend) {
    Write-Host '== Backend: ruff check ==' -ForegroundColor Cyan
    Push-Location $scriptDir
    try {
        Invoke-Checked $backendPython -m ruff check backend/app backend/export_workspace_members.py
    }
    finally {
        Pop-Location
    }

    Write-Host '== Backend: pytest ==' -ForegroundColor Cyan
    Push-Location $backendDir
    try {
        Invoke-Checked $backendPython -m pytest
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipFrontend) {
    Write-Host '== Frontend: typecheck ==' -ForegroundColor Cyan
    Push-Location $frontendDir
    try {
        Invoke-Checked 'npm' run typecheck
    }
    finally {
        Pop-Location
    }

    Write-Host '== Frontend: tests ==' -ForegroundColor Cyan
    Push-Location $frontendDir
    try {
        Invoke-Checked 'npm' test
    }
    finally {
        Pop-Location
    }
}
