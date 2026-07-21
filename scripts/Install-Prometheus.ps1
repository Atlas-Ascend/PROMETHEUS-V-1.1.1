[CmdletBinding()]
param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath $Root).Path
$Venv = Join-Path $Root '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'

foreach ($Command in @('python', 'git', 'codex')) {
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "Required command is unavailable: $Command"
    }
}

Push-Location $Root
try {
    if (-not (Test-Path -LiteralPath $Python)) {
        python -m venv $Venv
        if ($LASTEXITCODE -ne 0) {
            throw 'Python virtual environment creation failed.'
        }
    }

    & $Python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw 'pip upgrade failed.'
    }

    & $Python -m pip install -e .
    if ($LASTEXITCODE -ne 0) {
        throw 'PROMETHEUS editable installation failed.'
    }

    if (-not $SkipTests) {
        & $Python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) {
            throw 'PROMETHEUS installation tests failed.'
        }
    }

    $Launcher = Join-Path $Root 'PROMETHEUS.ps1'
    $LauncherBody = @"
`$ErrorActionPreference = 'Stop'
`$Root = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$Python = Join-Path `$Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath `$Python)) {
    throw 'PROMETHEUS is not installed. Run scripts\Install-Prometheus.ps1.'
}
& `$Python -m prometheus_kernel @args
exit `$LASTEXITCODE
"@
    Set-Content -LiteralPath $Launcher -Value $LauncherBody -Encoding UTF8

    Write-Host ''
    Write-Host '==================================================' -ForegroundColor Green
    Write-Host ' PROMETHEUS V-1.1.1: INSTALLED AND TESTED' -ForegroundColor Green
    Write-Host " Root:     $Root" -ForegroundColor Cyan
    Write-Host " Python:   $Python" -ForegroundColor Cyan
    Write-Host " Launcher: $Launcher" -ForegroundColor Cyan
    Write-Host '==================================================' -ForegroundColor Green
}
finally {
    Pop-Location
}
