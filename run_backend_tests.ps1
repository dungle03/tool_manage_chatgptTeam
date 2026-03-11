param(
    [string[]]$PytestArgs = @('tests', '-vv')
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir 'backend'

if (-not (Test-Path $backendDir)) {
    throw "Backend directory not found: $backendDir"
}

Push-Location $backendDir
try {
    python -m pytest @PytestArgs
}
finally {
    Pop-Location
}
